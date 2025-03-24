import pytest
import json
from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from characters.models import *
from characters.views import *
from django.utils import timezone
import responses


@pytest.mark.django_db
class TestCharacterViews(APITestCase):
    @pytest.fixture(autouse=True)
    def setup(self, api_client):
        """테스트 데이터 설정"""
        self.client = api_client
        self.ocid = "1234567890abcdef"
        self.character_name = "테스트캐릭터"
        self.test_date = timezone.now()

        # 기본 캐릭터 생성
        self.character = CharacterBasic.objects.create(
            ocid=self.ocid,
            character_name=self.character_name,
            world_name="스카니아",
            character_gender="여",
            character_class="아크메이지(불,독)"
        )

    @responses.activate
    def test_character_id_view(self):
        """CharacterIdView 테스트"""
        # API 응답 모킹
        responses.add(
            responses.GET,
            f"{CHARACTER_ID_URL}",
            json={"ocid": self.ocid},
            status=200,
            match=[responses.matchers.query_param_matcher(
                {"character_name": self.character_name})]
        )

        # API 호출
        response = self.client.get(
            reverse('character-id'),
            {'character_name': self.character_name}
        )

        assert response.status_code == 200
        assert response.json()['ocid'] == self.ocid

    @responses.activate
    def test_character_basic_view(self):
        """CharacterBasicView 테스트"""
        test_data = {
            "date": self.test_date.strftime("%Y-%m-%d %H:%M:%S"),
            "character_name": self.character_name,
            "world_name": "스카니아",
            "character_gender": "여",
            "character_class": "아크메이지(불,독)",
            "character_level": 200,
            "character_exp": 123456789,
            "character_exp_rate": "95.12",
            "character_guild_name": "길드명",
            "character_image": "http://example.com/image.png"
        }

        responses.add(
            responses.GET,
            f"{CHARACTER_BASIC_URL}",
            json=test_data,
            status=200,
            match=[responses.matchers.query_param_matcher({"ocid": self.ocid})]
        )

        response = self.client.get(
            reverse('character-basic', kwargs={'ocid': self.ocid})
        )

        assert response.status_code == 200
        assert response.json()['character_name'] == self.character_name

    @responses.activate
    def test_character_stat_view(self):
        """CharacterStatView 테스트"""
        test_data = {
            "date": self.test_date.strftime("%Y-%m-%d %H:%M:%S"),
            "character_class": "아크메이지(불,독)",
            "remain_ap": 0,
            "final_stat": [
                {"stat_name": "HP", "stat_value": "12345"},
                {"stat_name": "MP", "stat_value": "12345"},
                {"stat_name": "STR", "stat_value": "123"},
                {"stat_name": "DEX", "stat_value": "123"},
                {"stat_name": "INT", "stat_value": "999"},
                {"stat_name": "LUK", "stat_value": "123"}
            ]
        }

        responses.add(
            responses.GET,
            f"{CHARACTER_STAT_URL}?ocid={self.ocid}",
            json=test_data,
            status=200
        )

        response = self.client.get(
            reverse('character-stat', kwargs={'ocid': self.ocid})
        )

        assert response.status_code == 200
        assert len(response.json()['final_stat']) == 6

    @responses.activate
    def test_character_item_equipment_view(self):
        """CharacterItemEquipmentView 테스트"""
        test_data = {
            "date": self.test_date.strftime("%Y-%m-%d %H:%M:%S"),
            "character_gender": "여",
            "character_class": "아크메이지(불,독)",
            "item_equipment": [
                {
                    "item_equipment_part": "무기",
                    "item_equipment_slot": "무기",
                    "item_name": "테스트 무기",
                    "item_icon": "http://example.com/weapon.png",
                    "item_description": "테스트 무기입니다.",
                    "item_shape_name": "테스트 무기",
                    "item_shape_icon": "http://example.com/weapon.png",
                    "item_gender": "여",
                    "item_total_option": {
                        "str": "0",
                        "dex": "0",
                        "int": "150",
                        "luk": "0",
                        "max_hp": "0",
                        "max_mp": "0",
                        "attack_power": "171",
                        "magic_power": "283",
                    }
                }
            ]
        }

        responses.add(
            responses.GET,
            f"{CHARACTER_ITEM_EQUIPMENT_URL}?ocid={self.ocid}",
            json=test_data,
            status=200
        )

        response = self.client.get(
            reverse('character-item-equipment', kwargs={'ocid': self.ocid})
        )

        assert response.status_code == 200
        assert len(response.json()['item_equipment']) == 1

    @responses.activate
    def test_character_all_data_view(self):
        """CharacterAllDataView 테스트"""
        # 모든 API 엔드포인트에 대한 모킹
        basic_data = {
            "date": self.test_date.strftime("%Y-%m-%d %H:%M:%S"),
            "character_name": self.character_name,
            "world_name": "스카니아",
            "character_gender": "여",
            "character_class": "아크메이지(불,독)"
        }

        stat_data = {
            "date": self.test_date.strftime("%Y-%m-%d %H:%M:%S"),
            "character_class": "아크메이지(불,독)",
            "final_stat": []
        }

        # 각 엔드포인트에 대한 응답 모킹
        responses.add(
            responses.GET,
            f"{CHARACTER_BASIC_URL}?ocid={self.ocid}",
            json=basic_data,
            status=200
        )

        responses.add(
            responses.GET,
            f"{CHARACTER_STAT_URL}?ocid={self.ocid}",
            json=stat_data,
            status=200
        )

        # 나머지 엔드포인트들도 비슷하게 모킹...

        response = self.client.get(
            reverse('character-all-data', kwargs={'ocid': self.ocid})
        )

        assert response.status_code == 200
        assert 'basic' in response.json()
        assert 'stat' in response.json()

    def test_redis_health_check_view(self):
        """RedisHealthCheckView 테스트"""
        with patch('characters.views.redis_client') as mock_redis:
            mock_redis.ping.return_value = True
            response = self.client.get(reverse('redis-health-check'))
            assert response.status_code == 200
            assert response.json()['status'] == 'success'

            # Redis 연결 실패 케이스
            mock_redis.ping.side_effect = Exception("Connection failed")
            response = self.client.get(reverse('redis-health-check'))
            assert response.status_code == 500
            assert response.json()['status'] == 'error'


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
    """통합 테스트"""

    def test_character_workflow(self, api_client):
        """전체 캐릭터 조회 워크플로우 테스트"""
        ocid = "test_ocid"
        character_name = "테스트캐릭터"

        with responses.RequestsMock() as rsps:
            # ID 조회
            rsps.add(
                responses.GET,
                f"{CHARACTER_ID_URL}",
                json={"ocid": ocid},
                status=200,
                match=[responses.matchers.query_param_matcher(
                    {"character_name": character_name})]
            )

            response = api_client.get(
                reverse('character-id'),
                {'character_name': character_name}
            )
            assert response.status_code == 200
            assert response.json()['ocid'] == ocid

            # 기본 정보 조회
            rsps.add(
                responses.GET,
                f"{CHARACTER_BASIC_URL}",
                json={
                    "character_name": character_name,
                    "world_name": "스카니아",
                    "character_level": 200
                },
                status=200,
                match=[responses.matchers.query_param_matcher({"ocid": ocid})]
            )

            response = api_client.get(
                reverse('character-basic', kwargs={'ocid': ocid})
            )
            assert response.status_code == 200
            assert response.json()['character_name'] == character_name
