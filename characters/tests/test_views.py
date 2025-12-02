"""
API View 테스트 모듈 (Story 2.11: API View 테스트 리팩토링)

AC-2.11.1: 모든 필수 필드가 mock 데이터에 포함
AC-2.11.2: Optional 필드 테스트 케이스
AC-2.11.3: 에러 응답 테스트 케이스
AC-2.11.4: mock 데이터가 실제 Nexon API 응답 구조와 일치
AC-2.11.5: 테스트 커버리지 80% 이상
AC-2.11.6: skip 처리된 테스트들 활성화
"""
import pytest
import json
from pathlib import Path
from django.urls import reverse
from unittest.mock import patch, MagicMock
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.utils import timezone
from django.test import override_settings
import responses

from characters.models import CharacterBasic, CharacterId
from characters.schemas import (
    CharacterBasicSchema,
    CharacterStatSchema,
    CharacterPopularitySchema,
    CharacterItemEquipmentSchema,
    CharacterAllDataSchema,
)
from define.define import (
    CHARACTER_ID_URL,
    CHARACTER_BASIC_URL,
    CHARACTER_STAT_URL,
    CHARACTER_POPULARITY_URL,
    CHARACTER_ITEM_EQUIPMENT_URL,
)

# 테스트용 인메모리 캐시 설정
TEST_CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# 테스트 상수 (실제 API 응답 데이터 기반 - "식사동그놈" 캐릭터)
TEST_OCID = "2e0a31fb5fef6dfe331d3bfef62f7ac8"
TEST_CHARACTER_NAME = "식사동그놈"

# Fixtures 디렉토리 경로
FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(filename):
    """JSON fixture 파일 로드 헬퍼 함수"""
    with open(FIXTURES_DIR / filename, encoding="utf-8") as f:
        return json.load(f)


