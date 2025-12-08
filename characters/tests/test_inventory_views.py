"""
Story 3.4: 인벤토리 아이템 목록 조회 테스트
Story 3.5: 카테고리별 필터링 테스트

테스트 케이스:
- test_inventory_list_success: 인벤토리 목록 조회 성공 (AC-3.4.1)
- test_inventory_list_empty: 아이템 없는 경우 빈 배열 반환 (AC-3.4.3)
- test_inventory_list_with_expirable: 기간제 아이템 days_until_expiry 확인 (AC-3.4.4)
- test_inventory_list_not_found: 존재하지 않는 캐릭터 404 응답
- test_inventory_list_unauthorized: 비인증 사용자 401 응답
- test_inventory_list_other_user_character: 다른 사용자 캐릭터 404 응답
- test_inventory_list_response_fields: 응답 필드 확인 (AC-3.4.2)

Story 3.5 테스트 케이스:
- test_inventory_filter_all: 전체 필터 동작 확인 (AC-3.5.1, AC-3.5.2)
- test_inventory_filter_equipment: 장비만 필터링 (AC-3.5.1)
- test_inventory_filter_consumable: 소비만 필터링 (AC-3.5.1)
- test_inventory_filter_etc: 기타만 필터링 (AC-3.5.1)
- test_inventory_filter_expirable: 기간제만 필터링 (AC-3.5.1)
- test_inventory_filter_invalid: 잘못된 카테고리 무시 (all로 처리) (AC-3.5.2)
"""
import pytest
from datetime import timedelta
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from accounts.models import Character
from characters.models import CharacterBasic, Inventory


# Override cache clearing fixture to avoid Redis connection issues
@pytest.fixture(autouse=True)
def clear_cache():
    """각 테스트 전에 캐시 초기화 (Redis 없이 동작)"""
    try:
        from django.core.cache import cache
        cache.clear()
    except Exception:
        pass  # Redis 연결 실패 시 무시
    yield
    try:
        from django.core.cache import cache
        cache.clear()
    except Exception:
        pass


@pytest.fixture
def api_client():
    """API 테스트를 위한 클라이언트"""
    return APIClient()


@pytest.fixture
def test_user(db):
    """테스트 사용자 생성"""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpassword123'
    )


@pytest.fixture
def other_user(db):
    """다른 사용자 생성 (ownership 테스트용)"""
    return User.objects.create_user(
        username='otheruser',
        email='other@example.com',
        password='otherpassword123'
    )


@pytest.fixture
def test_character(db, test_user):
    """테스트 캐릭터 생성 (accounts.Character)"""
    return Character.objects.create(
        user=test_user,
        ocid='test_ocid_12345',
        character_name='테스트캐릭터',
        world_name='스카니아',
        character_class='아크메이지(불,독)',
        character_level=280
    )


@pytest.fixture
def test_character_basic(db, test_character):
    """테스트 CharacterBasic 생성"""
    return CharacterBasic.objects.create(
        ocid=test_character.ocid,
        character_name=test_character.character_name,
        world_name=test_character.world_name,
        character_gender='남',
        character_class=test_character.character_class
    )


@pytest.fixture
def test_inventory_items(db, test_character_basic):
    """테스트 인벤토리 아이템 생성"""
    crawled_at = timezone.now()
    items = []

    # 일반 아이템
    items.append(Inventory.objects.create(
        character_basic=test_character_basic,
        item_type='consumables',
        item_name='엘릭서',
        item_icon='https://example.com/elixir.png',
        quantity=100,
        slot_position=1,
        crawled_at=crawled_at
    ))

    # 장비 아이템 (강화 수치 포함)
    items.append(Inventory.objects.create(
        character_basic=test_character_basic,
        item_type='equips',
        item_name='아케인셰이드 스태프',
        item_icon='https://example.com/staff.png',
        quantity=1,
        item_options={'enhancement': 22, 'potential_grade': '레전드리'},
        slot_position=2,
        crawled_at=crawled_at
    ))

    return items


@pytest.fixture
def test_expirable_item(db, test_character_basic):
    """기간제 아이템 생성"""
    return Inventory.objects.create(
        character_basic=test_character_basic,
        item_type='cashes',
        item_name='7일 펫',
        item_icon='https://example.com/pet.png',
        quantity=1,
        slot_position=3,
        expiry_date=timezone.now() + timedelta(days=5),
        crawled_at=timezone.now()
    )


@pytest.fixture
def authenticated_client(api_client, test_user):
    """인증된 API 클라이언트"""
    api_client.force_authenticate(user=test_user)
    return api_client


