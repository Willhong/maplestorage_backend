"""
메이플스토리 백엔드 애플리케이션의 유틸리티 함수 모듈
"""
import logging
import requests
import traceback
from django.db import DatabaseError as DjangoDatabaseError
from pydantic import ValidationError
from rest_framework.response import Response

from .exceptions import (
    MapleAPIError, APIRateLimitError, APIConnectionError,
    APITimeoutError, CharacterNotFoundError, InvalidParameterError,
    DataValidationError, DatabaseError
)

# 로거 설정
logger = logging.getLogger('maple_api')


def handle_api_exception(func):
    """
    API 호출 관련 예외를 처리하는 데코레이터

    Args:
        func: 데코레이트할 함수

    Returns:
        wrapper: 예외 처리 로직이 추가된 함수
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if hasattr(
                e, 'response') else 500

            # HTTP 상태 코드에 따른 예외 처리
            if status_code == 429:
                logger.warning(f"API 호출 제한 초과: {str(e)}")
                raise APIRateLimitError(detail=str(e))
            elif status_code == 404:
                logger.warning(f"캐릭터를 찾을 수 없음: {str(e)}")
                raise CharacterNotFoundError(detail=str(e))
            elif status_code >= 500:
                logger.error(f"메이플스토리 API 서버 오류: {str(e)}")
                raise MapleAPIError(detail=str(e))
            else:
                logger.error(f"API 호출 중 HTTP 오류: {str(e)}")
                raise MapleAPIError(detail=str(e), status_code=status_code)

        except requests.exceptions.ConnectionError as e:
            logger.error(f"API 연결 오류: {str(e)}")
            raise APIConnectionError(detail=str(e))

        except requests.exceptions.Timeout as e:
            logger.error(f"API 타임아웃: {str(e)}")
            raise APITimeoutError(detail=str(e))

        except requests.exceptions.RequestException as e:
            logger.error(f"API 요청 오류: {str(e)}")
            raise MapleAPIError(detail=str(e))

        except ValidationError as e:
            logger.error(f"데이터 검증 오류: {str(e)}")
            raise DataValidationError(detail=str(e))

        except DjangoDatabaseError as e:
            logger.error(f"데이터베이스 오류: {str(e)}")
            raise DatabaseError(detail=str(e))

        except (CharacterNotFoundError, APIRateLimitError, APIConnectionError,
                APITimeoutError, InvalidParameterError, DataValidationError,
                DatabaseError, MapleAPIError):
            # 이미 처리된 커스텀 예외는 그대로 전파
            raise

        except Exception as e:
            logger.error(f"예상치 못한 오류: {str(e)}\n{traceback.format_exc()}")
            raise MapleAPIError(
                message="서버에서 예상치 못한 오류가 발생했습니다.",
                detail=str(e),
                status_code=500
            )

    return wrapper


def api_exception_handler(exc, context):
    """
    DRF 예외 핸들러

    Args:
        exc: 발생한 예외
        context: 예외 컨텍스트

    Returns:
        Response: 예외 정보를 담은 응답 객체
    """
    if isinstance(exc, MapleAPIError):
        logger.error(f"{exc.__class__.__name__}: {exc.message} - {exc.detail}")
        return Response(
            exc.to_dict(),
            status=exc.status_code
        )

    # 기본 DRF 예외 처리로 위임
    from rest_framework.views import exception_handler as drf_exception_handler
    return drf_exception_handler(exc, context)


def log_api_call(api_name, params=None):
    """
    API 호출 로깅

    Args:
        api_name: API 이름
        params: API 파라미터
    """
    params_str = str(params) if params else "없음"
    logger.info(f"API 호출: {api_name}, 파라미터: {params_str}")


def validate_character_name(character_name):
    """
    캐릭터 이름 유효성 검사

    Args:
        character_name: 검사할 캐릭터 이름

    Raises:
        InvalidParameterError: 캐릭터 이름이 유효하지 않은 경우
    """
    if not character_name:
        raise InvalidParameterError(message="캐릭터 이름은 필수 항목입니다.")

    if len(character_name) < 2 or len(character_name) > 12:
        raise InvalidParameterError(message="캐릭터 이름은 2~12자 사이여야 합니다.")


def validate_date_format(date_str):
    """
    날짜 형식 유효성 검사

    Args:
        date_str: 검사할 날짜 문자열

    Raises:
        InvalidParameterError: 날짜 형식이 유효하지 않은 경우
    """
    if not date_str:
        return

    import re
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        raise InvalidParameterError(
            message="날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식이어야 합니다."
        )
