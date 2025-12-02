import datetime
import json
import requests
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.utils import timezone
import logging
import asyncio
import aiohttp
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from util.rate_limiter import rate_limited
from util.redis_client import redis_client
import time
import pytz

from define.define import (
    CHARACTER_ID_URL, CHARACTER_BASIC_URL, CHARACTER_POPULARITY_URL,
    CHARACTER_STAT_URL, CHARACTER_ABILITY_URL, CHARACTER_ITEM_EQUIPMENT_URL,
    CHARACTER_CASHITEM_EQUIPMENT_URL, CHARACTER_SYMBOL_URL, CHARACTER_LINK_SKILL_URL,
    CHARACTER_SKILL_URL, CHARACTER_HEXAMATRIX_URL, CHARACTER_HEXAMATRIX_STAT_URL,
    CHARACTER_VMATRIX_URL, CHARACTER_DOJANG_URL, CHARACTER_SET_EFFECT_URL,
    CHARACTER_BEAUTY_EQUIPMENT_URL, CHARACTER_ANDROID_EQUIPMENT_URL,
    CHARACTER_PET_EQUIPMENT_URL, CHARACTER_PROPENSITY_URL, CHARACTER_HYPER_STAT_URL,
    APIKEY
)
from .mixins import MapleAPIClientMixin, APIViewMixin, CharacterDataMixin
from .models import *
from .schemas import (
    AndroidEquipmentSchema, CharacterBasicSchema, CharacterPopularitySchema, CharacterStatSchema,
    CharacterAbilitySchema, CharacterItemEquipmentSchema, CharacterCashItemEquipmentSchema, CharacterSymbolEquipmentSchema,
    CharacterLinkSkillSchema, CharacterSkillSchema,
    CharacterHexaMatrixSchema, CharacterHexaMatrixStatSchema, CharacterVMatrixSchema,
    CharacterDojangSchema, CharacterSetEffectSchema, CharacterBeautyEquipmentSchema,
    CharacterPetEquipmentSchema, CharacterPropensitySchema,
    CharacterHyperStatSchema, CharacterAllDataSchema
)
from pydantic import ValidationError
from .serializers import (
    AndroidEquipmentSerializer, CharacterAbilitySerializer, CharacterBasicSerializer,
    CharacterBeautyEquipmentSerializer, CharacterCashItemEquipmentSerializer,
    CharacterDojangSerializer, CharacterHexaMatrixStatSerializer,
    CharacterHexaMatrixSerializer, CharacterHyperStatSerializer,
    CharacterItemEquipmentSerializer, CharacterLinkSkillSerializer, CharacterPetEquipmentSerializer,
    CharacterPopularitySerializer, CharacterPropensitySerializer,
    CharacterSetEffectSerializer, CharacterSkillSerializer, CharacterStatSerializer, CharacterSymbolEquipmentSerializer, CharacterVMatrixSerializer, CharacterAllDataSerializer
)

logger = logging.getLogger('maple_api')


