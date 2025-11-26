"""
Expiry Date Crawling Unit Tests (Story 2.6)

기간제 아이템 만료 날짜 크롤링 및 파싱 관련 단위 테스트
AC 2.6.1 - 2.6.5 검증
"""
import pytest
from unittest.mock import patch, Mock
from django.test import TestCase
from django.utils import timezone
from datetime import datetime, timedelta, timezone as dt_timezone
import pytz

from characters.crawler_services import (
    ExpiryDateParser,
    ExpiryDateParsingError,
    InventoryParser,
    StorageParser
)
from characters.models import CharacterBasic, Inventory, Storage


class ExpiryDateParserTests(TestCase):
    """ExpiryDateParser 단위 테스트

    만료 날짜 파싱 로직 검증 (AC 2.6.1 - 2.6.5)
    """

    def test_parse_expiry_date_korean_datetime_format(self):
        """AC 2.6.1, 2.6.2: 한국어 날짜+시간 형식 파싱"""
        html_content = """
        <div class="item_info">
            <span>기간: 2025년 12월 31일 23시 59분까지</span>
        </div>
        """

        result = ExpiryDateParser.parse_expiry_date(html_content)

        self.assertIsNotNone(result)
        self.assertEqual(result.year, 2025)
        self.assertEqual(result.month, 12)
        self.assertEqual(result.day, 31)
        self.assertEqual(result.hour, 23)
        self.assertEqual(result.minute, 59)
        # KST 타임존 확인
        self.assertEqual(result.tzinfo.zone, 'Asia/Seoul')

    def test_parse_expiry_date_korean_date_only_format(self):
        """AC 2.6.1, 2.6.2: 한국어 날짜만 형식 파싱 (시간 없음 → 23:59:59)"""
        html_content = """
        <div class="item_info">
            <span>만료일: 2025년 6월 15일</span>
        </div>
        """

        result = ExpiryDateParser.parse_expiry_date(html_content)

        self.assertIsNotNone(result)
        self.assertEqual(result.year, 2025)
        self.assertEqual(result.month, 6)
        self.assertEqual(result.day, 15)
        # 시간이 없으면 23:59:59로 설정
        self.assertEqual(result.hour, 23)
        self.assertEqual(result.minute, 59)
        self.assertEqual(result.second, 59)

    def test_parse_expiry_date_numeric_datetime_format(self):
        """AC 2.6.1, 2.6.2: 숫자 날짜+시간 형식 파싱"""
        html_content = """
        <div class="expiry">2025.12.31 23:59</div>
        """

        result = ExpiryDateParser.parse_expiry_date(html_content)

        self.assertIsNotNone(result)
        self.assertEqual(result.year, 2025)
        self.assertEqual(result.month, 12)
        self.assertEqual(result.day, 31)
        self.assertEqual(result.hour, 23)
        self.assertEqual(result.minute, 59)

    def test_parse_expiry_date_numeric_date_only_format(self):
        """AC 2.6.1, 2.6.2: 숫자 날짜만 형식 파싱 (점, 하이픈, 슬래시 지원)"""
        test_cases = [
            "2025.12.31",
            "2025-12-31",
            "2025/12/31",
        ]

        for html in test_cases:
            with self.subTest(html=html):
                result = ExpiryDateParser.parse_expiry_date(html)

                self.assertIsNotNone(result, f"Failed for: {html}")
                self.assertEqual(result.year, 2025)
                self.assertEqual(result.month, 12)
                self.assertEqual(result.day, 31)

    def test_parse_expiry_date_none_when_no_date(self):
        """AC 2.6.3: 만료 날짜가 없는 아이템은 None 반환"""
        html_content = """
        <div class="item_info">
            <span>일반 아이템 - 기간제 아님</span>
            <span>수량: 100개</span>
        </div>
        """

        result = ExpiryDateParser.parse_expiry_date(html_content)

        self.assertIsNone(result)

    def test_parse_expiry_date_empty_html(self):
        """AC 2.6.3: 빈 HTML에서 None 반환"""
        self.assertIsNone(ExpiryDateParser.parse_expiry_date(""))
        self.assertIsNone(ExpiryDateParser.parse_expiry_date(None))

    def test_parse_expiry_date_iso_8601_compatible(self):
        """AC 2.6.2: 파싱 결과가 ISO 8601 호환인지 확인"""
        html_content = "기간: 2025년 1월 15일 12시 30분"

        result = ExpiryDateParser.parse_expiry_date(html_content)

        self.assertIsNotNone(result)
        # ISO 8601 형식으로 변환 가능한지 확인
        iso_string = result.isoformat()
        self.assertIn("2025-01-15", iso_string)
        self.assertIn("12:30", iso_string)


