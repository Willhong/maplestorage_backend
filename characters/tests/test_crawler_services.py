"""
Unit tests for CrawlerService and InventoryParser (Story 2.3)

테스트 실행: uv run python manage.py test characters.tests.test_crawler_services
"""
import pytest
import asyncio
from django.test import TestCase
from unittest.mock import Mock, patch, AsyncMock
from characters.crawler_services import CrawlerService, InventoryParser, CrawlingError, ParsingError


class InventoryParserTests(TestCase):
    """InventoryParser 단위 테스트 (AC 2.3.2 - 2.3.5)"""

    def test_parse_inventory_success(self):
        """AC 2.3.2: 인벤토리 HTML 파싱 성공 (레거시 HTML 형식)"""
        # 실제 메이플스토리 웹사이트 HTML 구조 기반 Mock
        html = """
        <div class="inven_list">
            <div class="inven_item_img">
                <img src="//avatar.maplestory.nexon.com/ItemIcon/KEODIEPC.png" />
                <h1><a href="/MyMaple/Item/Detail?itemId=12345">엘릭서&nbsp;(100개)</a></h1>
            </div>
            <div class="inven_item_img">
                <img src="//avatar.maplestory.nexon.com/ItemIcon/ABCDEFGH.png" />
                <h1><a href="/MyMaple/Item/Detail?itemId=67890">파워 엘릭서</a></h1>
            </div>
        </div>
        """

        items = InventoryParser.parse_inventory(html)

        # AC 2.3.3: 아이템 정보 추출 확인
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]['item_name'], '엘릭서')
        self.assertEqual(items[0]['quantity'], 100)
        self.assertEqual(items[1]['item_name'], '파워 엘릭서')
        self.assertEqual(items[1]['quantity'], 1)  # 수량 없으면 기본값 1

    def test_parse_inventory_empty(self):
        """빈 인벤토리 파싱"""
        html = '<div class="inventory"></div>'
        items = InventoryParser.parse_inventory(html)
        self.assertEqual(len(items), 0)

    def test_parse_inventory_invalid_html(self):
        """잘못된 HTML 파싱 실패"""
        html = 'invalid html content'
        # 파싱 에러는 발생하지 않지만 빈 리스트 반환
        items = InventoryParser.parse_inventory(html)
        self.assertEqual(len(items), 0)

    def test_parse_single_item_full(self):
        """AC 2.3.3: 아이템 데이터 파싱 (모든 필드)"""
        item_html = """
        <div class="inven_item_img">
            <img src="//avatar.maplestory.nexon.com/ItemIcon/KEODIEPC.png" />
            <h1><a href="/MyMaple/Item/Detail?itemId=12345">엘릭서&nbsp;(100개)</a></h1>
        </div>
        """

        item_data = InventoryParser._parse_single_item(item_html, 'consumables', 0)

        self.assertIsNotNone(item_data)
        self.assertEqual(item_data['item_name'], '엘릭서')
        self.assertTrue(item_data['item_icon'].startswith('http'))
        self.assertEqual(item_data['quantity'], 100)
        self.assertEqual(item_data['slot_position'], 0)
        self.assertEqual(item_data['item_type'], 'consumables')

    def test_parse_single_item_default_quantity(self):
        """수량 없는 아이템은 기본값 1"""
        item_html = """
        <div class="inven_item_img">
            <img src="//avatar.maplestory.nexon.com/ItemIcon/ABCDEFGH.png" />
            <h1><a href="/MyMaple/Item/Detail?itemId=67890">파워 엘릭서</a></h1>
        </div>
        """

        item_data = InventoryParser._parse_single_item(item_html, 'consumables', 5)

        self.assertIsNotNone(item_data)
        self.assertEqual(item_data['quantity'], 1)
        self.assertEqual(item_data['slot_position'], 5)

    def test_parse_single_item_with_options(self):
        """스타포스/주문서 강화 옵션 파싱"""
        item_html = """
        <div class="inven_item_img">
            <img src="//avatar.maplestory.nexon.com/ItemIcon/KEODIEPC.png" />
            <h1><a href="/MyMaple/Item/Detail?itemId=12345">테스트 장비 (+7)</a></h1>
            <em>15성 강화</em>
            <div class="item_memo_sel">레어</div>
        </div>
        """

        item_data = InventoryParser._parse_single_item(item_html, 'equips', 0)

        self.assertIsNotNone(item_data)
        self.assertIsNotNone(item_data['item_options'])
        self.assertEqual(item_data['item_options']['star_force'], 15)
        self.assertEqual(item_data['item_options']['spell_trace'], 7)
        self.assertEqual(item_data['item_options']['rarity'], '레어')


class CrawlerServiceTests(TestCase):
    """CrawlerService 단위 테스트 (AC 2.3.1)"""

    def test_crawl_inventory_success(self):
        """AC 2.3.1: 인벤토리 크롤링 성공"""
        crawler = CrawlerService()
        test_url = "https://maplestory.nexon.com/MyMaple/Character/Detail/테스트캐릭터?p=1234"

        # Mock HTML 반환
        with patch.object(crawler, '_fetch_inventory_page', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = """
            <div class="inven_list">
                <div class="inven_item_img">
                    <img src="//avatar.maplestory.nexon.com/ItemIcon/KEODIEPC.png" />
                    <h1><a href="/MyMaple/Item/Detail?itemId=12345">엘릭서&nbsp;(100개)</a></h1>
                </div>
            </div>
            """

            result = asyncio.run(crawler.crawl_inventory(test_url, '테스트캐릭터'))

            self.assertEqual(result['character_name'], '테스트캐릭터')
            self.assertEqual(len(result['items']), 1)
            self.assertIn('crawled_at', result)

    def test_crawl_inventory_parsing_error(self):
        """AC 2.3.7: 파싱 실패 시 에러 로깅"""
        crawler = CrawlerService()
        test_url = "https://maplestory.nexon.com/MyMaple/Character/Detail/테스트캐릭터?p=1234"

        with patch.object(InventoryParser, 'parse_inventory', side_effect=ParsingError('파싱 실패')):
            with self.assertRaises(CrawlingError):
                asyncio.run(crawler.crawl_inventory(test_url, '테스트캐릭터'))

    def test_request_delay_setting(self):
        """Rate limiting: 요청 간격 설정 확인"""
        crawler = CrawlerService()
        self.assertEqual(crawler.request_delay, 2)
        self.assertEqual(crawler.user_agent, "MapleStorage/1.0 (Educational Purpose)")

    def test_build_inventory_url(self):
        """URL 생성 로직 테스트 (SubPage 패턴)"""
        crawler = CrawlerService()

        # 쿼리 파라미터 있는 경우
        base_url = "https://maplestory.nexon.com/MyMaple/Character/Detail/test123?p=1234"
        inventory_url = crawler._build_inventory_url(base_url)
        self.assertEqual(
            inventory_url,
            "https://maplestory.nexon.com/MyMaple/Character/Detail/test123/Inventory?p=1234"
        )

        # 쿼리 파라미터 없는 경우
        base_url_no_query = "https://maplestory.nexon.com/MyMaple/Character/Detail/test123"
        inventory_url_no_query = crawler._build_inventory_url(base_url_no_query)
        self.assertEqual(
            inventory_url_no_query,
            "https://maplestory.nexon.com/MyMaple/Character/Detail/test123/Inventory"
        )