class BaseCharacterView(MapleAPIClientMixin, APIViewMixin, CharacterDataMixin):
    """
    캐릭터 조회 기본 뷰 클래스
    Story 1.8 AC #8: 모든 조회 API는 인증 없이 접근 가능 (AllowAny)
    """
    model_class = None
    related_name = None
    schema_class = None  # Pydantic 스키마 클래스
    permission_classes = [AllowAny]  # Story 1.8: 게스트 모드 지원

    def validate_data(self, data):
        """API 응답 데이터를 Pydantic 스키마로 검증"""
        if not self.schema_class:
            return data

        try:
            validated_data = self.schema_class(**data)
            # logger.info(f"{self.model_class.__name__} 데이터 검증 성공")
            return validated_data.model_dump(by_alias=True)
        except ValidationError as e:
            logger.error(f"{self.model_class.__name__} 데이터 검증 실패: {str(e)}")
            raise ValueError(
                f"{self.model_class.__name__} 데이터 검증 실패: {str(e)}")

    def save_to_database(self, data, ocid=None):
        """데이터베이스에 API 응답 데이터 저장"""
        try:
            # 데이터 검증
            validated_data = self.validate_data(data)

            if not self.model_class:
                return

            # 기본 데이터 준비
            defaults = {
                'date': validated_data.get('date') or timezone.now(),
            }
            # CharacterId 모델인 경우, ocid 필드 업데이트
            if self.model_class == CharacterId:
                defaults['ocid'] = validated_data.get('ocid')
                obj, created = self.model_class.objects.update_or_create(
                    ocid=validated_data.get('ocid'),
                    defaults=defaults
                )
                return obj

            # CharacterBasic 모델이 아닌 경우, character 관계 설정
            if self.model_class == CharacterBasic:
                validated_data['ocid'] = ocid
                obj = self.model_class.create_from_data(
                    validated_data)
                if obj:
                    created = True
            else:
                if not ocid:
                    logger.error("OCID가 필요한 모델에 OCID가 제공되지 않았습니다.")
                    return

                try:
                    character = CharacterBasic.objects.get(ocid=ocid)
                    defaults['character'] = character
                    obj = self.model_class.create_from_data(
                        character, validated_data)
                    if obj:
                        created = True
                except CharacterBasic.DoesNotExist:
                    logger.error(
                        f"CharacterBasic 모델에서 OCID {ocid}를 찾을 수 없습니다.")
                    return

            # logger.info(
            #     f"{self.model_class.__name__} 데이터 저장 완료: {'생성됨' if created else '업데이트됨'}")
            return obj

        except Exception as e:
            logger.error(f"데이터베이스 저장 중 오류 발생: {str(e)}")
            return None

    def _fetch_and_process_data(self, request, ocid=None):
        # 캐시된 데이터 확인
        cached_response = self.check_and_return_cached_data(
            request,
            self.model_class,
            ocid,
            self.related_name,
            self.serializer_class
        )
        if cached_response:
            return cached_response

        # API 호출
        try:
            data = self.get_api_data(
                self.api_url, {'ocid': ocid} if ocid else None)
            if data.get('date') is None:
                data['date'] = timezone.now()
            # 데이터베이스에 저장
            data = self.save_to_database(data, ocid)

            if self.serializer_class:
                serializer = self.serializer_class(
                    data, context={'request': request})
                return serializer.data

            return data
        except Exception as e:
            raise e

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'ocid',
                openapi.IN_PATH,
                description='캐릭터 식별자',
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'force_refresh',
                openapi.IN_QUERY,
                description='캐시 무시하고 새로운 데이터 조회',
                type=openapi.TYPE_BOOLEAN,
                default=False
            )
        ],
        responses={
            200: "성공",
            400: "잘못된 요청",
            404: "찾을 수 없음",
            500: "서버 에러"
        }
    )
    def get(self, request, ocid=None):
        try:
            result = self._fetch_and_process_data(request, ocid)
            # 캐시에서 반환된 경우 이미 Response 객체임
            if isinstance(result, Response):
                return result
            return Response(self.format_response_data(result))
        except Exception as e:
            return self.handle_exception(e)


class CharacterIdView(BaseCharacterView):
    model_class = CharacterId
    api_url = CHARACTER_ID_URL

    def _fetch_and_process_data(self, request):
        char_name = request.query_params.get('character_name')
        if not char_name:
            raise ValueError('캐릭터 이름이 필요합니다.')

        # 캐시된 데이터 확인
        cached_response = self.check_and_return_cached_data(
            request,
            self.model_class,
            None,
            None,
            None,
            {'character_name': char_name}
        )
        if cached_response:
            return cached_response

        # OCID 조회
        data = self.get_api_data(
            CHARACTER_ID_URL, {'character_name': char_name})
        if not data or 'ocid' not in data:
            return Response({'error': '캐릭터를 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)
        ocid = data.get('ocid')

        # 데이터베이스에 저장
        self.save_to_database(data, ocid)

        self.model_class = CharacterBasic
        self.api_url = CHARACTER_BASIC_URL
        # 캐릭터 기본 정보 조회
        basic_data = self.get_api_data(
            CHARACTER_BASIC_URL, {'ocid': ocid})
        if basic_data:
            self.save_to_database(basic_data, ocid)

        return data

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'character_name',
                openapi.IN_QUERY,
                description='캐릭터 이름',
                type=openapi.TYPE_STRING,
                required=True
            )
        ],
        responses={
            200: openapi.Response(
                description="성공",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'ocid': openapi.Schema(type=openapi.TYPE_STRING, description='캐릭터 식별자')
                    }
                )
            ),
            400: "캐릭터 이름이 필요합니다.",
            404: "캐릭터를 찾을 수 없습니다."
        }
    )
    def get(self, request):
        try:
            data = self._fetch_and_process_data(request)
            return Response(self.format_response_data(data))
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return self.handle_exception(e)


@swagger_auto_schema(tags=['캐릭터 기본 정보'])
class CharacterBasicView(BaseCharacterView):
    model_class = CharacterBasic
    api_url = CHARACTER_BASIC_URL
    schema_class = CharacterBasicSchema
    serializer_class = CharacterBasicSerializer