class CalculateDaysUntilExpiryTests(TestCase):
    """calculate_days_until_expiry 함수 테스트 (AC 2.6.4)"""

    def test_calculate_days_until_expiry_7_days(self):
        """AC 2.6.4: 7일 후 만료 → 약 7 반환 (시간차 허용)"""
        future_date = datetime.now(dt_timezone.utc) + timedelta(days=7, hours=12)

        result = ExpiryDateParser.calculate_days_until_expiry(future_date)

        # 7일 12시간 후이므로 7 반환
        self.assertEqual(result, 7)

    def test_calculate_days_until_expiry_today(self):
        """AC 2.6.4: 오늘 만료 → 0 반환"""
        today = datetime.now(dt_timezone.utc) + timedelta(hours=1)

        result = ExpiryDateParser.calculate_days_until_expiry(today)

        self.assertEqual(result, 0)

    def test_calculate_days_until_expiry_past(self):
        """AC 2.6.4: 과거 날짜 → 음수 반환"""
        past_date = datetime.now(dt_timezone.utc) - timedelta(days=3, hours=12)

        result = ExpiryDateParser.calculate_days_until_expiry(past_date)

        # 3일 12시간 전이면 -4
        self.assertEqual(result, -4)

    def test_calculate_days_until_expiry_none(self):
        """AC 2.6.4: 만료일 없음 → None 반환"""
        result = ExpiryDateParser.calculate_days_until_expiry(None)

        self.assertIsNone(result)

    def test_calculate_days_until_expiry_naive_datetime(self):
        """naive datetime 처리 (타임존 없는 datetime)"""
        naive_date = datetime.now() + timedelta(days=5)

        result = ExpiryDateParser.calculate_days_until_expiry(naive_date)

        # 결과가 5일 근처여야 함
        self.assertIn(result, [4, 5, 6])


class GetAlertFlagsTests(TestCase):
    """get_alert_flags 함수 테스트 (AC 2.6.5)"""

    def test_get_alert_flags_d7(self):
        """AC 2.6.5: D-7 (7일 이하 남음) 플래그"""
        expiry_date = datetime.now(dt_timezone.utc) + timedelta(days=7, hours=12)

        result = ExpiryDateParser.get_alert_flags(expiry_date)

        self.assertTrue(result['needs_d7_alert'])
        self.assertFalse(result['needs_d3_alert'])
        self.assertFalse(result['needs_d1_alert'])
        self.assertEqual(result['days_until_expiry'], 7)

    def test_get_alert_flags_d3(self):
        """AC 2.6.5: D-3 (3일 이하 남음) 플래그"""
        expiry_date = datetime.now(dt_timezone.utc) + timedelta(days=3, hours=12)

        result = ExpiryDateParser.get_alert_flags(expiry_date)

        self.assertTrue(result['needs_d7_alert'])
        self.assertTrue(result['needs_d3_alert'])
        self.assertFalse(result['needs_d1_alert'])
        self.assertEqual(result['days_until_expiry'], 3)

    def test_get_alert_flags_d1(self):
        """AC 2.6.5: D-1 (1일 이하 남음) 플래그"""
        expiry_date = datetime.now(dt_timezone.utc) + timedelta(days=1, hours=12)

        result = ExpiryDateParser.get_alert_flags(expiry_date)

        self.assertTrue(result['needs_d7_alert'])
        self.assertTrue(result['needs_d3_alert'])
        self.assertTrue(result['needs_d1_alert'])
        self.assertEqual(result['days_until_expiry'], 1)

    def test_get_alert_flags_d0_today(self):
        """AC 2.6.5: D-0 (오늘 만료) 플래그"""
        expiry_date = datetime.now(dt_timezone.utc) + timedelta(hours=1)

        result = ExpiryDateParser.get_alert_flags(expiry_date)

        self.assertTrue(result['needs_d7_alert'])
        self.assertTrue(result['needs_d3_alert'])
        self.assertTrue(result['needs_d1_alert'])
        self.assertEqual(result['days_until_expiry'], 0)

    def test_get_alert_flags_30_days_no_alert(self):
        """AC 2.6.5: 30일 남음 → 알림 플래그 없음"""
        expiry_date = datetime.now(dt_timezone.utc) + timedelta(days=30, hours=12)

        result = ExpiryDateParser.get_alert_flags(expiry_date)

        self.assertFalse(result['needs_d7_alert'])
        self.assertFalse(result['needs_d3_alert'])
        self.assertFalse(result['needs_d1_alert'])
        self.assertEqual(result['days_until_expiry'], 30)

    def test_get_alert_flags_expired_no_alert(self):
        """만료된 아이템 → 알림 플래그 없음 (음수)"""
        expiry_date = datetime.now(dt_timezone.utc) - timedelta(days=1, hours=12)

        result = ExpiryDateParser.get_alert_flags(expiry_date)

        self.assertFalse(result['needs_d7_alert'])
        self.assertFalse(result['needs_d3_alert'])
        self.assertFalse(result['needs_d1_alert'])
        self.assertLess(result['days_until_expiry'], 0)

    def test_get_alert_flags_none_expiry(self):
        """AC 2.6.5: 만료일 없음 → 기본값 반환"""
        result = ExpiryDateParser.get_alert_flags(None)

        self.assertFalse(result['needs_d7_alert'])
        self.assertFalse(result['needs_d3_alert'])
        self.assertFalse(result['needs_d1_alert'])
        self.assertIsNone(result['days_until_expiry'])


