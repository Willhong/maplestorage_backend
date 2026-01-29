import datetime
import json
import requests
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.utils import timezone
from django.db.models import F
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

        Returns:
            dict: {'task_id': str, 'status': str} 또는 None
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
                return None

            # 현재 진행 중인 크롤링이 있는지 확인
            pending_crawl = CrawlTask.objects.filter(
                character_basic=character_basic,
                status__in=['PENDING', 'STARTED']
            ).order_by('-created_at').first()

            if pending_crawl:
                logger.info(f"진행 중인 크롤링 있음, task_id 반환 - OCID: {ocid}")
                return {'task_id': pending_crawl.task_id, 'status': pending_crawl.status}

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
            return {'task_id': task.id, 'status': 'PENDING'}

        except Exception as e:
            # 크롤링 실패해도 API 응답에는 영향 없음
            logger.warning(f"자동 크롤링 시작 실패 - OCID: {ocid}, 오류: {str(e)}")
            return None

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
            crawl_task = self._trigger_auto_crawl(ocid, character)
            # --- 자동 크롤링 끝 ---

            total_duration = time.time() - start_time  # 성공 응답 전 시간 측정
            logger.info(
                f"전체 데이터 조회 성공 응답 - OCID: {ocid}, 총 소요시간: {total_duration:.2f}초")

            # 응답 데이터 구성 (크롤링 task 정보 포함)
            response_data = self.format_response_data(serialized_data)
            if crawl_task:
                response_data['crawl_task'] = crawl_task
            return Response(response_data)
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


# =============================================================================
# 캐릭터 목록 뷰 (Story 3.1)
# =============================================================================

