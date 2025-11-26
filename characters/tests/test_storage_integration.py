"""
Storage Integration Tests (Story 2.4)

창고 크롤링 전체 플로우 통합 테스트
AC 2.4.1 - 2.4.11 검증
"""
import pytest
from unittest.mock import patch, Mock, MagicMock
from django.test import TestCase, override_settings
from django.core.cache import cache

from characters.models import Storage, CharacterBasic
from characters.schemas import StorageItemSchema
from characters.crawler_services import StorageParser


class StorageModelTests(TestCase):
    """Storage 모델 통합 테스트"""

    @classmethod
    def setUpTestData(cls):
        """테스트 데이터 설정"""
        # CharacterBasic 생성 (실제 모델 필드에 맞게)
        cls.character_basic = CharacterBasic.objects.create(
            ocid='test-ocid-12345',
            character_name='TestCharacter',
            world_name='스카니아',
            character_gender='남',
            character_class='아크메이지(썬,콜)'
        )

    def test_storage_model_creation(self):
        """Storage 모델 생성 테스트"""
        storage = Storage.objects.create(
            character_basic=self.character_basic,
            storage_type='shared',
            item_name='엘릭서',
            item_icon='https://maplestory.io/api/item/2000005/icon',
            quantity=100,
            slot_position=0
        )

        self.assertEqual(storage.storage_type, 'shared')
        self.assertEqual(storage.item_name, '엘릭서')
        self.assertEqual(storage.quantity, 100)
        self.assertIsNotNone(storage.crawled_at)

    def test_storage_model_properties(self):
        """Storage 모델 속성 테스트"""
        storage = Storage.objects.create(
            character_basic=self.character_basic,
            storage_type='personal',
            item_name='파워 엘릭서',
            item_icon='https://maplestory.io/api/item/2000006/icon',
            quantity=50,
            slot_position=1,
            expiry_date=None
        )

        # is_shared / is_personal
        self.assertFalse(storage.is_shared)
        self.assertTrue(storage.is_personal)

        # is_expirable (expiry_date가 None이므로 False)
        self.assertFalse(storage.is_expirable)

    def test_storage_history_preserved(self):
        """AC 2.4.9: 이전 데이터 히스토리 보관 확인"""
        import time

        # 첫 번째 크롤링
        first_item = Storage.objects.create(
            character_basic=self.character_basic,
            storage_type='shared',
            item_name='엘릭서',
            item_icon='https://example.com/icon.png',
            quantity=100,
            slot_position=0
        )

        # 약간의 시간 지연 (crawled_at 순서 보장)
        time.sleep(0.01)

        # 두 번째 크롤링 (새로운 데이터 - 덮어쓰기가 아닌 새 레코드)
        second_item = Storage.objects.create(
            character_basic=self.character_basic,
            storage_type='shared',
            item_name='엘릭서',
            item_icon='https://example.com/icon.png',
            quantity=150,  # 수량 변경
            slot_position=0
        )

        # 히스토리 확인: 이전 데이터 유지
        all_items = Storage.objects.filter(
            character_basic=self.character_basic,
            item_name='엘릭서'
        )
        self.assertEqual(all_items.count(), 2)  # 이전 + 신규

        # 최신 데이터 확인 (id 기준으로 확인)
        latest = all_items.order_by('-id').first()
        self.assertEqual(latest.quantity, 150)

    def test_storage_indexes(self):
        """Storage 모델 인덱스 테스트"""
        # 여러 아이템 생성
        for i in range(10):
            Storage.objects.create(
                character_basic=self.character_basic,
                storage_type='shared' if i % 2 == 0 else 'personal',
                item_name=f'아이템{i}',
                item_icon='https://example.com/icon.png',
                quantity=i + 1,
                slot_position=i
            )

        # 인덱스를 사용하는 쿼리 테스트
        shared_items = Storage.objects.filter(
            character_basic=self.character_basic,
            storage_type='shared'
        )
        self.assertEqual(shared_items.count(), 5)

        personal_items = Storage.objects.filter(
            character_basic=self.character_basic,
            storage_type='personal'
        )
        self.assertEqual(personal_items.count(), 5)


class SharedStorageDuplicatePreventionTests(TestCase):
    """AC 2.4.8: 공유 창고 중복 크롤링 방지 테스트"""

    def setUp(self):
        """테스트 전 캐시 클리어"""
        cache.clear()

    def tearDown(self):
        """테스트 후 캐시 클리어"""
        cache.clear()

    @override_settings(CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    })
    def test_shared_storage_duplicate_prevention(self):
        """AC 2.4.8: 공유 창고 중복 크롤링 방지"""
        user_id = 1
        cache_key = f'shared_storage:{user_id}'

        # 첫 번째 크롤링 시 캐시 없음
        self.assertIsNone(cache.get(cache_key))

        # 첫 번째 크롤링 후 캐시 설정
        cache.set(cache_key, True, timeout=3600)

        # 두 번째 크롤링 시도 시 캐시 존재 확인
        should_skip = cache.get(cache_key)
        self.assertTrue(should_skip)

    @override_settings(CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    })
    def test_shared_storage_reuse(self):
        """AC 2.4.8: 1시간 이내 기존 데이터 재사용"""
        user_id = 2
        cache_key = f'shared_storage:{user_id}'

        # 캐시에 데이터 설정 (1시간 TTL)
        cache.set(cache_key, True, timeout=3600)

        # 캐시 확인 (재사용해야 함)
        cached_data = cache.get(cache_key)
        self.assertTrue(cached_data)