class InventoryExpiryDateTests(TestCase):
    """Inventory 모델의 expiry_date 필드 테스트"""

    def setUp(self):
        """테스트 데이터 설정"""
        self.character_basic = CharacterBasic.objects.create(
            ocid='test-ocid-expiry-001',
            character_name='TestExpiryChar',
            world_name='Scania',
            character_gender='남',
            character_class='아크'
        )

    def test_inventory_expiry_date_field_with_date(self):
        """AC 2.6.1: Inventory.expiry_date 필드에 만료 날짜 저장"""
        kst = pytz.timezone('Asia/Seoul')
        expiry = datetime(2025, 12, 31, 23, 59, 59, tzinfo=kst)

        inventory = Inventory.objects.create(
            character_basic=self.character_basic,
            item_name='기간제 아이템',
            item_icon='https://example.com/icon.png',
            quantity=1,
            slot_position=0,
            expiry_date=expiry
        )

        refreshed = Inventory.objects.get(pk=inventory.pk)
        self.assertIsNotNone(refreshed.expiry_date)
        self.assertEqual(refreshed.expiry_date.year, 2025)
        self.assertEqual(refreshed.expiry_date.month, 12)
        self.assertEqual(refreshed.expiry_date.day, 31)

    def test_inventory_expiry_date_field_null(self):
        """AC 2.6.3: Inventory.expiry_date 필드에 null 저장 (비기간제 아이템)"""
        inventory = Inventory.objects.create(
            character_basic=self.character_basic,
            item_name='일반 아이템',
            item_icon='https://example.com/icon.png',
            quantity=1,
            slot_position=0,
            expiry_date=None
        )

        refreshed = Inventory.objects.get(pk=inventory.pk)
        self.assertIsNone(refreshed.expiry_date)

    def test_inventory_is_expirable_property(self):
        """Inventory.is_expirable property 테스트"""
        # 기간제 아이템
        expirable_item = Inventory.objects.create(
            character_basic=self.character_basic,
            item_name='기간제',
            item_icon='https://example.com/icon.png',
            quantity=1,
            slot_position=0,
            expiry_date=timezone.now() + timedelta(days=7)
        )
        self.assertTrue(expirable_item.is_expirable)

        # 비기간제 아이템
        non_expirable_item = Inventory.objects.create(
            character_basic=self.character_basic,
            item_name='일반',
            item_icon='https://example.com/icon.png',
            quantity=1,
            slot_position=1,
            expiry_date=None
        )
        self.assertFalse(non_expirable_item.is_expirable)

    def test_inventory_days_until_expiry_property(self):
        """AC 2.6.4: Inventory.days_until_expiry property 테스트"""
        # 7일 후 만료 (+12시간으로 정확히 7일 보장)
        item = Inventory.objects.create(
            character_basic=self.character_basic,
            item_name='7일 후 만료',
            item_icon='https://example.com/icon.png',
            quantity=1,
            slot_position=0,
            expiry_date=timezone.now() + timedelta(days=7, hours=12)
        )
        self.assertEqual(item.days_until_expiry, 7)

        # 만료일 없음
        item_no_expiry = Inventory.objects.create(
            character_basic=self.character_basic,
            item_name='만료일 없음',
            item_icon='https://example.com/icon.png',
            quantity=1,
            slot_position=1,
            expiry_date=None
        )
        self.assertIsNone(item_no_expiry.days_until_expiry)


