"""
Story 3.1: 캐릭터 목록 조회 테스트

테스트 케이스:
- test_character_list_authenticated: 인증된 사용자 목록 조회 (AC-3.1.1)
- test_character_list_empty: 캐릭터 없는 경우 빈 배열 반환 (AC-3.1.3)
- test_character_list_order_by_created: 최근 등록순 정렬 확인 (AC-3.1.4)
- test_character_list_unauthorized: 비인증 사용자 401 응답
- test_character_list_only_own_characters: 본인 캐릭터만 조회
- test_character_list_response_format: 응답 형식 확인 (count, results)
- test_character_list_fields: 필드 포함 확인 (AC-3.1.2)
"""
import pytest
from datetime import timedelta
from unittest.mock import patch, MagicMock
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from accounts.models import Character, CrawlTask
from characters.models import CharacterBasic, CharacterBasicHistory, Inventory


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
def test_character_history(db, test_character_basic):
    """테스트 CharacterBasicHistory 생성"""
    return CharacterBasicHistory.objects.create(
        character=test_character_basic,
        date=timezone.now(),
        character_name=test_character_basic.character_name,
        character_class=test_character_basic.character_class,
        character_class_level='6',
        character_level=280,
        character_exp=1000000000,
        character_exp_rate='50.5',
        character_guild_name='테스트길드',
        character_image='https://example.com/test_image.png',
        access_flag=True,
        liberation_quest_clear_flag=True
    )


@pytest.fixture
def authenticated_client(api_client, test_user):
    """인증된 API 클라이언트"""
    api_client.force_authenticate(user=test_user)
    return api_client


class TestCharacterListAuthenticated:
    """인증된 사용자 캐릭터 목록 조회 테스트"""

    def test_character_list_authenticated(
        self, authenticated_client, test_character, test_character_basic, test_character_history
    ):
        """
        AC-3.1.1: 로그인한 사용자가 캐릭터 목록을 조회하면 모든 캐릭터가 표시된다
        """
        response = authenticated_client.get('/api/characters/')

        assert response.status_code == status.HTTP_200_OK
        assert 'count' in response.data
        assert 'results' in response.data
        assert response.data['count'] == 1
        assert len(response.data['results']) == 1

    def test_character_list_response_format(
        self, authenticated_client, test_character, test_character_basic, test_character_history
    ):
        """
        응답 형식 확인: {count: number, results: Character[]}
        """
        response = authenticated_client.get('/api/characters/')

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data['count'], int)
        assert isinstance(response.data['results'], list)

    def test_character_list_fields(
        self, authenticated_client, test_character, test_character_basic, test_character_history
    ):
        """
        AC-3.1.2: 각 캐릭터에 필수 필드가 포함되어 있는지 확인
        - id, ocid, character_name, world_name, character_class,
        - character_level, character_image, last_crawled_at, inventory_count, has_expiring_items
        """
        response = authenticated_client.get('/api/characters/')

        assert response.status_code == status.HTTP_200_OK
        character = response.data['results'][0]

        # 필수 필드 확인
        assert 'id' in character
        assert 'ocid' in character
        assert 'character_name' in character
        assert 'world_name' in character
        assert 'character_class' in character
        assert 'character_level' in character
        assert 'character_image' in character
        assert 'last_crawled_at' in character
        assert 'inventory_count' in character
        assert 'has_expiring_items' in character

        # 값 확인
        assert character['character_name'] == '테스트캐릭터'
        assert character['world_name'] == '스카니아'
        assert character['character_class'] == '아크메이지(불,독)'
        assert character['character_level'] == 280
        assert character['character_image'] == 'https://example.com/test_image.png'


