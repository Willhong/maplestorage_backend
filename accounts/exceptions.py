"""
Custom exceptions for crawling errors (Story 2.9)

AC-2.9.1: 사용자 친화적인 에러 메시지
AC-2.9.2: 4가지 에러 케이스별 맞춤 메시지 제공
"""
from enum import Enum
from typing import Optional


class ErrorType(str, Enum):
    """크롤링 에러 타입 정의"""
    CHARACTER_NOT_FOUND = "CHARACTER_NOT_FOUND"
    NETWORK_ERROR = "NETWORK_ERROR"
    MAINTENANCE = "MAINTENANCE"
    UNKNOWN = "UNKNOWN"


# AC-2.9.2: 에러 타입별 사용자 친화적 메시지 매핑
ERROR_MESSAGES = {
    ErrorType.CHARACTER_NOT_FOUND: "캐릭터 정보를 찾을 수 없습니다. 캐릭터 공개 설정을 확인해주세요",
    ErrorType.NETWORK_ERROR: "일시적인 네트워크 오류입니다. 잠시 후 다시 시도해주세요",
    ErrorType.MAINTENANCE: "메이플스토리 공식 사이트 점검 중입니다",
    ErrorType.UNKNOWN: "알 수 없는 오류가 발생했습니다. 문제가 지속되면 고객센터에 문의해주세요",
}


class CrawlError(Exception):
    """
    크롤링 기본 에러 클래스

    AC-2.9.1: 사용자 친화적 메시지와 기술적 에러를 분리하여 저장
    AC-2.9.3: 기술적 에러 메시지는 개발자용으로 별도 저장
    """

    def __init__(
        self,
        error_type: ErrorType = ErrorType.UNKNOWN,
        technical_error: Optional[str] = None,
        user_message: Optional[str] = None,
    ):
        self.error_type = error_type
        self.technical_error = technical_error or ""
        # user_message가 제공되면 사용, 아니면 ERROR_MESSAGES에서 가져옴
        self.user_message = user_message or ERROR_MESSAGES.get(
            error_type, ERROR_MESSAGES[ErrorType.UNKNOWN]
        )
        super().__init__(self.user_message)

    def to_dict(self) -> dict:
        """에러 정보를 딕셔너리로 반환 (API 응답용)"""
        return {
            "error_type": self.error_type.value,
            "error_message": self.user_message,
            "technical_error": self.technical_error,
        }


class CharacterNotFoundError(CrawlError):
    """
    캐릭터를 찾을 수 없는 에러 (404, 비공개 캐릭터)

    AC-2.9.2: "캐릭터 정보를 찾을 수 없습니다. 캐릭터 공개 설정을 확인해주세요"
    """

    def __init__(self, technical_error: Optional[str] = None):
        super().__init__(
            error_type=ErrorType.CHARACTER_NOT_FOUND,
            technical_error=technical_error,
        )


class NetworkError(CrawlError):
    """
    네트워크 연결 오류 (Timeout, 연결 실패)

    AC-2.9.2: "일시적인 네트워크 오류입니다. 잠시 후 다시 시도해주세요"
    """

    def __init__(self, technical_error: Optional[str] = None):
        super().__init__(
            error_type=ErrorType.NETWORK_ERROR,
            technical_error=technical_error,
        )


class MaintenanceError(CrawlError):
    """
    메이플스토리 사이트 점검 중 (503, 점검 페이지 감지)

    AC-2.9.2: "메이플스토리 공식 사이트 점검 중입니다"
    """

    def __init__(self, technical_error: Optional[str] = None):
        super().__init__(
            error_type=ErrorType.MAINTENANCE,
            technical_error=technical_error,
        )


def classify_exception(exc: Exception) -> CrawlError:
    """
    일반 예외를 적절한 CrawlError 타입으로 분류

    Args:
        exc: 발생한 예외

    Returns:
        CrawlError: 분류된 에러 객체
    """
    import traceback
    from aiohttp import ClientError, ClientResponseError
    from asyncio import TimeoutError as AsyncTimeoutError

    technical_error = f"{type(exc).__name__}: {str(exc)}\n{traceback.format_exc()}"

    # 이미 CrawlError 타입인 경우
    if isinstance(exc, CrawlError):
        return exc

    # 네트워크 관련 에러
    if isinstance(exc, (AsyncTimeoutError, TimeoutError)):
        return NetworkError(technical_error=technical_error)

    if isinstance(exc, ClientError):
        if isinstance(exc, ClientResponseError):
            # HTTP 상태 코드 기반 분류
            if exc.status == 404:
                return CharacterNotFoundError(technical_error=technical_error)
            elif exc.status == 503:
                return MaintenanceError(technical_error=technical_error)
        return NetworkError(technical_error=technical_error)

    # 문자열 기반 에러 분류
    error_str = str(exc).lower()

    if "not found" in error_str or "404" in error_str:
        return CharacterNotFoundError(technical_error=technical_error)

    if "maintenance" in error_str or "점검" in error_str:
        return MaintenanceError(technical_error=technical_error)

    if any(keyword in error_str for keyword in ["timeout", "connection", "network"]):
        return NetworkError(technical_error=technical_error)

    # 기본: Unknown 에러
    return CrawlError(
        error_type=ErrorType.UNKNOWN,
        technical_error=technical_error,
    )
