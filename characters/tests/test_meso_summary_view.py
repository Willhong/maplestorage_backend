"""
Meso Summary View Tests (Story 4.3)

메소 요약 API 테스트
사용자의 모든 캐릭터와 창고의 메소를 집계하여 반환하는 API를 검증합니다.
"""
import pytest
from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.utils import timezone

from accounts.models import Character
from characters.models import CharacterBasic, Storage


class MesoSummaryViewTests(TestCase):
    """
    메소 요약 뷰 테스트 (Story 4.3)

    사용자의 전체 메소 요약 조회 API를 검증합니다.
    """

    def setUp(self):
        """테스트 데이터 설정"""
        # 사용자 생성
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            password='otherpass123'
        )

        # API 클라이언트 설정
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        # URL
        self.url = reverse('meso-summary')

        # 캐릭터 및 CharacterBasic 생성
        self.char1_ocid = 'test-ocid-001'
        self.char2_ocid = 'test-ocid-002'
        self.char3_ocid = 'test-ocid-003'

        # 사용자의 캐릭터 생성
        Character.objects.create(
            user=self.user,
            ocid=self.char1_ocid,
            character_name='윌홍',
            world_name='스카니아',
            character_class='나이트로드',
            character_level=250
        )
        Character.objects.create(
            user=self.user,
            ocid=self.char2_ocid,
            character_name='부캐',
            world_name='스카니아',
            character_class='아크',
            character_level=230
        )

        # 다른 사용자의 캐릭터
        Character.objects.create(
            user=self.other_user,
            ocid=self.char3_ocid,
            character_name='타인캐릭',
            world_name='베라',
            character_class='제로',
            character_level=200
        )

        # CharacterBasic 데이터 생성 (메소 포함)
        self.char1_basic = CharacterBasic.objects.create(
            ocid=self.char1_ocid,
            character_name='윌홍',
            world_name='스카니아',
            character_gender='남',
            character_class='나이트로드',
            character_level=250,
            meso=500_000_000  # 5억
        )
        self.char2_basic = CharacterBasic.objects.create(
            ocid=self.char2_ocid,
            character_name='부캐',
            world_name='스카니아',
            character_gender='여',
            character_class='아크',
            character_level=230,
            meso=300_000_000  # 3억
        )
        CharacterBasic.objects.create(
            ocid=self.char3_ocid,
            character_name='타인캐릭',
            world_name='베라',
            character_gender='남',
            character_class='제로',
            character_level=200,
            meso=1_000_000_000  # 10억 (다른 사용자)
        )

        # 창고 메소 생성 (계정 공유)
        self.storage = Storage.objects.create(
            character_basic=self.char1_basic,
            storage_type='shared',
            item_name='더미 아이템',
            item_icon='https://example.com/icon.png',
            quantity=1,
            slot_position=1,
            meso=234_567_890,  # 창고 메소
            crawled_at=timezone.now()
        )

    def test_authentication_required(self):
        """인증되지 않은 사용자는 접근할 수 없음"""
        client = APIClient()  # 인증 없는 클라이언트
        response = client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_meso_summary_success(self):
        """정상적인 메소 요약 조회"""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # 총 메소 = 캐릭터 메소 + 창고 메소
        expected_character_total = 500_000_000 + 300_000_000  # 8억
        expected_storage_meso = 234_567_890
        expected_total = expected_character_total + expected_storage_meso

        self.assertEqual(data['total_meso'], expected_total)
        self.assertEqual(data['character_meso_total'], expected_character_total)
        self.assertEqual(data['storage_meso'], expected_storage_meso)

    def test_character_list_in_summary(self):
        """캐릭터 목록이 올바르게 반환됨"""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # 캐릭터 수 확인
        self.assertEqual(len(data['characters']), 2)

        # 첫 번째 캐릭터 확인 (메소 기준 내림차순 정렬)
        char1 = data['characters'][0]
        self.assertEqual(char1['ocid'], self.char1_ocid)
        self.assertEqual(char1['character_name'], '윌홍')
        self.assertEqual(char1['world_name'], '스카니아')
        self.assertEqual(char1['meso'], 500_000_000)
        self.assertEqual(char1['character_class'], '나이트로드')
        self.assertEqual(char1['character_level'], 250)

    def test_storage_meso_in_summary(self):
        """창고 메소 정보가 올바르게 반환됨"""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        storage_data = data['storage']
        self.assertEqual(storage_data['meso'], 234_567_890)
        self.assertIsNotNone(storage_data['last_updated'])

    def test_null_meso_handled_as_zero(self):
        """NULL 메소는 0으로 처리"""
        # 메소가 NULL인 캐릭터 생성
        char4_ocid = 'test-ocid-004'
        Character.objects.create(
            user=self.user,
            ocid=char4_ocid,
            character_name='메소없는캐릭',
            world_name='스카니아'
        )
        CharacterBasic.objects.create(
            ocid=char4_ocid,
            character_name='메소없는캐릭',
            world_name='스카니아',
            character_gender='남',
            character_class='데몬슬레이어',
            character_level=100,
            meso=None  # NULL
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # NULL은 0으로 처리되어 합계에 영향 없음
        expected_total = 500_000_000 + 300_000_000 + 0 + 234_567_890
        self.assertEqual(data['total_meso'], expected_total)

        # 캐릭터 목록에서 meso가 0으로 표시됨
        char4_data = next(
            (c for c in data['characters'] if c['ocid'] == char4_ocid),
            None
        )
        self.assertIsNotNone(char4_data)
        self.assertEqual(char4_data['meso'], 0)

    def test_no_characters_returns_empty_summary(self):
        """캐릭터가 없는 사용자는 빈 요약 반환"""
        # 새로운 사용자 (캐릭터 없음)
        new_user = User.objects.create_user(
            username='newuser',
            password='newpass123'
        )
        client = APIClient()
        client.force_authenticate(user=new_user)

        response = client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertEqual(data['total_meso'], 0)
        self.assertEqual(data['character_meso_total'], 0)
        self.assertEqual(data['storage_meso'], 0)
        self.assertEqual(len(data['characters']), 0)
        self.assertEqual(data['storage']['meso'], 0)
        self.assertIsNone(data['storage']['last_updated'])

    def test_sort_by_meso_desc(self):
        """메소 기준 내림차순 정렬 (기본값)"""
        response = self.client.get(self.url, {'sort': 'meso', 'order': 'desc'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # 메소가 많은 순서: 윌홍(5억) > 부캐(3억)
        self.assertEqual(data['characters'][0]['character_name'], '윌홍')
        self.assertEqual(data['characters'][1]['character_name'], '부캐')

    def test_sort_by_meso_asc(self):
        """메소 기준 오름차순 정렬"""
        response = self.client.get(self.url, {'sort': 'meso', 'order': 'asc'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # 메소가 적은 순서: 부캐(3억) > 윌홍(5억)
        self.assertEqual(data['characters'][0]['character_name'], '부캐')
        self.assertEqual(data['characters'][1]['character_name'], '윌홍')

    def test_sort_by_name(self):
        """이름 기준 정렬"""
        response = self.client.get(self.url, {'sort': 'name', 'order': 'asc'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # 이름 오름차순: 부캐 < 윌홍
        self.assertEqual(data['characters'][0]['character_name'], '부캐')
        self.assertEqual(data['characters'][1]['character_name'], '윌홍')

    def test_sort_by_level(self):
        """레벨 기준 정렬"""
        response = self.client.get(self.url, {'sort': 'level', 'order': 'desc'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # 레벨 내림차순: 윌홍(250) > 부캐(230)
        self.assertEqual(data['characters'][0]['character_level'], 250)
        self.assertEqual(data['characters'][1]['character_level'], 230)

    def test_invalid_sort_field_defaults_to_meso(self):
        """잘못된 정렬 필드는 기본값(meso)으로 처리"""
        response = self.client.get(self.url, {'sort': 'invalid_field'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # 기본 정렬(메소 내림차순) 적용됨
        self.assertEqual(data['characters'][0]['character_name'], '윌홍')

    def test_invalid_sort_order_defaults_to_desc(self):
        """잘못된 정렬 순서는 기본값(desc)으로 처리"""
        response = self.client.get(self.url, {'sort': 'meso', 'order': 'invalid'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # 기본 순서(내림차순) 적용됨
        self.assertEqual(data['characters'][0]['character_name'], '윌홍')

    def test_storage_meso_account_shared(self):
        """창고 메소는 계정 공유 - 중복 집계 안 됨"""
        # 두 번째 캐릭터에도 창고 메소 추가 (동일 사용자)
        Storage.objects.create(
            character_basic=self.char2_basic,
            storage_type='shared',
            item_name='더미 아이템2',
            item_icon='https://example.com/icon2.png',
            quantity=1,
            slot_position=2,
            meso=100_000_000,  # 추가 창고 메소
            crawled_at=timezone.now()
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # 가장 최근 크롤링된 창고 메소만 사용 (중복 집계 안 됨)
        # 두 Storage 레코드 중 최신 것의 메소만 포함
        storage_meso = data['storage_meso']
        self.assertIn(storage_meso, [234_567_890, 100_000_000])

    def test_only_user_characters_included(self):
        """본인 캐릭터만 포함됨 (다른 사용자 캐릭터 제외)"""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # 본인 캐릭터 2개만 포함됨
        self.assertEqual(len(data['characters']), 2)
        character_names = [c['character_name'] for c in data['characters']]
        self.assertIn('윌홍', character_names)
        self.assertIn('부캐', character_names)
        self.assertNotIn('타인캐릭', character_names)

    def test_last_updated_field_present(self):
        """last_updated 필드가 존재함"""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertIn('last_updated', data)
        self.assertIsNotNone(data['last_updated'])

    def test_multiple_storage_entries_uses_latest(self):
        """여러 창고 크롤링 기록 중 최신 것만 사용"""
        # 과거 창고 메소
        past_time = timezone.now() - timezone.timedelta(hours=2)
        Storage.objects.create(
            character_basic=self.char1_basic,
            storage_type='shared',
            item_name='과거 아이템',
            item_icon='https://example.com/icon_old.png',
            quantity=1,
            slot_position=10,
            meso=50_000_000,  # 과거 메소
            crawled_at=past_time
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # 최신 창고 메소(234_567_890)가 사용됨
        self.assertEqual(data['storage_meso'], 234_567_890)
