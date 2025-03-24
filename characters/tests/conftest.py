import pytest
from rest_framework.test import APIClient
from django.core.cache import cache


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