@swagger_auto_schema(tags=['캐릭터 인기도'])
class CharacterPopularityView(BaseCharacterView):
    model_class = CharacterPopularity
    api_url = CHARACTER_POPULARITY_URL
    related_name = 'popularity'
    schema_class = CharacterPopularitySchema
    serializer_class = CharacterPopularitySerializer


@swagger_auto_schema(tags=['캐릭터 스탯'])
class CharacterStatView(BaseCharacterView):
    model_class = CharacterStat
    api_url = CHARACTER_STAT_URL
    related_name = 'stats'
    schema_class = CharacterStatSchema
    serializer_class = CharacterStatSerializer


@swagger_auto_schema(tags=['캐릭터 어빌리티'])
class CharacterAbilityView(BaseCharacterView):
    model_class = CharacterAbility
    api_url = CHARACTER_ABILITY_URL
    related_name = 'abilities'
    schema_class = CharacterAbilitySchema
    serializer_class = CharacterAbilitySerializer


@swagger_auto_schema(tags=['캐릭터 장비'])
class CharacterItemEquipmentView(BaseCharacterView):
    model_class = CharacterItemEquipment
    api_url = CHARACTER_ITEM_EQUIPMENT_URL
    related_name = 'equipments'
    schema_class = CharacterItemEquipmentSchema
    serializer_class = CharacterItemEquipmentSerializer


@swagger_auto_schema(tags=['캐릭터 캐시 장비'])
class CharacterCashItemEquipmentView(BaseCharacterView):
    model_class = CharacterCashItemEquipment
    api_url = CHARACTER_CASHITEM_EQUIPMENT_URL
    related_name = 'cash_equipments'
    schema_class = CharacterCashItemEquipmentSchema
    serializer_class = CharacterCashItemEquipmentSerializer


@swagger_auto_schema(tags=['캐릭터 심볼'])
class CharacterSymbolView(BaseCharacterView):
    model_class = CharacterSymbolEquipment
    api_url = CHARACTER_SYMBOL_URL
    related_name = 'symbols'
    schema_class = CharacterSymbolEquipmentSchema
    serializer_class = CharacterSymbolEquipmentSerializer


@swagger_auto_schema(tags=['캐릭터 링크 스킬'])
class CharacterLinkSkillView(BaseCharacterView):
    model_class = CharacterLinkSkill
    api_url = CHARACTER_LINK_SKILL_URL
    related_name = 'link_skills'
    schema_class = CharacterLinkSkillSchema
    serializer_class = CharacterLinkSkillSerializer


@swagger_auto_schema(tags=['캐릭터 스킬'])
class CharacterSkillView(BaseCharacterView):
    model_class = CharacterSkill
    api_url = CHARACTER_SKILL_URL
    related_name = 'skills'
    schema_class = CharacterSkillSchema
    serializer_class = CharacterSkillSerializer

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'ocid',
                openapi.IN_PATH,
                description='캐릭터 식별자',
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'character_skill_grade',
                openapi.IN_QUERY,
                description='스킬 전직 차수',
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'force_refresh',
                openapi.IN_QUERY,
                description='캐시 무시하고 새로운 데이터 조회',
                type=openapi.TYPE_BOOLEAN,
                default=False
            )
        ],
        responses={
            200: "성공",
            400: "잘못된 요청",
            404: "찾을 수 없음",
            500: "서버 에러"
        }
    )
    def get(self, request, ocid=None):
        character_skill_grade = request.query_params.get(
            'character_skill_grade')
        if not character_skill_grade:
            return Response({'error': '스킬 전직 차수가 필요합니다.'}, status=status.HTTP_400_BAD_REQUEST)

        # 캐시된 데이터 확인
        cached_response = self.check_and_return_cached_data(
            request,
            self.model_class,
            ocid,
            self.related_name,
            self.serializer_class,
            {'character_skill_grade': character_skill_grade}  # 추가 필터 전달
        )
        if cached_response:
            return cached_response

        # API 호출
        try:
            data = self.get_api_data(
                self.api_url,
                {
                    'ocid': ocid,
                    'character_skill_grade': character_skill_grade
                } if ocid else None
            )
            if data.get('date') is None:
                data['date'] = timezone.now()
            # 데이터베이스에 저장
            data = self.save_to_database(data, ocid)

            if self.serializer_class:
                serializer = self.serializer_class(
                    data, context={'request': request})
                return Response(self.format_response_data(serializer.data))

            return Response(self.format_response_data(data))
        except Exception as e:
            return self.handle_exception(e)