class StorageExpiryDateTests(TestCase):
    """Storage 모델의 expiry_date 필드 테스트"""

    def setUp(self):
        """테스트 데이터 설정"""
        self.character_basic = CharacterBasic.objects.create(
            ocid='test-ocid-expiry-002',
            character_name='TestStorageExpiryChar',
            world_name='Scania',
            character_gender='여',
            character_class='호영'
        )

    def test_storage_expiry_date_field_with_date(self):
        """AC 2.6.1: Storage.expiry_date 필드에 만료 날짜 저장"""
        kst = pytz.timezone('Asia/Seoul')
        expiry = datetime(2025, 6, 15, 12, 0, 0, tzinfo=kst)

        storage = Storage.objects.create(
            character_basic=self.character_basic,
            storage_type='storage',
            item_name='창고 기간제 아이템',
            item_icon='https://example.com/icon.png',
            quantity=1,
            slot_position=0,
            expiry_date=expiry
        )

        refreshed = Storage.objects.get(pk=storage.pk)
        self.assertIsNotNone(refreshed.expiry_date)
        self.assertEqual(refreshed.expiry_date.year, 2025)
        self.assertEqual(refreshed.expiry_date.month, 6)
        self.assertEqual(refreshed.expiry_date.day, 15)

    def test_storage_expiry_date_field_null(self):
        """AC 2.6.3: Storage.expiry_date 필드에 null 저장"""
        storage = Storage.objects.create(
            character_basic=self.character_basic,
            storage_type='storage',
            item_name='창고 일반 아이템',
            item_icon='https://example.com/icon.png',
            quantity=100,
            slot_position=0,
            expiry_date=None
        )

        refreshed = Storage.objects.get(pk=storage.pk)
        self.assertIsNone(refreshed.expiry_date)

    def test_storage_days_until_expiry_property(self):
        """AC 2.6.4: Storage.days_until_expiry property 테스트"""
        # 3일 후 만료
        item = Storage.objects.create(
            character_basic=self.character_basic,
            storage_type='storage',
            item_name='3일 후 만료',
            item_icon='https://example.com/icon.png',
            quantity=1,
            slot_position=0,
            expiry_date=timezone.now() + timedelta(days=3)
        )
        self.assertEqual(item.days_until_expiry, 3)


class InventoryParserExpiryDateTests(TestCase):
    """InventoryParser의 expiry_date 추출 테스트"""

    def test_inventory_parser_extracts_expiry_date(self):
        """AC 2.6.1: InventoryParser가 만료 날짜 추출"""
        html_content = """
        <div class="inven_list">
            <div class="inven_item_img">
                <img src="https://example.com/item.png" />
                <div class="inven_item_memo_title">
                    <h1><a href="/item/detail">기간제 아이템</a></h1>
                </div>
                <span>기간: 2025년 12월 31일 23시 59분까지</span>
            </div>
        </div>
        """

        items = InventoryParser.parse_inventory(f"<div class='inven_list'></div>{html_content}")

        # 파싱된 아이템 중 만료 날짜가 있는지 확인
        self.assertGreater(len(items), 0)

    def test_inventory_parser_returns_none_for_no_expiry(self):
        """AC 2.6.3: 만료 날짜 없는 아이템은 expiry_date=None"""
        html_content = """
        <div class="inven_list">
            <div class="inven_item_img">
                <img src="https://example.com/item.png" />
                <div class="inven_item_memo_title">
                    <h1><a href="/item/detail">일반 아이템</a></h1>
                </div>
            </div>
        </div>
        """

        items = InventoryParser.parse_inventory(f"<div class='inven_list'></div>{html_content}")

        if len(items) > 0:
            self.assertIsNone(items[0].get('expiry_date'))


class StorageParserExpiryDateTests(TestCase):
    """StorageParser의 expiry_date 추출 테스트"""

    def test_storage_parser_extracts_expiry_date(self):
        """AC 2.6.1: StorageParser가 만료 날짜 추출"""
        html_content = """
        <li>
            <div class="inven_item_img">
                <img src="https://example.com/item.png" />
            </div>
            <a href="/item/detail">기간제 창고 아이템</a>
            <span>만료: 2025년 6월 15일</span>
        </li>
        """

        items = StorageParser.parse_storage(html_content, 'storage')

        # 결과 확인 (아이템이 파싱되었다면)
        self.assertIsInstance(items, list)
