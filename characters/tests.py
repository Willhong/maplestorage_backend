from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from accounts.models import Character
from .models import CharacterBasic
from unittest.mock import patch, MagicMock
from django.utils import timezone
import json


class CharacterAPITests(APITestCase):
    def setUp(self):
        # 테스트용 캐릭터 데이터 생성
        self.character = Character.objects.create(
            ocid="1234567890",
            character_name="테스트캐릭터",
            world_name="스카니아",
            character_class="히어로",
            character_level=275
        )

        self.character_basic = CharacterBasic.objects.create(
            ocid="1234567890",
            date=timezone.now(),
            character_name="테스트캐릭터",
            world_name="스카니아",
            character_gender="남",
            character_class="히어로",
            character_class_level="6차",
            character_level=275,
            character_exp=0,
            character_exp_rate="0",
            character_guild_name="길드",
            character_image="http://example.com/image.png",
            access_flag=True,
            liberation_quest_clear_flag=True
        )

    def setup_mock_response(self, mock_get, response_data):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = response_data
        mock_get.return_value = mock_response

    @patch('characters.views.requests.get')
    def test_character_basic_api(self, mock_get):
        """기본 정보 API 테스트"""
        url = reverse('character-basic')
        response = self.client.get(f"{url}?character_name=테스트캐릭터")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('characters.views.requests.get')
    def test_character_ability_api(self, mock_get):
        """어빌리티 API 테스트"""
        # OCID 조회 응답 설정
        mock_get.side_effect = [
            MagicMock(status_code=200, json=lambda: {"ocid": "1234567890"}),
            MagicMock(status_code=200, json=lambda: {
                "date": "2024-12-21T00:00+09:00",
                "ability_info": [
                    {
                        "ability_no": 1,
                        "ability_grade": "레전드리",
                        "ability_value": "공격력 12% 증가"
                    }
                ]
            })
        ]

        url = reverse('character-ability')
        response = self.client.get(f"{url}?character_name=테스트캐릭터")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('characters.views.requests.get')
    def test_character_item_equipment_api(self, mock_get):
        """장비 정보 API 테스트"""
        # OCID 조회 응답 설정
        mock_get.side_effect = [
            MagicMock(status_code=200, json=lambda: {"ocid": "1234567890"}),
            MagicMock(status_code=200, json=lambda: {
                "date": "2024-12-21T00:00+09:00",
                "item_equipment": [
                    {
                        "item_equipment_part": "무기",
                        "item_equipment_slot": "무기",
                        "item_name": "아케인셰이드 투핸드소드",
                        "item_icon": "http://example.com/weapon.png",
                        "item_description": "설명",
                        "item_option": {},
                        "starforce": 22,
                        "potential_option_grade": "레전드리",
                        "additional_potential_option_grade": "유니크",
                        "potential_options": [],
                        "additional_potential_options": []
                    }
                ]
            })
        ]

        url = reverse('character-item-equipment')
        response = self.client.get(f"{url}?character_name=테스트캐릭터")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('characters.views.requests.get')
    def test_character_cashitem_equipment_api(self, mock_get):
        """캐시 장비 API 테스트"""
        # OCID 조회 응답 설정
        mock_get.side_effect = [
            MagicMock(status_code=200, json=lambda: {"ocid": "1234567890"}),
            MagicMock(status_code=200, json=lambda: {
                "date": "2024-12-21T00:00+09:00",
                "cash_item_equipment": [
                    {
                        "cash_item_equipment_part": "모자",
                        "cash_item_equipment_slot": "모자",
                        "cash_item_name": "블랙 배럿",
                        "cash_item_icon": "http://example.com/hat.png",
                        "cash_item_description": "설명",
                        "cash_item_option": {},
                        "date_expire": None,
                        "date_option_expire": None
                    }
                ]
            })
        ]

        url = reverse('character-cashitem-equipment')
        response = self.client.get(f"{url}?character_name=테스트캐릭터")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('characters.views.requests.get')
    def test_character_symbol_api(self, mock_get):
        """심볼 API 테스트"""
        # OCID 조회 응답 설정
        mock_get.side_effect = [
            MagicMock(status_code=200, json=lambda: {"ocid": "1234567890"}),
            MagicMock(status_code=200, json=lambda: {
                "date": "2024-12-21T00:00+09:00",
                "symbol": [
                    {
                        "symbol_name": "아케인심볼: 소멸의 여로",
                        "symbol_icon": "http://example.com/symbol.png",
                        "symbol_description": "설명",
                        "symbol_force": 100,
                        "symbol_level": 20,
                        "symbol_exp": 0,
                        "symbol_exp_required": 2679
                    }
                ]
            })
        ]

        url = reverse('character-symbol')
        response = self.client.get(f"{url}?character_name=테스트캐릭터")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('characters.views.requests.get')
    def test_character_link_skill_api(self, mock_get):
        """링크 스킬 API 테스트"""
        # OCID 조회 응답 설정
        mock_get.side_effect = [
            MagicMock(status_code=200, json=lambda: {"ocid": "1234567890"}),
            MagicMock(status_code=200, json=lambda: {
                "date": "2024-12-21T00:00+09:00",
                "link_skill": [
                    {
                        "link_skill_name": "인빈서블 빌리프",
                        "link_skill_description": "설명",
                        "link_skill_level": 2,
                        "link_skill_effect": "스탠스 확률 15% 증가, 상태 이상 내성 15 증가",
                        "link_skill_icon": "http://example.com/link.png"
                    }
                ]
            })
        ]

        url = reverse('character-link-skill')
        response = self.client.get(f"{url}?character_name=테스트캐릭터")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('characters.views.requests.get')
    def test_character_v_matrix_api(self, mock_get):
        """V매트릭스 API 테스트"""
        # OCID 조회 응답 설정
        mock_get.side_effect = [
            MagicMock(status_code=200, json=lambda: {"ocid": "1234567890"}),
            MagicMock(status_code=200, json=lambda: {
                "date": "2024-12-21T00:00+09:00",
                "v_core": [
                    {
                        "slot_id": 1,
                        "slot_level": 30,
                        "skill_name": "레이징 블로우 강화",
                        "skill_description": "설명",
                        "skill_level": 60,
                        "skill_effect": "데미지 2% 증가",
                        "skill_icon": "http://example.com/skill.png"
                    }
                ]
            })
        ]

        url = reverse('character-skill')
        response = self.client.get(f"{url}?character_name=테스트캐릭터")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('characters.views.requests.get')
    def test_character_hexa_matrix_api(self, mock_get):
        """HEXA 매트릭스 API 테스트"""
        # OCID 조회 응답 설정
        mock_get.side_effect = [
            MagicMock(status_code=200, json=lambda: {"ocid": "1234567890"}),
            MagicMock(status_code=200, json=lambda: {
                "date": "2024-12-21T00:00+09:00",
                "hexa_core_equipment": [
                    {
                        "hexa_core_name": "마스터리 코어",
                        "hexa_core_level": 1,
                        "hexa_core_type": "마스터리",
                        "linked_skill": []
                    }
                ]
            })
        ]

        url = reverse('character-hexamatrix')
        response = self.client.get(f"{url}?character_name=테스트캐릭터")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('characters.views.requests.get')
    def test_character_hexa_stat_api(self, mock_get):
        """HEXA 스탯 API 테스트"""
        # OCID 조회 응답 설정
        mock_get.side_effect = [
            MagicMock(status_code=200, json=lambda: {"ocid": "1234567890"}),
            MagicMock(status_code=200, json=lambda: {
                "date": "2024-12-21T00:00+09:00",
                "character_hexa_stat_core": [
                    {
                        "stat_name": "STR",
                        "stat_level": 1,
                        "stat_increase": 100,
                        "stat_type": "주스탯"
                    }
                ]
            })
        ]

        url = reverse('character-hexamatrix-stat')
        response = self.client.get(f"{url}?character_name=테스트캐릭터")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('characters.views.requests.get')
    def test_invalid_character_name(self, mock_get):
        """존재하지 않는 캐릭터 테스트"""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"error": "Character not found"}
        mock_get.return_value = mock_response

        url = reverse('character-basic')
        response = self.client.get(f"{url}?character_name=존재하지않는캐릭터")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_missing_character_name(self):
        """캐릭터명 누락 테스트"""
        url = reverse('character-basic')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