class TestInventoryListSuccess:
    """인벤토리 목록 조회 성공 테스트"""

    def test_inventory_list_success(
        self, authenticated_client, test_character, test_character_basic, test_inventory_items
    ):
        """
        AC-3.4.1: 인벤토리 데이터를 조회하면 모든 인벤토리 아이템이 반환된다
        """
        response = authenticated_client.get(f'/characters/{test_character.ocid}/inventory/')

        assert response.status_code == status.HTTP_200_OK
        assert 'character_name' in response.data
        assert 'items' in response.data
        assert 'total_count' in response.data
        assert response.data['total_count'] == 2
        assert len(response.data['items']) == 2

    def test_inventory_list_response_fields(
        self, authenticated_client, test_character, test_character_basic, test_inventory_items
    ):
        """
        AC-3.4.2: 각 아이템에 필수 필드가 포함되어 있는지 확인
        - id, item_name, item_icon, quantity, item_type, item_options
        - slot_position, expiry_date, crawled_at, days_until_expiry, is_expirable
        """
        response = authenticated_client.get(f'/characters/{test_character.ocid}/inventory/')

        assert response.status_code == status.HTTP_200_OK
        item = response.data['items'][0]

        # 필수 필드 확인
        assert 'id' in item
        assert 'item_name' in item
        assert 'item_icon' in item
        assert 'quantity' in item
        assert 'item_type' in item
        assert 'item_options' in item
        assert 'slot_position' in item
        assert 'expiry_date' in item
        assert 'crawled_at' in item
        assert 'days_until_expiry' in item
        assert 'is_expirable' in item

    def test_inventory_item_with_enhancement(
        self, authenticated_client, test_character, test_character_basic, test_inventory_items
    ):
        """
        AC-3.4.2: 장비 아이템의 강화 수치(item_options.enhancement)가 포함되어 있는지 확인
        """
        response = authenticated_client.get(f'/characters/{test_character.ocid}/inventory/')

        assert response.status_code == status.HTTP_200_OK

        # 장비 아이템 찾기
        equip_item = next(
            (item for item in response.data['items'] if item['item_type'] == 'equips'),
            None
        )

        assert equip_item is not None
        assert equip_item['item_options'] is not None
        assert equip_item['item_options']['enhancement'] == 22


