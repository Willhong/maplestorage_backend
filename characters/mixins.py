import requests
import time
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from define.define import APIKEY
from .exceptions import MapleAPIError


class MapleAPIClientMixin:
    """
    메이플스토리 API 호출을 위한 공통 로직을 제공하는 믹스인
    """

    def get_headers(self):
        """API 호출용 헤더 반환"""
        return {
            "accept": "application/json",
            "x-nxopen-api-key": APIKEY
        }

    def get_api_data(self, url, params=None):
        """
        API 호출 및 응답 데이터 반환

        Args:
            url (str): API 엔드포인트 URL
            params (dict, optional): URL 파라미터

        Returns:
            dict: API 응답 데이터

        Raises:
            requests.exceptions.RequestException: API 호출 실패 시
        """
        start_time = time.time()
        headers = self.get_headers()

        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            print(f"API 호출 소요시간: {time.time() - start_time:.2f}초")
            return data
        except requests.exceptions.RequestException as e:
            print(f"API 호출 실패: {str(e)}")
            raise

    def validate_data(self, schema_class, data):
        """
        데이터 검증

        Args:
            schema_class: Pydantic 스키마 클래스
            data (dict): 검증할 데이터

        Returns:
            object: 검증된 Pydantic 모델 인스턴스
        """
        validation_start = time.time()
        validated_data = schema_class.model_validate(data)
        print(f"데이터 검증 소요시간: {time.time() - validation_start:.2f}초")
        return validated_data


class APIViewMixin(APIView):
    """
    API 뷰 공통 로직을 제공하는 믹스인
    """

    def handle_exception(self, exc):
        """
        예외 처리 공통 로직

        Args:
            exc: 발생한 예외

        Returns:
            Response: 예외 정보를 담은 응답 객체
        """
        # 커스텀 MapleAPIError 예외 처리
        if isinstance(exc, MapleAPIError):
            return Response(
                exc.to_dict(),
                status=exc.status_code
            )

        # requests 라이브러리 예외 처리
        if isinstance(exc, requests.exceptions.HTTPError):
            status_code = exc.response.status_code if hasattr(
                exc, 'response') else 500
            error_message = "메이플스토리 API 호출 중 HTTP 오류가 발생했습니다."
            return Response(
                {"error": error_message, "detail": str(exc)},
                status=status_code
            )

        if isinstance(exc, requests.exceptions.ConnectionError):
            return Response(
                {"error": "메이플스토리 API 서버에 연결할 수 없습니다.", "detail": str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        if isinstance(exc, requests.exceptions.Timeout):
            return Response(
                {"error": "메이플스토리 API 요청 시간이 초과되었습니다.", "detail": str(exc)},
                status=status.HTTP_504_GATEWAY_TIMEOUT
            )

        if isinstance(exc, requests.exceptions.RequestException):
            return Response(
                {"error": "메이플스토리 API 호출 중 오류가 발생했습니다.", "detail": str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        # 기본 DRF 예외 처리
        return super().handle_exception(exc)

    def get_date_param(self, request):
        """
        요청에서 date 파라미터 추출

        Args:
            request: HTTP 요청 객체

        Returns:
            str or None: date 파라미터 값
        """
        return request.query_params.get('date')

    def check_cache(self, cache_key, cache_time=3600):
        """
        캐시 확인 로직 (구현 예시)

        Args:
            cache_key (str): 캐시 키
            cache_time (int): 캐시 유효 시간(초)

        Returns:
            object or None: 캐시된 데이터 또는 None
        """
        # 캐시 구현은 실제 프로젝트에 맞게 수정 필요
        # 예: Django의 cache framework 또는 Redis 사용
        return None


class CharacterDataMixin:
    """
    캐릭터 데이터 처리를 위한 공통 로직을 제공하는 믹스인
    """

    def format_response_data(self, data, message=None):
        """
        API 응답 데이터 포맷팅

        Args:
            data: 응답 데이터
            message (str, optional): 응답 메시지

        Returns:
            dict: 포맷팅된 응답 데이터
        """
        response = {
            "data": data
        }

        if message:
            response["message"] = message

        return response

    def convert_to_local_time(self, date_value):
        """
        다양한 형태의 날짜/시간 데이터를 서버 시간대로 변환

        Args:
            date_value: 변환할 날짜/시간 (str, datetime, None)

        Returns:
            datetime: 서버 시간대로 변환된 datetime 객체
        """
        import logging
        logger = logging.getLogger('maple_api')

        try:
            # None인 경우 현재 시간 반환
            if date_value is None:
                return timezone.now()

            # 이미 datetime 객체인 경우
            if isinstance(date_value, timezone.datetime):
                # timezone-aware인지 확인
                if timezone.is_aware(date_value):
                    # 서버 타임존으로 변환
                    return timezone.localtime(date_value)
                else:
                    # timezone-naive인 경우 UTC로 가정하고 변환
                    aware_dt = timezone.make_aware(date_value, timezone.utc)
                    return timezone.localtime(aware_dt)

            # 문자열인 경우
            elif isinstance(date_value, str):
                # ISO 형식의 문자열을 datetime 객체로 변환
                dt = timezone.datetime.fromisoformat(
                    date_value.replace('Z', '+00:00'))
                # UTC 시간을 서버의 타임존으로 변환
                return timezone.localtime(dt)

            # 그 외의 경우 현재 시간 반환
            else:
                logger.warning(f"알 수 없는 날짜 형식: {type(date_value)}")
                return timezone.now()

        except Exception as e:
            logger.error(f"날짜 변환 오류: {str(e)}")
            return timezone.now()

    def log_request(self, request_type, character_name=None, ocid=None):
        """
        요청 로깅

        Args:
            request_type (str): 요청 유형
            character_name (str, optional): 캐릭터 이름
            ocid (str, optional): 캐릭터 OCID
        """
        print(
            f"[{timezone.now()}] {request_type} 요청 - 캐릭터: {character_name}, OCID: {ocid}")
