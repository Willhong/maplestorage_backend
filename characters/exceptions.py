"""
메이플스토리 백엔드 애플리케이션의 예외 처리를 위한 커스텀 예외 클래스 모듈
"""
from rest_framework import status


class MapleAPIError(Exception):
    """메이플스토리 API 관련 기본 예외 클래스"""
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_message = "메이플스토리 API 호출 중 오류가 발생했습니다."

    def __init__(self, message=None, status_code=None, detail=None):
        self.message = message or self.default_message
        self.status_code = status_code or self.status_code
        self.detail = detail
        super().__init__(self.message)

    def to_dict(self):
        """예외 정보를 딕셔너리로 변환"""
        error_dict = {
            "error": self.message,
            "status_code": self.status_code
        }
        if self.detail:
            error_dict["detail"] = self.detail
        return error_dict


class APIRateLimitError(MapleAPIError):
    """API 호출 제한 관련 예외"""
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_message = "API 호출 제한에 도달했습니다. 잠시 후 다시 시도해주세요."


class APIConnectionError(MapleAPIError):
    """API 연결 관련 예외"""
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_message = "메이플스토리 API 서버에 연결할 수 없습니다."


class APITimeoutError(MapleAPIError):
    """API 타임아웃 관련 예외"""
    status_code = status.HTTP_504_GATEWAY_TIMEOUT
    default_message = "메이플스토리 API 요청 시간이 초과되었습니다."


class CharacterNotFoundError(MapleAPIError):
    """캐릭터를 찾을 수 없는 경우의 예외"""
    status_code = status.HTTP_404_NOT_FOUND
    default_message = "캐릭터를 찾을 수 없습니다."


class InvalidParameterError(MapleAPIError):
    """잘못된 파라미터 관련 예외"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_message = "잘못된 요청 파라미터입니다."


class DataValidationError(MapleAPIError):
    """데이터 검증 관련 예외"""
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_message = "데이터 검증에 실패했습니다."


class DatabaseError(MapleAPIError):
    """데이터베이스 관련 예외"""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_message = "데이터베이스 작업 중 오류가 발생했습니다."


class AuthenticationError(MapleAPIError):
    """인증 관련 예외"""
    status_code = status.HTTP_401_UNAUTHORIZED
    default_message = "인증에 실패했습니다."


class PermissionDeniedError(MapleAPIError):
    """권한 관련 예외"""
    status_code = status.HTTP_403_FORBIDDEN
    default_message = "접근 권한이 없습니다."
