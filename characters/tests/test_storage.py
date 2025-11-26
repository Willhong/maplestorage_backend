"""
Storage Unit Tests (Story 2.4)

창고 크롤링 및 파싱 관련 단위 테스트
AC 2.4.1 - 2.4.9 검증
"""
import pytest
from unittest.mock import patch, Mock, AsyncMock
from django.test import TestCase
from pydantic import ValidationError

from characters.crawler_services import (
    StorageParser,
    CrawlerService,
    StorageParsingError,
    CrawlingError
)
from characters.schemas import StorageItemSchema


class StorageParserTests(TestCase):
    """StorageParser 단위 테스트

    레거시 파서(mapleApi.py get_storage_list)는 <li> 태그 기반으로 파싱합니다.
    테스트 HTML은 실제 웹사이트 구조와 동일해야 합니다.
    """

    def test_parse_storage_shared(self):
        """AC 2.4.2-2.4.4: 공유 창고 HTML 파싱 및 아이템 추출"""
        # 레거시 파서 형식: &nbsp; 로 이름 추출, >(N개) 로 수량 추출
        html_content = """
        <ul class="item_list">
            <li>
                <div class="inven_item_img">
                    <img src="//maplestory.nexon.com/images/item/2000005.png" alt="엘릭서">
                </div>
                <div class="inven_item_name">
                    <a href="/item/2000005">엘릭서&nbsp;>(200개)</a>
                </div>
            </li>
        </ul>
        """

        items = StorageParser.parse_storage(html_content, 'shared')

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['item_name'], '엘릭서')
        self.assertEqual(items[0]['quantity'], 200)
        self.assertEqual(items[0]['storage_type'], 'shared')
        self.assertEqual(items[0]['slot_position'], 0)

    def test_parse_storage_personal(self):
        """AC 2.4.2-2.4.4: 개인 창고 HTML 파싱"""
        html_content = """
        <ul class="item_list">
            <li>
                <div class="inven_item_img">
                    <img src="//maplestory.nexon.com/images/item/2000006.png" alt="파워 엘릭서">
                </div>
                <div class="inven_item_name">
                    <a href="/item/2000006">파워 엘릭서&nbsp;>(50개)</a>
                </div>
            </li>
        </ul>
        """

        items = StorageParser.parse_storage(html_content, 'personal')

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['storage_type'], 'personal')
        self.assertEqual(items[0]['item_name'], '파워 엘릭서')
        self.assertEqual(items[0]['quantity'], 50)

    def test_parse_storage_empty(self):
        """AC 2.4.3: 빈 창고 처리"""
        html_content = """
        <div class="my_info">
            <div class="inven_list">
                <p>보관된 아이템이 없습니다.</p>
            </div>
        </div>
        """

        items = StorageParser.parse_storage(html_content, 'shared')

        self.assertEqual(len(items), 0)

    def test_extract_storage_item_data(self):
        """AC 2.4.4: 창고 아이템 데이터 추출 확인"""
        # 레거시 파서 형식: &nbsp; 로 이름 추출, >(N개) 로 수량 추출
        html_content = """
        <ul class="item_list">
            <li>
                <div class="inven_item_img">
                    <img src="https://maplestory.nexon.com/images/item/1234.png" alt="테스트 아이템">
                </div>
                <div class="inven_item_name">
                    <a href="/item/1234">테스트 아이템&nbsp;>(5개)</a>
                </div>
            </li>
        </ul>
        """

        items = StorageParser.parse_storage(html_content, 'shared')

        self.assertEqual(len(items), 1)
        item = items[0]

        # 필수 필드 확인
        self.assertIn('item_name', item)
        self.assertIn('item_icon', item)
        self.assertIn('quantity', item)
        self.assertIn('slot_position', item)
        self.assertIn('storage_type', item)

        # 값 검증
        self.assertEqual(item['item_name'], '테스트 아이템')
        self.assertTrue(item['item_icon'].startswith('https://'))
        self.assertEqual(item['quantity'], 5)
        self.assertGreaterEqual(item['slot_position'], 0)

    def test_storage_type_validation(self):
        """AC 2.4.2: storage_type 검증 (공유/개인 구분 없이 단일 창고)"""
        # storage_type은 단순 문자열 필드
        storage_data = {
            'storage_type': 'storage',
            'item_name': '테스트',
            'item_icon': 'https://example.com/icon.png',
            'quantity': 1,
            'slot_position': 0
        }
        validated = StorageItemSchema(**storage_data)
        self.assertEqual(validated.storage_type, 'storage')

        # 기본값 사용
        default_data = {
            'item_name': '테스트',
            'item_icon': 'https://example.com/icon.png',
            'quantity': 1,
            'slot_position': 0
        }
        validated = StorageItemSchema(**default_data)
        self.assertEqual(validated.storage_type, 'storage')

    def test_parse_storage_with_starforce(self):
        """AC 2.4.4: 강화 수치 추출"""
        # 레거시 파서는 [17성 강화]<br /> 형식으로 스타포스를 파싱
        html_content = """
        <ul class="item_list">
            <li>
                <div class="inven_item_img">
                    <img src="https://maplestory.nexon.com/images/item/1234.png" alt="아케인셰이드 스태프">
                </div>
                <div class="inven_item_name">
                    <a href="/item/1234">아케인셰이드 스태프 +7&nbsp;(1개)</a>
                    <em>[17성 강화]<br /></em>
                </div>
            </li>
        </ul>
        """

        items = StorageParser.parse_storage(html_content, 'shared')

        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertIsNotNone(item.get('item_options'))
        self.assertEqual(item['item_options'].get('star_force'), 17)
        self.assertEqual(item['item_options'].get('spell_trace'), 7)

    def test_parse_storage_multiple_items(self):
        """AC 2.4.3: 여러 아이템 파싱"""
        # 레거시 파서 형식: &nbsp; 로 이름 추출, >(N개) 로 수량 추출
        html_content = """
        <ul class="item_list">
            <li>
                <div class="inven_item_img">
                    <img src="https://example.com/item1.png" alt="아이템1">
                </div>
                <div class="inven_item_name">
                    <a href="/item/1">아이템1&nbsp;>(10개)</a>
                </div>
            </li>
            <li>
                <div class="inven_item_img">
                    <img src="https://example.com/item2.png" alt="아이템2">
                </div>
                <div class="inven_item_name">
                    <a href="/item/2">아이템2&nbsp;>(20개)</a>
                </div>
            </li>
            <li>
                <div class="inven_item_img">
                    <img src="https://example.com/item3.png" alt="아이템3">
                </div>
                <div class="inven_item_name">
                    <a href="/item/3">아이템3&nbsp;>(30개)</a>
                </div>
            </li>
        </ul>
        """

        items = StorageParser.parse_storage(html_content, 'personal')

        self.assertEqual(len(items), 3)
        self.assertEqual(items[0]['storage_type'], 'personal')
        self.assertEqual(items[0]['item_name'], '아이템1')
        self.assertEqual(items[0]['quantity'], 10)
        self.assertEqual(items[1]['item_name'], '아이템2')
        self.assertEqual(items[1]['quantity'], 20)
        self.assertEqual(items[2]['item_name'], '아이템3')
        self.assertEqual(items[2]['quantity'], 30)

    def test_crawl_storage_parsing_error(self):
        """AC 2.4.10: 파싱 에러 처리"""
        # 잘못된 HTML 구조
        invalid_html = "<invalid>not valid html"

        # 빈 결과 반환 (에러 발생하지 않음)
        items = StorageParser.parse_storage(invalid_html, 'shared')
        self.assertEqual(len(items), 0)


