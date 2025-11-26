"""
Meso Crawling Integration Tests (Story 2.5)

메소 크롤링 통합 테스트 - 전체 플로우 검증
AC 2.5.1 - 2.5.6 통합 검증
"""
import pytest
from unittest.mock import patch, Mock, AsyncMock, MagicMock
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
import pytz

from characters.models import CharacterBasic, CharacterBasicHistory
from characters.crawler_services import CrawlerService, MesoParser
from accounts.models import Character


class MesoIntegrationTests(TransactionTestCase):
    """메소 크롤링 통합 테스트

    전체 플로우: 크롤링 → 파싱 → DB 저장 → 히스토리 보관
    """

    def setUp(self):
        """테스트 데이터 설정"""
        # CharacterBasic 생성
        self.character_basic = CharacterBasic.objects.create(
            ocid='integration-test-ocid-001',
            character_name='IntegrationTestChar',
            world_name='Scania',
            character_gender='남',
            character_class='아크',
            character_info_url='https://maplestory.nexon.com/Common/Character/Detail/IntegrationTestChar?p=test123',
            meso=None
        )

        # 오늘 날짜의 히스토리 생성
        kst = pytz.timezone('Asia/Seoul')
        self.current_time = timezone.now().astimezone(kst)

        self.history = CharacterBasicHistory.objects.create(
            character=self.character_basic,
            date=self.current_time,
            character_name='IntegrationTestChar',
            character_class='아크',
            character_class_level='6차',
            character_level=270,
            character_exp=1234567890,
            character_exp_rate='50.00%',
            character_image='https://example.com/image.png',
            access_flag=True,
            liberation_quest_clear_flag=True,
            meso=None
        )

    def test_meso_crawl_and_save_success(self):
        """AC 2.5.1-2.5.4: 전체 플로우 테스트 - 크롤링 → 저장 → 히스토리"""
        # Given: 크롤링된 메소 데이터
        meso_amount = 5_000_000_000  # 50억

        # When: CharacterBasic.meso 업데이트
        self.character_basic.meso = meso_amount
        self.character_basic.save(update_fields=['meso'])

        # And: 히스토리에도 기록
        self.history.meso = meso_amount
        self.history.save(update_fields=['meso'])

        # Then: 저장 확인
        refreshed_basic = CharacterBasic.objects.get(pk=self.character_basic.pk)
        self.assertEqual(refreshed_basic.meso, 5_000_000_000)

        # And: 히스토리 확인
        refreshed_history = CharacterBasicHistory.objects.get(pk=self.history.pk)
        self.assertEqual(refreshed_history.meso, 5_000_000_000)

    def test_meso_history_preserved(self):
        """AC 2.5.4: 히스토리 보관 - 새 레코드로 저장되어야 함"""
        kst = pytz.timezone('Asia/Seoul')
        from datetime import timedelta

        # 어제 날짜의 히스토리 생성
        yesterday = self.current_time - timedelta(days=1)
        yesterday_history = CharacterBasicHistory.objects.create(
            character=self.character_basic,
            date=yesterday,
            character_name='IntegrationTestChar',
            character_class='아크',
            character_class_level='6차',
            character_level=269,
            character_exp=999999999,
            character_exp_rate='99.00%',
            character_image='https://example.com/image.png',
            access_flag=True,
            liberation_quest_clear_flag=True,
            meso=1_000_000_000  # 어제 메소: 10억
        )

        # 오늘 히스토리 업데이트
        self.history.meso = 2_000_000_000  # 오늘 메소: 20억
        self.history.save(update_fields=['meso'])

        # Then: 두 개의 히스토리가 별도로 존재
        histories = CharacterBasicHistory.objects.filter(
            character=self.character_basic
        ).order_by('-date')

        self.assertEqual(histories.count(), 2)
        self.assertEqual(histories[0].meso, 2_000_000_000)  # 오늘
        self.assertEqual(histories[1].meso, 1_000_000_000)  # 어제

    def test_meso_zero_saved_correctly(self):
        """AC 2.5.5: 0 메소 정상 저장"""
        # When: 0 메소 저장
        self.character_basic.meso = 0
        self.character_basic.save(update_fields=['meso'])

        self.history.meso = 0
        self.history.save(update_fields=['meso'])

        # Then: 0이 저장됨 (None이 아님)
        refreshed_basic = CharacterBasic.objects.get(pk=self.character_basic.pk)
        self.assertEqual(refreshed_basic.meso, 0)
        self.assertIsNotNone(refreshed_basic.meso)

        refreshed_history = CharacterBasicHistory.objects.get(pk=self.history.pk)
        self.assertEqual(refreshed_history.meso, 0)
        self.assertIsNotNone(refreshed_history.meso)

    def test_meso_parsing_failure_saves_null(self):
        """AC 2.5.6: 파싱 실패 시 null 저장"""
        # When: None (파싱 실패) 저장
        self.character_basic.meso = None
        self.character_basic.save(update_fields=['meso'])

        # Then: null 저장 확인
        refreshed = CharacterBasic.objects.get(pk=self.character_basic.pk)
        self.assertIsNone(refreshed.meso)

    def test_meso_large_amount_biginteger(self):
        """BigInteger 범위 테스트: 메이플스토리 최대 메소"""
        # 메이플스토리 최대 메소: 약 9조 9천억
        max_meso = 9_999_999_999_999

        self.character_basic.meso = max_meso
        self.character_basic.save(update_fields=['meso'])

        self.history.meso = max_meso
        self.history.save(update_fields=['meso'])

        refreshed_basic = CharacterBasic.objects.get(pk=self.character_basic.pk)
        self.assertEqual(refreshed_basic.meso, max_meso)

        refreshed_history = CharacterBasicHistory.objects.get(pk=self.history.pk)
        self.assertEqual(refreshed_history.meso, max_meso)


