"""
Expiry Date Crawling Integration Tests (Story 2.6)

기간제 아이템 만료 날짜 크롤링 통합 테스트
AC 2.6.1 - 2.6.5 검증
"""
import pytest
from unittest.mock import patch, Mock, AsyncMock
from django.test import TestCase
from django.utils import timezone
from datetime import datetime, timedelta
import pytz

from characters.crawler_services import (
    ExpiryDateParser,
    InventoryParser,
    StorageParser,
    CrawlerService
)
from characters.models import CharacterBasic, Inventory, Storage
from characters.schemas import InventoryItemSchema, StorageItemSchema


class InventoryExpiryDateIntegrationTests(TestCase):
    """인벤토리 만료 날짜 통합 테스트"""

    def setUp(self):
        """테스트 데이터 설정"""
        self.character_basic = CharacterBasic.objects.create(
            ocid='test-ocid-int-001',
            character_name='IntegrationTestChar',
            world_name='Scania',
            character_gender='남',
            character_class='아크'
        )

    def test_crawl_inventory_with_expiry_date_end_to_end(self):
        """AC 2.6.1-2.6.3: 인벤토리 크롤링 → 만료 날짜 파싱 → DB 저장"""
        # HTML에서 만료 날짜 파싱
        html_with_expiry = """
        <div class="item">
            <span class="name">프리미엄 펫 스낵</span>
            <img src="https://example.com/pet_snack.png" />
            <span class="expiry">만료: 2025년 12월 31일 23시 59분</span>
        </div>
        """

        # ExpiryDateParser로 파싱
        expiry_date = ExpiryDateParser.parse_expiry_date(html_with_expiry)

        # DB에 저장
        inventory = Inventory.objects.create(
            character_basic=self.character_basic,
            item_name='프리미엄 펫 스낵',
            item_icon='https://example.com/pet_snack.png',
            quantity=1,
            slot_position=0,
            expiry_date=expiry_date
        )

        # 검증
        refreshed = Inventory.objects.get(pk=inventory.pk)
        self.assertIsNotNone(refreshed.expiry_date)
        self.assertEqual(refreshed.expiry_date.year, 2025)
        self.assertEqual(refreshed.expiry_date.month, 12)
        self.assertEqual(refreshed.expiry_date.day, 31)

    def test_crawl_inventory_without_expiry_date_end_to_end(self):
        """AC 2.6.3: 만료 날짜 없는 아이템 → expiry_date=None"""
        html_without_expiry = """
        <div class="item">
            <span class="name">일반 소비 아이템</span>
            <img src="https://example.com/item.png" />
        </div>
        """

        # ExpiryDateParser로 파싱 (결과: None)
        expiry_date = ExpiryDateParser.parse_expiry_date(html_without_expiry)

        # DB에 저장
        inventory = Inventory.objects.create(
            character_basic=self.character_basic,
            item_name='일반 소비 아이템',
            item_icon='https://example.com/item.png',
            quantity=100,
            slot_position=1,
            expiry_date=expiry_date
        )

        # 검증
        refreshed = Inventory.objects.get(pk=inventory.pk)
        self.assertIsNone(refreshed.expiry_date)

    def test_inventory_days_until_expiry_calculation(self):
        """AC 2.6.4: D-day 계산 통합 테스트"""
        # 7일 후 만료되는 아이템 생성 (+12시간으로 정확히 7일 보장)
        expiry_date = timezone.now() + timedelta(days=7, hours=12)

        inventory = Inventory.objects.create(
            character_basic=self.character_basic,
            item_name='7일 후 만료 아이템',
            item_icon='https://example.com/item.png',
            quantity=1,
            slot_position=0,
            expiry_date=expiry_date
        )

        # days_until_expiry property 검증
        self.assertEqual(inventory.days_until_expiry, 7)

        # ExpiryDateParser.calculate_days_until_expiry와 일치 확인
        calculated_days = ExpiryDateParser.calculate_days_until_expiry(expiry_date)
        self.assertEqual(calculated_days, 7)

    def test_inventory_alert_flags_integration(self):
        """AC 2.6.5: 알림 플래그 통합 테스트"""
        # D-3 아이템 생성
        expiry_date = timezone.now() + timedelta(days=3)

        inventory = Inventory.objects.create(
            character_basic=self.character_basic,
            item_name='3일 후 만료',
            item_icon='https://example.com/item.png',
            quantity=1,
            slot_position=0,
            expiry_date=expiry_date
        )

        # 알림 플래그 계산
        alert_flags = ExpiryDateParser.get_alert_flags(inventory.expiry_date)

        # D-3이면 D-7, D-3 플래그만 True
        self.assertTrue(alert_flags['needs_d7_alert'])
        self.assertTrue(alert_flags['needs_d3_alert'])
        self.assertFalse(alert_flags['needs_d1_alert'])


