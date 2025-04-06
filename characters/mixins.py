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
from util.rate_limiter import rate_limited
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

    @rate_limited(500)
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

    def get_cached_data(self, ocid, model_class, related_name=None, hours=1, additional_filters=None, additional_cache_key=None):
        """
        캐시된 데이터 조회를 위한 공통 메서드

        Args:
            ocid (str): 캐릭터 식별자
            model_class: 조회할 모델 클래스
            related_name (str): 관련 데이터 필드명 (있는 경우)
            hours (int): 캐시 유효 시간 (기본 1시간)
            additional_filters (dict): 추가 필터링 조건 (있는 경우)
            additional_cache_key (str): 캐시 키에 추가할 구분자 (있는 경우)

        Returns:
            tuple: (캐시된 데이터, 관련 데이터)
        """
        try:
            # 현재 시간에서 지정된 시간 전 계산
            cache_time = timezone.now() - timedelta(hours=hours)
            # logger.info(f"현재 시간: {timezone.now()}, {hours}시간 전: {cache_time}")

            # 먼저 CharacterBasic에서 캐릭터 정보 조회
            character = CharacterBasic.objects.filter(ocid=ocid).first()
            if not character:
                logger.info(f"캐릭터 기본 정보 없음: {ocid}")
                return None, None

            # 모델 클래스가 CharacterBasic인 경우 바로 반환
            if model_class == CharacterBasic:
                if character.last_updated >= cache_time:
                    # logger.info(
                    # f"캐시된 기본 데이터 찾음: {ocid}, 날짜: {character.last_updated}")
                    return character, None
                else:
                    logger.info(
                        f"기본 데이터 캐시 만료: {ocid}, 날짜: {character.last_updated}")
                    return None, None

            # related_name이 있는 경우 역참조를 통해 데이터 조회
            if related_name and hasattr(character, related_name):
                related_manager = getattr(character, related_name)

                if hasattr(related_manager, 'filter'):
                    # QuerySet인 경우 (Many 관계)
                    filter_kwargs = {'date__gte': cache_time}

                    # 추가 필터가 있는 경우 적용
                    if additional_filters:
                        filter_kwargs.update(additional_filters)

                    cached_data = related_manager.filter(
                        **filter_kwargs
                    ).order_by('-date').first()

                    if cached_data:
                        # logger.info(
                        #     f"캐시된 관련 데이터 찾음: {character.character_name}, 날짜: {cached_data.date}")
                        # 추가 관련 데이터가 있는 경우 함께 반환
                        additional_related = None
                        if hasattr(cached_data, related_name):
                            additional_manager = getattr(
                                cached_data, related_name)
                            if hasattr(additional_manager, 'all'):
                                additional_related = additional_manager.all()
                            else:
                                additional_related = additional_manager
                        return cached_data, additional_related
                    else:
                        # 시간 필터링 없이 다시 조회
                        filter_kwargs = {}
                        if additional_filters:
                            filter_kwargs.update(additional_filters)

                        any_data = related_manager.filter(
                            **filter_kwargs
                        ).order_by('-date').first()

                        if any_data:
                            logger.info(
                                f"관련 데이터 있으나 {hours}시간 초과: {character.character_name}, 날짜: {any_data.date}")
                        else:
                            logger.info(
                                f"관련 데이터 없음: {character.character_name}")
                        return None, None
                else:
                    # 단일 객체인 경우 (One 관계)
                    cached_data = related_manager
                    if cached_data and hasattr(cached_data, 'date') and cached_data.date >= cache_time:
                        logger.info(
                            f"캐시된 단일 관련 데이터 찾음: {character.character_name}, 날짜: {cached_data.date}")
                        return cached_data, None
                    else:
                        logger.info(
                            f"단일 관련 데이터 없거나 만료됨: {character.character_name}")
                        return None, None

            # related_name이 없는 경우 character_name으로 필터링
            filter_kwargs = {
                'character_name': character.character_name,
                'date__gte': cache_time
            }

            # 추가 필터가 있는 경우 적용
            if additional_filters:
                filter_kwargs.update(additional_filters)

            cached_data = model_class.objects.filter(
                **filter_kwargs
            ).order_by('-date').first()

            if cached_data:
                logger.info(
                    f"캐시된 데이터 찾음: {character.character_name}, 날짜: {cached_data.date}")
                return cached_data, None
            else:
                # 시간 필터링 없이 다시 조회
                filter_kwargs = {'character_name': character.character_name}
                if additional_filters:
                    filter_kwargs.update(additional_filters)

                any_data = model_class.objects.filter(
                    **filter_kwargs
                ).order_by('-date').first()

                if any_data:
                    logger.info(
                        f"캐시된 데이터 있으나 {hours}시간 초과: {character.character_name}, 날짜: {any_data.date}")
                else:
                    logger.info(f"캐시된 데이터 없음: {character.character_name}")

                return None, None

        except Exception as e:
            logger.error(f"캐시된 데이터 조회 중 오류 발생: {str(e)}")
            return None, None

    def check_and_return_cached_data(self, request, model_class, ocid=None, related_name=None, serializer_class=None, additional_filters=None, additional_cache_key=None):
        """
        캐시된 데이터 확인 및 반환을 위한 공통 메서드

        Args:
            request: HTTP 요청 객체
            model_class: 조회할 모델 클래스
            ocid: 캐릭터 식별자
            related_name (str): 관련 데이터 필드명 (있는 경우)
            serializer_class: 사용할 시리얼라이저 클래스 (있는 경우)
            additional_filters (dict): 추가 필터링 조건 (있는 경우)
            additional_cache_key (str): 캐시 키에 추가할 구분자 (있는 경우)

        Returns:
            Response or None: 캐시된 데이터가 있으면 Response 객체, 없으면 None
        """
        try:
            # force_refresh 파라미터 확인
            force_refresh = request.query_params.get(
                'force_refresh', 'false').lower() == 'true'
            if force_refresh:
                return None

            # 캐릭터 기본 정보 조회
            if not ocid:
                return None

            # 캐시된 데이터 조회
            cached_data, related_data = self.get_cached_data(
                ocid, model_class, related_name, additional_filters=additional_filters, additional_cache_key=additional_cache_key)

            if cached_data:
                # serializer_class가 제공된 경우 해당 serializer 사용
                if serializer_class:
                    if related_data and isinstance(related_data, (list, models.QuerySet)):
                        # Many 관계인 경우
                        serializer = serializer_class(
                            cached_data, context={'request': request})
                    else:
                        # One 관계이거나 관련 데이터가 없는 경우
                        serializer = serializer_class(
                            cached_data, context={'request': request})
                    return Response(self.format_response_data(serializer.data))

                # serializer가 없는 경우 기존 로직 사용
                response_data = {}

                # 모델 인스턴스의 필드를 딕셔너리로 변환
                for field in cached_data._meta.fields:
                    # CharacterBasic이 아닌 경우 character 관련 필드 제외
                    if model_class != CharacterBasic and field.name in ['character', 'id']:
                        continue
                    response_data[field.name] = getattr(
                        cached_data, field.name)

                # 관련 데이터가 있는 경우 처리
                if related_data:
                    if isinstance(related_data, (list, models.QuerySet)):
                        # Many 관계인 경우
                        related_list = []
                        for item in related_data:
                            item_data = {}
                            for field in item._meta.fields:
                                if field.name not in ['id', 'character']:
                                    item_data[field.name] = getattr(
                                        item, field.name)
                            related_list.append(item_data)
                        response_data[related_name] = related_list
                    else:
                        # One 관계인 경우
                        related_data_dict = {}
                        for field in related_data._meta.fields:
                            if field.name not in ['id', 'character']:
                                related_data_dict[field.name] = getattr(
                                    related_data, field.name)
                        response_data[related_name] = related_data_dict

                return Response(self.format_response_data(response_data))

            return None

        except Exception as e:
            logger.error(f"캐시된 데이터 확인 중 오류 발생: {str(e)}")
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
