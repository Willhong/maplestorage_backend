"""
Story 2.9: 크롤링 에러 처리 및 메시지 테스트

테스트 대상:
- AC-2.9.1: 사용자 친화적 에러 메시지 반환
- AC-2.9.2: 4가지 에러 케이스별 맞춤 메시지
- AC-2.9.3: 기술적 에러 메시지 포함 (개발자용)
- AC-2.9.5: 에러 발생 시간 표시
"""
import pytest
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from unittest.mock import patch, MagicMock

from characters.models import CharacterBasic
from accounts.models import Character, CrawlTask
from accounts.exceptions import (
    CrawlError, CharacterNotFoundError, NetworkError, MaintenanceError,
    ErrorType, ERROR_MESSAGES, classify_exception
)


@pytest.fixture
def user(db):
    """테스트용 사용자 생성"""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpassword'
    )


@pytest.fixture
def character_basic(db):
    """테스트용 CharacterBasic 생성"""
    return CharacterBasic.objects.create(
        ocid='test-ocid-29',
        character_name='에러테스트캐릭터',
        world_name='스카니아',
        character_gender='남',
        character_class='아크메이지(불,독)'
    )


@pytest.fixture
def api_client():
    """API 테스트 클라이언트"""
    return APIClient()


class TestErrorTypeDefinitions:
    """에러 타입 정의 테스트"""

    def test_error_type_enum_has_four_types(self):
        """AC-2.9.2: 4가지 에러 타입이 정의되어 있음"""
        assert len(ErrorType) == 4
        assert ErrorType.CHARACTER_NOT_FOUND.value == "CHARACTER_NOT_FOUND"
        assert ErrorType.NETWORK_ERROR.value == "NETWORK_ERROR"
        assert ErrorType.MAINTENANCE.value == "MAINTENANCE"
        assert ErrorType.UNKNOWN.value == "UNKNOWN"

    def test_error_messages_mapping_exists(self):
        """AC-2.9.2: 각 에러 타입에 대한 메시지 매핑이 존재"""
        assert ErrorType.CHARACTER_NOT_FOUND in ERROR_MESSAGES
        assert ErrorType.NETWORK_ERROR in ERROR_MESSAGES
        assert ErrorType.MAINTENANCE in ERROR_MESSAGES
        assert ErrorType.UNKNOWN in ERROR_MESSAGES


class TestUserFriendlyErrorMessages:
    """AC-2.9.1: 사용자 친화적 에러 메시지 테스트"""

    def test_ac2_9_1_user_friendly_error_message(self):
        """에러 발생 시 사용자 친화적 메시지가 설정됨"""
        error = CrawlError(error_type=ErrorType.NETWORK_ERROR)
        assert "잠시 후 다시 시도" in error.user_message

    def test_crawl_error_provides_user_message(self):
        """CrawlError가 user_message 속성을 제공"""
        error = CrawlError()
        assert error.user_message is not None
        assert len(error.user_message) > 0


class TestErrorCaseMessages:
    """AC-2.9.2: 4가지 에러 케이스별 맞춤 메시지 테스트"""

    def test_ac2_9_2_character_not_found_error_message(self):
        """CharacterNotFoundError 메시지 검증"""
        error = CharacterNotFoundError()
        expected = "캐릭터 정보를 찾을 수 없습니다. 캐릭터 공개 설정을 확인해주세요"
        assert error.user_message == expected
        assert error.error_type == ErrorType.CHARACTER_NOT_FOUND

    def test_ac2_9_2_network_error_message(self):
        """NetworkError 메시지 검증"""
        error = NetworkError()
        expected = "일시적인 네트워크 오류입니다. 잠시 후 다시 시도해주세요"
        assert error.user_message == expected
        assert error.error_type == ErrorType.NETWORK_ERROR

    def test_ac2_9_2_maintenance_error_message(self):
        """MaintenanceError 메시지 검증"""
        error = MaintenanceError()
        expected = "메이플스토리 공식 사이트 점검 중입니다"
        assert error.user_message == expected
        assert error.error_type == ErrorType.MAINTENANCE

    def test_ac2_9_2_unknown_error_message(self):
        """Unknown 에러 메시지 검증"""
        error = CrawlError(error_type=ErrorType.UNKNOWN)
        expected = "알 수 없는 오류가 발생했습니다. 문제가 지속되면 고객센터에 문의해주세요"
        assert error.user_message == expected


class TestTechnicalErrorMessage:
    """AC-2.9.3: 기술적 에러 메시지 테스트"""

    def test_ac2_9_3_technical_error_included(self):
        """기술적 에러 메시지가 별도로 저장됨"""
        technical_msg = "TimeoutError: Connection timed out after 30s"
        error = NetworkError(technical_error=technical_msg)
        assert error.technical_error == technical_msg

    def test_to_dict_includes_technical_error(self):
        """to_dict() 메서드가 technical_error를 포함"""
        technical_msg = "requests.exceptions.Timeout: Read timed out"
        error = NetworkError(technical_error=technical_msg)
        error_dict = error.to_dict()

        assert "error_type" in error_dict
        assert "error_message" in error_dict
        assert "technical_error" in error_dict
        assert error_dict["technical_error"] == technical_msg


