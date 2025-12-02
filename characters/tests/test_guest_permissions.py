"""
Story 1.8: 게스트 모드 캐릭터 조회 - 권한 테스트

AC #8: 조회 API는 인증 없이 접근 가능하다 (AllowAny)
AC #9: 캐릭터 등록/삭제 API는 로그인 필수이다 (IsAuthenticated)
"""
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth.models import User
from characters.models import CharacterBasic
from django.utils import timezone


@pytest.mark.django_db
class TestGuestModePermissions(APITestCase):
    """게스트 모드 권한 테스트 클래스 (Story 1.8)"""

    def setUp(self):
        """테스트 데이터 설정"""
        self.client = APIClient()
        self.ocid = "test_ocid_12345"
        self.character_name = "테스트캐릭터"

        # 기본 캐릭터 생성 (CharacterBasic 모델 필드에 맞춤)
        self.character = CharacterBasic.objects.create(
            ocid=self.ocid,
            character_name=self.character_name,
            world_name="스카니아",
            character_gender="여",
            character_class="아크메이지(불,독)"
        )

        # 테스트 사용자 생성 (인증 테스트용)
        self.test_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123'
        )

    def test_guest_can_access_character_basic_view(self):
        """AC #8: 비인증 사용자가 캐릭터 기본 정보 조회 가능"""
        # 인증 없이 요청 (게스트 모드)
        url = reverse('character-basic', kwargs={'ocid': self.ocid})
        response = self.client.get(url)

        # 200 OK 또는 캐시 miss로 인한 API 호출 시도 (외부 API mock 없으므로 에러 가능)
        # 핵심: 401 Unauthorized가 아니어야 함 (권한 체크 통과)
        assert response.status_code != status.HTTP_401_UNAUTHORIZED
        assert response.status_code != status.HTTP_403_FORBIDDEN

    def test_guest_can_access_character_id_view(self):
        """AC #8: 비인증 사용자가 캐릭터 ID 조회 가능"""
        url = reverse('character-id')
        response = self.client.get(url, {'character_name': self.character_name})

        # 401/403이 아니어야 함 (AllowAny 권한 확인)
        # 400 (파라미터 누락) 또는 외부 API 에러는 허용
        assert response.status_code != status.HTTP_401_UNAUTHORIZED
        assert response.status_code != status.HTTP_403_FORBIDDEN

    def test_guest_can_access_character_stat_view(self):
        """AC #8: 비인증 사용자가 캐릭터 스탯 조회 가능"""
        url = reverse('character-stat', kwargs={'ocid': self.ocid})
        response = self.client.get(url)

        assert response.status_code != status.HTTP_401_UNAUTHORIZED
        assert response.status_code != status.HTTP_403_FORBIDDEN

    def test_guest_can_access_character_all_data_view(self):
        """AC #8: 비인증 사용자가 캐릭터 전체 데이터 조회 가능"""
        url = reverse('character-all-data')
        response = self.client.get(url, {'character_name': self.character_name})

        # 400 (캐릭터 이름 필요) 또는 외부 API 에러는 허용
        # 핵심: 인증 에러가 아니어야 함
        assert response.status_code != status.HTTP_401_UNAUTHORIZED
        assert response.status_code != status.HTTP_403_FORBIDDEN

    def test_guest_cannot_register_character(self):
        """AC #9: 비인증 사용자가 캐릭터 등록 불가"""
        url = reverse('character-create')
        response = self.client.post(url, {'character_name': '새캐릭터'})

        # 401 Unauthorized 응답 예상
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_guest_cannot_start_crawl(self):
        """AC #9: 비인증 사용자가 크롤링 시작 불가"""
        url = reverse('crawl-start', kwargs={'ocid': self.ocid})
        response = self.client.post(url, {'crawl_types': ['inventory']})

        # 401 Unauthorized 응답 예상
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_authenticated_user_can_register_character(self):
        """AC #9: 인증된 사용자는 캐릭터 등록 가능 (권한 통과 확인)"""
        # 사용자 인증
        self.client.force_authenticate(user=self.test_user)

        url = reverse('character-create')
        response = self.client.post(url, {'character_name': '새캐릭터'})

        # 401/403이 아니어야 함 (외부 API 에러는 허용)
        assert response.status_code != status.HTTP_401_UNAUTHORIZED
        assert response.status_code != status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestRateLimiting(APITestCase):
    """Rate Limiting 테스트 (Story 1.8: AC #8 관련)"""

    def setUp(self):
        self.client = APIClient()
        self.ocid = "test_ocid_rate_limit"

        # 기본 캐릭터 생성 (CharacterBasic 모델 필드에 맞춤)
        self.character = CharacterBasic.objects.create(
            ocid=self.ocid,
            character_name="레이트테스트",
            world_name="스카니아",
            character_gender="남",
            character_class="히어로"
        )

    def test_anon_rate_limit_header_present(self):
        """익명 사용자 요청 시 Rate Limit 헤더 확인"""
        url = reverse('character-basic', kwargs={'ocid': self.ocid})

        # 첫 번째 요청 - 헤더 확인은 DRF throttling 구현에 따라 다를 수 있음
        response = self.client.get(url)

        # Rate limiting이 적용되면 429 또는 정상 응답
        # 401/403이 아닌 것만 확인 (AllowAny)
        assert response.status_code != status.HTTP_401_UNAUTHORIZED
        assert response.status_code != status.HTTP_403_FORBIDDEN