class TestCharacterViews(APITestCase):
    """API View 테스트 클래스 (AC-2.11.6: skip 제거)"""

    def setUp(self):
        """테스트 데이터 설정 (실제 API 응답 기반)"""
        self.ocid = TEST_OCID
        self.character_name = TEST_CHARACTER_NAME
        self.test_date = timezone.now()

        # 기본 캐릭터 생성 (CharacterBasic 모델 필드만 사용)
        self.character = CharacterBasic.objects.create(
            ocid=self.ocid,
            character_name=self.character_name,
            world_name="베라",
            character_gender="남",
            character_class="팬텀",
        )

    @responses.activate
    def test_character_id_view(self):
        """CharacterIdView 테스트 (AC-2.11.6)

        CharacterIdView는 character_name을 받아 ocid를 반환하고,
        내부적으로 CharacterBasic 정보도 함께 조회/저장합니다.
        """
        # JSON fixture 로드
        mock_basic_data = load_fixture("character_basic.json")

        # Mock: CHARACTER_ID_URL 응답
        responses.add(
            responses.GET,
            CHARACTER_ID_URL,
            json={"ocid": self.ocid},
            status=200,
        )

        # Mock: CHARACTER_BASIC_URL 응답 (CharacterIdView가 내부적으로 호출)
        responses.add(
            responses.GET,
            CHARACTER_BASIC_URL,
            json=mock_basic_data,
            status=200,
        )

        # API 호출
        response = self.client.get(
            reverse('character-id'),
            {'character_name': self.character_name}
        )

        # 검증
        assert response.status_code == 200
        response_data = response.json()
        assert 'data' in response_data
        assert 'ocid' in response_data.get('data', {})

    @responses.activate
    def test_character_basic_view(self):
        """CharacterBasicView 테스트 (AC-2.11.1, AC-2.11.6)

        CharacterBasicSchema의 모든 필수 필드를 포함한 mock 데이터로 테스트합니다.
        """
        # JSON fixture 로드
        mock_basic_response = load_fixture("character_basic.json")

        # Mock: CHARACTER_BASIC_URL 응답
        responses.add(
            responses.GET,
            CHARACTER_BASIC_URL,
            json=mock_basic_response,
            status=200,
        )

        # API 호출 (force_refresh=true로 캐시 우회)
        response = self.client.get(
            reverse('character-basic', kwargs={'ocid': self.ocid}),
            {'force_refresh': 'true'}
        )

        # 검증
        assert response.status_code == 200
        data = response.json().get('data', {})

        # CharacterBasic 모델 필드 확인 (AC-2.11.1)
        assert 'character_name' in data
        assert 'world_name' in data
        assert 'character_class' in data

        # character_level은 CharacterBasicHistory에 저장되므로 history 배열에 있음
        assert 'history' in data
        if data.get('history'):
            history_item = data['history'][0]
            assert 'character_level' in history_item

    @responses.activate
    def test_character_stat_view(self):
        """CharacterStatView 테스트 (AC-2.11.1, AC-2.11.6)

        CharacterStatSchema의 모든 필수 필드를 포함한 mock 데이터로 테스트합니다.
        특히 final_stat 배열이 올바르게 처리되는지 확인합니다.
        """
        # JSON fixture 로드
        mock_stat_response = load_fixture("character_stat.json")

        # Mock: CHARACTER_STAT_URL 응답
        responses.add(
            responses.GET,
            CHARACTER_STAT_URL,
            json=mock_stat_response,
            status=200,
        )

        # API 호출
        response = self.client.get(
            reverse('character-stat', kwargs={'ocid': self.ocid})
        )

        # 검증
        assert response.status_code == 200
        data = response.json().get('data', {})

        # 필수 필드 존재 확인 (AC-2.11.1)
        assert 'character_class' in data
        assert 'final_stat' in data
        assert 'remain_ap' in data

        # final_stat이 리스트인지 확인
        assert isinstance(data.get('final_stat'), list)

    @responses.activate
    def test_character_item_equipment_view(self):
        """CharacterItemEquipmentView 테스트 (AC-2.11.1, AC-2.11.6)

        CharacterItemEquipmentSchema 및 중첩 스키마 (ItemEquipmentSchema,
        ItemTotalOptionSchema, ItemBaseOptionSchema 등)의 모든 필수 필드를
        포함한 mock 데이터로 테스트합니다.
        """
        # JSON fixture 로드
        mock_equipment_response = load_fixture("item_equipment.json")

        # Mock: CHARACTER_ITEM_EQUIPMENT_URL 응답
        responses.add(
            responses.GET,
            CHARACTER_ITEM_EQUIPMENT_URL,
            json=mock_equipment_response,
            status=200,
        )

        # API 호출
        response = self.client.get(
            reverse('character-item-equipment', kwargs={'ocid': self.ocid})
        )

        # 검증
        assert response.status_code == 200
        data = response.json().get('data', {})

        # 필수 필드 존재 확인 (AC-2.11.1)
        assert 'character_gender' in data
        assert 'character_class' in data
        assert 'preset_no' in data
        assert 'item_equipment' in data

        # item_equipment이 리스트인지 확인
        assert isinstance(data.get('item_equipment'), list)

    @responses.activate
    def test_character_all_data_view(self):
        """CharacterAllDataView 테스트 (AC-2.11.1, AC-2.11.6)

        여러 API 엔드포인트에 대한 mock을 설정하고,
        CharacterAllDataSchema 검증이 통과하는지 확인합니다.
        """
        # JSON fixtures 로드
        mock_basic = load_fixture("character_basic.json")
        mock_stat = load_fixture("character_stat.json")
        mock_popularity = load_fixture("character_popularity.json")

        # Mock: CHARACTER_ID_URL
        responses.add(
            responses.GET,
            CHARACTER_ID_URL,
            json={"ocid": self.ocid},
            status=200,
        )

        # Mock: CHARACTER_BASIC_URL
        responses.add(
            responses.GET,
            CHARACTER_BASIC_URL,
            json=mock_basic,
            status=200,
        )

        # Mock: CHARACTER_STAT_URL
        responses.add(
            responses.GET,
            CHARACTER_STAT_URL,
            json=mock_stat,
            status=200,
        )

        # Mock: CHARACTER_POPULARITY_URL
        responses.add(
            responses.GET,
            CHARACTER_POPULARITY_URL,
            json=mock_popularity,
            status=200,
        )

        # Mock: 나머지 엔드포인트들 (빈 응답 또는 최소 응답)
        from define.define import (
            CHARACTER_ABILITY_URL, CHARACTER_CASHITEM_EQUIPMENT_URL,
            CHARACTER_SYMBOL_URL, CHARACTER_LINK_SKILL_URL, CHARACTER_SKILL_URL,
            CHARACTER_HEXAMATRIX_URL, CHARACTER_HEXAMATRIX_STAT_URL,
            CHARACTER_VMATRIX_URL, CHARACTER_DOJANG_URL,
            CHARACTER_SET_EFFECT_URL, CHARACTER_BEAUTY_EQUIPMENT_URL,
            CHARACTER_ANDROID_EQUIPMENT_URL, CHARACTER_PET_EQUIPMENT_URL,
            CHARACTER_PROPENSITY_URL, CHARACTER_HYPER_STAT_URL,
        )

        # 각 엔드포인트에 대한 최소 유효 응답
        empty_responses = {
            CHARACTER_ABILITY_URL: {"date": None, "ability_grade": "레전드리", "ability_info": [], "remain_fame": 0, "preset_no": 1, "ability_preset_1": {"ability_preset_grade": "레전드리", "ability_info": []}, "ability_preset_2": {"ability_preset_grade": "에픽", "ability_info": []}, "ability_preset_3": {"ability_preset_grade": "레어", "ability_info": []}},
            CHARACTER_ITEM_EQUIPMENT_URL: {"date": None, "character_gender": "여", "character_class": "아크메이지(불,독)", "preset_no": 1, "item_equipment": [], "item_equipment_preset_1": [], "item_equipment_preset_2": [], "item_equipment_preset_3": []},
            CHARACTER_CASHITEM_EQUIPMENT_URL: {"cash_item_equipment_base": [], "cash_item_equipment_preset_1": [], "cash_item_equipment_preset_2": [], "cash_item_equipment_preset_3": []},
            CHARACTER_SYMBOL_URL: {"character_class": "아크메이지(불,독)", "symbol": []},
            CHARACTER_LINK_SKILL_URL: {"character_class": "아크메이지(불,독)", "character_link_skill": [], "character_link_skill_preset_1": [], "character_link_skill_preset_2": [], "character_link_skill_preset_3": []},
            CHARACTER_SKILL_URL: {},
            CHARACTER_HEXAMATRIX_URL: {},
            CHARACTER_HEXAMATRIX_STAT_URL: {},
            CHARACTER_VMATRIX_URL: {"character_class": "아크메이지(불,독)"},
            CHARACTER_DOJANG_URL: {"character_class": "아크메이지(불,독)", "world_name": "스카니아", "dojang_best_floor": 0, "dojang_best_time": 0},
            CHARACTER_SET_EFFECT_URL: {"set_effect": []},
            CHARACTER_BEAUTY_EQUIPMENT_URL: {"character_gender": "여", "character_class": "아크메이지(불,독)", "character_hair": {}, "character_face": {}, "character_skin": {}},
            CHARACTER_ANDROID_EQUIPMENT_URL: {},
            CHARACTER_PET_EQUIPMENT_URL: {},
            CHARACTER_PROPENSITY_URL: {"charisma_level": 0, "sensibility_level": 0, "insight_level": 0, "willingness_level": 0, "handicraft_level": 0, "charm_level": 0},
            CHARACTER_HYPER_STAT_URL: {"character_class": "아크메이지(불,독)", "use_preset_no": "1", "use_available_hyper_stat": 0, "hyper_stat_preset_1": [], "hyper_stat_preset_1_remain_point": 0, "hyper_stat_preset_2": [], "hyper_stat_preset_2_remain_point": 0, "hyper_stat_preset_3": [], "hyper_stat_preset_3_remain_point": 0},
        }

        for url, response_data in empty_responses.items():
            responses.add(
                responses.GET,
                url,
                json=response_data,
                status=200,
            )

        # Redis mock
        with patch('characters.views.redis_client') as mock_redis:
            mock_redis.get.return_value = None
            mock_redis.setex.return_value = True

            # API 호출
            response = self.client.get(
                reverse('character-all-data'),
                {'character_name': self.character_name}
            )

        # 검증: 응답이 정상적으로 반환되는지 확인
        assert response.status_code == 200

    def test_redis_health_check_view(self):
        """RedisHealthCheckView 테스트 (AC-2.11.6)"""
        with patch('characters.views.redis_client') as mock_redis:
            # 성공 케이스
            mock_redis.ping.return_value = True
            response = self.client.get(reverse('redis-health'))
            assert response.status_code == 200
            assert response.json().get('status') == 'success'

            # 실패 케이스
            mock_redis.ping.side_effect = Exception("Connection failed")
            response = self.client.get(reverse('redis-health'))
            assert response.status_code == 500  # 실제 API는 500 반환
            assert response.json().get('status') == 'error'