class TestExceptionClassification:
    """예외 분류 테스트"""

    def test_classify_timeout_as_network_error(self):
        """TimeoutError는 NetworkError로 분류"""
        exc = TimeoutError("Connection timed out")
        result = classify_exception(exc)
        assert isinstance(result, NetworkError)
        assert result.error_type == ErrorType.NETWORK_ERROR

    def test_classify_already_crawl_error(self):
        """이미 CrawlError인 경우 그대로 반환"""
        original = CharacterNotFoundError()
        result = classify_exception(original)
        assert result is original

    def test_classify_generic_exception_as_unknown(self):
        """일반 예외는 UNKNOWN으로 분류"""
        exc = RuntimeError("Something went wrong")
        result = classify_exception(exc)
        assert result.error_type == ErrorType.UNKNOWN

    def test_classify_404_in_message(self):
        """메시지에 404가 포함된 예외는 CharacterNotFoundError"""
        exc = Exception("HTTP 404 Not Found")
        result = classify_exception(exc)
        assert result.error_type == ErrorType.CHARACTER_NOT_FOUND

    def test_classify_maintenance_in_message(self):
        """메시지에 점검이 포함된 예외는 MaintenanceError"""
        exc = Exception("서버 점검 중입니다")
        result = classify_exception(exc)
        assert result.error_type == ErrorType.MAINTENANCE


class TestCrawlTaskModelErrorFields:
    """CrawlTask 모델 에러 필드 테스트"""

    def test_crawl_task_has_error_type_field(self, character_basic):
        """CrawlTask 모델에 error_type 필드가 있음"""
        task = CrawlTask.objects.create(
            task_id='test-task-error-type',
            character_basic=character_basic,
            task_type='inventory',
            status='FAILURE',
            error_type='NETWORK_ERROR',
            error_message='일시적인 네트워크 오류입니다.'
        )
        assert task.error_type == 'NETWORK_ERROR'

    def test_crawl_task_has_technical_error_field(self, character_basic):
        """CrawlTask 모델에 technical_error 필드가 있음"""
        technical_error = "TimeoutError: Connection timed out after 30s"
        task = CrawlTask.objects.create(
            task_id='test-task-technical',
            character_basic=character_basic,
            task_type='inventory',
            status='FAILURE',
            technical_error=technical_error
        )
        assert task.technical_error == technical_error


class TestCrawlStatusAPIErrorResponse:
    """크롤링 상태 API 에러 응답 테스트"""

    def test_ac2_9_3_api_response_includes_technical_error(self, api_client, character_basic):
        """AC-2.9.3: API 응답에 technical_error 필드 포함"""
        # Given: 실패한 크롤링 작업
        task = CrawlTask.objects.create(
            task_id='test-api-technical',
            character_basic=character_basic,
            task_type='inventory',
            status='FAILURE',
            error_type='NETWORK_ERROR',
            error_message='일시적인 네트워크 오류입니다.',
            technical_error='TimeoutError: Connection timed out'
        )

        # When: API 호출
        response = api_client.get(f'/api/crawl-tasks/{task.task_id}/')

        # Then: 응답에 에러 정보 포함
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'FAILURE'
        assert data['error_type'] == 'NETWORK_ERROR'
        assert 'error_message' in data
        assert 'technical_error' in data

    def test_ac2_9_5_api_response_includes_timestamp(self, api_client, character_basic):
        """AC-2.9.5: API 응답에 updated_at 타임스탬프 포함"""
        # Given: 실패한 크롤링 작업
        task = CrawlTask.objects.create(
            task_id='test-api-timestamp',
            character_basic=character_basic,
            task_type='inventory',
            status='FAILURE',
            error_type='CHARACTER_NOT_FOUND',
            error_message='캐릭터를 찾을 수 없습니다.'
        )

        # When: API 호출
        response = api_client.get(f'/api/crawl-tasks/{task.task_id}/')

        # Then: updated_at 포함
        assert response.status_code == 200
        data = response.json()
        assert 'updated_at' in data
        assert data['updated_at'] is not None

    def test_api_error_type_values(self, api_client, character_basic):
        """각 에러 타입 값이 올바르게 반환됨"""
        error_types = ['CHARACTER_NOT_FOUND', 'NETWORK_ERROR', 'MAINTENANCE', 'UNKNOWN']

        for error_type in error_types:
            task = CrawlTask.objects.create(
                task_id=f'test-type-{error_type}',
                character_basic=character_basic,
                task_type='inventory',
                status='FAILURE',
                error_type=error_type,
                error_message=f'Test message for {error_type}'
            )

            response = api_client.get(f'/api/crawl-tasks/{task.task_id}/')
            assert response.status_code == 200
            assert response.json()['error_type'] == error_type