class CharacterListView(APIView):
    """
    캐릭터 목록 조회 뷰 (Story 3.1)

    GET /api/characters/ - 인증된 사용자의 캐릭터 목록 반환

    AC-3.1.1: 모든 캐릭터가 카드 형태로 표시
    AC-3.1.4: 캐릭터는 최근 업데이트 순으로 정렬
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="인증된 사용자의 캐릭터 목록 조회",
        responses={
            200: openapi.Response(
                description="성공",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'count': openapi.Schema(type=openapi.TYPE_INTEGER, description='캐릭터 수'),
                        'results': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'ocid': openapi.Schema(type=openapi.TYPE_STRING),
                                    'character_name': openapi.Schema(type=openapi.TYPE_STRING),
                                    'world_name': openapi.Schema(type=openapi.TYPE_STRING),
                                    'character_class': openapi.Schema(type=openapi.TYPE_STRING),
                                    'character_level': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'character_image': openapi.Schema(type=openapi.TYPE_STRING),
                                    'last_crawled_at': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                    'inventory_count': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'has_expiring_items': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                }
                            )
                        )
                    }
                )
            ),
            401: "인증되지 않은 사용자"
        },
        tags=['캐릭터 목록']
    )
    def get(self, request):
        """
        인증된 사용자의 캐릭터 목록을 반환합니다.

        AC-3.1.4: 최근 업데이트 순으로 정렬 (created_at 기준 내림차순)
        """
        from accounts.models import Character
        from .serializers import CharacterListSerializer

        # 본인 캐릭터만 조회 (AC-ownership)
        characters = Character.objects.filter(
            user=request.user
        ).order_by('-created_at')  # 최근 등록순 정렬 (AC-3.1.4)

        serializer = CharacterListSerializer(characters, many=True)

        return Response({
            'count': characters.count(),
            'results': serializer.data
        })


# =============================================================================
# 인벤토리 목록 뷰 (Story 3.4)
# =============================================================================

class InventoryListView(APIView):
    """
    인벤토리 아이템 목록 조회 뷰 (Story 3.4, 3.5)

    GET /api/characters/{ocid}/inventory/ - 특정 캐릭터의 인벤토리 아이템 반환
    GET /api/characters/{ocid}/inventory/?category=equipment - 카테고리 필터링 (Story 3.5)

    AC-3.4.1: 모든 인벤토리 아이템이 그리드 형태로 표시 (Frontend 구현)
    AC-3.4.2: 각 아이템은 아이콘, 이름, 수량, 강화 수치 포함
    AC-3.4.4: 기간제 아이템 days_until_expiry 필드 포함
    AC-3.5.1: 카테고리 필터 선택 시 해당 카테고리만 표시
    AC-3.5.2: 카테고리 옵션: all, equipment, consumable, etc, expirable
    """
    permission_classes = [IsAuthenticated]

    # 카테고리 필터 매핑 (Story 3.5)
    # API 값 -> DB item_type 필드 값
    CATEGORY_MAPPING = {
        'equipment': 'equips',
        'consumable': 'consumables',
        'etc': 'miscs',
        # 'expirable'은 item_type이 아닌 expiry_date 필드로 필터링
    }

    # 허용된 정렬 필드 (Story 3.9: AC-3.9.1)
    VALID_SORT_FIELDS = ['slot_position', 'item_name', 'quantity', 'crawled_at', 'expiry_date']

    @swagger_auto_schema(
        operation_description="인증된 사용자의 캐릭터 인벤토리 목록 조회 (카테고리 필터링, 정렬 지원)",
        manual_parameters=[
            openapi.Parameter(
                'ocid',
                openapi.IN_PATH,
                description="캐릭터 OCID",
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'category',
                openapi.IN_QUERY,
                description="카테고리 필터 (all, equipment, consumable, etc, expirable)",
                type=openapi.TYPE_STRING,
                required=False,
                default='all'
            ),
            openapi.Parameter(
                'sort',
                openapi.IN_QUERY,
                description="정렬 기준 (slot_position, item_name, quantity, crawled_at, expiry_date)",
                type=openapi.TYPE_STRING,
                required=False,
                default='slot_position'
            ),
            openapi.Parameter(
                'order',
                openapi.IN_QUERY,
                description="정렬 순서 (asc, desc)",
                type=openapi.TYPE_STRING,
                required=False,
                default='asc'
            )
        ],
        responses={
            200: openapi.Response(
                description="성공",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'character_name': openapi.Schema(type=openapi.TYPE_STRING, description='캐릭터 이름'),
                        'items': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'item_name': openapi.Schema(type=openapi.TYPE_STRING),
                                    'item_icon': openapi.Schema(type=openapi.TYPE_STRING),
                                    'quantity': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'item_type': openapi.Schema(type=openapi.TYPE_STRING),
                                    'item_options': openapi.Schema(type=openapi.TYPE_OBJECT, nullable=True),
                                    'slot_position': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'expiry_date': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                    'crawled_at': openapi.Schema(type=openapi.TYPE_STRING),
                                    'days_until_expiry': openapi.Schema(type=openapi.TYPE_INTEGER, nullable=True),
                                    'is_expirable': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                }
                            )
                        ),
                        'total_count': openapi.Schema(type=openapi.TYPE_INTEGER, description='총 아이템 수'),
                        'last_crawled_at': openapi.Schema(type=openapi.TYPE_STRING, nullable=True, description='마지막 크롤링 시간'),
                        'category': openapi.Schema(type=openapi.TYPE_STRING, description='적용된 카테고리'),
                        'sort': openapi.Schema(type=openapi.TYPE_STRING, description='적용된 정렬 기준'),
                        'order': openapi.Schema(type=openapi.TYPE_STRING, description='적용된 정렬 순서')
                    }
                )
            ),
            401: "인증되지 않은 사용자",
            404: "캐릭터를 찾을 수 없음"
        },
        tags=['인벤토리']
    )
    def get(self, request, ocid):
        """
        특정 캐릭터의 인벤토리 아이템 목록을 반환합니다.

        AC-3.4.1: 모든 인벤토리 아이템 반환
        AC-3.4.2: 아이콘, 이름, 수량, 강화 수치(item_options) 포함
        AC-3.4.4: 기간제 아이템 days_until_expiry 포함
        AC-3.5.1: 카테고리 필터 선택 시 해당 카테고리만 표시
        AC-3.5.2: 카테고리 옵션: all, equipment, consumable, etc, expirable
        AC-3.9.1: 정렬 옵션: slot_position, item_name, quantity, crawled_at, expiry_date
        AC-3.9.6: 만료일 정렬 시 null 값은 마지막에 표시
        """
        from accounts.models import Character
        from .models import CharacterBasic, Inventory
        from .serializers import InventoryItemSerializer

        # 1. 소유권 검증: 사용자가 이 캐릭터를 소유하는지 확인 (AC-ownership)
        # 정보 노출 방지를 위해 403 대신 404 반환
        try:
            character = Character.objects.get(ocid=ocid, user=request.user)
        except Character.DoesNotExist:
            return Response(
                {"error": "캐릭터를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )

        # 2. CharacterBasic 조회
        try:
            character_basic = CharacterBasic.objects.get(ocid=ocid)
        except CharacterBasic.DoesNotExist:
            return Response(
                {"error": "캐릭터 기본 정보를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )

        # 3. 인벤토리 아이템 조회 (AC-3.4.1: 모든 아이템)
        inventory_items = Inventory.objects.filter(
            character_basic=character_basic
        )

        # 4. 카테고리 필터 적용 (Story 3.5: AC-3.5.1, AC-3.5.2)
        category = request.query_params.get('category', 'all')

        if category == 'expirable':
            # 기간제 아이템: expiry_date가 있는 아이템만
            inventory_items = inventory_items.filter(expiry_date__isnull=False)
        elif category in self.CATEGORY_MAPPING:
            # item_type 기반 필터링 (equipment, consumable, etc)
            db_item_type = self.CATEGORY_MAPPING[category]
            inventory_items = inventory_items.filter(item_type=db_item_type)
        # 'all' 또는 잘못된 카테고리는 필터 없이 전체 반환 (AC-3.5.2 기본값)

        # 5. 정렬 적용 (Story 3.9: AC-3.9.1, AC-3.9.4, AC-3.9.6)
        sort_field = request.query_params.get('sort', 'slot_position')
        order = request.query_params.get('order', 'asc')

        # 허용된 정렬 필드 검증 (허용되지 않은 필드는 기본값으로)
        if sort_field not in self.VALID_SORT_FIELDS:
            sort_field = 'slot_position'

        # 정렬 순서 검증
        if order not in ['asc', 'desc']:
            order = 'asc'

        # AC-3.9.6: 만료일 정렬 시 null 값은 마지막에 표시 (NULLS LAST)
        if sort_field == 'expiry_date':
            if order == 'asc':
                inventory_items = inventory_items.order_by(F('expiry_date').asc(nulls_last=True))
            else:
                inventory_items = inventory_items.order_by(F('expiry_date').desc(nulls_last=True))
        else:
            # 일반 정렬
            if order == 'desc':
                inventory_items = inventory_items.order_by(f'-{sort_field}')
            else:
                inventory_items = inventory_items.order_by(sort_field)

        # 6. Serializer로 직렬화 (AC-3.4.2, AC-3.4.4)
        serializer = InventoryItemSerializer(inventory_items, many=True)

        # 7. 마지막 크롤링 시간 계산
        last_crawled_at = None
        if inventory_items.exists():
            latest_item = inventory_items.order_by('-crawled_at').first()
            if latest_item:
                last_crawled_at = latest_item.crawled_at.isoformat()

        return Response({
            'character_name': character_basic.character_name,
            'items': serializer.data,
            'total_count': inventory_items.count(),
            'last_crawled_at': last_crawled_at,
            'category': category,  # 현재 적용된 카테고리 반환 (Story 3.5)
            'sort': sort_field,    # 현재 적용된 정렬 기준 반환 (Story 3.9: AC-3.9.5)
            'order': order         # 현재 적용된 정렬 순서 반환 (Story 3.9: AC-3.9.4)
        })


class StorageListView(APIView):
    """
    창고 아이템 목록 조회 뷰 (Story 3.6, 3.9)

    GET /api/characters/{ocid}/storage/ - 사용자 계정의 창고 아이템 반환
    GET /api/characters/{ocid}/storage/?category=equipment - 카테고리 필터링
    GET /api/characters/{ocid}/storage/?sort=item_name&order=asc - 정렬 (Story 3.9)

    중요: 창고는 계정 내 모든 캐릭터가 공유합니다.
    어떤 캐릭터 ocid로 조회해도 동일한 창고 아이템 목록이 반환됩니다.

    AC-3.6.1: 창고 탭 선택 시 창고 아이템 그리드 표시
    AC-3.6.2: 계정 내 모든 캐릭터가 동일한 창고 공유
    AC-3.6.3: 아이콘, 이름, 수량, 강화 수치 포함
    AC-3.6.4: 빈 창고 시 빈 배열 반환
    AC-3.6.5: 로딩 처리 (Frontend)
    AC-3.6.6: 에러 처리 (Frontend)
    AC-3.9.1: 정렬 옵션: slot_position, item_name, quantity, crawled_at, expiry_date
    AC-3.9.6: 만료일 정렬 시 null 값은 마지막에 표시
    """
    permission_classes = [IsAuthenticated]

    # 허용된 정렬 필드 (Story 3.9: AC-3.9.1)
    VALID_SORT_FIELDS = ['slot_position', 'item_name', 'quantity', 'crawled_at', 'expiry_date']

    @swagger_auto_schema(
        operation_description="인증된 사용자의 창고 아이템 목록 조회 (계정 공유, 카테고리 필터링, 정렬 지원)",
        manual_parameters=[
            openapi.Parameter(
                'ocid',
                openapi.IN_PATH,
                description="캐릭터 OCID (소유권 검증용, 창고는 계정 공유)",
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'category',
                openapi.IN_QUERY,
                description="카테고리 필터 (all, equipment, consumable, etc, expirable)",
                type=openapi.TYPE_STRING,
                required=False,
                default='all'
            ),
            openapi.Parameter(
                'sort',
                openapi.IN_QUERY,
                description="정렬 기준 (slot_position, item_name, quantity, crawled_at, expiry_date)",
                type=openapi.TYPE_STRING,
                required=False,
                default='slot_position'
            ),
            openapi.Parameter(
                'order',
                openapi.IN_QUERY,
                description="정렬 순서 (asc, desc)",
                type=openapi.TYPE_STRING,
                required=False,
                default='asc'
            )
        ],
        responses={
            200: openapi.Response(
                description="성공",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'items': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'storage_type': openapi.Schema(type=openapi.TYPE_STRING),
                                    'item_name': openapi.Schema(type=openapi.TYPE_STRING),
                                    'item_icon': openapi.Schema(type=openapi.TYPE_STRING),
                                    'quantity': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'item_options': openapi.Schema(type=openapi.TYPE_OBJECT, nullable=True),
                                    'slot_position': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'expiry_date': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                    'crawled_at': openapi.Schema(type=openapi.TYPE_STRING),
                                    'days_until_expiry': openapi.Schema(type=openapi.TYPE_INTEGER, nullable=True),
                                    'is_expirable': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                }
                            )
                        ),
                        'total_count': openapi.Schema(type=openapi.TYPE_INTEGER, description='총 아이템 수'),
                        'last_crawled_at': openapi.Schema(type=openapi.TYPE_STRING, nullable=True, description='마지막 크롤링 시간'),
                        'category': openapi.Schema(type=openapi.TYPE_STRING, description='적용된 카테고리'),
                        'sort': openapi.Schema(type=openapi.TYPE_STRING, description='적용된 정렬 기준'),
                        'order': openapi.Schema(type=openapi.TYPE_STRING, description='적용된 정렬 순서')
                    }
                )
            ),
            401: "인증되지 않은 사용자",
            404: "캐릭터를 찾을 수 없음"
        },
        tags=['창고']
    )
    def get(self, request, ocid):
        """
        사용자 계정의 창고 아이템 목록을 반환합니다.

        창고는 계정 내 모든 캐릭터가 공유하므로,
        어떤 캐릭터의 ocid로 조회해도 동일한 창고 아이템이 반환됩니다.

        AC-3.6.1: 창고 아이템 그리드 표시
        AC-3.6.2: 계정 공유 - 동일 사용자의 모든 캐릭터에서 같은 창고
        AC-3.6.3: 아이콘, 이름, 수량, 강화 수치(item_options) 포함
        AC-3.6.4: 빈 창고 시 빈 배열 반환
        AC-3.9.1: 정렬 옵션: slot_position, item_name, quantity, crawled_at, expiry_date
        AC-3.9.6: 만료일 정렬 시 null 값은 마지막에 표시
        """
        from accounts.models import Character
        from .models import CharacterBasic, Storage
        from .serializers import StorageItemSerializer

        # 1. 소유권 검증: 사용자가 이 캐릭터를 소유하는지 확인
        # 정보 노출 방지를 위해 403 대신 404 반환
        try:
            character = Character.objects.get(ocid=ocid, user=request.user)
        except Character.DoesNotExist:
            return Response(
                {"error": "캐릭터를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )

        # 2. 창고 아이템 조회 (AC-3.6.2: 계정 공유)
        # 창고는 사용자(계정) 기준 조회 - 캐릭터와 무관하게 동일
        # 사용자의 모든 캐릭터 ocid 목록 조회
        user_character_ocids = Character.objects.filter(
            user=request.user
        ).values_list('ocid', flat=True)

        # 해당 ocid에 해당하는 CharacterBasic의 Storage 조회
        storage_items = Storage.objects.filter(
            character_basic__ocid__in=user_character_ocids
        )

        # 3. 카테고리 필터 적용 (Story 3.5 패턴 재사용)
        category = request.query_params.get('category', 'all')

        if category == 'expirable':
            # 기간제 아이템: expiry_date가 있는 아이템만
            storage_items = storage_items.filter(expiry_date__isnull=False)
        elif category == 'equipment':
            # 장비 아이템: item_options에 enhancement가 있는 아이템
            storage_items = storage_items.filter(item_options__isnull=False)
        elif category == 'consumable':
            # 소비 아이템: 수량이 1보다 크거나 소비류 키워드 포함
            storage_items = storage_items.filter(quantity__gt=1)
        elif category == 'etc':
            # 기타: 장비도 소비도 아닌 아이템
            storage_items = storage_items.filter(
                item_options__isnull=True,
                quantity=1,
                expiry_date__isnull=True
            )
        # 'all' 또는 잘못된 카테고리는 필터 없이 전체 반환

        # 4. 정렬 적용 (Story 3.9: AC-3.9.1, AC-3.9.4, AC-3.9.6)
        sort_field = request.query_params.get('sort', 'slot_position')
        order = request.query_params.get('order', 'asc')

        # 허용된 정렬 필드 검증 (허용되지 않은 필드는 기본값으로)
        if sort_field not in self.VALID_SORT_FIELDS:
            sort_field = 'slot_position'

        # 정렬 순서 검증
        if order not in ['asc', 'desc']:
            order = 'asc'

        # AC-3.9.6: 만료일 정렬 시 null 값은 마지막에 표시 (NULLS LAST)
        if sort_field == 'expiry_date':
            if order == 'asc':
                storage_items = storage_items.order_by(F('expiry_date').asc(nulls_last=True))
            else:
                storage_items = storage_items.order_by(F('expiry_date').desc(nulls_last=True))
        else:
            # 일반 정렬
            if order == 'desc':
                storage_items = storage_items.order_by(f'-{sort_field}')
            else:
                storage_items = storage_items.order_by(sort_field)

        # 5. Serializer로 직렬화 (AC-3.6.3)
        serializer = StorageItemSerializer(storage_items, many=True)

        # 6. 마지막 크롤링 시간 계산
        last_crawled_at = None
        if storage_items.exists():
            latest_item = storage_items.order_by('-crawled_at').first()
            if latest_item:
                last_crawled_at = latest_item.crawled_at.isoformat()

        return Response({
            'items': serializer.data,
            'total_count': storage_items.count(),
            'last_crawled_at': last_crawled_at,
            'category': category,
            'sort': sort_field,    # 현재 적용된 정렬 기준 반환 (Story 3.9: AC-3.9.5)
            'order': order         # 현재 적용된 정렬 순서 반환 (Story 3.9: AC-3.9.4)
        })


# =============================================================================
# 아이템 검색 뷰 (Story 4.1)
# =============================================================================

class ItemSearchView(APIView):
    """
    통합 아이템 검색 뷰 (Story 4.1)

    GET /api/search/items/ - 사용자의 모든 캐릭터에서 아이템 검색

    사용자가 소유한 모든 캐릭터의 인벤토리와 창고에서 아이템을 검색합니다.
    검색 결과는 페이지네이션되어 반환됩니다.

    Query Parameters:
    - q (required): 검색어 (아이템 이름 부분 일치, 대소문자 무시)
    - type (optional): 아이템 타입 필터 ('equips', 'consumables', 'miscs', 'installables', 'cashes')
    - location (optional): 위치 필터 ('inventory', 'storage', 'all', default: 'all')
    - page (optional): 페이지 번호 (default: 1)
    - page_size (optional): 페이지당 결과 수 (default: 20, max: 100)
    """
    permission_classes = [IsAuthenticated]

    # 허용된 item_type 값
    VALID_ITEM_TYPES = ['equips', 'consumables', 'miscs', 'installables', 'cashes']

    @swagger_auto_schema(
        operation_description="사용자의 모든 캐릭터에서 아이템 검색",
        manual_parameters=[
            openapi.Parameter(
                'q',
                openapi.IN_QUERY,
                description="검색어 (아이템 이름)",
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'type',
                openapi.IN_QUERY,
                description="아이템 타입 필터 (equips, consumables, miscs, installables, cashes)",
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'location',
                openapi.IN_QUERY,
                description="위치 필터 (inventory, storage, all)",
                type=openapi.TYPE_STRING,
                required=False,
                default='all'
            ),
            openapi.Parameter(
                'page',
                openapi.IN_QUERY,
                description="페이지 번호",
                type=openapi.TYPE_INTEGER,
                required=False,
                default=1
            ),
            openapi.Parameter(
                'page_size',
                openapi.IN_QUERY,
                description="페이지당 결과 수 (최대 100)",
                type=openapi.TYPE_INTEGER,
                required=False,
                default=20
            )
        ],
        responses={
            200: openapi.Response(
                description="성공",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'count': openapi.Schema(type=openapi.TYPE_INTEGER, description='총 결과 수'),
                        'next': openapi.Schema(type=openapi.TYPE_STRING, nullable=True, description='다음 페이지 URL'),
                        'previous': openapi.Schema(type=openapi.TYPE_STRING, nullable=True, description='이전 페이지 URL'),
                        'results': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'item_name': openapi.Schema(type=openapi.TYPE_STRING),
                                    'item_type': openapi.Schema(type=openapi.TYPE_STRING),
                                    'quantity': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'item_icon': openapi.Schema(type=openapi.TYPE_STRING),
                                    'item_options': openapi.Schema(type=openapi.TYPE_OBJECT, nullable=True),
                                    'location': openapi.Schema(type=openapi.TYPE_STRING),
                                    'character_name': openapi.Schema(type=openapi.TYPE_STRING),
                                    'character_ocid': openapi.Schema(type=openapi.TYPE_STRING),
                                    'world_name': openapi.Schema(type=openapi.TYPE_STRING),
                                    'expiry_date': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                    'days_until_expiry': openapi.Schema(type=openapi.TYPE_INTEGER, nullable=True),
                                    'is_expirable': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                }
                            )
                        )
                    }
                )
            ),
            400: "잘못된 요청 (검색어 누락)",
            401: "인증되지 않은 사용자"
        },
        tags=['아이템 검색']
    )
    def get(self, request):
        """
        사용자의 모든 캐릭터에서 아이템을 검색합니다.
        """
        from accounts.models import Character
        from .models import CharacterBasic, Inventory, Storage
        from .serializers import ItemSearchResultSerializer
        from django.core.paginator import Paginator, EmptyPage

        # 1. 검색어 검증
        query = request.query_params.get('q', '').strip()
        if not query:
            return Response(
                {"error": "검색어(q)가 필요합니다."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2. 필터 파라미터 추출
        item_type = request.query_params.get('type', '').strip()
        location = request.query_params.get('location', 'all').lower()

        # item_type 검증
        if item_type and item_type not in self.VALID_ITEM_TYPES:
            return Response(
                {"error": f"유효하지 않은 아이템 타입입니다. 허용된 값: {', '.join(self.VALID_ITEM_TYPES)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # location 검증
        if location not in ['inventory', 'storage', 'all']:
            location = 'all'

        # 3. 사용자의 모든 캐릭터 OCID 조회
        user_character_ocids = Character.objects.filter(
            user=request.user
        ).values_list('ocid', flat=True)

        if not user_character_ocids:
            # 사용자가 캐릭터를 등록하지 않은 경우
            return Response({
                'count': 0,
                'next': None,
                'previous': None,
                'results': []
            })

        # 4. 아이템 검색 결과 수집
        results = []

        # 4-1. 인벤토리 검색 (location이 'inventory' 또는 'all')
        if location in ['inventory', 'all']:
            inventory_query = Inventory.objects.filter(
                character_basic__ocid__in=user_character_ocids,
                item_name__icontains=query
            ).select_related('character_basic')

            # item_type 필터 적용
            if item_type:
                inventory_query = inventory_query.filter(item_type=item_type)

            # 최근 크롤링 데이터만 조회 (각 캐릭터의 최신 crawled_at)
            for ocid in user_character_ocids:
                latest_crawled = Inventory.objects.filter(
                    character_basic__ocid=ocid
                ).order_by('-crawled_at').first()

                if latest_crawled:
                    items = inventory_query.filter(
                        character_basic__ocid=ocid,
                        crawled_at=latest_crawled.crawled_at
                    )

                    for item in items:
                        results.append({
                            'item_name': item.item_name,
                            'item_type': item.item_type,
                            'quantity': item.quantity,
                            'item_icon': item.item_icon,
                            'item_options': item.item_options,
                            'location': 'inventory',
                            'character_name': item.character_basic.character_name,
                            'character_ocid': item.character_basic.ocid,
                            'world_name': item.character_basic.world_name,
                            'expiry_date': item.expiry_date,
                            'days_until_expiry': item.days_until_expiry,
                            'is_expirable': item.is_expirable,
                        })

        # 4-2. 창고 검색 (location이 'storage' 또는 'all')
        if location in ['storage', 'all']:
            storage_query = Storage.objects.filter(
                character_basic__ocid__in=user_character_ocids,
                item_name__icontains=query
            ).select_related('character_basic')

            # 창고는 item_type 필드가 없으므로, 필터링하지 않음
            # (필요시 item_options 유무 등으로 유추 가능)

            # 최근 크롤링 데이터만 조회
            for ocid in user_character_ocids:
                latest_crawled = Storage.objects.filter(
                    character_basic__ocid=ocid
                ).order_by('-crawled_at').first()

                if latest_crawled:
                    items = storage_query.filter(
                        character_basic__ocid=ocid,
                        crawled_at=latest_crawled.crawled_at
                    )

                    for item in items:
                        results.append({
                            'item_name': item.item_name,
                            'item_type': None,  # Storage 모델에는 item_type 필드 없음
                            'quantity': item.quantity,
                            'item_icon': item.item_icon,
                            'item_options': item.item_options,
                            'location': 'storage',
                            'character_name': item.character_basic.character_name,
                            'character_ocid': item.character_basic.ocid,
                            'world_name': item.character_basic.world_name,
                            'expiry_date': item.expiry_date,
                            'days_until_expiry': item.days_until_expiry,
                            'is_expirable': item.is_expirable,
                        })

        # 5. 페이지네이션 처리
        page_number = request.query_params.get('page', 1)
        page_size = min(int(request.query_params.get('page_size', 20)), 100)  # 최대 100개

        paginator = Paginator(results, page_size)

        try:
            page_obj = paginator.page(page_number)
        except EmptyPage:
            # 페이지 번호가 범위를 벗어난 경우 빈 결과 반환
            return Response({
                'count': paginator.count,
                'next': None,
                'previous': None,
                'results': []
            })

        # 6. next/previous URL 생성
        next_url = None
        previous_url = None

        if page_obj.has_next():
            next_url = request.build_absolute_uri(
                f'?q={query}&location={location}&page={page_obj.next_page_number()}&page_size={page_size}'
            )
            if item_type:
                next_url += f'&type={item_type}'

        if page_obj.has_previous():
            previous_url = request.build_absolute_uri(
                f'?q={query}&location={location}&page={page_obj.previous_page_number()}&page_size={page_size}'
            )
            if item_type:
                previous_url += f'&type={item_type}'

        # 7. 직렬화 및 응답
        serializer = ItemSearchResultSerializer(page_obj.object_list, many=True)

        return Response({
            'count': paginator.count,
            'next': next_url,
            'previous': previous_url,
            'results': serializer.data
        })


# =============================================================================
# 메소 요약 뷰 (Story 4.3)
# =============================================================================

class MesoSummaryView(APIView):
    """
    메소 요약 조회 뷰 (Story 4.3)

    GET /api/characters/meso/summary/ - 사용자의 전체 메소 요약 반환

    사용자의 모든 캐릭터가 보유한 메소와 창고 메소를 집계합니다.
    창고 메소는 계정 공유이므로 중복 집계되지 않습니다.
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="인증된 사용자의 전체 메소 요약 조회 (캐릭터 메소 + 창고 메소)",
        manual_parameters=[
            openapi.Parameter(
                'sort',
                openapi.IN_QUERY,
                description="정렬 기준 (meso, name, level)",
                type=openapi.TYPE_STRING,
                required=False,
                default='meso'
            ),
            openapi.Parameter(
                'order',
                openapi.IN_QUERY,
                description="정렬 순서 (asc, desc)",
                type=openapi.TYPE_STRING,
                required=False,
                default='desc'
            )
        ],
        responses={
            200: openapi.Response(
                description="성공",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'total_meso': openapi.Schema(type=openapi.TYPE_INTEGER, description='총 메소 (캐릭터 + 창고)'),
                        'character_meso_total': openapi.Schema(type=openapi.TYPE_INTEGER, description='캐릭터 메소 합계'),
                        'storage_meso': openapi.Schema(type=openapi.TYPE_INTEGER, description='창고 메소'),
                        'characters': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'ocid': openapi.Schema(type=openapi.TYPE_STRING),
                                    'character_name': openapi.Schema(type=openapi.TYPE_STRING),
                                    'world_name': openapi.Schema(type=openapi.TYPE_STRING),
                                    'meso': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'character_class': openapi.Schema(type=openapi.TYPE_STRING),
                                    'character_level': openapi.Schema(type=openapi.TYPE_INTEGER),
                                }
                            )
                        ),
                        'storage': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'meso': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'last_updated': openapi.Schema(type=openapi.TYPE_STRING),
                            }
                        ),
                        'last_updated': openapi.Schema(type=openapi.TYPE_STRING, description='마지막 업데이트 시간'),
                    }
                )
            ),
            401: "인증되지 않은 사용자"
        },
        tags=['메소 요약']
    )
    def get(self, request):
        """
        사용자의 전체 메소 요약을 반환합니다.

        - 모든 캐릭터의 메소 합계 계산
        - 창고 메소는 계정 공유이므로 1회만 집계
        - 정렬 옵션: meso (기본값), name, level
        - 정렬 순서: desc (기본값), asc
        """
        from accounts.models import Character
        from .models import CharacterBasic, Storage
        from .serializers import MesoSummarySerializer
        from django.db.models import Sum, Max, Q, F
        from django.db.models.functions import Coalesce

        # 1. 사용자의 캐릭터 OCID 목록 조회
        user_character_ocids = Character.objects.filter(
            user=request.user
        ).values_list('ocid', flat=True)

        if not user_character_ocids:
            # 캐릭터가 없는 경우 빈 요약 반환
            return Response({
                'total_meso': 0,
                'character_meso_total': 0,
                'storage_meso': 0,
                'characters': [],
                'storage': {
                    'meso': 0,
                    'last_updated': None
                },
                'last_updated': timezone.now().isoformat()
            })

        # 2. 캐릭터 메소 집계 (NULL 값은 0으로 처리)
        character_basics = CharacterBasic.objects.filter(
            ocid__in=user_character_ocids
        ).annotate(
            safe_meso=Coalesce('meso', 0)
        )

        # 캐릭터 메소 총합 계산
        character_meso_aggregate = character_basics.aggregate(
            total=Sum('safe_meso')
        )
        character_meso_total = character_meso_aggregate['total'] or 0

        # 3. 창고 메소 조회 (가장 최근 크롤링된 창고 메소)
        latest_storage = Storage.objects.filter(
            character_basic__ocid__in=user_character_ocids,
            meso__isnull=False
        ).order_by('-crawled_at').first()

        storage_meso = latest_storage.meso if latest_storage and latest_storage.meso else 0
        storage_last_updated = latest_storage.crawled_at if latest_storage else None

        # 4. 정렬 옵션 처리
        sort_field = request.query_params.get('sort', 'meso')
        order = request.query_params.get('order', 'desc')

        # 허용된 정렬 필드 검증
        valid_sort_fields = {
            'meso': 'safe_meso',
            'name': 'character_name',
            'level': 'character_level'
        }

        if sort_field not in valid_sort_fields:
            sort_field = 'meso'

        db_sort_field = valid_sort_fields[sort_field]

        # 정렬 순서 검증
        if order not in ['asc', 'desc']:
            order = 'desc'

        # 정렬 적용
        if order == 'desc':
            character_basics = character_basics.order_by(f'-{db_sort_field}')
        else:
            character_basics = character_basics.order_by(db_sort_field)

        # 5. 캐릭터 목록 직렬화
        characters_data = []
        for char in character_basics:
            characters_data.append({
                'ocid': char.ocid,
                'character_name': char.character_name,
                'world_name': char.world_name,
                'meso': char.safe_meso,
                'character_class': char.character_class,
                'character_level': char.character_level
            })

        # 6. 최종 응답 데이터 구성
        total_meso = character_meso_total + storage_meso

        # 마지막 업데이트 시간 계산 (캐릭터 또는 창고 중 최신)
        last_updated = timezone.now()
        if character_basics.exists():
            latest_char_update = character_basics.aggregate(Max('last_updated'))['last_updated__max']
            if latest_char_update:
                last_updated = latest_char_update
        if storage_last_updated and storage_last_updated > last_updated:
            last_updated = storage_last_updated

        response_data = {
            'total_meso': total_meso,
            'character_meso_total': character_meso_total,
            'storage_meso': storage_meso,
            'characters': characters_data,
            'storage': {
                'meso': storage_meso,
                'last_updated': storage_last_updated.isoformat() if storage_last_updated else None
            },
            'last_updated': last_updated.isoformat()
        }

        serializer = MesoSummarySerializer(data=response_data)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.data)


