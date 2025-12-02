import json
import pytest
from pathlib import Path
from rest_framework.test import APIClient
from django.core.cache import cache


# JSON Fixture 파일 경로
FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """모든 테스트에서 DB 접근 가능하도록 설정"""
    pass


@pytest.fixture
def api_client():
    """API 테스트를 위한 클라이언트"""
    return APIClient()


@pytest.fixture(autouse=True)
def clear_cache():
    """각 테스트 전에 캐시 초기화"""
    cache.clear()
    yield
    cache.clear()


# ============================================================
# JSON Fixture Loaders (Story 2.11 - AC-2.11.1, AC-2.11.4)
# ============================================================

@pytest.fixture
def mock_character_basic_response():
    """CharacterBasicSchema에 맞는 완전한 mock 데이터"""
    with open(FIXTURES_DIR / "character_basic.json", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def mock_character_stat_response():
    """CharacterStatSchema에 맞는 완전한 mock 데이터 (final_stat 포함)"""
    with open(FIXTURES_DIR / "character_stat.json", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def mock_character_popularity_response():
    """CharacterPopularitySchema에 맞는 mock 데이터"""
    with open(FIXTURES_DIR / "character_popularity.json", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def mock_item_equipment_response():
    """CharacterItemEquipmentSchema에 맞는 완전한 mock 데이터 (중첩 스키마 포함)"""
    with open(FIXTURES_DIR / "item_equipment.json", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def mock_character_all_data_response():
    """CharacterAllDataSchema에 맞는 mock 데이터"""
    with open(FIXTURES_DIR / "character_all_data.json", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# Optional 필드 테스트용 Fixture (Story 2.11 - AC-2.11.2)
# ============================================================

@pytest.fixture
def mock_character_basic_minimal():
    """Optional 필드가 None인 CharacterBasicSchema mock 데이터 (실제 API 응답 기반)"""
    return {
        "date": None,
        "character_name": "식사동그놈",
        "world_name": "베라",
        "character_gender": "남",
        "character_class": "팬텀",
        "character_class_level": "6",
        "character_level": 290,
        "character_exp": 13918173193066,
        "character_exp_rate": "4.729",
        "character_guild_name": None,
        "character_image": "https://open.api.nexon.com/static/maplestory/character/look/test",
        "character_date_create": None,
        "access_flag": "true",
        "liberation_quest_clear": "1"
    }


# ============================================================
# 테스트 상수 (실제 API 응답 데이터 기반 - "식사동그놈" 캐릭터)
# ============================================================

TEST_OCID = "2e0a31fb5fef6dfe331d3bfef62f7ac8"
TEST_CHARACTER_NAME = "식사동그놈"
