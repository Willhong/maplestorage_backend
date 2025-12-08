"""
Story 3.2: 캐릭터 삭제 (연결 해제) 테스트

테스트 케이스:
- test_character_unlink_success: 인증된 사용자 연결 해제 성공 (AC-3.2.3)
- test_character_unlink_preserves_data: 연결 해제 후 CharacterBasic, Inventory 등 보존 확인 (AC-3.2.3)
- test_character_unlink_not_found: 존재하지 않는 캐릭터 404 응답
- test_character_unlink_unauthorized: 비인증 사용자 401 응답
- test_character_unlink_other_user: 다른 사용자 캐릭터 연결 해제 시도 404 응답
"""
import pytest
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from accounts.models import Character
from characters.models import CharacterBasic, Inventory, Storage


@pytest.fixture(autouse=True)
def clear_cache():
    """각 테스트 전에 캐시 초기화 (Redis 없이 동작)"""
    try:
        from django.core.cache import cache
        cache.clear()
    except Exception:
        pass
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
def test_inventory(db, test_character_basic):
    """테스트 Inventory 아이템 생성"""
    return Inventory.objects.create(
        character_basic=test_character_basic,
        item_name='테스트아이템',
        item_icon='https://example.com/icon.png',
        quantity=10,
        slot_position=1,
        crawled_at=timezone.now()
    )


@pytest.fixture
def test_storage(db, test_character_basic):
    """테스트 Storage 아이템 생성"""
    return Storage.objects.create(
        character_basic=test_character_basic,
        item_name='창고아이템',
        item_icon='https://example.com/storage_icon.png',
        quantity=5,
        slot_position=1,
        storage_type='shared',
        crawled_at=timezone.now()
    )


@pytest.fixture
def authenticated_client(api_client, test_user):
    """인증된 API 클라이언트"""
    api_client.force_authenticate(user=test_user)
    return api_client


class TestCharacterUnlinkSuccess:
    """캐릭터 연결 해제 성공 테스트"""

    def test_character_unlink_success(self, authenticated_client, test_character):
        """
        AC-3.2.3: 인증된 사용자가 캐릭터 연결 해제에 성공한다
        - DELETE /api/characters/{id}/ → 204 No Content
        - character.user = None으로 연결 해제
        """
        character_id = test_character.id
        response = authenticated_client.delete(f'/api/characters/{character_id}/')

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # 데이터베이스에서 캐릭터 확인
        test_character.refresh_from_db()
        assert test_character.user is None  # 연결 해제됨

    def test_character_unlink_character_still_exists(self, authenticated_client, test_character):
        """
        연결 해제 후 캐릭터 데이터(Character 모델)는 삭제되지 않고 유지된다
        """
        character_id = test_character.id
        ocid = test_character.ocid
        character_name = test_character.character_name

        response = authenticated_client.delete(f'/api/characters/{character_id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # 캐릭터가 여전히 존재하는지 확인
        character = Character.objects.get(id=character_id)
        assert character is not None
        assert character.ocid == ocid
        assert character.character_name == character_name
        assert character.user is None  # 사용자만 연결 해제됨


class TestCharacterUnlinkPreservesData:
    """연결 해제 후 데이터 보존 테스트"""

    def test_character_unlink_preserves_character_basic(
        self, authenticated_client, test_character, test_character_basic
    ):
        """
        AC-3.2.3: 연결 해제 후 CharacterBasic 데이터가 보존된다
        """
        character_id = test_character.id
        ocid = test_character.ocid

        response = authenticated_client.delete(f'/api/characters/{character_id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # CharacterBasic이 그대로 존재하는지 확인
        character_basic = CharacterBasic.objects.get(ocid=ocid)
        assert character_basic is not None
        assert character_basic.character_name == '테스트캐릭터'
        assert character_basic.world_name == '스카니아'

    def test_character_unlink_preserves_inventory(
        self, authenticated_client, test_character, test_character_basic, test_inventory
    ):
        """
        AC-3.2.3: 연결 해제 후 Inventory 데이터가 보존된다
        """
        character_id = test_character.id
        inventory_id = test_inventory.id

        response = authenticated_client.delete(f'/api/characters/{character_id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Inventory가 그대로 존재하는지 확인
        inventory = Inventory.objects.get(id=inventory_id)
        assert inventory is not None
        assert inventory.item_name == '테스트아이템'
        assert inventory.quantity == 10

    def test_character_unlink_preserves_storage(
        self, authenticated_client, test_character, test_character_basic, test_storage
    ):
        """
        AC-3.2.3: 연결 해제 후 Storage 데이터가 보존된다
        """
        character_id = test_character.id
        storage_id = test_storage.id

        response = authenticated_client.delete(f'/api/characters/{character_id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Storage가 그대로 존재하는지 확인
        storage = Storage.objects.get(id=storage_id)
        assert storage is not None
        assert storage.item_name == '창고아이템'
        assert storage.quantity == 5


class TestCharacterUnlinkNotFound:
    """캐릭터를 찾을 수 없는 경우 테스트"""

    def test_character_unlink_not_found(self, authenticated_client):
        """
        존재하지 않는 캐릭터 ID로 요청 시 404 Not Found 응답
        """
        non_existent_id = 99999
        response = authenticated_client.delete(f'/api/characters/{non_existent_id}/')

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestCharacterUnlinkUnauthorized:
    """비인증 사용자 테스트"""

    def test_character_unlink_unauthorized(self, api_client, test_character):
        """
        비인증 사용자는 401 Unauthorized 응답을 받는다
        """
        character_id = test_character.id
        response = api_client.delete(f'/api/characters/{character_id}/')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestCharacterUnlinkOtherUser:
    """다른 사용자 캐릭터 접근 테스트"""

    def test_character_unlink_other_user(self, authenticated_client, other_user, db):
        """
        다른 사용자의 캐릭터 연결 해제 시도 시 404 Not Found 응답 (정보 노출 방지)
        """
        # 다른 사용자의 캐릭터 생성
        other_character = Character.objects.create(
            user=other_user,
            ocid='other_ocid',
            character_name='다른유저캐릭터',
            world_name='베라',
            character_class='팬텀',
            character_level=290
        )

        response = authenticated_client.delete(f'/api/characters/{other_character.id}/')

        # 403 Forbidden 대신 404 Not Found (정보 노출 방지)
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # 다른 사용자 캐릭터는 그대로 유지됨
        other_character.refresh_from_db()
        assert other_character.user == other_user


class TestCharacterUnlinkReRegistration:
    """연결 해제 후 재등록 테스트"""

    def test_character_can_be_re_registered(
        self, authenticated_client, test_user, test_character, test_character_basic
    ):
        """
        연결 해제된 캐릭터는 나중에 다시 등록할 수 있다
        (같은 ocid로 다른 사용자가 등록하거나 같은 사용자가 재등록 가능)
        """
        character_id = test_character.id
        ocid = test_character.ocid

        # 연결 해제
        response = authenticated_client.delete(f'/api/characters/{character_id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT

        test_character.refresh_from_db()
        assert test_character.user is None

        # 재등록 시뮬레이션 (직접 user 연결)
        test_character.user = test_user
        test_character.save()

        # 다시 연결됨
        test_character.refresh_from_db()
        assert test_character.user == test_user