@swagger_auto_schema(tags=['캐릭터 HEXA 매트릭스'])
class CharacterHexaMatrixView(BaseCharacterView):
    model_class = CharacterHexaMatrix
    api_url = CHARACTER_HEXAMATRIX_URL
    related_name = 'hexa_matrix'
    schema_class = CharacterHexaMatrixSchema
    serializer_class = CharacterHexaMatrixSerializer


@swagger_auto_schema(tags=['캐릭터 HEXA 스탯'])
class CharacterHexaMatrixStatView(BaseCharacterView):
    model_class = CharacterHexaMatrixStat
    api_url = CHARACTER_HEXAMATRIX_STAT_URL
    related_name = 'hexa_stats'
    schema_class = CharacterHexaMatrixStatSchema
    serializer_class = CharacterHexaMatrixStatSerializer


@swagger_auto_schema(tags=['캐릭터 V매트릭스'])
class CharacterVMatrixView(BaseCharacterView):
    model_class = CharacterVMatrix
    api_url = CHARACTER_VMATRIX_URL
    related_name = 'v_matrix'
    schema_class = CharacterVMatrixSchema
    serializer_class = CharacterVMatrixSerializer


@swagger_auto_schema(tags=['캐릭터 무릉도장'])
class CharacterDojangView(BaseCharacterView):
    model_class = CharacterDojang
    api_url = CHARACTER_DOJANG_URL
    related_name = 'dojang'
    schema_class = CharacterDojangSchema
    serializer_class = CharacterDojangSerializer


@swagger_auto_schema(tags=['캐릭터 세트효과'])
class CharacterSetEffectView(BaseCharacterView):
    model_class = CharacterSetEffect
    api_url = CHARACTER_SET_EFFECT_URL
    related_name = 'set_effects'
    schema_class = CharacterSetEffectSchema
    serializer_class = CharacterSetEffectSerializer


@swagger_auto_schema(tags=['캐릭터 성형/헤어'])
class CharacterBeautyEquipmentView(BaseCharacterView):
    model_class = CharacterBeautyEquipment
    api_url = CHARACTER_BEAUTY_EQUIPMENT_URL
    related_name = 'beauty_equipments'
    schema_class = CharacterBeautyEquipmentSchema
    serializer_class = CharacterBeautyEquipmentSerializer


@swagger_auto_schema(tags=['캐릭터 안드로이드'])
class CharacterAndroidEquipmentView(BaseCharacterView):
    model_class = AndroidEquipment
    api_url = CHARACTER_ANDROID_EQUIPMENT_URL
    related_name = 'android_equipments'
    schema_class = AndroidEquipmentSchema
    serializer_class = AndroidEquipmentSerializer


@swagger_auto_schema(tags=['캐릭터 펫'])
class CharacterPetEquipmentView(BaseCharacterView):
    model_class = CharacterPetEquipment
    api_url = CHARACTER_PET_EQUIPMENT_URL
    related_name = 'pet_equipments'
    schema_class = CharacterPetEquipmentSchema
    serializer_class = CharacterPetEquipmentSerializer


@swagger_auto_schema(tags=['캐릭터 성향'])
class CharacterPropensityView(BaseCharacterView):
    model_class = CharacterPropensity
    api_url = CHARACTER_PROPENSITY_URL
    related_name = 'propensities'
    schema_class = CharacterPropensitySchema
    serializer_class = CharacterPropensitySerializer


@swagger_auto_schema(tags=['캐릭터 하이퍼스탯'])
class CharacterHyperStatView(BaseCharacterView):
    model_class = CharacterHyperStat
    api_url = CHARACTER_HYPER_STAT_URL
    related_name = 'hyper_stats'
    schema_class = CharacterHyperStatSchema
    serializer_class = CharacterHyperStatSerializer