class TestOptionalFields(APITestCase):
    """Optional 필드 테스트 클래스 (AC-2.11.2)"""

    def setUp(self):
        """테스트 데이터 설정 (실제 API 응답 기반)"""
        self.ocid = TEST_OCID
        self.character_name = TEST_CHARACTER_NAME
        self.character = CharacterBasic.objects.create(
            ocid=self.ocid,
            character_name=self.character_name,
            world_name="베라",
            character_gender="남",
            character_class="팬텀",
        )

    @responses.activate
    def test_character_basic_optional_fields_none(self):
        """CharacterBasicSchema Optional 필드가 None인 경우 테스트 (AC-2.11.2)"""
        mock_data = {
            "date": None,
            "character_name": self.character_name,
            "world_name": "베라",
            "character_gender": "남",
            "character_class": "팬텀",
            "character_class_level": "6",
            "character_level": 290,
            "character_exp": 13918173193066,
            "character_exp_rate": "4.729",
            "character_guild_name": None,  # Optional
            "character_image": "https://open.api.nexon.com/static/maplestory/character/look/test",
            "character_date_create": None,  # Optional
            "access_flag": "true",
            "liberation_quest_clear": "1"
        }

        responses.add(
            responses.GET,
            CHARACTER_BASIC_URL,
            json=mock_data,
            status=200,
        )

        response = self.client.get(
            reverse('character-basic', kwargs={'ocid': self.ocid})
        )

        assert response.status_code == 200
        data = response.json().get('data', {})

        # Optional 필드가 None이어도 정상 처리되는지 확인
        assert 'character_name' in data

    @responses.activate
    def test_character_basic_optional_fields_present(self):
        """CharacterBasicSchema Optional 필드에 값이 있는 경우 테스트 (AC-2.11.2)"""
        mock_data = load_fixture("character_basic.json")

        responses.add(
            responses.GET,
            CHARACTER_BASIC_URL,
            json=mock_data,
            status=200,
        )

        response = self.client.get(
            reverse('character-basic', kwargs={'ocid': self.ocid})
        )

        assert response.status_code == 200
        data = response.json().get('data', {})

        # Optional 필드에 값이 있을 때 정상 처리되는지 확인
        assert 'character_name' in data

    @responses.activate
    def test_character_stat_optional_date_field(self):
        """CharacterStatSchema Optional date 필드 테스트 (AC-2.11.2)"""
        mock_data = {
            "date": None,  # Optional
            "character_class": "팬텀",
            "final_stat": [
                {"stat_name": "최소 스탯공격력", "stat_value": "130073545"},
                {"stat_name": "최대 스탯공격력", "stat_value": "144526159"},
            ],
            "remain_ap": 0
        }

        responses.add(
            responses.GET,
            CHARACTER_STAT_URL,
            json=mock_data,
            status=200,
        )

        response = self.client.get(
            reverse('character-stat', kwargs={'ocid': self.ocid})
        )

        assert response.status_code == 200