class TestCharacterListEmpty:
    """캐릭터가 없는 경우 테스트"""

    def test_character_list_empty(self, authenticated_client):
        """
        AC-3.1.3: 캐릭터가 없는 경우 빈 배열 반환
        """
        response = authenticated_client.get('/api/characters/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 0
        assert response.data['results'] == []


class TestCharacterListOrder:
    """캐릭터 정렬 테스트"""

    def test_character_list_order_by_created(self, authenticated_client, test_user, db):
        """
        AC-3.1.4: 캐릭터는 최근 등록순으로 정렬된다
        """
        # 첫 번째 캐릭터 (먼저 생성)
        char1 = Character.objects.create(
            user=test_user,
            ocid='first_ocid',
            character_name='첫번째캐릭터',
            world_name='스카니아',
            character_class='비숍',
            character_level=200
        )

        # 두 번째 캐릭터 (나중에 생성)
        char2 = Character.objects.create(
            user=test_user,
            ocid='second_ocid',
            character_name='두번째캐릭터',
            world_name='베라',
            character_class='아크메이지(썬,콜)',
            character_level=250
        )

        response = authenticated_client.get('/api/characters/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 2

        # 나중에 생성된 캐릭터가 먼저 나와야 함 (order_by('-created_at'))
        results = response.data['results']
        assert results[0]['character_name'] == '두번째캐릭터'
        assert results[1]['character_name'] == '첫번째캐릭터'


class TestCharacterListUnauthorized:
    """비인증 사용자 테스트"""

    def test_character_list_unauthorized(self, api_client):
        """
        비인증 사용자는 401 Unauthorized 응답을 받는다
        """
        response = api_client.get('/api/characters/')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestCharacterListOwnership:
    """캐릭터 소유권 테스트"""

    def test_character_list_only_own_characters(
        self, authenticated_client, test_user, other_user, db
    ):
        """
        본인 캐릭터만 조회되고 다른 사용자의 캐릭터는 조회되지 않는다
        """
        # 본인 캐릭터 생성
        my_char = Character.objects.create(
            user=test_user,
            ocid='my_ocid',
            character_name='내캐릭터',
            world_name='스카니아',
            character_class='나이트로드',
            character_level=280
        )

        # 다른 사용자의 캐릭터 생성
        other_char = Character.objects.create(
            user=other_user,
            ocid='other_ocid',
            character_name='다른유저캐릭터',
            world_name='베라',
            character_class='팬텀',
            character_level=290
        )

        response = authenticated_client.get('/api/characters/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1

        # 본인 캐릭터만 조회됨
        character_names = [c['character_name'] for c in response.data['results']]
        assert '내캐릭터' in character_names
        assert '다른유저캐릭터' not in character_names


class TestCharacterListWithCrawlData:
    """크롤링 데이터가 있는 경우 테스트"""

    def test_character_list_with_last_crawled_at(
        self, authenticated_client, test_character, test_character_basic, db
    ):
        """
        마지막 크롤링 시간이 정상적으로 반환되는지 확인
        """
        # CrawlTask 생성
        crawl_task = CrawlTask.objects.create(
            task_id='test_task_id',
            character_basic=test_character_basic,
            task_type='inventory',
            status='SUCCESS',
            progress=100
        )

        response = authenticated_client.get('/api/characters/')

        assert response.status_code == status.HTTP_200_OK
        character = response.data['results'][0]
        assert character['last_crawled_at'] is not None

    def test_character_list_with_inventory_count(
        self, authenticated_client, test_character, test_character_basic, db
    ):
        """
        인벤토리 아이템 수가 정상적으로 반환되는지 확인
        """
        # 인벤토리 아이템 생성
        crawled_at = timezone.now()
        Inventory.objects.create(
            character_basic=test_character_basic,
            item_name='테스트아이템1',
            item_icon='https://example.com/icon1.png',
            quantity=1,
            slot_position=1,
            crawled_at=crawled_at
        )
        Inventory.objects.create(
            character_basic=test_character_basic,
            item_name='테스트아이템2',
            item_icon='https://example.com/icon2.png',
            quantity=1,
            slot_position=2,
            crawled_at=crawled_at
        )

        response = authenticated_client.get('/api/characters/')

        assert response.status_code == status.HTTP_200_OK
        character = response.data['results'][0]
        assert character['inventory_count'] == 2

    def test_character_list_has_expiring_items(
        self, authenticated_client, test_character, test_character_basic, db
    ):
        """
        7일 이내 만료 아이템 유무가 정상적으로 반환되는지 확인
        """
        crawled_at = timezone.now()

        # 5일 후 만료 아이템 생성 (has_expiring_items = True)
        Inventory.objects.create(
            character_basic=test_character_basic,
            item_name='만료예정아이템',
            item_icon='https://example.com/icon.png',
            quantity=1,
            slot_position=1,
            expiry_date=timezone.now() + timedelta(days=5),
            crawled_at=crawled_at
        )

        response = authenticated_client.get('/api/characters/')

        assert response.status_code == status.HTTP_200_OK
        character = response.data['results'][0]
        assert character['has_expiring_items'] is True

    def test_character_list_no_expiring_items(
        self, authenticated_client, test_character, test_character_basic, db
    ):
        """
        7일 이내 만료 아이템이 없으면 has_expiring_items = False
        """
        crawled_at = timezone.now()

        # 30일 후 만료 아이템 생성 (7일 이내가 아님)
        Inventory.objects.create(
            character_basic=test_character_basic,
            item_name='만료아직아이템',
            item_icon='https://example.com/icon.png',
            quantity=1,
            slot_position=1,
            expiry_date=timezone.now() + timedelta(days=30),
            crawled_at=crawled_at
        )

        response = authenticated_client.get('/api/characters/')

        assert response.status_code == status.HTTP_200_OK
        character = response.data['results'][0]
        assert character['has_expiring_items'] is False