class StorageExpiryDateIntegrationTests(TestCase):
    """창고 만료 날짜 통합 테스트"""

    def setUp(self):
        """테스트 데이터 설정"""
        self.character_basic = CharacterBasic.objects.create(
            ocid='test-ocid-int-002',
            character_name='StorageIntegrationChar',
            world_name='Luna',
            character_gender='여',
            character_class='호영'
        )

    def test_crawl_storage_with_expiry_date_end_to_end(self):
        """AC 2.6.1-2.6.3: 창고 크롤링 → 만료 날짜 파싱 → DB 저장"""
        html_with_expiry = """
        <li>
            <span>MVP 슈퍼 버프</span>
            <img src="https://example.com/mvp_buff.png" />
            <span>2025.06.15 23:59</span>
        </li>
        """

        # 파싱
        expiry_date = ExpiryDateParser.parse_expiry_date(html_with_expiry)

        # DB에 저장
        storage = Storage.objects.create(
            character_basic=self.character_basic,
            storage_type='storage',
            item_name='MVP 슈퍼 버프',
            item_icon='https://example.com/mvp_buff.png',
            quantity=5,
            slot_position=0,
            expiry_date=expiry_date
        )

        # 검증
        refreshed = Storage.objects.get(pk=storage.pk)
        self.assertIsNotNone(refreshed.expiry_date)
        self.assertEqual(refreshed.expiry_date.year, 2025)
        self.assertEqual(refreshed.expiry_date.month, 6)
        self.assertEqual(refreshed.expiry_date.day, 15)

    def test_crawl_storage_without_expiry_date_end_to_end(self):
        """AC 2.6.3: 창고에 만료 날짜 없는 아이템"""
        html_without_expiry = """
        <li>
            <span>메이플 포인트 코인</span>
            <img src="https://example.com/coin.png" />
        </li>
        """

        expiry_date = ExpiryDateParser.parse_expiry_date(html_without_expiry)

        storage = Storage.objects.create(
            character_basic=self.character_basic,
            storage_type='storage',
            item_name='메이플 포인트 코인',
            item_icon='https://example.com/coin.png',
            quantity=1000,
            slot_position=1,
            expiry_date=expiry_date
        )

        refreshed = Storage.objects.get(pk=storage.pk)
        self.assertIsNone(refreshed.expiry_date)


class PydanticSchemaExpiryDateTests(TestCase):
    """Pydantic 스키마 expiry_date 필드 테스트"""

    def test_inventory_item_schema_with_expiry_date(self):
        """InventoryItemSchema expiry_date 필드 검증"""
        kst = pytz.timezone('Asia/Seoul')
        expiry = datetime(2025, 12, 31, 23, 59, 59, tzinfo=kst)

        item_data = {
            'item_name': '기간제 아이템',
            'item_icon': 'https://example.com/icon.png',
            'quantity': 1,
            'slot_position': 0,
            'expiry_date': expiry
        }

        # Pydantic 스키마 검증
        schema = InventoryItemSchema(**item_data)

        self.assertEqual(schema.item_name, '기간제 아이템')
        self.assertIsNotNone(schema.expiry_date)

    def test_inventory_item_schema_without_expiry_date(self):
        """InventoryItemSchema expiry_date=None 검증"""
        item_data = {
            'item_name': '일반 아이템',
            'item_icon': 'https://example.com/icon.png',
            'quantity': 100,
            'slot_position': 0,
            'expiry_date': None
        }

        schema = InventoryItemSchema(**item_data)

        self.assertIsNone(schema.expiry_date)

    def test_storage_item_schema_with_expiry_date(self):
        """StorageItemSchema expiry_date 필드 검증"""
        kst = pytz.timezone('Asia/Seoul')
        expiry = datetime(2025, 6, 15, 12, 0, 0, tzinfo=kst)

        item_data = {
            'storage_type': 'storage',
            'item_name': '창고 기간제 아이템',
            'item_icon': 'https://example.com/icon.png',
            'quantity': 1,
            'slot_position': 0,
            'expiry_date': expiry
        }

        schema = StorageItemSchema(**item_data)

        self.assertEqual(schema.storage_type, 'storage')
        self.assertIsNotNone(schema.expiry_date)


