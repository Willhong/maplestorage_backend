"""
Story 4.1: 통합 아이템 검색 API 테스트

테스트 케이스:
- test_item_search_success: 아이템 검색 성공
- test_item_search_multiple_characters: 여러 캐릭터에서 검색
- test_item_search_filter_by_type: item_type 필터링
- test_item_search_filter_by_location_inventory: 인벤토리만 검색
- test_item_search_filter_by_location_storage: 창고만 검색
- test_item_search_pagination: 페이지네이션 동작 확인
- test_item_search_empty_results: 결과 없는 경우
- test_item_search_no_query: 검색어 없는 경우 400 에러
- test_item_search_invalid_type: 잘못된 item_type 400 에러
- test_item_search_unauthorized: 비인증 사용자 401 에러
- test_item_search_no_characters: 캐릭터 없는 사용자 빈 결과
- test_item_search_case_insensitive: 대소문자 무시 검색
"""
import pytest
from datetime import timedelta
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from accounts.models import Character
from characters.models import CharacterBasic, Inventory, Storage


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
    """다른 사용자 생성"""
    return User.objects.create_user(
        username='otheruser',
        email='other@example.com',
        password='otherpassword123'
    )


@pytest.fixture
def test_character1(db, test_user):
    """테스트 캐릭터 1"""
    return Character.objects.create(
        user=test_user,
        ocid='test_ocid_1',
        character_name='캐릭터1',
        world_name='스카니아',
        character_class='아크메이지(불,독)',
        character_level=280
    )


@pytest.fixture
def test_character2(db, test_user):
    """테스트 캐릭터 2"""
    return Character.objects.create(
        user=test_user,
        ocid='test_ocid_2',
        character_name='캐릭터2',
        world_name='베라',
        character_class='나이트로드',
        character_level=250
    )


@pytest.fixture
def test_character_basic1(db, test_character1):
    """테스트 CharacterBasic 1"""
    return CharacterBasic.objects.create(
        ocid=test_character1.ocid,
        character_name=test_character1.character_name,
        world_name=test_character1.world_name,
        character_gender='남',
        character_class=test_character1.character_class
    )


@pytest.fixture
def test_character_basic2(db, test_character2):
    """테스트 CharacterBasic 2"""
    return CharacterBasic.objects.create(
        ocid=test_character2.ocid,
        character_name=test_character2.character_name,
        world_name=test_character2.world_name,
        character_gender='여',
        character_class=test_character2.character_class
    )


@pytest.fixture
def sample_inventory_items(db, test_character_basic1):
    """샘플 인벤토리 아이템 생성"""
    now = timezone.now()
    items = [
        Inventory.objects.create(
            character_basic=test_character_basic1,
            item_type='equips',
            item_name='강화 주문서',
            item_icon='http://example.com/icon1.png',
            quantity=5,
            slot_position=1,
            crawled_at=now
        ),
        Inventory.objects.create(
            character_basic=test_character_basic1,
            item_type='consumables',
            item_name='강화의 물약',
            item_icon='http://example.com/icon2.png',
            quantity=10,
            slot_position=2,
            crawled_at=now
        ),
        Inventory.objects.create(
            character_basic=test_character_basic1,
            item_type='miscs',
            item_name='메이플스토리 기념 코인',
            item_icon='http://example.com/icon3.png',
            quantity=1,
            slot_position=3,
            crawled_at=now
        ),
    ]
    return items


@pytest.fixture
def sample_storage_items(db, test_character_basic1):
    """샘플 창고 아이템 생성"""
    now = timezone.now()
    items = [
        Storage.objects.create(
            character_basic=test_character_basic1,
            storage_type='shared',
            item_name='강화석',
            item_icon='http://example.com/storage1.png',
            quantity=20,
            slot_position=1,
            crawled_at=now
        ),
        Storage.objects.create(
            character_basic=test_character_basic1,
            storage_type='shared',
            item_name='메이플 장비',
            item_icon='http://example.com/storage2.png',
            quantity=1,
            slot_position=2,
            crawled_at=now
        ),
    ]
    return items