# =============================================================================
# 대시보드 통계 뷰 (Story 5.6)
# =============================================================================

class DashboardStatsView(APIView):
    """
    대시보드 통계 조회 뷰 (Story 5.6)

    GET /api/characters/dashboard/stats/ - 사용자의 전체 대시보드 통계 반환

    사용자의 모든 캐릭터 통계를 집계합니다:
    - 총 캐릭터 수
    - 총 메소 (캐릭터 보유 메소 합계)
    - 7일 이내 만료 아이템 수
    - 최근 크롤링 정보
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="인증된 사용자의 대시보드 통계 조회",
        responses={
            200: openapi.Response(
                description="성공",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'total_characters': openapi.Schema(type=openapi.TYPE_INTEGER, description='총 캐릭터 수'),
                        'total_meso': openapi.Schema(type=openapi.TYPE_INTEGER, description='총 메소 (캐릭터 보유)'),
                        'expiring_items_count': openapi.Schema(type=openapi.TYPE_INTEGER, description='7일 이내 만료 아이템 수'),
                        'recent_crawl': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'last_crawled_at': openapi.Schema(type=openapi.TYPE_STRING, nullable=True, description='마지막 크롤링 시간'),
                                'characters_updated': openapi.Schema(type=openapi.TYPE_INTEGER, description='24시간 내 업데이트된 캐릭터 수'),
                            }
                        ),
                    }
                )
            ),
            401: "인증되지 않은 사용자"
        },
        tags=['대시보드']
    )
    def get(self, request):
        """
        사용자의 대시보드 통계를 반환합니다.

        - 총 캐릭터 수
        - 총 메소 (캐릭터 보유 메소 합계)
        - 7일 이내 만료 아이템 수
        - 최근 크롤링 정보 (마지막 크롤링 시간, 24시간 내 업데이트된 캐릭터 수)
        """
        from accounts.models import Character
        from .models import CharacterBasic, Inventory, Storage
        from .serializers import DashboardStatsSerializer
        from django.db.models import Sum
        from django.db.models.functions import Coalesce
        from datetime import timedelta

        # 1. 사용자의 캐릭터 OCID 목록 조회
        user_ocids = Character.objects.filter(user=request.user).values_list('ocid', flat=True)

        # 2. 총 캐릭터 수
        total_characters = user_ocids.count()

        # 3. 총 메소 (CharacterBasic의 meso 필드 합계)
        total_meso = CharacterBasic.objects.filter(
            ocid__in=user_ocids
        ).aggregate(
            total=Coalesce(Sum('meso'), 0)
        )['total']

        # 4. 7일 이내 만료 아이템 수
        seven_days = timezone.now() + timedelta(days=7)

        # 인벤토리에서 7일 이내 만료 아이템
        expiring_inventory = Inventory.objects.filter(
            character_basic__ocid__in=user_ocids,
            expiry_date__isnull=False,
            expiry_date__lte=seven_days
        ).count()

        # 창고에서 7일 이내 만료 아이템
        expiring_storage = Storage.objects.filter(
            character_basic__ocid__in=user_ocids,
            expiry_date__isnull=False,
            expiry_date__lte=seven_days
        ).count()

        expiring_items_count = expiring_inventory + expiring_storage

        # 5. 최근 크롤링 정보
        # 가장 최근에 크롤링된 캐릭터 정보
        recent_crawl_char = CharacterBasic.objects.filter(
            ocid__in=user_ocids
        ).order_by('-last_updated').first()

        # 24시간 이내에 크롤링된 캐릭터 수
        twenty_four_hours_ago = timezone.now() - timedelta(hours=24)
        characters_updated = CharacterBasic.objects.filter(
            ocid__in=user_ocids,
            last_updated__gte=twenty_four_hours_ago
        ).count()

        crawl_info = {
            'last_crawled_at': recent_crawl_char.last_updated.isoformat() if recent_crawl_char and recent_crawl_char.last_updated else None,
            'characters_updated': characters_updated
        }

        # 6. 응답 데이터 구성
        response_data = {
            'total_characters': total_characters,
            'total_meso': total_meso,
            'expiring_items_count': expiring_items_count,
            'recent_crawl': crawl_info
        }

        serializer = DashboardStatsSerializer(data=response_data)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.data)


# =============================================================================
# 만료 예정 아이템 목록 조회 뷰 (Story 5.1/5.4)
# =============================================================================

class ExpiringItemsView(APIView):
    """
    만료 예정 아이템 목록 조회 뷰 (Story 5.1/5.4)

    GET /api/characters/dashboard/expiring-items/ - 7일 이내 만료 예정 아이템 목록 반환

    사용자의 모든 캐릭터에서 7일 이내 만료되는 아이템을 조회합니다:
    - 인벤토리 및 창고의 만료 예정 아이템
    - D-day 계산 및 긴급도 레벨 (danger/warning/info)
    - 만료 임박 순으로 정렬
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="인증된 사용자의 7일 이내 만료 예정 아이템 목록 조회",
        responses={
            200: openapi.Response(
                description="성공",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'count': openapi.Schema(type=openapi.TYPE_INTEGER, description='만료 예정 아이템 수'),
                        'items': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='아이템 ID'),
                                    'item_name': openapi.Schema(type=openapi.TYPE_STRING, description='아이템 이름'),
                                    'item_icon': openapi.Schema(type=openapi.TYPE_STRING, description='아이템 아이콘 URL'),
                                    'character_name': openapi.Schema(type=openapi.TYPE_STRING, description='캐릭터 이름'),
                                    'character_ocid': openapi.Schema(type=openapi.TYPE_STRING, description='캐릭터 OCID'),
                                    'location': openapi.Schema(type=openapi.TYPE_STRING, description='위치 (inventory/storage)'),
                                    'expiry_date': openapi.Schema(type=openapi.TYPE_STRING, description='만료 날짜 (ISO 8601)'),
                                    'days_until_expiry': openapi.Schema(type=openapi.TYPE_INTEGER, description='만료까지 남은 일수'),
                                    'urgency': openapi.Schema(type=openapi.TYPE_STRING, description='긴급도 (danger/warning/info)'),
                                }
                            )
                        ),
                    }
                )
            ),
            401: "인증되지 않은 사용자"
        },
        tags=['대시보드']
    )
    def get(self, request):
        """
        사용자의 7일 이내 만료 예정 아이템 목록을 반환합니다.

        - 인벤토리 및 창고에서 만료 예정 아이템 조회
        - D-day 계산 및 긴급도 레벨 추가
        - 만료 임박 순으로 정렬
        """
        from accounts.models import Character
        from .models import CharacterBasic, Inventory, Storage
        from .serializers import ExpiringItemSerializer
        from datetime import timedelta

        # 1. 사용자의 캐릭터 OCID 목록 조회
        user_ocids = Character.objects.filter(user=request.user).values_list('ocid', flat=True)

        # 2. CharacterBasic을 통해 캐릭터 정보 매핑
        character_basics = CharacterBasic.objects.filter(
            ocid__in=user_ocids
        ).select_related().only('ocid', 'character_name')

        character_map = {cb.ocid: cb.character_name for cb in character_basics}

        # 3. 7일 이내 만료 아이템 조회
        seven_days_later = timezone.now() + timedelta(days=7)
        now = timezone.now()

        # 인벤토리 아이템
        inventory_items = Inventory.objects.filter(
            character_basic__ocid__in=user_ocids,
            expiry_date__isnull=False,
            expiry_date__gte=now,
            expiry_date__lte=seven_days_later
        ).select_related('character_basic').order_by('expiry_date')

        # 창고 아이템
        storage_items = Storage.objects.filter(
            character_basic__ocid__in=user_ocids,
            expiry_date__isnull=False,
            expiry_date__gte=now,
            expiry_date__lte=seven_days_later
        ).select_related('character_basic').order_by('expiry_date')

        # 4. 통합 아이템 목록 구성
        items_data = []

        # 인벤토리 아이템 추가
        for item in inventory_items:
            days_until_expiry = item.days_until_expiry

            # 긴급도 계산
            if days_until_expiry <= 1:
                urgency = "danger"
            elif days_until_expiry <= 3:
                urgency = "warning"
            else:
                urgency = "info"

            items_data.append({
                'id': item.id,
                'item_name': item.item_name,
                'item_icon': item.item_icon,
                'character_name': character_map.get(item.character_basic.ocid, item.character_basic.character_name),
                'character_ocid': item.character_basic.ocid,
                'location': 'inventory',
                'expiry_date': item.expiry_date.isoformat(),
                'days_until_expiry': days_until_expiry,
                'urgency': urgency
            })

        # 창고 아이템 추가
        for item in storage_items:
            days_until_expiry = item.days_until_expiry

            # 긴급도 계산
            if days_until_expiry <= 1:
                urgency = "danger"
            elif days_until_expiry <= 3:
                urgency = "warning"
            else:
                urgency = "info"

            items_data.append({
                'id': item.id,
                'item_name': item.item_name,
                'item_icon': item.item_icon,
                'character_name': character_map.get(item.character_basic.ocid, item.character_basic.character_name),
                'character_ocid': item.character_basic.ocid,
                'location': 'storage',
                'expiry_date': item.expiry_date.isoformat(),
                'days_until_expiry': days_until_expiry,
                'urgency': urgency
            })

        # 5. 만료 임박 순으로 정렬 (이미 쿼리에서 정렬되어 있지만 통합 후 재정렬)
        items_data.sort(key=lambda x: x['expiry_date'])

        # 6. 응답 데이터 구성
        response_data = {
            'count': len(items_data),
            'items': items_data
        }

        serializer = ExpiringItemSerializer(data=response_data)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.data)