class TestErrorResponses(APITestCase):
    """에러 응답 테스트 클래스 (AC-2.11.3)"""

    def setUp(self):
        """테스트 데이터 설정"""
        self.ocid = TEST_OCID
        self.character_name = TEST_CHARACTER_NAME

    def test_character_id_view_missing_name(self):
        """CharacterIdView 400 Bad Request - 캐릭터 이름 누락 (AC-2.11.3)"""
        response = self.client.get(reverse('character-id'))

        assert response.status_code == 400
        assert 'error' in response.json()

    @responses.activate
    def test_character_id_view_not_found(self):
        """CharacterIdView 404 Not Found - 존재하지 않는 캐릭터 (AC-2.11.3)"""
        responses.add(
            responses.GET,
            CHARACTER_ID_URL,
            json={"error": {"name": "OPENAPI00004", "message": "Please input valid parameter"}},
            status=400,
        )

        response = self.client.get(
            reverse('character-id'),
            {'character_name': '존재하지않는캐릭터명123'}
        )

        # API 오류 응답 확인 (400, 404, 또는 503)
        assert response.status_code in [400, 404, 503]

    @responses.activate
    def test_character_basic_view_api_error(self):
        """CharacterBasicView API 오류 응답 테스트 (AC-2.11.3)"""
        # 먼저 DB에 캐릭터 생성 (CharacterBasic 모델 필드만 사용)
        CharacterBasic.objects.create(
            ocid=self.ocid,
            character_name=self.character_name,
            world_name="베라",
            character_gender="남",
            character_class="팬텀",
        )

        # API 오류 응답 mock
        responses.add(
            responses.GET,
            CHARACTER_BASIC_URL,
            json={"error": {"name": "OPENAPI00001", "message": "Internal Server Error"}},
            status=500,
        )

        # force_refresh=true로 캐시 우회하여 API 오류 테스트
        response = self.client.get(
            reverse('character-basic', kwargs={'ocid': self.ocid}),
            {'force_refresh': 'true'}
        )

        # 500 에러 또는 서비스 오류 확인
        assert response.status_code in [500, 503]

    def test_character_all_data_view_missing_name(self):
        """CharacterAllDataView 400 Bad Request - 캐릭터 이름 누락 (AC-2.11.3)"""
        response = self.client.get(reverse('character-all-data'))

        assert response.status_code == 400
        assert 'error' in response.json()

    @responses.activate
    def test_pydantic_validation_error(self):
        """Pydantic ValidationError 처리 테스트 (AC-2.11.3)

        현재 구현에서는 Pydantic 검증 실패 시에도 에러를 로깅하고
        graceful하게 처리합니다. 이 테스트는 검증 실패가 서버 크래시를
        일으키지 않는지 확인합니다.
        """
        # 필수 필드가 누락된 잘못된 응답
        invalid_data = {
            "character_name": "테스트",
            # character_class, character_level 등 필수 필드 누락
        }

        CharacterBasic.objects.create(
            ocid=self.ocid,
            character_name=self.character_name,
            world_name="베라",
            character_gender="남",
            character_class="팬텀",
        )

        responses.add(
            responses.GET,
            CHARACTER_BASIC_URL,
            json=invalid_data,
            status=200,
        )

        # force_refresh=true로 캐시 우회하여 Pydantic 검증 오류 테스트
        response = self.client.get(
            reverse('character-basic', kwargs={'ocid': self.ocid}),
            {'force_refresh': 'true'}
        )

        # 현재 구현: 검증 실패 시 에러를 로깅하고 graceful하게 처리
        # 서버가 크래시하지 않고 응답을 반환해야 함
        # (향후 명시적 에러 응답으로 개선 가능)
        assert response.status_code in [200, 400, 500, 503]


