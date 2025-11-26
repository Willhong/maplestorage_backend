"""
Integration tests for Inventory crawling (Story 2.3)

테스트 실행: uv run python manage.py test characters.tests.test_inventory_integration
"""
from django.test import TestCase
from unittest.mock import patch, AsyncMock
from accounts.models import Character
from characters.models import CharacterBasic, Inventory
from characters.crawler_services import CrawlerService
from characters.schemas import InventoryItemSchema
from pydantic import ValidationError
import asyncio


class InventoryCrawlingIntegrationTests(TestCase):
    """인벤토리 크롤링 전체 플로우 통합 테스트"""

    def setUp(self):
        """테스트 데이터 설정"""
        # CharacterBasic 생성
        self.character_basic = CharacterBasic.objects.create(
            ocid='test_ocid_123',
            character_name='테스트캐릭터',
            world_name='스카니아',
            character_gender='남',
            character_class='히어로',
            character_info_url='https://maplestory.nexon.com/MyMaple/Character/Detail/테스트캐릭터?p=1234'
        )

        # Character 생성 (accounts 앱)
        self.character = Character.objects.create(
            ocid='test_ocid_123',
            character_name='테스트캐릭터',
            world_name='스카니아',
            character_class='히어로'
        )

    def test_crawl_and_save_inventory_success(self):
        """AC 2.3.1 - 2.3.6: 크롤링 → 검증 → DB 저장 전체 플로우"""
        # Mock 크롤링 데이터 (레거시 HTML 형식)
        mock_html = """
        <div class="inven_list">
            <div class="inven_item_img">
                <img src="//avatar.maplestory.nexon.com/ItemIcon/KEODIEPC.png" />
                <h1><a href="/MyMaple/Item/Detail?itemId=12345">엘릭서&nbsp;(100개)</a></h1>
            </div>
            <div class="inven_item_img">
                <img src="//avatar.maplestory.nexon.com/ItemIcon/ABCDEFGH.png" />
                <h1><a href="/MyMaple/Item/Detail?itemId=67890">파워 엘릭서&nbsp;(50개)</a></h1>
            </div>
        </div>
        """

        async def run_crawl():
            crawler = CrawlerService()
            with patch.object(crawler, '_fetch_inventory_page', new_callable=AsyncMock) as mock_fetch:
                mock_fetch.return_value = mock_html
                return await crawler.crawl_inventory(
                    self.character_basic.character_info_url,
                    self.character.character_name
                )

        # 비동기 실행
        crawled_data = asyncio.run(run_crawl())

        # 데이터 검증 및 저장 (AC 2.3.8: detail_url 포함)
        for item_data in crawled_data['items']:
            validated_item = InventoryItemSchema(**item_data)
            Inventory.objects.create(
                character_basic=self.character_basic,
                item_name=validated_item.item_name,
                item_icon=validated_item.item_icon,
                quantity=validated_item.quantity,
                item_options=validated_item.item_options,
                slot_position=validated_item.slot_position,
                expiry_date=validated_item.expiry_date,
                detail_url=validated_item.detail_url,
                has_detail=False
            )

        # 검증
        saved_items = Inventory.objects.filter(character_basic=self.character_basic)
        self.assertEqual(saved_items.count(), 2)

        # AC 2.3.3: 아이템 정보 확인
        elixir = saved_items.filter(item_name='엘릭서').first()
        self.assertIsNotNone(elixir)
        self.assertEqual(elixir.quantity, 100)
        self.assertEqual(elixir.slot_position, 0)
        # AC 2.3.8: detail_url 저장 확인
        self.assertIsNotNone(elixir.detail_url)
        self.assertIn('/MyMaple/Item/Detail?itemId=12345', elixir.detail_url)
        self.assertFalse(elixir.has_detail)  # 아직 상세 정보 크롤링 안됨

        power_elixir = saved_items.filter(item_name='파워 엘릭서').first()
        self.assertIsNotNone(power_elixir)
        self.assertEqual(power_elixir.quantity, 50)
        # AC 2.3.8: detail_url 저장 확인
        self.assertIsNotNone(power_elixir.detail_url)
        self.assertIn('/MyMaple/Item/Detail?itemId=67890', power_elixir.detail_url)

    def test_inventory_history_preservation(self):
        """AC 2.3.6: 이전 데이터 히스토리 보관"""
        # 첫 번째 크롤링
        item1 = Inventory.objects.create(
            character_basic=self.character_basic,
            item_name='엘릭서',
            item_icon='https://maplestory.io/api/item/2000005/icon',
            quantity=100,
            slot_position=0
        )

        # 두 번째 크롤링 (같은 아이템, 다른 수량)
        item2 = Inventory.objects.create(
            character_basic=self.character_basic,
            item_name='엘릭서',
            item_icon='https://maplestory.io/api/item/2000005/icon',
            quantity=80,  # 수량 변경
            slot_position=0
        )

        # AC 2.3.6: 이전 데이터가 덮어써지지 않고 보관됨
        all_items = Inventory.objects.filter(
            character_basic=self.character_basic,
            item_name='엘릭서'
        ).order_by('id')  # ID 순서로 정렬 (생성 순서 보장)

        self.assertEqual(all_items.count(), 2)
        self.assertEqual(all_items[0].id, item1.id)
        self.assertEqual(all_items[0].quantity, 100)
        self.assertEqual(all_items[1].id, item2.id)
        self.assertEqual(all_items[1].quantity, 80)

    def test_pydantic_validation_failure(self):
        """AC 2.3.7: 검증 실패 시 에러 처리"""
        # 잘못된 데이터 (item_icon이 URL 형식이 아님)
        invalid_data = {
            'item_name': '테스트아이템',
            'item_icon': 'not_a_url',  # 잘못된 형식
            'quantity': 1,
            'slot_position': 0,
            'item_options': None,
            'expiry_date': None
        }

        with self.assertRaises(ValidationError):
            InventoryItemSchema(**invalid_data)

    def test_inventory_model_properties(self):
        """Inventory 모델 속성 테스트"""
        from datetime import datetime, timedelta, timezone

        # 일반 아이템
        normal_item = Inventory.objects.create(
            character_basic=self.character_basic,
            item_name='엘릭서',
            item_icon='https://maplestory.io/api/item/2000005/icon',
            quantity=100,
            slot_position=0
        )

        self.assertFalse(normal_item.is_expirable)
        self.assertIsNone(normal_item.days_until_expiry)

        # 기간제 아이템
        future_date = datetime.now(timezone.utc) + timedelta(days=7)
        expirable_item = Inventory.objects.create(
            character_basic=self.character_basic,
            item_name='30일 경험치 쿠폰',
            item_icon='https://maplestory.io/api/item/5000001/icon',
            quantity=1,
            slot_position=1,
            expiry_date=future_date
        )

        self.assertTrue(expirable_item.is_expirable)
        self.assertIsNotNone(expirable_item.days_until_expiry)
        self.assertGreaterEqual(expirable_item.days_until_expiry, 6)  # 약 7일
        self.assertLessEqual(expirable_item.days_until_expiry, 7)