class StorageSchemaTests(TestCase):
    """StorageItemSchema 단위 테스트"""

    def test_valid_storage_item(self):
        """유효한 창고 아이템 검증"""
        data = {
            'storage_type': 'shared',
            'item_name': '엘릭서',
            'item_icon': 'https://maplestory.io/api/item/2000005/icon',
            'quantity': 100,
            'slot_position': 0,
            'item_options': {'star_force': 10},
            'expiry_date': None
        }

        validated = StorageItemSchema(**data)

        self.assertEqual(validated.storage_type, 'shared')
        self.assertEqual(validated.item_name, '엘릭서')
        self.assertEqual(validated.quantity, 100)

    def test_storage_type_default(self):
        """storage_type 기본값 검증"""
        # storage_type 없이 생성하면 기본값 'storage' 사용
        data = {
            'item_name': '테스트',
            'item_icon': 'https://example.com/icon.png',
            'quantity': 1,
            'slot_position': 0
        }

        validated = StorageItemSchema(**data)
        self.assertEqual(validated.storage_type, 'storage')

    def test_invalid_item_icon_url(self):
        """잘못된 item_icon URL 검증"""
        data = {
            'storage_type': 'shared',
            'item_name': '테스트',
            'item_icon': 'not-a-valid-url',  # Invalid
            'quantity': 1,
            'slot_position': 0
        }

        with self.assertRaises(ValidationError):
            StorageItemSchema(**data)

    def test_invalid_quantity(self):
        """잘못된 quantity 검증 (0 이하)"""
        data = {
            'storage_type': 'shared',
            'item_name': '테스트',
            'item_icon': 'https://example.com/icon.png',
            'quantity': 0,  # Invalid (must be >= 1)
            'slot_position': 0
        }

        with self.assertRaises(ValidationError):
            StorageItemSchema(**data)

    def test_invalid_slot_position(self):
        """잘못된 slot_position 검증 (음수)"""
        data = {
            'storage_type': 'shared',
            'item_name': '테스트',
            'item_icon': 'https://example.com/icon.png',
            'quantity': 1,
            'slot_position': -1  # Invalid (must be >= 0)
        }

        with self.assertRaises(ValidationError):
            StorageItemSchema(**data)


class CrawlerServiceStorageTests(TestCase):
    """CrawlerService.crawl_storage 단위 테스트"""

    def test_build_storage_url(self):
        """창고 URL 생성 테스트"""
        crawler = CrawlerService()

        # with query string
        url1 = 'https://maplestory.nexon.com/MyMaple/Character/Detail/test123?p=1234'
        result1 = crawler._build_storage_url(url1)
        self.assertEqual(
            result1,
            'https://maplestory.nexon.com/MyMaple/Character/Detail/test123/Storage?p=1234'
        )

        # without query string
        url2 = 'https://maplestory.nexon.com/MyMaple/Character/Detail/test123'
        result2 = crawler._build_storage_url(url2)
        self.assertEqual(
            result2,
            'https://maplestory.nexon.com/MyMaple/Character/Detail/test123/Storage'
        )