@swagger_auto_schema(tags=['캐릭터 전체 정보'])
class CharacterAllDataView(BaseCharacterView):
    """캐릭터의 모든 정보를 조회하는 뷰"""
    schema_class = CharacterAllDataSchema
    serializer_class = CharacterAllDataSerializer

    def _trigger_auto_crawl(self, ocid: str, character_basic):
        """
        API 조회 시 자동으로 크롤링 태스크 시작 (인벤토리/창고/메소)

        - 최근 1시간 이내 크롤링 기록이 없으면 자동 시작
        - Celery 태스크로 비동기 실행 (API 응답 지연 없음)
        """
        from datetime import timedelta
        from accounts.models import CrawlTask

        try:
            one_hour_ago = timezone.now() - timedelta(hours=1)

            # 최근 1시간 이내 성공한 크롤링이 있는지 확인
            recent_crawl = CrawlTask.objects.filter(
                character_basic=character_basic,
                status='SUCCESS',
                updated_at__gte=one_hour_ago
            ).exists()

            if recent_crawl:
                logger.info(f"최근 크롤링 기록 있음, 자동 크롤링 스킵 - OCID: {ocid}")
                return

            # 현재 진행 중인 크롤링이 있는지 확인
            pending_crawl = CrawlTask.objects.filter(
                character_basic=character_basic,
                status__in=['PENDING', 'STARTED']
            ).exists()

            if pending_crawl:
                logger.info(f"진행 중인 크롤링 있음, 자동 크롤링 스킵 - OCID: {ocid}")
                return

            # Celery 태스크 시작
            from accounts.tasks import crawl_character_data

            crawl_types = ['inventory', 'storage', 'meso']
            task = crawl_character_data.delay(ocid, crawl_types)

            # CrawlTask 레코드 생성
            CrawlTask.objects.create(
                task_id=task.id,
                character_basic=character_basic,
                task_type=','.join(crawl_types),
                status='PENDING',
                progress=0
            )

            logger.info(f"자동 크롤링 시작됨 - OCID: {ocid}, Task ID: {task.id}")

        except Exception as e:
            # 크롤링 실패해도 API 응답에는 영향 없음
            logger.warning(f"자동 크롤링 시작 실패 - OCID: {ocid}, 오류: {str(e)}")

    def validate_and_save_data(self, endpoint_name: str, data: dict, ocid: str, view_class):
        """각 엔드포인트의 데이터를 검증하고 저장"""
        try:
            view_instance = view_class()
            # 데이터 검증
            validated_data = view_instance.validate_data(data)
            # 데이터베이스 저장
            view_instance.save_to_database(validated_data, ocid)
            return validated_data
        except Exception as e:
            logger.error(f"{endpoint_name} 데이터 처리 중 오류 발생: {str(e)}")
            return None

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'character_name',
                openapi.IN_QUERY,
                description='캐릭터 이름',
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'force_refresh',
                openapi.IN_QUERY,
                description='캐시 무시하고 새로운 데이터 조회',
                type=openapi.TYPE_BOOLEAN,
                default=False
            )
        ],
        responses={
            200: "성공",
            400: "잘못된 요청",
            404: "찾을 수 없음",
            500: "서버 에러"
        }
    )
    def get(self, request):
        start_time = time.time()  # 시작 시간 기록
        ocid = None  # ocid 변수 초기화 (에러 로깅 시 사용 위함)
        character_name = request.query_params.get(
            'character_name')  # character_name 먼저 가져오기

        try:
            # character_name = request.query_params.get('character_name') # 위치 이동
            if not character_name:
                # 이름 없으면 바로 리턴하므로 여기서 시간 로깅
                total_duration = time.time() - start_time
                logger.warning(f"캐릭터 이름 누락 - 총 소요시간: {total_duration:.2f}초")
                return Response({'error': '캐릭터 이름이 필요합니다.'}, status=status.HTTP_400_BAD_REQUEST)

            # CharacterIdView를 사용하여 OCID 조회 및 기본 정보 저장 시도
            ocid_data = CharacterIdView()._fetch_and_process_data(request)
            ocid = ocid_data.get('ocid')  # ocid 할당

            if not ocid:
                total_duration = time.time() - start_time
                # ocid_data가 오류 응답일 수 있으므로 확인
                if isinstance(ocid_data, Response):
                    logger.error(
                        f"OCID 조회 실패 (응답 반환) - 캐릭터명: {character_name}, 총 소요시간: {total_duration:.2f}초")
                    return ocid_data  # 이미 Response 객체이므로 그대로 반환
                logger.error(
                    f"OCID 조회 실패 - 캐릭터명: {character_name}, 총 소요시간: {total_duration:.2f}초")
                return Response({'error': 'OCID를 조회할 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)

            # --- 캐시 확인 로직 수정 ---
            force_refresh = request.query_params.get(
                'force_refresh', 'false').lower() == 'true'
            if not force_refresh:
                cache_key = f"character_data:{ocid}:all_data"
                cached_data = redis_client.get(cache_key)
                if cached_data:
                    try:
                        response_data = json.loads(cached_data)
                        total_duration = time.time() - start_time  # 캐시 반환 전 시간 측정
                        logger.info(
                            f"캐시된 전체 데이터 반환 - OCID: {ocid}, 총 소요시간: {total_duration:.2f}초")
                        return Response({'data': response_data})  # 캐시 데이터 반환
                    except json.JSONDecodeError:
                        logger.warning(
                            f"캐시된 데이터 JSON 파싱 오류 - Key: {cache_key}")
                        # 파싱 오류 시 캐시 무시하고 새로 조회 (아래 로직으로 진행)
            # --- 캐시 확인 로직 끝 ---

            # API 엔드포인트와 뷰 클래스 매핑 (변경 없음)
            api_endpoints = {
                CHARACTER_BASIC_URL: ('basic', CharacterBasicView),
                CHARACTER_POPULARITY_URL: ('popularity', CharacterPopularityView),
                CHARACTER_STAT_URL: ('stat', CharacterStatView),
                CHARACTER_ABILITY_URL: ('ability', CharacterAbilityView),
                CHARACTER_ITEM_EQUIPMENT_URL: ('item_equipment', CharacterItemEquipmentView),
                CHARACTER_CASHITEM_EQUIPMENT_URL: ('cashitem_equipment', CharacterCashItemEquipmentView),
                CHARACTER_SYMBOL_URL: ('symbol', CharacterSymbolView),
                CHARACTER_LINK_SKILL_URL: ('link_skill', CharacterLinkSkillView),
                CHARACTER_SKILL_URL: ('skill', CharacterSkillView),
                CHARACTER_HEXAMATRIX_URL: ('hexamatrix', CharacterHexaMatrixView),
                CHARACTER_HEXAMATRIX_STAT_URL: ('hexamatrix_stat', CharacterHexaMatrixStatView),
                CHARACTER_VMATRIX_URL: ('vmatrix', CharacterVMatrixView),
                CHARACTER_DOJANG_URL: ('dojang', CharacterDojangView),
                CHARACTER_SET_EFFECT_URL: ('set_effect', CharacterSetEffectView),
                CHARACTER_BEAUTY_EQUIPMENT_URL: ('beauty_equipment', CharacterBeautyEquipmentView),
                CHARACTER_ANDROID_EQUIPMENT_URL: ('android_equipment', CharacterAndroidEquipmentView),
                CHARACTER_PET_EQUIPMENT_URL: ('pet_equipment', CharacterPetEquipmentView),
                CHARACTER_PROPENSITY_URL: ('propensity', CharacterPropensityView),
                CHARACTER_HYPER_STAT_URL: ('hyper_stat', CharacterHyperStatView),
            }

            # 비동기 호출 실행
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                results = loop.run_until_complete(
                    self.fetch_all_data(ocid, api_endpoints, request))
            finally:
                loop.close()

            # --- 데이터 조회 및 직렬화/캐싱 로직 수정 ---
            try:
                character = CharacterBasic.objects.get(ocid=ocid)
            except CharacterBasic.DoesNotExist:
                total_duration = time.time() - start_time  # 실패 응답 전 시간 측정
                logger.error(
                    f"모든 데이터 조회 후 CharacterBasic 조회 실패 - OCID: {ocid}, 총 소요시간: {total_duration:.2f}초")
                return Response({'error': '캐릭터 정보를 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)

            serializer = self.serializer_class(
                character, context={'request': request})
            serialized_data = serializer.data

            cache_key = f"character_data:{ocid}:all_data"
            cache_ttl = 3600
            redis_client.setex(cache_key, cache_ttl,
                               json.dumps(serialized_data))
            logger.info(f"전체 데이터 캐싱 완료 - Key: {cache_key}")

            # --- 자동 크롤링 시작 (인벤토리/창고/메소) ---
            self._trigger_auto_crawl(ocid, character)
            # --- 자동 크롤링 끝 ---

            total_duration = time.time() - start_time  # 성공 응답 전 시간 측정
            logger.info(
                f"전체 데이터 조회 성공 응답 - OCID: {ocid}, 총 소요시간: {total_duration:.2f}초")
            return Response(self.format_response_data(serialized_data))
            # --- 데이터 조회 및 직렬화/캐싱 로직 끝 ---

        except Exception as e:
            total_duration = time.time() - start_time  # 예외 응답 전 시간 측정
            logger.error(
                f"전체 데이터 조회 중 오류 발생 - 캐릭터명: {character_name}, OCID: {ocid}, 총 소요시간: {total_duration:.2f}초, 오류: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return Response(
                {'error': f'데이터 조회 중 오류가 발생했습니다: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    async def fetch_all_data(self, ocid, api_endpoints, request):
        """비동기로 모든 API 데이터 조회"""
        from asgiref.sync import sync_to_async
        import time

        total_start = time.time()
        logger.info(f"전체 데이터 조회 시작 - OCID: {ocid}")

        # # force_refresh 파라미터 확인
        # force_refresh = request.query_params.get(
        #     'force_refresh', 'false').lower() == 'true'

        async with aiohttp.ClientSession() as session:
            # CharacterSkillView 처럼 파라미터가 필요한 경우 처리 필요
            tasks = []
            semaphore = asyncio.Semaphore(20)  # 동시 요청 제한

            # @rate_limited 데코레이터는 async 함수에 직접 적용하기 어려울 수 있음
            # 필요하다면 asyncio-limiter 같은 라이브러리 사용 고려
            @rate_limited(500)
            async def fetch_with_semaphore(url, params):
                async with semaphore:
                    try:
                        request_start = time.time()
                        headers = {'x-nxopen-api-key': APIKEY}

                        # --- 개별 데이터 캐시 확인 (선택 사항) ---
                        # 만약 force_refresh가 아니고, 개별 데이터 캐시도 확인하고 싶다면 여기서 확인
                        # view_instance = api_endpoints[url][1]()
                        # cached_item = view_instance.check_and_return_cached_data(...)
                        # if cached_item and not force_refresh:
                        #     logger.info(f"개별 캐시 사용 ({url})")
                        #     return url, cached_item # 또는 DB 저장을 스킵할 플래그 반환
                        # --- 개별 캐시 확인 끝 ---

                        api_start = time.time()
                        async with session.get(url, params=params, headers=headers) as response:
                            api_time = time.time() - api_start
                            if response.status == 200:
                                data = await response.json()
                                logger.info(
                                    f"API 요청 성공 ({url}) - 상태: {response.status}, 소요시간: {api_time:.2f}초")

                                process_start = time.time()
                                endpoint_name, view_class = api_endpoints[url]

                                # --- 날짜 처리 로직 수정 ---
                                raw_date = data.get('date')
                                if raw_date:
                                    try:
                                        if isinstance(raw_date, datetime.datetime):
                                            # 이미 datetime 객체인 경우 timezone 확인
                                            if timezone.is_naive(raw_date):
                                                logger.warning(
                                                    f"API 응답에 naive datetime 포함 ({url}): {raw_date}. UTC로 가정.")
                                                # Django 설정의 TIME_ZONE을 사용하거나 UTC로 명시적 설정
                                                # data['date'] = timezone.make_aware(raw_date, timezone.get_current_timezone())
                                                data['date'] = timezone.make_aware(
                                                    raw_date, timezone.utc)
                                            else:
                                                # 이미 aware datetime이면 그대로 사용 (UTC로 변환하는 것을 고려할 수 있음)
                                                data['date'] = raw_date.astimezone(
                                                    timezone.utc)
                                        elif isinstance(raw_date, str):
                                            # 문자열인 경우 파싱 시도
                                            # ISO 8601 형식 (YYYY-MM-DDTHH:MM:SS+HH:MM 또는 YYYY-MM-DDTHH:MM:SSZ)
                                            date_str = raw_date.replace(
                                                'Z', '+00:00')
                                            dt_obj = datetime.datetime.fromisoformat(
                                                date_str)
                                            # Aware datetime 객체를 UTC로 변환하여 저장 일관성 확보
                                            data['date'] = dt_obj.astimezone(
                                                timezone.utc)
                                        else:
                                            # 예상치 못한 타입
                                            logger.warning(
                                                f"알 수 없는 날짜 타입 ({url}): {type(raw_date)}. 현재 시간(UTC) 사용.")
                                            # UTC 반환
                                            data['date'] = timezone.now()

                                    except (ValueError, TypeError) as dt_error:
                                        logger.warning(
                                            f"날짜 문자열 파싱 실패 ({url}): '{raw_date}'. 오류: {dt_error}. 현재 시간(UTC) 사용.")
                                        data['date'] = timezone.now()  # UTC 반환
                                else:
                                    # date 필드가 없거나 None인 경우 (예: ocid 응답)
                                    logger.info(
                                        f"API 응답에 'date' 필드 없음 ({url}). 현재 시간(UTC) 사용.")
                                    data['date'] = timezone.now()  # UTC 반환
                                # --- 날짜 처리 로직 끝 ---

                                db_start = time.time()
                                # sync_to_async로 DB 저장 호출
                                # save_to_database는 이제 timezone-aware UTC datetime 객체를 받음
                                view_instance = view_class()
                                await sync_to_async(view_instance.save_to_database)(data, ocid)
                                db_time = time.time() - db_start
                                logger.info(
                                    f"DB 저장 완료 ({endpoint_name}) - 소요시간: {db_time:.2f}초")

                                process_time = time.time() - process_start - db_time
                                logger.info(
                                    f"데이터 처리 완료 ({endpoint_name}) - 소요시간: {process_time:.2f}초")

                                total_request_time = time.time() - request_start
                                logger.info(
                                    f"요청 전체 처리 완료 ({url}) - 총 소요시간: {total_request_time:.2f}초")
                                return url, data  # 성공 시 데이터 반환

                            elif response.status == 400 and "INVALID_IDENTIFIER" in await response.text():
                                logger.warning(
                                    f"API 요청 실패 ({url}) - 잘못된 식별자(OCID): {ocid}, 상태: {response.status}, 소요시간: {api_time:.2f}초")
                                # 특정 에러 구분
                                return url, {'error': 'INVALID_IDENTIFIER'}
                            else:
                                error_text = await response.text()
                                logger.error(
                                    f"API 요청 실패 ({url}) - 상태: {response.status}, 내용: {error_text[:200]}, 소요시간: {api_time:.2f}초")
                                # 실패 시 에러 정보 포함
                                return url, {'error': f"API Error {response.status}"}

                    except aiohttp.ClientError as e:
                        logger.error(f"AIOHTTP ClientError ({url}): {str(e)}")
                        return url, {'error': f'Client Connection Error: {str(e)}'}
                    except asyncio.TimeoutError:
                        logger.error(f"API 요청 시간 초과 ({url})")
                        return url, {'error': 'Request Timeout'}
                    except Exception as e:
                        logger.error(f"API 호출/처리 중 예외 발생 ({url}): {str(e)}")
                        import traceback
                        logger.error(traceback.format_exc())
                        return url, {'error': f'Unexpected Error: {str(e)}'}

            # 각 엔드포인트에 맞는 파라미터 설정하여 tasks 생성
            for url, (endpoint_name, view_class) in api_endpoints.items():
                params = {'ocid': ocid}
                # CharacterSkillView 처럼 추가 파라미터가 필요한 경우 처리
                if view_class == CharacterSkillView:
                    # 가져올 스킬 차수 목록 (0차, 5차, 6차)
                    skill_grades_to_fetch = ['0', '5', '6']
                    for grade in skill_grades_to_fetch:
                        # 각 차수별 파라미터 설정
                        skill_params = {'ocid': ocid,
                                        'character_skill_grade': grade}
                        # 각 차수별로 비동기 작업 추가
                        tasks.append(fetch_with_semaphore(url, skill_params))
                        logger.info(
                            f"CharacterSkillView 작업 추가 - Grade: {grade}, URL: {url}")
                    # CharacterSkillView에 대한 기본 task 추가 방지
                    continue  # 다음 api_endpoint로 넘어감
                    # --- 기존 로직 주석 처리 또는 삭제 ---
                    # logger.warning(
                    #     f"CharacterSkillView는 전체 조회 시 파라미터 필요. 현재는 제외됨. URL: {url}")
                    # continue  # CharacterSkillView는 일단 제외

                # 다른 뷰들은 기존 로직대로 추가
                tasks.append(fetch_with_semaphore(url, params))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            total_time = time.time() - total_start
            successful_fetches = sum(1 for r in results if isinstance(
                r, tuple) and r[1] and not r[1].get('error'))
            failed_fetches = len(results) - successful_fetches
            logger.info(
                f"전체 데이터 fetch_all_data 완료 - 총 소요시간: {total_time:.2f}초, 성공: {successful_fetches}, 실패: {failed_fetches}")

            # 예외 처리 또는 실패 로깅
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"비동기 작업 중 예외 발생: {result}")
                elif isinstance(result, tuple) and result[1] and result[1].get('error'):
                    logger.warning(
                        f"데이터 조회 실패 - URL: {result[0]}, 오류: {result[1]['error']}")

            return results  # 결과 반환 (성공/실패 정보 포함)


class RedisHealthCheckView(APIView):
    def get(self, request):
        try:
            # Redis 연결 테스트
            redis_client.ping()
            return Response({
                "status": "success",
                "message": "Redis 서버에 정상적으로 연결되었습니다."
            })
        except Exception as e:
            return Response({
                "status": "error",
                "message": f"Redis 서버 연결 실패: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