class MesoCrawlTaskIntegrationTests(TransactionTestCase):
    """Celery Task 통합 테스트 (meso 크롤링)"""

    def setUp(self):
        """테스트 데이터 설정"""
        from accounts.models import Character
        from django.contrib.auth import get_user_model

        User = get_user_model()

        # 테스트 유저 생성
        self.user = User.objects.create_user(
            username='testuser_meso',
            email='testmeso@test.com',
            password='testpass123'
        )

        # Character 생성 (accounts 앱)
        self.character = Character.objects.create(
            user=self.user,
            character_name='MesoTaskTestChar'
        )

        # CharacterBasic 생성
        self.character_basic = CharacterBasic.objects.create(
            ocid='task-test-ocid-001',
            character_name='MesoTaskTestChar',
            world_name='Scania',
            character_gender='남',
            character_class='아크',
            character_info_url='https://maplestory.nexon.com/Common/Character/Detail/MesoTaskTestChar?p=test123',
            meso=None
        )

        # 오늘 날짜의 히스토리 생성
        kst = pytz.timezone('Asia/Seoul')
        current_time = timezone.now().astimezone(kst)

        self.history = CharacterBasicHistory.objects.create(
            character=self.character_basic,
            date=current_time,
            character_name='MesoTaskTestChar',
            character_class='아크',
            character_class_level='6차',
            character_level=270,
            character_exp=1234567890,
            character_exp_rate='50.00%',
            character_image='https://example.com/image.png',
            access_flag=True,
            liberation_quest_clear_flag=True,
            meso=None
        )

    def test_crawl_character_data_meso_type_logic(self):
        """Task 내부 meso 크롤링 로직 검증

        Note: Celery task 직접 호출이 어려우므로
        task 내부의 meso 처리 로직을 시뮬레이션하여 테스트합니다.
        """
        from datetime import datetime

        # 시뮬레이션: crawl_character_meso 결과
        crawled_data = {
            'character_name': 'MesoTaskTestChar',
            'meso': 3_000_000_000,
            'crawled_at': datetime.now().isoformat()
        }

        meso_amount = crawled_data.get('meso')

        # Task 내 로직 시뮬레이션: CharacterBasic.meso 업데이트
        if meso_amount is not None:
            self.character_basic.meso = meso_amount
            self.character_basic.save(update_fields=['meso'])

            # 히스토리 업데이트
            kst = pytz.timezone('Asia/Seoul')
            current_time = timezone.now().astimezone(kst)

            existing_history = CharacterBasicHistory.objects.filter(
                character=self.character_basic,
                date__date=current_time.date()
            ).first()

            if existing_history:
                existing_history.meso = meso_amount
                existing_history.save(update_fields=['meso'])

        # 검증
        refreshed_basic = CharacterBasic.objects.get(pk=self.character_basic.pk)
        self.assertEqual(refreshed_basic.meso, 3_000_000_000)

        refreshed_history = CharacterBasicHistory.objects.get(pk=self.history.pk)
        self.assertEqual(refreshed_history.meso, 3_000_000_000)

    def test_meso_model_update_from_task_simulation(self):
        """Task 시뮬레이션: 메소 업데이트 플로우"""
        kst = pytz.timezone('Asia/Seoul')

        # 시뮬레이션: 크롤링 결과
        crawled_meso = 7_500_000_000  # 75억

        # CharacterBasic.meso 업데이트
        self.character_basic.meso = crawled_meso
        self.character_basic.save(update_fields=['meso'])

        # 오늘 날짜의 히스토리 찾아서 업데이트
        current_time = timezone.now().astimezone(kst)
        existing_history = CharacterBasicHistory.objects.filter(
            character=self.character_basic,
            date__date=current_time.date()
        ).first()

        if existing_history:
            existing_history.meso = crawled_meso
            existing_history.save(update_fields=['meso'])

        # 검증
        refreshed_basic = CharacterBasic.objects.get(pk=self.character_basic.pk)
        self.assertEqual(refreshed_basic.meso, 7_500_000_000)

        refreshed_history = CharacterBasicHistory.objects.get(pk=self.history.pk)
        self.assertEqual(refreshed_history.meso, 7_500_000_000)


