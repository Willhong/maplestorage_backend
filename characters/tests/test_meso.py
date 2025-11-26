"""
Meso Crawling Unit Tests (Story 2.5)

메소 크롤링 및 파싱 관련 단위 테스트
AC 2.5.1 - 2.5.6 검증
"""
import pytest
from unittest.mock import patch, Mock, AsyncMock
from django.test import TestCase
from django.utils import timezone
from pydantic import ValidationError
import pytz

from characters.crawler_services import (
    MesoParser,
    CrawlerService,
    CrawlingError,
    MesoParsingError
)
from characters.models import CharacterBasic, CharacterBasicHistory


class MesoParserTests(TestCase):
    """MesoParser 단위 테스트

    메소 파싱 로직 검증 (AC 2.5.1 - 2.5.6)
    """

    def test_parse_character_meso_success(self):
        """AC 2.5.1: 캐릭터 기본정보 페이지에서 메소 파싱 성공"""
        html_content = """
        <html>
        <body>
            <div id="container">
                <div class="con_wrap">
                    <div class="contents_wrap">
                        <div>
                            <div class="tab01_con_wrap">
                                <table>
                                    <tbody>
                                        <tr>
                                            <th>레벨</th>
                                            <td>270</td>
                                        </tr>
                                    </tbody>
                                </table>
                                <table>
                                    <tbody>
                                        <tr>
                                            <th>경험치</th>
                                            <td>50%</td>
                                        </tr>
                                        <tr>
                                            <th>인기도</th>
                                            <td>100</td>
                                        </tr>
                                        <tr>
                                            <th>메소</th>
                                            <td><span>1,234,567,890</span></td>
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

        self.assertEqual(amount, 1234567890)

    def test_parse_meso_with_commas(self):
        """AC 2.5.2: 쉼표 제거 후 정수 변환"""
        html_content = """
        <table>
            <tr>
                <th>메소</th>
                <td><span>100,000,000</span></td>
            </tr>
        </table>
        """

        amount = MesoParser.parse_character_meso(html_content)

        self.assertEqual(amount, 100000000)

    def test_parse_meso_zero(self):
        """AC 2.5.5: 0 메소 정상 처리"""
        html_content = """
        <table>
            <tr>
                <th>메소</th>
                <td><span>0</span></td>
            </tr>
        </table>
        """

        amount = MesoParser.parse_character_meso(html_content)

        self.assertEqual(amount, 0)

    def test_parse_meso_large_amount(self):
        """BigInteger 지원: 큰 금액 처리 (억 단위)"""
        html_content = """
        <table>
            <tr>
                <th>메소</th>
                <td><span>9,999,999,999,999</span></td>
            </tr>
        </table>
        """

        amount = MesoParser.parse_character_meso(html_content)

        self.assertEqual(amount, 9999999999999)

    def test_parse_meso_failure_returns_none(self):
        """AC 2.5.6: 파싱 실패 시 None 반환"""
        html_content = """
        <html>
            <body>
                <p>No meso information here</p>
            </body>
        </html>
        """

        amount = MesoParser.parse_character_meso(html_content)

        self.assertIsNone(amount)

    def test_parse_storage_meso_success(self):
        """창고 메소 파싱 성공"""
        html_content = """
        <div id="container">
            <div class="con_wrap">
                <div class="contents_wrap">
                    <div>
                        <div>
                            <div>
                                <div>메소: 5,000,000</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        """

        amount = MesoParser.parse_storage_meso(html_content)

        self.assertEqual(amount, 5000000)

    def test_extract_meso_amount_from_text(self):
        """_extract_meso_amount 메서드 직접 테스트"""
        # 정상 케이스
        self.assertEqual(MesoParser._extract_meso_amount("1,234,567"), 1234567)
        self.assertEqual(MesoParser._extract_meso_amount("100"), 100)
        self.assertEqual(MesoParser._extract_meso_amount("0"), 0)

        # 메소 텍스트 포함
        self.assertEqual(MesoParser._extract_meso_amount("1,234 메소"), 1234)
        self.assertEqual(MesoParser._extract_meso_amount("메소: 5,000"), 5000)

        # 공백 처리
        self.assertEqual(MesoParser._extract_meso_amount("  1,000  "), 1000)

        # 실패 케이스
        self.assertIsNone(MesoParser._extract_meso_amount(""))
        self.assertIsNone(MesoParser._extract_meso_amount(None))
        self.assertIsNone(MesoParser._extract_meso_amount("no numbers"))

    def test_parse_meso_fallback_to_table_search(self):
        """Fallback: CSS selector 실패 시 테이블 검색"""
        html_content = """
        <html>
        <body>
            <table class="info_table">
                <tr>
                    <th><span>메소</span></th>
                    <td><span>999,999</span></td>
                </tr>
            </table>
        </body>
        </html>
        """

        amount = MesoParser.parse_character_meso(html_content)

        self.assertEqual(amount, 999999)


class MesoModelTests(TestCase):
    """CharacterBasic.meso 및 CharacterBasicHistory.meso 모델 테스트"""

    def setUp(self):
        """테스트 데이터 설정"""
        self.character_basic = CharacterBasic.objects.create(
            ocid='test-ocid-meso-001',
            character_name='TestMesoChar',
            world_name='Scania',
            character_gender='남',
            character_class='아크',
            meso=None
        )

    def test_character_basic_meso_field(self):
        """AC 2.5.3: CharacterBasic.meso 필드 테스트"""
        # 메소 저장
        self.character_basic.meso = 1234567890
        self.character_basic.save()

        # 조회 확인
        refreshed = CharacterBasic.objects.get(pk=self.character_basic.pk)
        self.assertEqual(refreshed.meso, 1234567890)

    def test_character_basic_meso_zero(self):
        """AC 2.5.5: 0 메소 정상 저장"""
        self.character_basic.meso = 0
        self.character_basic.save()

        refreshed = CharacterBasic.objects.get(pk=self.character_basic.pk)
        self.assertEqual(refreshed.meso, 0)

    def test_character_basic_meso_null(self):
        """AC 2.5.6: 파싱 실패 시 null 저장"""
        self.character_basic.meso = None
        self.character_basic.save()

        refreshed = CharacterBasic.objects.get(pk=self.character_basic.pk)
        self.assertIsNone(refreshed.meso)

    def test_character_basic_meso_large_amount(self):
        """BigInteger 테스트: 큰 금액 저장"""
        large_meso = 9_999_999_999_999  # 약 10조
        self.character_basic.meso = large_meso
        self.character_basic.save()

        refreshed = CharacterBasic.objects.get(pk=self.character_basic.pk)
        self.assertEqual(refreshed.meso, large_meso)

    def test_character_basic_history_meso_field(self):
        """AC 2.5.4: CharacterBasicHistory.meso 필드 테스트 - 히스토리 보관"""
        kst = pytz.timezone('Asia/Seoul')
        current_time = timezone.now().astimezone(kst)

        # 히스토리 생성 with meso
        history = CharacterBasicHistory.objects.create(
            character=self.character_basic,
            date=current_time,
            character_name='TestMesoChar',
            character_class='아크',
            character_class_level='6차',
            character_level=270,
            character_exp=1234567890,
            character_exp_rate='50.00%',
            character_image='https://example.com/image.png',
            access_flag=True,
            liberation_quest_clear_flag=True,
            meso=5_000_000_000  # 50억
        )

        # 조회 확인
        refreshed = CharacterBasicHistory.objects.get(pk=history.pk)
        self.assertEqual(refreshed.meso, 5_000_000_000)

    def test_meso_history_update(self):
        """기존 히스토리 meso 업데이트 테스트"""
        kst = pytz.timezone('Asia/Seoul')
        current_time = timezone.now().astimezone(kst)

        # 히스토리 생성 (초기 meso = None)
        history = CharacterBasicHistory.objects.create(
            character=self.character_basic,
            date=current_time,
            character_name='TestMesoChar',
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

        self.assertIsNone(history.meso)

        # meso 업데이트
        history.meso = 1_000_000_000
        history.save(update_fields=['meso'])

        refreshed = CharacterBasicHistory.objects.get(pk=history.pk)
        self.assertEqual(refreshed.meso, 1_000_000_000)


class CrawlerServiceMesoTests(TestCase):
    """CrawlerService.crawl_character_meso 단위 테스트"""

    @patch('playwright.async_api.async_playwright')
    def test_crawl_character_meso_success(self, mock_playwright):
        """AC 2.5.1-2.5.3: 캐릭터 메소 크롤링 성공"""
        import asyncio

        # Mock HTML response
        mock_html = """
        <table>
            <tr>
                <th>메소</th>
                <td><span>1,234,567,890</span></td>
            </tr>
        </table>
        """

        # Mock playwright
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()

        mock_page.goto = AsyncMock(return_value=Mock(ok=True, status=200))
        mock_page.wait_for_selector = AsyncMock()
        mock_page.content = AsyncMock(return_value=mock_html)

        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()

        mock_playwright_instance = AsyncMock()
        mock_playwright_instance.chromium.launch = AsyncMock(return_value=mock_browser)

        mock_playwright.return_value.__aenter__.return_value = mock_playwright_instance

        # Execute
        crawler = CrawlerService()
        result = asyncio.run(
            crawler.crawl_character_meso('http://test.url', 'TestChar')
        )

        # Verify
        self.assertEqual(result['character_name'], 'TestChar')
        self.assertEqual(result['meso'], 1234567890)
        self.assertIn('crawled_at', result)

    @patch('playwright.async_api.async_playwright')
    def test_crawl_character_meso_zero(self, mock_playwright):
        """AC 2.5.5: 0 메소 크롤링"""
        import asyncio

        mock_html = """
        <table>
            <tr><th>메소</th><td><span>0</span></td></tr>
        </table>
        """

        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()

        mock_page.goto = AsyncMock(return_value=Mock(ok=True, status=200))
        mock_page.wait_for_selector = AsyncMock()
        mock_page.content = AsyncMock(return_value=mock_html)

        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()

        mock_playwright_instance = AsyncMock()
        mock_playwright_instance.chromium.launch = AsyncMock(return_value=mock_browser)

        mock_playwright.return_value.__aenter__.return_value = mock_playwright_instance

        crawler = CrawlerService()
        result = asyncio.run(
            crawler.crawl_character_meso('http://test.url', 'TestChar')
        )

        self.assertEqual(result['meso'], 0)

    @patch('playwright.async_api.async_playwright')
    def test_crawl_character_meso_parsing_failure(self, mock_playwright):
        """AC 2.5.6: 파싱 실패 시 None 반환"""
        import asyncio

        mock_html = "<html><body>No meso info</body></html>"

        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()

        mock_page.goto = AsyncMock(return_value=Mock(ok=True, status=200))
        mock_page.wait_for_selector = AsyncMock()
        mock_page.content = AsyncMock(return_value=mock_html)

        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()

        mock_playwright_instance = AsyncMock()
        mock_playwright_instance.chromium.launch = AsyncMock(return_value=mock_browser)

        mock_playwright.return_value.__aenter__.return_value = mock_playwright_instance

        crawler = CrawlerService()
        result = asyncio.run(
            crawler.crawl_character_meso('http://test.url', 'TestChar')
        )

        self.assertIsNone(result['meso'])