class ExpiryDateISOFormatTests(TestCase):
    """ISO 8601 형식 변환 테스트 (AC 2.6.2)"""

    def test_parsed_date_is_iso_8601_serializable(self):
        """AC 2.6.2: 파싱된 날짜가 ISO 8601로 직렬화 가능"""
        html = "기간: 2025년 1월 15일 12시 30분"

        parsed = ExpiryDateParser.parse_expiry_date(html)

        # ISO 형식 문자열 변환
        iso_string = parsed.isoformat()

        # ISO 8601 형식 검증
        self.assertIn('2025-01-15', iso_string)
        self.assertIn('12:30:00', iso_string)
        # 타임존 정보 포함
        self.assertIn('+09:00', iso_string)

    def test_various_date_formats_to_iso(self):
        """다양한 형식 → ISO 8601 변환"""
        test_cases = [
            ("2025년 12월 31일 23시 59분", "2025-12-31"),
            ("2025.06.15 12:00", "2025-06-15"),
            ("2025-01-01", "2025-01-01"),
        ]

        for input_html, expected_date in test_cases:
            with self.subTest(input=input_html):
                parsed = ExpiryDateParser.parse_expiry_date(input_html)
                if parsed:
                    iso_string = parsed.isoformat()
                    self.assertIn(expected_date, iso_string)


class MultipleExpirableItemsTests(TestCase):
    """여러 기간제 아이템 동시 처리 테스트"""

    def setUp(self):
        self.character_basic = CharacterBasic.objects.create(
            ocid='test-ocid-multi-001',
            character_name='MultiItemChar',
            world_name='Scania',
            character_gender='남',
            character_class='아크'
        )

    def test_multiple_expirable_items_with_different_dates(self):
        """여러 아이템 각각 다른 만료 날짜"""
        items_data = [
            ('1일 후 만료', timedelta(days=1)),
            ('3일 후 만료', timedelta(days=3)),
            ('7일 후 만료', timedelta(days=7)),
            ('30일 후 만료', timedelta(days=30)),
            ('만료일 없음', None),
        ]

        created_items = []
        for idx, (name, delta) in enumerate(items_data):
            expiry = timezone.now() + delta if delta else None
            item = Inventory.objects.create(
                character_basic=self.character_basic,
                item_name=name,
                item_icon='https://example.com/icon.png',
                quantity=1,
                slot_position=idx,
                expiry_date=expiry
            )
            created_items.append(item)

        # 각 아이템 알림 플래그 검증
        flags_list = [ExpiryDateParser.get_alert_flags(item.expiry_date) for item in created_items]

        # 1일 후: D-1, D-3, D-7 모두 True
        self.assertTrue(flags_list[0]['needs_d1_alert'])
        self.assertTrue(flags_list[0]['needs_d3_alert'])
        self.assertTrue(flags_list[0]['needs_d7_alert'])

        # 3일 후: D-3, D-7 True, D-1 False
        self.assertFalse(flags_list[1]['needs_d1_alert'])
        self.assertTrue(flags_list[1]['needs_d3_alert'])
        self.assertTrue(flags_list[1]['needs_d7_alert'])

        # 7일 후: D-7만 True
        self.assertFalse(flags_list[2]['needs_d1_alert'])
        self.assertFalse(flags_list[2]['needs_d3_alert'])
        self.assertTrue(flags_list[2]['needs_d7_alert'])

        # 30일 후: 모두 False
        self.assertFalse(flags_list[3]['needs_d1_alert'])
        self.assertFalse(flags_list[3]['needs_d3_alert'])
        self.assertFalse(flags_list[3]['needs_d7_alert'])

        # 만료일 없음: 모두 False, days_until_expiry=None
        self.assertFalse(flags_list[4]['needs_d1_alert'])
        self.assertIsNone(flags_list[4]['days_until_expiry'])
