import requests
import time
import logging
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from datetime import timedelta, datetime
from django.db import models

from define.define import APIKEY
from characters.models import *
from .exceptions import MapleAPIError

logger = logging.getLogger('maple_api')


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

    def format_response_data(self, data, message=None):
        """응답 데이터 포맷팅"""
        response = {"data": data}
        if message:
            response["message"] = message
        return response

    def log_request(self, action, character_name):
        """요청 로깅"""
        print(f"{action} 요청 - 캐릭터: {character_name}")

    def get_cached_data(self, character_name, model_class, related_name=None, hours=1):
        """
        캐시된 데이터 조회를 위한 공통 메서드

        Args:
            character_name (str): 캐릭터 이름
            model_class: 조회할 모델 클래스
            related_name (str): 관련 데이터 필드명 (있는 경우)
            hours (int): 캐시 유효 시간 (기본 1시간)

        Returns:
            tuple: (캐시된 데이터, 관련 데이터)
        """
        try:
            # 현재 시간에서 지정된 시간 전 계산
            cache_time = timezone.now() - timedelta(hours=hours)
            print(f"현재 시간: {timezone.now()}, {hours}시간 전: {cache_time}")

            # 캐릭터 이름과 시간으로 필터링하여 최신 데이터 반환
            cached_data = model_class.objects.filter(
                character_name=character_name,
                date__gte=cache_time
            ).order_by('-date').first()

            if cached_data:
                print(f"캐시된 데이터 찾음: {character_name}, 날짜: {cached_data.date}")

                # 관련 데이터가 있는 경우 함께 반환
                related_data = None
                if related_name and hasattr(cached_data, related_name):
                    related_manager = getattr(cached_data, related_name)
                    if hasattr(related_manager, 'all'):
                        related_data = related_manager.all()
                    else:
                        related_data = related_manager

                return cached_data, related_data
            else:
                # 시간 필터링 없이 다시 조회
                any_data = model_class.objects.filter(
                    character_name=character_name
                ).order_by('-date').first()

                if any_data:
                    print(
                        f"캐시된 데이터 있으나 {hours}시간 초과: {character_name}, 날짜: {any_data.date}")
                else:
                    print(f"캐시된 데이터 없음: {character_name}")

                return None, None

        except Exception as e:
            print(f"캐시된 데이터 조회 중 오류 발생: {str(e)}")
            return None, None

    def check_and_return_cached_data(self, request, model_class, related_name=None, serializer_class=None, schema_class=None):
        """
        캐시된 데이터 확인 및 반환을 위한 공통 메서드

        Args:
            request: HTTP 요청 객체
            model_class: 조회할 모델 클래스
            related_name (str): 관련 데이터 필드명 (있는 경우)
            serializer_class: 직렬화에 사용할 시리얼라이저 클래스
            schema_class: 데이터 검증에 사용할 스키마 클래스

        Returns:
            Response or None: 캐시된 데이터가 있으면 Response 객체, 없으면 None
        """
        try:
            # OCID 가져오기
            ocid = request.query_params.get('ocid')
            if not ocid:
                return None

            # 1시간 전 시간 계산
            one_hour_ago = timezone.now() - timezone.timedelta(hours=1)

            # CharacterBasic 모델이 아닌 경우 character 관계를 통해 조회
            if model_class != CharacterBasic:
                try:
                    character = CharacterBasic.objects.get(ocid=ocid)
                    cached_data = model_class.objects.filter(
                        character=character,
                        date__gte=one_hour_ago
                    ).order_by('-date').first()
                except CharacterBasic.DoesNotExist:
                    return None
            else:
                # CharacterBasic 모델인 경우 직접 조회
                cached_data = model_class.objects.filter(
                    ocid=ocid,
                    date__gte=one_hour_ago
                ).order_by('-date').first()

            if not cached_data:
                return None

            # 시리얼라이저가 제공된 경우 직렬화
            if serializer_class:
                serialized_data = serializer_class(cached_data).data
                return Response(serialized_data)

            # 스키마가 제공된 경우 스키마 변환
            if schema_class:
                schema = schema_class()
                return Response(schema.dump(cached_data))

            # 기본 응답
            return Response({
                'date': cached_data.date,
                'data': cached_data.__dict__
            })

        except Exception as e:
            logger.error(f"캐시된 데이터 조회 중 오류 발생: {str(e)}")
            return None


class CharacterDataMixin:
    """
    캐릭터 데이터 처리를 위한 공통 로직을 제공하는 믹스인
    """

    def convert_to_local_time(self, date_value):
        """
        다양한 형태의 날짜/시간 데이터를 서버 시간대로 변환

        Args:
            date_value: 변환할 날짜/시간 (str, datetime, None)

        Returns:
            datetime: 서버 시간대로 변환된 datetime 객체
        """
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