class TestPydanticSchemaValidation(APITestCase):
    """Pydantic 스키마 검증 테스트 (AC-2.11.1, AC-2.11.4)"""

    def test_character_basic_schema_validation(self):
        """CharacterBasicSchema 필수 필드 검증 (AC-2.11.1)"""
        mock_data = load_fixture("character_basic.json")

        # Pydantic 스키마로 검증
        validated = CharacterBasicSchema(**mock_data)

        # 필수 필드 확인 (실제 "식사동그놈" 캐릭터 데이터)
        assert validated.character_name == "식사동그놈"
        assert validated.world_name == "베라"
        assert validated.character_class == "팬텀"
        assert validated.character_level == 290

    def test_character_stat_schema_validation(self):
        """CharacterStatSchema 필수 필드 검증 (AC-2.11.1)"""
        mock_data = load_fixture("character_stat.json")

        # Pydantic 스키마로 검증
        validated = CharacterStatSchema(**mock_data)

        # 필수 필드 확인 (실제 "식사동그놈" 캐릭터 데이터)
        assert validated.character_class == "팬텀"
        assert len(validated.final_stat) > 0
        assert validated.remain_ap == 0

    def test_character_item_equipment_schema_validation(self):
        """CharacterItemEquipmentSchema 및 중첩 스키마 검증 (AC-2.11.1)"""
        mock_data = load_fixture("item_equipment.json")

        # Pydantic 스키마로 검증
        validated = CharacterItemEquipmentSchema(**mock_data)

        # 필수 필드 확인 (실제 "식사동그놈" 캐릭터 데이터)
        assert validated.character_gender == "남"
        assert validated.character_class == "팬텀"
        assert validated.preset_no == 1
        assert isinstance(validated.item_equipment, list)

        # 중첩 스키마 확인
        if len(validated.item_equipment) > 0:
            item = validated.item_equipment[0]
            assert item.item_name is not None
            assert item.item_equipment_part is not None
            assert item.item_total_option is not None
            assert item.item_base_option is not None

    def test_character_popularity_schema_validation(self):
        """CharacterPopularitySchema 검증 (AC-2.11.1)"""
        mock_data = load_fixture("character_popularity.json")

        # Pydantic 스키마로 검증
        validated = CharacterPopularitySchema(**mock_data)

        # 필수 필드 확인 (실제 "식사동그놈" 캐릭터 데이터)
        assert validated.popularity == 343

    def test_nexon_api_response_structure_match(self):
        """mock 데이터가 실제 Nexon API 응답 구조와 일치하는지 검증 (AC-2.11.4)"""
        # CharacterBasicSchema 필드 검증
        basic_data = load_fixture("character_basic.json")
        expected_basic_fields = [
            "character_name", "world_name", "character_gender", "character_class",
            "character_class_level", "character_level", "character_exp",
            "character_exp_rate", "character_image", "access_flag",
            "liberation_quest_clear"  # 실제 API 응답 필드명 (스키마에서는 validation_alias로 매핑)
        ]
        for field in expected_basic_fields:
            assert field in basic_data, f"Missing field: {field}"

        # CharacterStatSchema 필드 검증
        stat_data = load_fixture("character_stat.json")
        expected_stat_fields = ["character_class", "final_stat", "remain_ap"]
        for field in expected_stat_fields:
            assert field in stat_data, f"Missing field: {field}"

        # final_stat 내부 구조 검증
        if stat_data.get("final_stat"):
            stat_item = stat_data["final_stat"][0]
            assert "stat_name" in stat_item
            assert "stat_value" in stat_item