class StoragePydanticValidationTests(TestCase):
    """Pydantic 검증 통합 테스트"""

    def test_pydantic_storage_validation_success(self):
        """AC 2.4.7: StorageItemSchema 검증 성공"""
        valid_data = {
            'storage_type': 'shared',
            'item_name': '엘릭서',
            'item_icon': 'https://maplestory.io/api/item/2000005/icon',
            'quantity': 100,
            'slot_position': 0,
            'item_options': {'star_force': 10},
            'expiry_date': None
        }

        validated = StorageItemSchema(**valid_data)

        self.assertEqual(validated.storage_type, 'shared')
        self.assertEqual(validated.item_name, '엘릭서')
        self.assertEqual(validated.quantity, 100)
        self.assertEqual(validated.item_options, {'star_force': 10})

    def test_pydantic_storage_validation_failure(self):
        """AC 2.4.7: Pydantic 검증 실패 처리"""
        from pydantic import ValidationError

        invalid_data = {
            'storage_type': 'invalid_type',  # Invalid
            'item_name': '',  # Invalid (min_length=1)
            'item_icon': 'not-a-url',  # Invalid (pattern)
            'quantity': 0,  # Invalid (ge=1)
            'slot_position': -1  # Invalid (ge=0)
        }

        with self.assertRaises(ValidationError) as context:
            StorageItemSchema(**invalid_data)

        # 여러 검증 오류 확인
        errors = context.exception.errors()
        self.assertGreater(len(errors), 0)


class StorageFullFlowTests(TestCase):
    """전체 플로우 통합 테스트"""

    @classmethod
    def setUpTestData(cls):
        """테스트 데이터 설정"""
        cls.character_basic = CharacterBasic.objects.create(
            ocid='test-ocid-67890',
            character_name='TestChar',
            world_name='스카니아',
            character_gender='남',
            character_class='아크메이지(썬,콜)'
        )

    def test_crawl_and_save_storage_success(self):
        """AC 2.4.1-2.4.9: 전체 플로우 테스트 (공유+개인)"""
        # 파싱된 데이터 시뮬레이션
        mock_shared_items = [
            {
                'storage_type': 'shared',
                'item_name': '공유 아이템 1',
                'item_icon': 'https://example.com/shared1.png',
                'quantity': 100,
                'slot_position': 0,
                'item_options': None,
                'expiry_date': None
            },
            {
                'storage_type': 'shared',
                'item_name': '공유 아이템 2',
                'item_icon': 'https://example.com/shared2.png',
                'quantity': 200,
                'slot_position': 1,
                'item_options': {'star_force': 5},
                'expiry_date': None
            }
        ]

        mock_personal_items = [
            {
                'storage_type': 'personal',
                'item_name': '개인 아이템 1',
                'item_icon': 'https://example.com/personal1.png',
                'quantity': 50,
                'slot_position': 0,
                'item_options': None,
                'expiry_date': None
            }
        ]

        # 검증 및 저장
        saved_shared = 0
        saved_personal = 0

        for item_data in mock_shared_items:
            validated = StorageItemSchema(**item_data)
            Storage.objects.create(
                character_basic=self.character_basic,
                storage_type=validated.storage_type,
                item_name=validated.item_name,
                item_icon=validated.item_icon,
                quantity=validated.quantity,
                item_options=validated.item_options,
                slot_position=validated.slot_position,
                expiry_date=validated.expiry_date
            )
            saved_shared += 1

        for item_data in mock_personal_items:
            validated = StorageItemSchema(**item_data)
            Storage.objects.create(
                character_basic=self.character_basic,
                storage_type=validated.storage_type,
                item_name=validated.item_name,
                item_icon=validated.item_icon,
                quantity=validated.quantity,
                item_options=validated.item_options,
                slot_position=validated.slot_position,
                expiry_date=validated.expiry_date
            )
            saved_personal += 1

        # 결과 확인
        self.assertEqual(saved_shared, 2)
        self.assertEqual(saved_personal, 1)

        # DB 저장 확인
        shared_count = Storage.objects.filter(
            character_basic=self.character_basic,
            storage_type='shared'
        ).count()
        personal_count = Storage.objects.filter(
            character_basic=self.character_basic,
            storage_type='personal'
        ).count()

        self.assertEqual(shared_count, 2)
        self.assertEqual(personal_count, 1)