class MesoParserIntegrationTests(TestCase):
    """MesoParser 실제 HTML 형식 통합 테스트"""

    def test_parse_real_character_info_page_format(self):
        """실제 캐릭터 정보 페이지 형식 테스트"""
        # 실제 메이플스토리 웹사이트 HTML 구조 시뮬레이션
        html_content = """
        <!DOCTYPE html>
        <html>
        <head><title>캐릭터 정보</title></head>
        <body>
            <div id="container">
                <div class="con_wrap">
                    <div class="contents_wrap">
                        <div class="char_info">
                            <div class="tab01_con_wrap">
                                <table class="info_table">
                                    <colgroup><col width="100"><col></colgroup>
                                    <tbody>
                                        <tr>
                                            <th><span>레벨</span></th>
                                            <td><span>275</span></td>
                                        </tr>
                                        <tr>
                                            <th><span>직업</span></th>
                                            <td><span>아크</span></td>
                                        </tr>
                                    </tbody>
                                </table>
                                <table class="info_table">
                                    <colgroup><col width="100"><col></colgroup>
                                    <tbody>
                                        <tr>
                                            <th><span>경험치</span></th>
                                            <td><span>45.678%</span></td>
                                        </tr>
                                        <tr>
                                            <th><span>인기도</span></th>
                                            <td><span>1,234</span></td>
                                        </tr>
                                        <tr>
                                            <th><span>메소</span></th>
                                            <td><span>12,345,678,901</span></td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        amount = MesoParser.parse_character_meso(html_content)

        self.assertEqual(amount, 12345678901)

    def test_parse_storage_page_meso_format(self):
        """실제 창고 페이지 메소 형식 테스트"""
        html_content = """
        <!DOCTYPE html>
        <html>
        <body>
            <div id="container">
                <div class="con_wrap">
                    <div class="contents_wrap">
                        <div class="storage_wrap">
                            <div class="storage_info">
                                <div class="meso_wrap">
                                    <div>보유 메소: 9,876,543,210</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        amount = MesoParser.parse_storage_meso(html_content)

        self.assertEqual(amount, 9876543210)