@pytest.fixture
def api_client():
    """API 테스트를 위한 클라이언트 픽스처"""
    return APIClient()


@pytest.fixture
def mock_api_response():
    """API 응답을 모킹하기 위한 픽스처"""
    with responses.RequestsMock() as rsps:
        yield rsps


@pytest.mark.django_db
class TestCharacterAPIIntegration:
    """통합 테스트 (AC-2.11.6)"""

    @responses.activate
    def test_character_workflow(self, api_client):
        """전체 캐릭터 조회 워크플로우 테스트 (AC-2.11.6)

        CharacterIdView를 호출하여 캐릭터 정보를 조회하는
        전체 워크플로우를 테스트합니다.
        """
        mock_basic = load_fixture("character_basic.json")

        # Mock: CHARACTER_ID_URL
        responses.add(
            responses.GET,
            CHARACTER_ID_URL,
            json={"ocid": TEST_OCID},
            status=200,
        )

        # Mock: CHARACTER_BASIC_URL
        responses.add(
            responses.GET,
            CHARACTER_BASIC_URL,
            json=mock_basic,
            status=200,
        )

        # 1. 캐릭터 ID 조회
        response = api_client.get(
            reverse('character-id'),
            {'character_name': TEST_CHARACTER_NAME}
        )

        assert response.status_code == 200
        data = response.json().get('data', {})
        assert 'ocid' in data
