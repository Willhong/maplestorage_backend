"""
Unit tests for ItemDetail (Story 2.3 Phase 6)
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from django.test import TestCase
from django.utils import timezone
from pydantic import ValidationError

from django.contrib.auth.models import User
from characters.models import CharacterBasic, Inventory, ItemDetail
from characters.schemas import ItemDetailSchema
from characters.crawler_services import ItemDetailParser, ItemDetailCrawler, ParsingError
from accounts.models import Character


class ItemDetailParserTests(TestCase):
    """ItemDetailParser 단위 테스트 (Story 2.3 Phase 6)"""

    def test_parse_base_stats(self):
        """AC-2.3.10: 기본 스탯 파싱"""
        span_data = {
            '공격력': ['+171'],
            '마력': ['+283'],
            'STR': ['+0'],
            'DEX': ['+0'],
            'INT': ['+150'],
            'LUK': ['+0'],
            'MaxHP': ['+300'],
            'MaxMP': ['+500'],
            '방어력': ['+200'],
            '올스탯': ['+9%'],
            '보스 몬스터 공격 시 데미지': ['+30%'],
            '몬스터 방어율 무시': ['+15%']
        }

        stats = ItemDetailParser._parse_base_stats(span_data)

        self.assertEqual(stats['attack_power'], 171)
        self.assertEqual(stats['magic_power'], 283)
        self.assertEqual(stats['int_stat'], 150)
        self.assertEqual(stats['hp_stat'], 300)
        self.assertEqual(stats['mp_stat'], 500)
        self.assertEqual(stats['defense'], 200)
        self.assertEqual(stats['all_stat'], 9)
        self.assertEqual(stats['boss_damage'], 30)
        self.assertEqual(stats['ignore_defense'], 15)

    def test_parse_potential(self):
        """AC-2.3.11: 잠재능력 파싱"""
        span_data = {
            '잠재옵션 등급': '유니크',
            '아이템': ['INT +9%', '마력 +9%', '보스 공격력 +30%']
        }

        potential = ItemDetailParser._parse_potential(span_data)

        self.assertEqual(potential['potential_grade'], '유니크')
        self.assertEqual(potential['potential_option_1'], 'INT +9%')
        self.assertEqual(potential['potential_option_2'], '마력 +9%')
        self.assertEqual(potential['potential_option_3'], '보스 공격력 +30%')

    def test_parse_additional_potential(self):
        """AC-2.3.12: 에디셔널 잠재능력 파싱"""
        span_data = {
            '에디셔널 잠재옵션 등급': '에픽',
            '에디셔널 아이템': ['INT +5%', '마력 +5%', 'HP +100']
        }

        additional = ItemDetailParser._parse_additional_potential(span_data)

        self.assertEqual(additional['additional_potential_grade'], '에픽')
        self.assertEqual(additional['additional_potential_option_1'], 'INT +5%')
        self.assertEqual(additional['additional_potential_option_2'], '마력 +5%')
        self.assertEqual(additional['additional_potential_option_3'], 'HP +100')

    def test_parse_soul_option(self):
        """AC-2.3.13: 소울 옵션 파싱"""
        span_data = {
            '소울옵션': '매그너스의 소울 : STR +7%, DEX +7%'
        }

        soul = ItemDetailParser._parse_soul_option(span_data)

        self.assertEqual(soul['soul_name'], '매그너스의 소울')
        self.assertEqual(soul['soul_option'], 'STR +7%, DEX +7%')

    def test_item_detail_schema_validation(self):
        """AC-2.3.16: Pydantic 검증"""
        # 유효한 데이터
        valid_data = {
            'item_category': '무기',
            'required_level': 200,
            'attack_power': 171,
            'magic_power': 283,
            'int_stat': 150,
            'boss_damage': 30,
            'potential_grade': '유니크',
            'potential_option_1': 'INT +9%'
        }

        schema = ItemDetailSchema(**valid_data)
        self.assertEqual(schema.required_level, 200)
        self.assertEqual(schema.attack_power, 171)

        # 잘못된 데이터 (레벨 범위 초과)
        invalid_data = {
            'required_level': 999,  # > 300
            'boss_damage': 150  # > 100
        }

        with self.assertRaises(ValidationError):
            ItemDetailSchema(**invalid_data)

    def test_parse_detail_page_full(self):
        """AC-2.3.10-13: 전체 HTML 파싱"""
        mock_html = """
        <html>
            <span>장비분류 | 무기</span>
            <span>REQ LEV</span><em>200</em>
            <span>착용 가능한 직업 | 마법사</span>
            <span>공격력</span><div>+171</div>
            <span>마력</span><div>+283</div>
            <span>INT</span><div>+150</div>
            <span>아이템 (유니크)</span><div>INT +9%<br>마력 +9%</div>
            <span>소울옵션</span><div>매그너스의 소울 : STR +7%</div>
        </html>
        """

        result = ItemDetailParser.parse_detail_page(mock_html, '테스트무기')

        self.assertEqual(result['item_category'], '무기')
        self.assertEqual(result['required_level'], 200)
        self.assertEqual(result['attack_power'], 171)
        self.assertEqual(result['magic_power'], 283)
        self.assertEqual(result['potential_grade'], '유니크')


class ItemDetailCrawlerTests(TestCase):
    """ItemDetailCrawler 통합 테스트 (Story 2.3 Phase 6)"""

    def setUp(self):
        """테스트 데이터 준비"""
        # User 생성
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

        # Character 생성
        self.character = Character.objects.create(
            user_id=self.user.id,
            character_name='테스트캐릭터'
        )

        # CharacterBasic 생성
        self.character_basic = CharacterBasic.objects.create(
            ocid='test-ocid-12345',
            character_name='테스트캐릭터',
            world_name='스카니아',
            character_gender='남',
            character_class='비숍'
        )

        # Inventory 아이템 생성
        self.inventory_item = Inventory.objects.create(
            character_basic=self.character_basic,
            item_name='아케인셰이드 완드',
            item_icon='https://example.com/icon.png',
            quantity=1,
            slot_position=0,
            detail_url='https://maplestory.nexon.com/Common/Resource/Item?p=12345',
            has_detail=False
        )

    def test_rate_limiting_config(self):
        """AC-2.3.14: Rate limiting 설정 확인"""
        crawler = ItemDetailCrawler()

        self.assertGreaterEqual(crawler.request_delay_min, 2.0)
        self.assertLessEqual(crawler.request_delay_max, 3.0)
        self.assertEqual(crawler.batch_size, 50)
        self.assertEqual(crawler.batch_rest_time, 30)
