"""
Story 3.6: 창고 아이템 목록 조회 테스트

테스트 케이스:
- test_storage_list_authenticated: 인증 사용자 조회 성공 (AC-3.6.1)
- test_storage_list_unauthenticated: 미인증 시 401 반환
- test_storage_list_not_owner: 다른 사용자 캐릭터 조회 시 404 반환
- test_storage_items: 창고 아이템 정상 반환 (AC-3.6.3)
- test_storage_empty: 빈 창고 시 빈 배열 반환 (AC-3.6.4)
- test_storage_same_for_all_characters: 동일 사용자의 다른 캐릭터에서도 같은 창고 표시 (AC-3.6.2)
- test_storage_filter_expirable: 기간제 아이템 필터링
- test_storage_sort_by_name: 이름순 정렬
"""
import pytest
from datetime import timedelta
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from accounts.models import Character
from characters.models import CharacterBasic, Storage


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
        ocid='test_ocid_storage',
        character_name='테스트캐릭터',
        world_name='스카니아',
        character_class='아크메이지(불,독)',
        character_level=280
    )


@pytest.fixture
def test_character_2(db, test_user):
    """동일 사용자의 두 번째 캐릭터 (AC-3.6.2 테스트용)"""
    return Character.objects.create(
        user=test_user,
        ocid='test_ocid_storage_2',
        character_name='테스트캐릭터2',
        world_name='스카니아',
        character_class='팬텀',
        character_level=275
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
def test_character_basic_2(db, test_character_2):
    """두 번째 캐릭터의 CharacterBasic 생성"""
    return CharacterBasic.objects.create(
        ocid=test_character_2.ocid,
        character_name=test_character_2.character_name,
        world_name=test_character_2.world_name,
        character_gender='여',
        character_class=test_character_2.character_class
    )


@pytest.fixture
def test_storage_items(db, test_character_basic):
    """테스트 창고 아이템 생성"""
    crawled_at = timezone.now()
    items = []

    # 일반 아이템
    items.append(Storage.objects.create(
        character_basic=test_character_basic,
        storage_type='shared',
        item_name='영환불',
        item_icon='https://example.com/flame.png',
        quantity=50,
        slot_position=1,
        crawled_at=crawled_at
    ))

    # 장비 아이템 (강화 수치 포함)
    items.append(Storage.objects.create(
        character_basic=test_character_basic,
        storage_type='shared',
        item_name='아케인셰이드 스태프',
        item_icon='https://example.com/staff.png',
        quantity=1,
        item_options={'enhancement': 17, 'potential_grade': '유니크'},
        slot_position=2,
        crawled_at=crawled_at
    ))

    return items


@pytest.fixture
def test_expirable_storage_item(db, test_character_basic):
    """기간제 창고 아이템 생성"""
    return Storage.objects.create(
        character_basic=test_character_basic,
        storage_type='shared',
        item_name='30일 2배 쿠폰',
        item_icon='https://example.com/coupon.png',
        quantity=1,
        slot_position=3,
        expiry_date=timezone.now() + timedelta(days=15),
        crawled_at=timezone.now()
    )


@pytest.fixture
def authenticated_client(api_client, test_user):
    """인증된 API 클라이언트"""
    api_client.force_authenticate(user=test_user)
    return api_client


class TestStorageListAuthenticated:
    """인증된 사용자 창고 조회 테스트"""

    def test_storage_list_authenticated(
        self, authenticated_client, test_character, test_character_basic, test_storage_items
    ):
        """
        AC-3.6.1: 창고 탭 선택 시 창고 아이템 목록이 그리드 형태로 표시
        """
        response = authenticated_client.get(f'/characters/{test_character.ocid}/storage/')

        assert response.status_code == status.HTTP_200_OK
        assert 'items' in response.data
        assert 'total_count' in response.data
        assert response.data['total_count'] == 2
        assert len(response.data['items']) == 2


class TestStorageListUnauthenticated:
    """비인증 사용자 테스트"""

    def test_storage_list_unauthenticated(self, api_client, test_character):
        """
        비인증 사용자는 401 Unauthorized 응답을 받는다
        """
        response = api_client.get(f'/characters/{test_character.ocid}/storage/')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestStorageListNotOwner:
    """캐릭터 소유권 테스트"""

    def test_storage_list_not_owner(self, authenticated_client, other_user, db):
        """
        다른 사용자의 캐릭터 창고 조회 시 404 응답 (정보 노출 방지)
        """
        # 다른 사용자의 캐릭터 생성
        other_character = Character.objects.create(
            user=other_user,
            ocid='other_user_storage_ocid',
            character_name='다른캐릭터',
            world_name='베라',
            character_class='팬텀',
            character_level=290
        )

        response = authenticated_client.get(f'/characters/{other_character.ocid}/storage/')

        # 403 대신 404 반환 (정보 노출 방지)
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestStorageItems:
    """창고 아이템 필드 테스트"""

    def test_storage_item_fields(
        self, authenticated_client, test_character, test_character_basic, test_storage_items
    ):
        """
        AC-3.6.3: 각 아이템은 아이콘, 이름, 수량, 강화 수치 포함
        """
        response = authenticated_client.get(f'/characters/{test_character.ocid}/storage/')

        assert response.status_code == status.HTTP_200_OK
        item = response.data['items'][0]

        # 필수 필드 확인
        assert 'id' in item
        assert 'item_name' in item
        assert 'item_icon' in item
        assert 'quantity' in item
        assert 'storage_type' in item
        assert 'item_options' in item
        assert 'slot_position' in item
        assert 'expiry_date' in item
        assert 'crawled_at' in item
        assert 'days_until_expiry' in item
        assert 'is_expirable' in item

    def test_storage_item_with_enhancement(
        self, authenticated_client, test_character, test_character_basic, test_storage_items
    ):
        """
        AC-3.6.3: 장비 아이템의 강화 수치(item_options.enhancement)가 포함
        """
        response = authenticated_client.get(f'/characters/{test_character.ocid}/storage/')

        assert response.status_code == status.HTTP_200_OK

        # 장비 아이템 찾기 (item_options가 있는 아이템)
        equip_item = next(
            (item for item in response.data['items'] if item['item_options'] is not None),
            None
        )

        assert equip_item is not None
        assert equip_item['item_options']['enhancement'] == 17


class TestStorageListEmpty:
    """빈 창고 테스트"""

    def test_storage_list_empty(
        self, authenticated_client, test_character, test_character_basic
    ):
        """
        AC-3.6.4: 빈 창고인 경우 빈 배열 반환
        """
        response = authenticated_client.get(f'/characters/{test_character.ocid}/storage/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['total_count'] == 0
        assert response.data['items'] == []


class TestStorageSameForAllCharacters:
    """AC-3.6.2: 계정 공유 창고 테스트"""

    def test_storage_same_for_all_characters(
        self, authenticated_client, test_character, test_character_2,
        test_character_basic, test_character_basic_2, test_storage_items
    ):
        """
        AC-3.6.2: 동일 사용자의 여러 캐릭터에서 동일한 창고 아이템 목록 표시

        창고는 계정 공유이므로, 어떤 캐릭터로 조회해도 동일한 결과가 반환되어야 함
        """
        # 첫 번째 캐릭터로 조회
        response1 = authenticated_client.get(f'/characters/{test_character.ocid}/storage/')

        # 두 번째 캐릭터로 조회
        response2 = authenticated_client.get(f'/characters/{test_character_2.ocid}/storage/')

        assert response1.status_code == status.HTTP_200_OK
        assert response2.status_code == status.HTTP_200_OK

        # 동일한 아이템 개수
        assert response1.data['total_count'] == response2.data['total_count']

        # 동일한 아이템 목록 (id로 비교)
        items1_ids = {item['id'] for item in response1.data['items']}
        items2_ids = {item['id'] for item in response2.data['items']}
        assert items1_ids == items2_ids


class TestStorageExpirable:
    """기간제 아이템 테스트"""

    def test_storage_expirable_item(
        self, authenticated_client, test_character, test_character_basic, test_expirable_storage_item
    ):
        """
        기간제 아이템의 days_until_expiry 필드가 정확히 계산되는지 확인
        """
        response = authenticated_client.get(f'/characters/{test_character.ocid}/storage/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['items']) == 1

        item = response.data['items'][0]
        assert item['is_expirable'] is True
        assert item['days_until_expiry'] is not None
        assert item['days_until_expiry'] >= 14  # 15일 후 만료 - 약간의 시간 오차 허용
        assert item['days_until_expiry'] <= 15

    def test_storage_filter_expirable(
        self, authenticated_client, test_character, test_character_basic,
        test_storage_items, test_expirable_storage_item
    ):
        """
        category=expirable 시 기간제 아이템만 반환
        """
        response = authenticated_client.get(
            f'/characters/{test_character.ocid}/storage/?category=expirable'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['total_count'] == 1
        assert response.data['category'] == 'expirable'

        # 모든 아이템이 기간제인지 확인
        for item in response.data['items']:
            assert item['is_expirable'] is True
            assert item['expiry_date'] is not None


class TestStorageSort:
    """정렬 테스트"""

    def test_storage_sort_by_name_asc(
        self, authenticated_client, test_character, test_character_basic, test_storage_items
    ):
        """
        sort=item_name&order=asc 시 이름 오름차순 정렬
        """
        response = authenticated_client.get(
            f'/characters/{test_character.ocid}/storage/?sort=item_name&order=asc'
        )

        assert response.status_code == status.HTTP_200_OK
        items = response.data['items']

        # 이름 오름차순 정렬 확인 (가나다순)
        if len(items) >= 2:
            names = [item['item_name'] for item in items]
            assert names == sorted(names)

    def test_storage_sort_by_name_desc(
        self, authenticated_client, test_character, test_character_basic, test_storage_items
    ):
        """
        sort=item_name&order=desc 시 이름 내림차순 정렬
        """
        response = authenticated_client.get(
            f'/characters/{test_character.ocid}/storage/?sort=item_name&order=desc'
        )

        assert response.status_code == status.HTTP_200_OK
        items = response.data['items']

        # 이름 내림차순 정렬 확인
        if len(items) >= 2:
            names = [item['item_name'] for item in items]
            assert names == sorted(names, reverse=True)


class TestStorageLastCrawledAt:
    """크롤링 시간 테스트"""

    def test_storage_last_crawled_at(
        self, authenticated_client, test_character, test_character_basic, test_storage_items
    ):
        """
        last_crawled_at 필드가 올바르게 반환되는지 확인
        """
        response = authenticated_client.get(f'/characters/{test_character.ocid}/storage/')

        assert response.status_code == status.HTTP_200_OK
        assert 'last_crawled_at' in response.data
        assert response.data['last_crawled_at'] is not None

    def test_storage_last_crawled_at_empty(
        self, authenticated_client, test_character, test_character_basic
    ):
        """
        아이템이 없을 때 last_crawled_at은 None
        """
        response = authenticated_client.get(f'/characters/{test_character.ocid}/storage/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['last_crawled_at'] is None