@pytest.mark.django_db
class TestItemSearchView:
    """아이템 검색 뷰 테스트"""

    def test_item_search_success(self, api_client, test_user, test_character1,
                                  test_character_basic1, sample_inventory_items):
        """기본 아이템 검색 성공 테스트"""
        api_client.force_authenticate(user=test_user)

        response = api_client.get('/characters/search/items/', {'q': '강화'})

        assert response.status_code == status.HTTP_200_OK
        assert 'count' in response.data
        assert 'results' in response.data
        assert response.data['count'] == 2  # '강화 주문서', '강화의 물약'

        # 결과 필드 확인
        result = response.data['results'][0]
        assert 'item_name' in result
        assert 'item_type' in result
        assert 'quantity' in result
        assert 'item_icon' in result
        assert 'location' in result
        assert 'character_name' in result
        assert 'character_ocid' in result
        assert 'world_name' in result

    def test_item_search_multiple_characters(self, api_client, test_user,
                                             test_character1, test_character2,
                                             test_character_basic1, test_character_basic2):
        """여러 캐릭터에서 아이템 검색"""
        api_client.force_authenticate(user=test_user)

        now = timezone.now()
        # 캐릭터1의 인벤토리
        Inventory.objects.create(
            character_basic=test_character_basic1,
            item_type='consumables',
            item_name='힘의 물약',
            item_icon='http://example.com/item1.png',
            quantity=10,
            slot_position=1,
            crawled_at=now
        )

        # 캐릭터2의 인벤토리
        Inventory.objects.create(
            character_basic=test_character_basic2,
            item_type='consumables',
            item_name='힘의 물약',
            item_icon='http://example.com/item1.png',
            quantity=5,
            slot_position=1,
            crawled_at=now
        )

        response = api_client.get('/characters/search/items/', {'q': '힘의 물약'})

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 2

        # 두 캐릭터에서 각각 검색되어야 함
        character_names = [r['character_name'] for r in response.data['results']]
        assert '캐릭터1' in character_names
        assert '캐릭터2' in character_names

    def test_item_search_filter_by_type(self, api_client, test_user,
                                        test_character1, test_character_basic1,
                                        sample_inventory_items):
        """item_type 필터링 테스트"""
        api_client.force_authenticate(user=test_user)

        # equips 타입만 검색
        response = api_client.get('/characters/search/items/', {
            'q': '강화',
            'type': 'equips'
        })

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert response.data['results'][0]['item_name'] == '강화 주문서'

    def test_item_search_filter_by_location_inventory(self, api_client, test_user,
                                                       test_character1, test_character_basic1,
                                                       sample_inventory_items, sample_storage_items):
        """인벤토리만 검색 (location=inventory)"""
        api_client.force_authenticate(user=test_user)

        response = api_client.get('/characters/search/items/', {
            'q': '강화',
            'location': 'inventory'
        })

        assert response.status_code == status.HTTP_200_OK
        # 인벤토리: '강화 주문서', '강화의 물약'
        assert response.data['count'] == 2
        for result in response.data['results']:
            assert result['location'] == 'inventory'

    def test_item_search_filter_by_location_storage(self, api_client, test_user,
                                                     test_character1, test_character_basic1,
                                                     sample_inventory_items, sample_storage_items):
        """창고만 검색 (location=storage)"""
        api_client.force_authenticate(user=test_user)

        response = api_client.get('/characters/search/items/', {
            'q': '강화',
            'location': 'storage'
        })

        assert response.status_code == status.HTTP_200_OK
        # 창고: '강화석'
        assert response.data['count'] == 1
        assert response.data['results'][0]['location'] == 'storage'
        assert response.data['results'][0]['item_name'] == '강화석'

    def test_item_search_pagination(self, api_client, test_user,
                                    test_character1, test_character_basic1):
        """페이지네이션 동작 확인"""
        api_client.force_authenticate(user=test_user)

        now = timezone.now()
        # 15개의 아이템 생성
        for i in range(15):
            Inventory.objects.create(
                character_basic=test_character_basic1,
                item_type='miscs',
                item_name=f'테스트 아이템 {i+1}',
                item_icon='http://example.com/icon.png',
                quantity=1,
                slot_position=i+1,
                crawled_at=now
            )

        # 첫 페이지 (page_size=5)
        response = api_client.get('/characters/search/items/', {
            'q': '테스트',
            'page_size': 5,
            'page': 1
        })

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 15
        assert len(response.data['results']) == 5
        assert response.data['next'] is not None
        assert response.data['previous'] is None

        # 두 번째 페이지
        response = api_client.get('/characters/search/items/', {
            'q': '테스트',
            'page_size': 5,
            'page': 2
        })

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 5
        assert response.data['previous'] is not None

    def test_item_search_empty_results(self, api_client, test_user,
                                       test_character1, test_character_basic1,
                                       sample_inventory_items):
        """결과 없는 검색"""
        api_client.force_authenticate(user=test_user)

        response = api_client.get('/characters/search/items/', {'q': '존재하지않는아이템'})

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 0
        assert response.data['results'] == []

    def test_item_search_no_query(self, api_client, test_user):
        """검색어 없는 경우 400 에러"""
        api_client.force_authenticate(user=test_user)

        response = api_client.get('/characters/search/items/')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data

    def test_item_search_invalid_type(self, api_client, test_user,
                                      test_character1, test_character_basic1):
        """잘못된 item_type 400 에러"""
        api_client.force_authenticate(user=test_user)

        response = api_client.get('/characters/search/items/', {
            'q': '아이템',
            'type': 'invalid_type'
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data

    def test_item_search_unauthorized(self, api_client):
        """비인증 사용자 401 에러"""
        response = api_client.get('/characters/search/items/', {'q': '아이템'})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_item_search_no_characters(self, api_client, test_user):
        """캐릭터 없는 사용자 빈 결과"""
        api_client.force_authenticate(user=test_user)

        response = api_client.get('/characters/search/items/', {'q': '아이템'})

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 0
        assert response.data['results'] == []

    def test_item_search_case_insensitive(self, api_client, test_user,
                                          test_character1, test_character_basic1):
        """대소문자 무시 검색 (영문 아이템 가정)"""
        api_client.force_authenticate(user=test_user)

        now = timezone.now()
        Inventory.objects.create(
            character_basic=test_character_basic1,
            item_type='consumables',
            item_name='Power Elixir',
            item_icon='http://example.com/elixir.png',
            quantity=10,
            slot_position=1,
            crawled_at=now
        )

        # 소문자로 검색
        response = api_client.get('/characters/search/items/', {'q': 'power'})

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert 'Power Elixir' in response.data['results'][0]['item_name']

        # 대문자로 검색
        response = api_client.get('/characters/search/items/', {'q': 'POWER'})

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1

    def test_item_search_includes_both_locations(self, api_client, test_user,
                                                  test_character1, test_character_basic1,
                                                  sample_inventory_items, sample_storage_items):
        """location=all 시 인벤토리와 창고 모두 검색"""
        api_client.force_authenticate(user=test_user)

        response = api_client.get('/characters/search/items/', {
            'q': '강화',
            'location': 'all'
        })

        assert response.status_code == status.HTTP_200_OK
        # 인벤토리: '강화 주문서', '강화의 물약'
        # 창고: '강화석'
        assert response.data['count'] == 3

        locations = [r['location'] for r in response.data['results']]
        assert 'inventory' in locations
        assert 'storage' in locations

    def test_item_search_latest_crawl_only(self, api_client, test_user,
                                           test_character1, test_character_basic1):
        """최신 크롤링 데이터만 검색되는지 확인"""
        api_client.force_authenticate(user=test_user)

        old_time = timezone.now() - timedelta(days=1)
        new_time = timezone.now()

        # 이전 크롤링 데이터
        Inventory.objects.create(
            character_basic=test_character_basic1,
            item_type='miscs',
            item_name='구버전 아이템',
            item_icon='http://example.com/old.png',
            quantity=1,
            slot_position=1,
            crawled_at=old_time
        )

        # 최신 크롤링 데이터
        Inventory.objects.create(
            character_basic=test_character_basic1,
            item_type='miscs',
            item_name='신규 아이템',
            item_icon='http://example.com/new.png',
            quantity=1,
            slot_position=1,
            crawled_at=new_time
        )

        response = api_client.get('/characters/search/items/', {'q': '아이템'})

        assert response.status_code == status.HTTP_200_OK
        # 최신 크롤링 데이터만 반환 (신규 아이템만)
        assert response.data['count'] == 1
        assert response.data['results'][0]['item_name'] == '신규 아이템'

    def test_item_search_expirable_fields(self, api_client, test_user,
                                          test_character1, test_character_basic1):
        """기간제 아이템 필드 확인"""
        api_client.force_authenticate(user=test_user)

        now = timezone.now()
        expiry_date = now + timedelta(days=3)

        Inventory.objects.create(
            character_basic=test_character_basic1,
            item_type='consumables',
            item_name='기간제 아이템',
            item_icon='http://example.com/expirable.png',
            quantity=1,
            slot_position=1,
            expiry_date=expiry_date,
            crawled_at=now
        )

        response = api_client.get('/characters/search/items/', {'q': '기간제'})

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1

        result = response.data['results'][0]
        assert result['is_expirable'] is True
        assert result['expiry_date'] is not None
        assert result['days_until_expiry'] == 3