class TestInventoryListEmpty:
    """인벤토리가 비어있는 경우 테스트"""

    def test_inventory_list_empty(
        self, authenticated_client, test_character, test_character_basic
    ):
        """
        AC-3.4.3: 아이템이 없는 경우 빈 배열 반환
        """
        response = authenticated_client.get(f'/characters/{test_character.ocid}/inventory/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['total_count'] == 0
        assert response.data['items'] == []


class TestInventoryListExpirable:
    """기간제 아이템 테스트"""

    def test_inventory_list_with_expirable(
        self, authenticated_client, test_character, test_character_basic, test_expirable_item
    ):
        """
        AC-3.4.4: 기간제 아이템의 days_until_expiry 필드가 정확히 계산되는지 확인
        """
        response = authenticated_client.get(f'/characters/{test_character.ocid}/inventory/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['items']) == 1

        item = response.data['items'][0]
        assert item['is_expirable'] is True
        assert item['days_until_expiry'] is not None
        assert item['days_until_expiry'] >= 4  # 5일 후 만료 - 약간의 시간 오차 허용
        assert item['days_until_expiry'] <= 5

    def test_inventory_list_non_expirable_item(
        self, authenticated_client, test_character, test_character_basic, test_inventory_items
    ):
        """
        비기간제 아이템의 days_until_expiry는 None, is_expirable은 False
        """
        response = authenticated_client.get(f'/characters/{test_character.ocid}/inventory/')

        assert response.status_code == status.HTTP_200_OK

        # 비기간제 아이템 찾기
        non_expirable = next(
            (item for item in response.data['items'] if item['expiry_date'] is None),
            None
        )

        assert non_expirable is not None
        assert non_expirable['is_expirable'] is False
        assert non_expirable['days_until_expiry'] is None


class TestInventoryListNotFound:
    """캐릭터 없음 테스트"""

    def test_inventory_list_not_found(self, authenticated_client):
        """
        존재하지 않는 캐릭터의 인벤토리 조회 시 404 응답
        """
        response = authenticated_client.get('/characters/non_existent_ocid/inventory/')

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'error' in response.data


class TestInventoryListUnauthorized:
    """비인증 사용자 테스트"""

    def test_inventory_list_unauthorized(self, api_client, test_character):
        """
        AC-3.4.6 (시스템 관점): 비인증 사용자는 401 Unauthorized 응답을 받는다
        """
        response = api_client.get(f'/characters/{test_character.ocid}/inventory/')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestInventoryListOwnership:
    """캐릭터 소유권 테스트"""

    def test_inventory_list_other_user_character(
        self, authenticated_client, other_user, db
    ):
        """
        다른 사용자의 캐릭터 인벤토리 조회 시 404 응답 (정보 노출 방지)
        """
        # 다른 사용자의 캐릭터 생성
        other_character = Character.objects.create(
            user=other_user,
            ocid='other_user_ocid',
            character_name='다른캐릭터',
            world_name='베라',
            character_class='팬텀',
            character_level=290
        )

        other_basic = CharacterBasic.objects.create(
            ocid=other_character.ocid,
            character_name=other_character.character_name,
            world_name=other_character.world_name,
            character_gender='여',
            character_class=other_character.character_class
        )

        response = authenticated_client.get(f'/characters/{other_character.ocid}/inventory/')

        # 403 대신 404 반환 (정보 노출 방지)
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestInventoryListCrawledAt:
    """크롤링 시간 테스트"""

    def test_inventory_list_last_crawled_at(
        self, authenticated_client, test_character, test_character_basic, test_inventory_items
    ):
        """
        last_crawled_at 필드가 올바르게 반환되는지 확인
        """
        response = authenticated_client.get(f'/characters/{test_character.ocid}/inventory/')

        assert response.status_code == status.HTTP_200_OK
        assert 'last_crawled_at' in response.data
        assert response.data['last_crawled_at'] is not None

    def test_inventory_list_last_crawled_at_empty(
        self, authenticated_client, test_character, test_character_basic
    ):
        """
        아이템이 없을 때 last_crawled_at은 None
        """
        response = authenticated_client.get(f'/characters/{test_character.ocid}/inventory/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['last_crawled_at'] is None


# =============================================================================
# Story 3.5: 카테고리별 필터링 테스트
# =============================================================================


@pytest.fixture
def test_mixed_inventory(db, test_character_basic):
    """다양한 카테고리의 인벤토리 아이템 생성 (필터링 테스트용)"""
    crawled_at = timezone.now()
    items = []

    # 장비 아이템 2개
    items.append(Inventory.objects.create(
        character_basic=test_character_basic,
        item_type='equips',
        item_name='아케인셰이드 스태프',
        item_icon='https://example.com/staff.png',
        quantity=1,
        item_options={'enhancement': 22},
        slot_position=1,
        crawled_at=crawled_at
    ))
    items.append(Inventory.objects.create(
        character_basic=test_character_basic,
        item_type='equips',
        item_name='아케인셰이드 로브',
        item_icon='https://example.com/robe.png',
        quantity=1,
        slot_position=2,
        crawled_at=crawled_at
    ))

    # 소비 아이템 3개
    items.append(Inventory.objects.create(
        character_basic=test_character_basic,
        item_type='consumables',
        item_name='엘릭서',
        item_icon='https://example.com/elixir.png',
        quantity=100,
        slot_position=3,
        crawled_at=crawled_at
    ))
    items.append(Inventory.objects.create(
        character_basic=test_character_basic,
        item_type='consumables',
        item_name='파워 엘릭서',
        item_icon='https://example.com/power_elixir.png',
        quantity=50,
        slot_position=4,
        crawled_at=crawled_at
    ))
    items.append(Inventory.objects.create(
        character_basic=test_character_basic,
        item_type='consumables',
        item_name='경험치 2배 쿠폰',
        item_icon='https://example.com/exp_coupon.png',
        quantity=1,
        slot_position=5,
        expiry_date=timezone.now() + timedelta(days=3),  # 기간제 소비
        crawled_at=crawled_at
    ))

    # 기타 아이템 2개
    items.append(Inventory.objects.create(
        character_basic=test_character_basic,
        item_type='miscs',
        item_name='영원의 환생의 불꽃',
        item_icon='https://example.com/flame.png',
        quantity=10,
        slot_position=6,
        crawled_at=crawled_at
    ))
    items.append(Inventory.objects.create(
        character_basic=test_character_basic,
        item_type='miscs',
        item_name='스타포스 강화 주문서',
        item_icon='https://example.com/starforce.png',
        quantity=5,
        slot_position=7,
        crawled_at=crawled_at
    ))

    # 기간제 아이템 (캐시) 1개
    items.append(Inventory.objects.create(
        character_basic=test_character_basic,
        item_type='cashes',
        item_name='30일 펫',
        item_icon='https://example.com/pet.png',
        quantity=1,
        slot_position=8,
        expiry_date=timezone.now() + timedelta(days=25),  # 기간제
        crawled_at=crawled_at
    ))

    return items


class TestInventoryFilterAll:
    """Story 3.5: 전체 필터 테스트"""

    def test_inventory_filter_all_explicit(
        self, authenticated_client, test_character, test_character_basic, test_mixed_inventory
    ):
        """
        AC-3.5.1, AC-3.5.2: category=all 시 모든 아이템 반환
        """
        response = authenticated_client.get(
            f'/characters/{test_character.ocid}/inventory/?category=all'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['total_count'] == 8  # 전체 아이템 개수
        assert response.data['category'] == 'all'

    def test_inventory_filter_default_is_all(
        self, authenticated_client, test_character, test_character_basic, test_mixed_inventory
    ):
        """
        AC-3.5.2: 카테고리 미지정 시 기본값은 all
        """
        response = authenticated_client.get(
            f'/characters/{test_character.ocid}/inventory/'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['total_count'] == 8
        assert response.data['category'] == 'all'


class TestInventoryFilterEquipment:
    """Story 3.5: 장비 필터 테스트"""

    def test_inventory_filter_equipment(
        self, authenticated_client, test_character, test_character_basic, test_mixed_inventory
    ):
        """
        AC-3.5.1: category=equipment 시 장비 아이템만 반환
        """
        response = authenticated_client.get(
            f'/characters/{test_character.ocid}/inventory/?category=equipment'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['total_count'] == 2  # 장비 2개
        assert response.data['category'] == 'equipment'

        # 모든 아이템이 장비인지 확인
        for item in response.data['items']:
            assert item['item_type'] == 'equips'


class TestInventoryFilterConsumable:
    """Story 3.5: 소비 필터 테스트"""

    def test_inventory_filter_consumable(
        self, authenticated_client, test_character, test_character_basic, test_mixed_inventory
    ):
        """
        AC-3.5.1: category=consumable 시 소비 아이템만 반환
        """
        response = authenticated_client.get(
            f'/characters/{test_character.ocid}/inventory/?category=consumable'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['total_count'] == 3  # 소비 3개
        assert response.data['category'] == 'consumable'

        # 모든 아이템이 소비인지 확인
        for item in response.data['items']:
            assert item['item_type'] == 'consumables'


class TestInventoryFilterEtc:
    """Story 3.5: 기타 필터 테스트"""

    def test_inventory_filter_etc(
        self, authenticated_client, test_character, test_character_basic, test_mixed_inventory
    ):
        """
        AC-3.5.1: category=etc 시 기타 아이템만 반환
        """
        response = authenticated_client.get(
            f'/characters/{test_character.ocid}/inventory/?category=etc'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['total_count'] == 2  # 기타 2개
        assert response.data['category'] == 'etc'

        # 모든 아이템이 기타인지 확인
        for item in response.data['items']:
            assert item['item_type'] == 'miscs'


class TestInventoryFilterExpirable:
    """Story 3.5: 기간제 필터 테스트"""

    def test_inventory_filter_expirable(
        self, authenticated_client, test_character, test_character_basic, test_mixed_inventory
    ):
        """
        AC-3.5.1: category=expirable 시 기간제 아이템만 반환
        (expiry_date가 있는 아이템)
        """
        response = authenticated_client.get(
            f'/characters/{test_character.ocid}/inventory/?category=expirable'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['total_count'] == 2  # 기간제 2개 (경험치 쿠폰 + 펫)
        assert response.data['category'] == 'expirable'

        # 모든 아이템이 기간제인지 확인
        for item in response.data['items']:
            assert item['is_expirable'] is True
            assert item['expiry_date'] is not None


class TestInventoryFilterInvalid:
    """Story 3.5: 잘못된 카테고리 테스트"""

    def test_inventory_filter_invalid_category(
        self, authenticated_client, test_character, test_character_basic, test_mixed_inventory
    ):
        """
        AC-3.5.2: 잘못된 카테고리는 무시하고 all로 처리
        """
        response = authenticated_client.get(
            f'/characters/{test_character.ocid}/inventory/?category=invalid_category'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['total_count'] == 8  # 전체 반환
        assert response.data['category'] == 'invalid_category'  # 요청한 카테고리 반환

    def test_inventory_filter_empty_category(
        self, authenticated_client, test_character, test_character_basic, test_mixed_inventory
    ):
        """
        빈 카테고리는 all로 처리 (기본값)
        """
        response = authenticated_client.get(
            f'/characters/{test_character.ocid}/inventory/?category='
        )

        assert response.status_code == status.HTTP_200_OK
        # 빈 문자열은 all이 아니므로 전체 반환
        assert response.data['total_count'] == 8
