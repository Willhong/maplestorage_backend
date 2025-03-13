import time
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta
import requests
import logging
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from accounts.models import Character
from define.define import (
    APIKEY,
    CHARACTER_ID_URL,
    CHARACTER_BASIC_URL,
    CHARACTER_ABILITY_URL,
    CHARACTER_ITEM_EQUIPMENT_URL,
    CHARACTER_CASHITEM_EQUIPMENT_URL,
    CHARACTER_SYMBOL_URL,
    CHARACTER_LINK_SKILL_URL,
    CHARACTER_SKILL_URL,
    CHARACTER_HEXAMATRIX_URL,
    CHARACTER_HEXAMATRIX_STAT_URL,
    CHARACTER_POPULARITY_URL,
    CHARACTER_STAT_URL
)
from util.util import CharacterDataManager
from .models import *
from .schemas import (
    CharacterItemEquipmentSchema, CharacterBasicSchema,
    CharacterPopularitySchema, CharacterStatSchema,
    CharacterAbilitySchema, CharacterCashItemEquipmentSchema,
    CharacterSymbolSchema, CharacterLinkSkillSchema,
    CharacterVMatrixSchema, CharacterHexaMatrixSchema,
    CharacterHexaStatSchema, StatInfoSchema
)
from .serializers import CharacterAbilitySerializer, CharacterBasicSerializer
from .services import MapleAPIService, EquipmentService
from .mixins import MapleAPIClientMixin, APIViewMixin, CharacterDataMixin
from .utils import validate_character_name, validate_date_format
from .exceptions import InvalidParameterError, CharacterNotFoundError

# 로거 설정
logger = logging.getLogger('maple_api')


class BaseAPIView(APIViewMixin, MapleAPIClientMixin, CharacterDataMixin):
    """
    모든 API 뷰의 기본 클래스
    """
    permission_classes = []

    def get_ocid_from_api(self, character_name):
        """
        캐릭터 OCID 조회 (하위 호환성을 위해 유지)
        새로운 코드에서는 MapleAPIService.get_ocid 사용 권장
        """
        return MapleAPIService.get_ocid(character_name)

    def get_character_basic(self, ocid, date=None):
        """
        기본 정보 조회 및 CharacterBasic 데이터 생성 (하위 호환성을 위해 유지)
        새로운 코드에서는 MapleAPIService.get_character_basic 사용 권장
        """
        return MapleAPIService.get_character_basic(ocid, date)

    def get_character_data(self, request):
        """
        캐릭터 데이터 조회를 위한 공통 로직

        Args:
            request: HTTP 요청 객체

        Returns:
            tuple: (character_name, ocid, date)

        Raises:
            InvalidParameterError: 파라미터가 유효하지 않은 경우
            CharacterNotFoundError: 캐릭터를 찾을 수 없는 경우
        """
        # 파라미터 추출
        character_name = request.query_params.get('character_name')
        date = self.get_date_param(request)

        # 파라미터 검증
        validate_character_name(character_name)
        if date:
            validate_date_format(date)

        # 로깅
        self.log_request("캐릭터 데이터 조회", character_name)
        logger.info(f"캐릭터 데이터 조회 요청 - 캐릭터: {character_name}, 날짜: {date}")

        # OCID 조회
        ocid = MapleAPIService.get_ocid(character_name)
        if not ocid:
            raise CharacterNotFoundError(
                message=f"'{character_name}' 캐릭터를 찾을 수 없습니다."
            )

        return character_name, ocid, date


class CharacterBasicView(BaseAPIView):
    @swagger_auto_schema(
        operation_summary="캐릭터 기본 정보 조회",
        operation_description="캐릭터의 기본 정보, 인기도, 스탯 정보를 조회합니다.",
        manual_parameters=[
            openapi.Parameter(
                'character_name',
                openapi.IN_QUERY,
                description="조회할 캐릭터 이름",
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'date',
                openapi.IN_QUERY,
                description="조회 기준일(YYYY-MM-DD 형식, 기본값: 오늘)",
                type=openapi.TYPE_STRING,
                required=False
            ),
        ],
        responses={
            200: openapi.Response(
                description="성공적으로 조회됨",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'data': openapi.Schema(type=openapi.TYPE_OBJECT),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            ),
            400: "잘못된 요청",
            404: "캐릭터를 찾을 수 없음",
            500: "서버 오류"
        }
    )
    def get(self, request):
        """
        캐릭터 기본 정보 조회
        """
        try:
            # 공통 데이터 조회
            character_name, ocid, date = self.get_character_data(request)

            # 캐시된 데이터 확인
            cached_data = self.get_cached_data(character_name)
            if cached_data:
                # 캐시된 데이터를 직렬화하여 반환
                # popularity와 stat 데이터도 함께 가져오기
                popularity_data = cached_data.popularity.order_by(
                    '-date').first()
                stat_data = cached_data.stats.filter(
                    date=cached_data.date).first()

                serialized_data = {
                    "character_basic": CharacterBasicSerializer(cached_data).data,
                }

                # popularity 데이터가 있으면 추가
                if popularity_data:
                    serialized_data["popularity"] = CharacterPopularitySchema(
                        date=popularity_data.date.isoformat() if popularity_data.date else None,
                        popularity=popularity_data.popularity
                    ).model_dump()

                # stat 데이터가 있으면 추가
                if stat_data:
                    # stat_detail 데이터 가져오기
                    stat_details = []
                    for detail in stat_data.final_stat.all():
                        stat_details.append({
                            "stat_name": detail.stat_name,
                            "stat_value": detail.stat_value
                        })

                    serialized_data["stat"] = CharacterStatSchema(
                        date=stat_data.date.isoformat() if stat_data.date else None,
                        character_class=stat_data.character_class,
                        remain_ap=stat_data.remain_ap,
                        final_stat=stat_details
                    ).model_dump()

                return Response(self.format_response_data(
                    serialized_data,
                    "캐시된 데이터를 반환합니다."
                ))

            # API에서 데이터 조회
            character_basic, current_time = MapleAPIService.get_character_basic(
                ocid, date)

            # 추가 데이터 조회
            popularity_data = MapleAPIService.get_character_popularity(
                ocid, date)
            popularity_validated = self.validate_data(
                CharacterPopularitySchema, popularity_data)

            stat_data = MapleAPIService.get_character_stat(ocid, date)
            stat_validated = self.validate_data(CharacterStatSchema, stat_data)

            # 데이터 병합 및 응답 생성
            response_data = {
                "character_basic": CharacterBasicSerializer(character_basic).data,
                "popularity": popularity_validated.model_dump(),
                "stat": stat_validated.model_dump()
            }

            # 날짜 형식 일관성 확인
            basic_date = response_data["character_basic"].get("date")
            if basic_date and isinstance(basic_date, str):
                logger.info(f"응답 데이터 날짜 확인 - character_basic: {basic_date}")

            popularity_date = response_data["popularity"].get("date")
            if popularity_date and isinstance(popularity_date, str):
                logger.info(f"응답 데이터 날짜 확인 - popularity: {popularity_date}")

            stat_date = response_data["stat"].get("date")
            if stat_date and isinstance(stat_date, str):
                logger.info(f"응답 데이터 날짜 확인 - stat: {stat_date}")

            # 날짜 형식 일관성 검증
            if basic_date and popularity_date and stat_date:
                logger.info(
                    f"날짜 형식 일관성 검증: character_basic({basic_date}), popularity({popularity_date}), stat({stat_date})")
                if basic_date.startswith(popularity_date[:10]) and basic_date.startswith(stat_date[:10]):
                    logger.info("날짜 형식 일관성 검증 성공: 모든 날짜가 같은 날짜를 가리킵니다.")
                else:
                    logger.warning("날짜 형식 일관성 검증 실패: 날짜가 서로 다릅니다.")
                    logger.warning(f"character_basic: {basic_date}")
                    logger.warning(f"popularity: {popularity_date}")
                    logger.warning(f"stat: {stat_date}")

            # 데이터베이스에 저장
            self.save_to_database(character_basic, ocid,
                                  popularity_validated.model_dump(), stat_validated.model_dump())

            return Response(self.format_response_data(
                response_data,
                f"{character_name} 캐릭터의 기본 정보를 조회했습니다."
            ))

        except (InvalidParameterError, CharacterNotFoundError) as e:
            logger.warning(f"캐릭터 기본 정보 조회 실패: {e.message}")
            return Response(
                {"error": e.message, "detail": e.detail if hasattr(
                    e, 'detail') else None},
                status=e.status_code
            )
        except Exception as e:
            logger.error(f"예상치 못한 오류: {str(e)}")
            return Response(
                {"error": "서버에서 예상치 못한 오류가 발생했습니다.", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def get_character_data_from_api(self, ocid, date):
        """캐릭터 기본 정보 API 호출 및 데이터 검증"""
        data = MapleAPIService.get_character_basic(ocid, date)[0]
        return self.validate_data(CharacterBasicSchema, data)

    def get_popularity_data_from_api(self, ocid, date):
        """캐릭터 인기도 정보 API 호출 및 데이터 검증"""
        data = MapleAPIService.get_character_popularity(ocid, date)
        validated_data = self.validate_data(CharacterPopularitySchema, data)

        # Pydantic 모델을 딕셔너리로 변환
        popularity_dict = validated_data.model_dump()

        # 날짜 정보가 없으면 현재 시간으로 설정
        if not popularity_dict.get('date'):
            current_time = timezone.now()
            popularity_dict['date'] = current_time.isoformat()
            logger.info(f"인기도 데이터에 날짜 추가: {popularity_dict['date']}")
        else:
            # 날짜 변환
            api_date = popularity_dict.get('date')
            local_time = self.convert_to_local_time(api_date)
            popularity_dict['date'] = local_time.isoformat()
            logger.info(f"인기도 데이터 날짜 변환: {api_date} -> {local_time}")

        return popularity_dict

    def get_stat_data_from_api(self, ocid, date):
        """캐릭터 스탯 정보 API 호출 및 데이터 검증"""
        data = MapleAPIService.get_character_stat(ocid, date)
        validated_data = self.validate_data(CharacterStatSchema, data)

        # Pydantic 모델을 딕셔너리로 변환
        stat_dict = validated_data.model_dump()

        # 날짜 정보가 없으면 현재 시간으로 설정
        if not stat_dict.get('date'):
            current_time = timezone.now()
            stat_dict['date'] = current_time.isoformat()
            logger.info(f"스탯 데이터에 날짜 추가: {stat_dict['date']}")
        else:
            # 날짜 변환
            api_date = stat_dict.get('date')
            local_time = self.convert_to_local_time(api_date)
            stat_dict['date'] = local_time.isoformat()
            logger.info(f"스탯 데이터 날짜 변환: {api_date} -> {local_time}")

        return stat_dict

    def get_cached_data(self, character_name):
        """캐시된 데이터 조회"""
        try:
            # 현재 시간에서 1시간 전 시간 계산 (서버 타임존 기준)
            one_hour_ago = timezone.now() - timedelta(hours=1)
            logger.info(f"현재 시간: {timezone.now()}, 1시간 전: {one_hour_ago}")

            # 캐릭터 이름과 시간으로 필터링하여 최신 데이터 반환
            latest_character = CharacterBasic.objects.filter(
                character_name=character_name,
                date__gte=one_hour_ago  # 서버 타임존 기준 1시간 이내 데이터만
            ).order_by('-date').first()  # 가장 최신 데이터 반환

            # 디버깅을 위한 로그 추가
            if latest_character:
                logger.info(
                    f"캐시된 데이터 찾음: {character_name}, 날짜: {latest_character.date}")
            else:
                # 시간 필터링 없이 다시 조회해보기
                any_character = CharacterBasic.objects.filter(
                    character_name=character_name
                ).order_by('-date').first()

                if any_character:
                    logger.info(
                        f"캐시된 데이터 있으나 1시간 초과: {character_name}, 날짜: {any_character.date}")
                else:
                    logger.info(f"캐시된 데이터 없음: {character_name}")

            return latest_character
        except CharacterBasic.DoesNotExist:
            logger.info(f"캐시된 데이터 조회 중 예외 발생: {character_name}")
            return None

    def save_to_database(self, character_basic, ocid, popularity_data=None, stat_data=None):
        # 날짜를 서버의 타임존으로 변환
        date_str = character_basic.date
        try:
            # 공통 메서드를 사용하여 날짜 변환
            date = self.convert_to_local_time(date_str)
            logger.info(
                f"저장 날짜 변환: {character_basic.date} -> {date} (타입: {type(date)})")
        except Exception as e:
            logger.error(f"날짜 변환 오류: {str(e)}")
            date = timezone.now()
            logger.info(f"오류로 인해 현재 시간으로 설정: {date}")

        char_basic, created = CharacterBasic.objects.update_or_create(
            ocid=ocid,
            defaults={
                'date': date,
                'character_name': character_basic.character_name,
                'world_name': character_basic.world_name,
                'character_gender': character_basic.character_gender,
                'character_class': character_basic.character_class,
                'character_class_level': character_basic.character_class_level,
                'character_level': character_basic.character_level,
                'character_exp': character_basic.character_exp,
                'character_exp_rate': character_basic.character_exp_rate,
                'character_guild_name': character_basic.character_guild_name,
                'character_image': character_basic.character_image,
                'character_date_create': character_basic.character_date_create,
                'access_flag': character_basic.access_flag,
                'liberation_quest_clear_flag': character_basic.liberation_quest_clear_flag
            }
        )

        # 인기도 데이터 저장
        if popularity_data:
            try:
                CharacterPopularity.objects.update_or_create(
                    character=char_basic,
                    date=date,
                    defaults={
                        'popularity': popularity_data.get('popularity', 0)
                    }
                )
                logger.info(
                    f"인기도 데이터 저장 완료: {popularity_data.get('popularity', 0)}")
            except Exception as e:
                logger.error(f"인기도 데이터 저장 오류: {str(e)}")

        # 스탯 데이터 저장
        if stat_data:
            try:
                stat, created = CharacterStat.objects.update_or_create(
                    character=char_basic,
                    date=date,
                    defaults={
                        'character_class': stat_data.get('character_class', ''),
                        'remain_ap': stat_data.get('remain_ap', 0)
                    }
                )

                # 스탯 상세 정보 저장
                if 'final_stat' in stat_data:
                    for stat_item in stat_data['final_stat']:
                        stat_name = None
                        stat_value = None

                        for item in stat_item:
                            if item[0] == 'stat_name':
                                stat_name = item[1]
                            elif item[0] == 'stat_value':
                                stat_value = item[1]

                        if stat_name and stat_value:
                            StatDetail.objects.update_or_create(
                                stat=stat,
                                stat_name=stat_name,
                                defaults={
                                    'stat_value': stat_value
                                }
                            )

                logger.info(f"스탯 데이터 저장 완료")
            except Exception as e:
                logger.error(f"스탯 데이터 저장 오류: {str(e)}")

        # Character 모델도 업데이트 또는 생성
        Character.objects.update_or_create(
            ocid=ocid,
            defaults={
                'character_name': character_basic.character_name,
                'world_name': character_basic.world_name,
                'character_class': character_basic.character_class,
                'character_level': character_basic.character_level
            }
        )

        return char_basic


class CharacterAbilityView(BaseAPIView):
    @swagger_auto_schema(
        operation_summary="캐릭터 어빌리티 정보 조회",
        operation_description="캐릭터의 어빌리티 정보를 조회합니다.",
        manual_parameters=[
            openapi.Parameter(
                'character_name',
                openapi.IN_QUERY,
                description="조회할 캐릭터 이름",
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'date',
                openapi.IN_QUERY,
                description="조회 기준일(YYYY-MM-DD 형식, 기본값: 오늘)",
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'force_refresh',
                openapi.IN_QUERY,
                description="캐시 무시하고 새로 조회할지 여부",
                type=openapi.TYPE_BOOLEAN,
                required=False
            ),
        ],
        responses={
            200: "성공적으로 조회됨",
            400: "잘못된 요청",
            404: "캐릭터를 찾을 수 없음",
            500: "서버 오류"
        }
    )
    def get(self, request):
        character_name = request.query_params.get('character_name')
        if not character_name:
            return Response({"error": "Character name is required"}, status=status.HTTP_400_BAD_REQUEST)
        character_name = character_name.strip()
        date = self.get_date_param(request)
        force_refresh = request.query_params.get('force_refresh', False)

        # 요청 로깅
        self.log_request("캐릭터 어빌리티 정보", character_name)

        try:
            # OCID 조회
            ocid = MapleAPIService.get_ocid(character_name)
            if not ocid:
                return Response({"error": "Character not found"}, status=status.HTTP_404_NOT_FOUND)

            character_exist = Character.objects.filter(
                character_name=character_name).exists()

            if character_exist and not force_refresh:
                character_basic = CharacterBasic.objects.filter(
                    ocid=ocid).order_by('-date').first()
                if character_basic:
                    current_time = character_basic.date

                    # 날짜 변환
                    local_time = self.convert_to_local_time(current_time)
                    logger.info(
                        f"어빌리티 데이터 날짜 변환: {current_time} -> {local_time}")

                    # 캐시된 어빌리티 데이터 확인
                    ability_data = character_basic.abilities.order_by(
                        '-date').first()
                    if ability_data:
                        return Response(self.format_response_data(
                            CharacterAbilitySerializer(ability_data).data,
                            "캐시된 어빌리티 데이터를 반환합니다."
                        ))

            # 기본 정보 조회
            character_basic, current_time = MapleAPIService.get_character_basic(
                ocid, date)

            # 날짜 변환
            local_time = self.convert_to_local_time(current_time)
            logger.info(f"어빌리티 데이터 날짜 변환: {current_time} -> {local_time}")

            # 어빌리티 API 호출
            ability_data = MapleAPIService.get_character_ability(ocid, date)
            validated_data = self.validate_data(
                CharacterAbilitySchema, ability_data)

            if date is None:
                validated_data.date = local_time

            CharacterDataManager.create_ability_data(
                validated_data, character_basic)

            return Response(self.format_response_data(
                validated_data.model_dump(),
                "캐릭터 어빌리티 정보를 성공적으로 가져왔습니다."
            ))
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CharacterItemEquipmentView(BaseAPIView):
    @swagger_auto_schema(
        operation_summary="캐릭터 장비 정보 조회",
        operation_description="캐릭터의 장착 중인 장비 정보를 조회합니다.",
        manual_parameters=[
            openapi.Parameter(
                'character_name',
                openapi.IN_QUERY,
                description="조회할 캐릭터 이름",
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'date',
                openapi.IN_QUERY,
                description="조회 기준일(YYYY-MM-DD 형식, 기본값: 오늘)",
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'force_refresh',
                openapi.IN_QUERY,
                description="캐시 무시하고 새로 조회할지 여부",
                type=openapi.TYPE_BOOLEAN,
                required=False
            ),
        ],
        responses={
            200: "성공적으로 조회됨",
            400: "잘못된 요청",
            404: "캐릭터를 찾을 수 없음",
            500: "서버 오류"
        }
    )
    def get(self, request):
        start_time = time.time()
        character_name = request.query_params.get('character_name')
        date = self.get_date_param(request)
        force_refresh = request.query_params.get('force_refresh', False)

        if not character_name:
            return Response({"error": "Character name is required"}, status=status.HTTP_400_BAD_REQUEST)

        # 요청 로깅
        self.log_request("캐릭터 장비 정보", character_name)

        try:
            # OCID 조회
            ocid = MapleAPIService.get_ocid(character_name)
            if not ocid:
                return Response({"error": "Character not found"}, status=status.HTTP_404_NOT_FOUND)

            # 기본 정보 조회
            character_basic, current_time = MapleAPIService.get_character_basic(
                ocid, date)
            print(f"기본 정보 조회 소요시간: {time.time() - start_time:.2f}초")

            # 날짜 변환
            local_time = self.convert_to_local_time(current_time)
            logger.info(f"장비 데이터 날짜 변환: {current_time} -> {local_time}")

            # 장비 정보 조회 및 처리
            equipment_data = MapleAPIService.get_character_item_equipment(
                ocid, date)
            validated_data = self.validate_data(
                CharacterItemEquipmentSchema, equipment_data)

            # 날짜 정보가 없으면 현재 시간으로 설정
            if not validated_data.date:
                validated_data.date = local_time.isoformat()
                logger.info(f"장비 데이터에 날짜 추가: {validated_data.date}")

            # 장비 데이터 저장
            character_equipment = EquipmentService.save_equipment_data(
                validated_data, character_basic, local_time)

            # 장비 데이터 로깅
            EquipmentService.log_equipment_data(character_name)

            return Response(self.format_response_data(
                validated_data.model_dump(),
                "캐릭터 장비 정보를 성공적으로 가져왔습니다."
            ))

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CharacterCashItemEquipmentView(BaseAPIView):
    @swagger_auto_schema(
        operation_summary="캐릭터 캐시 장비 정보 조회",
        operation_description="캐릭터의 장착 중인 캐시 아이템 정보를 조회합니다.",
        manual_parameters=[
            openapi.Parameter(
                'character_name',
                openapi.IN_QUERY,
                description="조회할 캐릭터 이름",
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'date',
                openapi.IN_QUERY,
                description="조회 기준일(YYYY-MM-DD 형식, 기본값: 오늘)",
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'force_refresh',
                openapi.IN_QUERY,
                description="캐시 무시하고 새로 조회할지 여부",
                type=openapi.TYPE_BOOLEAN,
                required=False
            ),
        ],
        responses={
            200: "성공적으로 조회됨",
            400: "잘못된 요청",
            404: "캐릭터를 찾을 수 없음",
            500: "서버 오류"
        }
    )
    def get(self, request):
        start_time = time.time()
        character_name = request.query_params.get('character_name')
        date = request.query_params.get('date')
        force_refresh = request.query_params.get('force_refresh', False)

        if not character_name:
            return Response({"error": "Character name is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            local_character = Character.objects.get(
                character_name=character_name)
            ocid = local_character.ocid
        except Character.DoesNotExist:
            ocid = self.get_ocid_from_api(character_name)
            if not ocid:
                return Response({"error": "Character not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            headers = {
                "accept": "application/json",
                "x-nxopen-api-key": APIKEY
            }

            # 기본 정보 조회 및 CharacterBasic 데이터 생성
            character_basic, current_time = self.get_character_basic(
                ocid, date)
            print(f"기본 정보 조회 소요시간: {time.time() - start_time:.2f}초")
            api_start = time.time()

            # 날짜 변환
            local_time = self.convert_to_local_time(current_time)
            logger.info(f"캐시 장비 데이터 날짜 변환: {current_time} -> {local_time}")

            # 캐시 장비 정보 API 호출
            cash_item_data = MapleAPIService.get_character_cashitem_equipment(
                ocid, date)
            print(f"API 호출 소요시간: {time.time() - api_start:.2f}초")

            # API 응답 데이터 로깅
            logger.info(f"캐시 장비 API 응답 데이터 키: {list(cash_item_data.keys())}")
            if 'cash_item_equipment_base' in cash_item_data and cash_item_data['cash_item_equipment_base']:
                base_sample = cash_item_data['cash_item_equipment_base'][0]
                logger.info(
                    f"cash_item_equipment_base 첫 번째 항목 키: {list(base_sample.keys())}")
                if 'cash_item_description' in base_sample:
                    logger.info(
                        f"cash_item_description 값 타입: {type(base_sample['cash_item_description'])}, 값: {base_sample['cash_item_description']}")

            # API 응답 데이터 전처리 - None 값을 빈 문자열로 대체
            def replace_none_with_empty_string(data, object_fields=["cash_item_coloring_prism"], date_fields=["date", "date_expire", "date_option_expire"]):
                if isinstance(data, dict):
                    result = {}
                    for k, v in data.items():
                        # 필드 이름 변환 (skills -> skill)
                        if k == "skills":
                            k = "skill"

                        # date 필드가 None인 경우 현재 시간으로 설정
                        if k == "date" and v is None:
                            result[k] = timezone.now().isoformat()
                        # 날짜 관련 필드나 객체 타입 필드는 None 유지
                        elif (k in date_fields and v is None) or (k in object_fields and v is None):
                            result[k] = None
                        else:
                            # 다른 필드는 재귀적으로 처리
                            result[k] = replace_none_with_empty_string(
                                v, object_fields, date_fields)
                    return result
                elif isinstance(data, list):
                    return [replace_none_with_empty_string(item, object_fields, date_fields) for item in data]
                elif data is None:
                    # 일반 필드의 None은 빈 문자열로 변환
                    return ""
                else:
                    return data

            # 데이터 전처리 적용
            processed_data = replace_none_with_empty_string(cash_item_data)
            logger.info("API 응답 데이터 전처리 완료 - None 값을 빈 문자열로 대체")

            # date 필드 확인 및 로깅
            if "date" in processed_data:
                logger.info(f"전처리 후 date 필드: {processed_data['date']}")
            else:
                # date 필드가 없으면 추가
                processed_data["date"] = timezone.now().isoformat()
                logger.info(f"date 필드 추가: {processed_data['date']}")

            validation_start = time.time()

            # 스키마로 검증
            try:
                validated_data = CharacterCashItemEquipmentSchema.model_validate(
                    processed_data)
                print(f"데이터 검증 소요시간: {time.time() - validation_start:.2f}초")
                save_start = time.time()

                # 데이터 저장 및 응답
                character_cash_equipment = CharacterCashItemEquipment.objects.create(
                    character=character_basic,
                    date=local_time,
                    character_gender=validated_data.character_gender,
                    character_class=validated_data.character_class,
                    character_look_mode=validated_data.character_look_mode,
                    preset_no=validated_data.preset_no
                )

                for item_data in validated_data.cash_item_equipment_base:
                    # CashItemEquipment 인스턴스 생성
                    cash_item = CashItemEquipment.objects.create(
                        cash_item_equipment_part=item_data.cash_item_equipment_part,
                        cash_item_equipment_slot=item_data.cash_item_equipment_slot,
                        cash_item_name=item_data.cash_item_name,
                        cash_item_icon=item_data.cash_item_icon,
                        cash_item_description=item_data.cash_item_description,
                        date_expire=item_data.date_expire,
                        date_option_expire=item_data.date_option_expire,
                        cash_item_label=item_data.cash_item_label,
                        cash_item_coloring_prism=None,  # 복잡한 객체는 별도 처리 필요
                        item_gender=item_data.item_gender
                    )

                    # 옵션 추가 (ManyToMany 필드)
                    for option_data in item_data.cash_item_option:
                        option = CashItemOption.objects.create(
                            option_type=option_data.option_type,
                            option_value=option_data.option_value
                        )
                        cash_item.cash_item_option.add(option)

                    # CharacterCashItemEquipment에 연결
                    character_cash_equipment.cash_item_equipment_base.add(
                        cash_item)

                print(f"데이터 저장 소요시간: {time.time() - save_start:.2f}초")
                print(f"전체 소요시간: {time.time() - start_time:.2f}초")

                return Response(validated_data.model_dump())
            except Exception as e:
                # 검증 오류 상세 로깅
                logger.error(f"캐시 장비 데이터 검증 오류: {str(e)}")

                # 오류 데이터 분석
                if hasattr(e, 'errors'):
                    for error in e.errors():
                        error_loc = '.'.join(str(loc) for loc in error['loc'])
                        error_msg = error['msg']
                        error_type = error['type']
                        logger.error(
                            f"필드: {error_loc}, 오류: {error_msg}, 타입: {error_type}")

                # API 응답 데이터 샘플 로깅 (민감 정보 제외)
                if cash_item_data:
                    try:
                        # 데이터 구조만 로깅
                        structure = {
                            k: type(v).__name__ for k, v in cash_item_data.items()}
                        logger.error(f"API 응답 데이터 구조: {structure}")

                        # 문제가 되는 필드 샘플 데이터 확인
                        if 'cash_item_equipment_base' in cash_item_data:
                            sample = cash_item_data['cash_item_equipment_base'][0] if cash_item_data['cash_item_equipment_base'] else {
                            }
                            logger.error(
                                f"cash_item_equipment_base 샘플: {sample}")
                    except Exception as log_error:
                        logger.error(f"응답 데이터 로깅 중 오류: {str(log_error)}")

                return Response({"error": str(e), "detail": "캐시 장비 데이터 검증 오류가 발생했습니다. 로그를 확인하세요."},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"캐시 장비 정보 조회 중 오류 발생: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CharacterSymbolView(BaseAPIView):
    @swagger_auto_schema(
        operation_summary="캐릭터 심볼 정보 조회",
        operation_description="캐릭터의 아케인 심볼 및 어센틱 심볼 정보를 조회합니다.",
        manual_parameters=[
            openapi.Parameter(
                'character_name',
                openapi.IN_QUERY,
                description="조회할 캐릭터 이름",
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'date',
                openapi.IN_QUERY,
                description="조회 기준일(YYYY-MM-DD 형식, 기본값: 오늘)",
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'force_refresh',
                openapi.IN_QUERY,
                description="캐시 무시하고 새로 조회할지 여부",
                type=openapi.TYPE_BOOLEAN,
                required=False
            ),
        ],
        responses={
            200: "성공적으로 조회됨",
            400: "잘못된 요청",
            404: "캐릭터를 찾을 수 없음",
            500: "서버 오류"
        }
    )
    def get(self, request):
        character_name = request.query_params.get('character_name')
        date = request.query_params.get('date')
        force_refresh = request.query_params.get('force_refresh', False)

        if not character_name:
            return Response({"error": "Character name is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # OCID 조회
            ocid = MapleAPIService.get_ocid(character_name)
            if not ocid:
                return Response({"error": "Character not found"}, status=status.HTTP_404_NOT_FOUND)

            # 기본 정보 조회
            character_basic, current_time = MapleAPIService.get_character_basic(
                ocid, date)

            # 날짜 변환
            local_time = self.convert_to_local_time(current_time)
            logger.info(f"심볼 데이터 날짜 변환: {current_time} -> {local_time}")

            # 심볼 정보 조회 및 처리
            symbol_data = MapleAPIService.get_character_symbol(ocid, date)

            # API 응답 데이터 로깅
            logger.info(f"심볼 API 응답 데이터 키: {list(symbol_data.keys())}")
            if 'symbol' in symbol_data:
                logger.info(f"심볼 데이터 개수: {len(symbol_data['symbol'])}")
                if symbol_data['symbol']:
                    logger.info(
                        f"첫 번째 심볼 데이터 키: {list(symbol_data['symbol'][0].keys())}")

            validated_data = self.validate_data(
                CharacterSymbolSchema, symbol_data)

            # 날짜 정보가 없으면 현재 시간으로 설정
            if not validated_data.date:
                validated_data.date = local_time.isoformat()
                logger.info(f"심볼 데이터에 날짜 추가: {validated_data.date}")

            # 데이터 저장 및 응답
            # CharacterSymbolEquipment 객체 생성
            character_symbol_equipment = CharacterSymbolEquipment.objects.create(
                character=character_basic,
                date=local_time,
                character_class=validated_data.character_class
            )

            # 심볼 데이터 저장
            for symbol_item in validated_data.symbol:
                try:
                    # Symbol 객체 생성
                    symbol = Symbol.objects.create(
                        symbol_name=symbol_item.symbol_name,
                        symbol_icon=symbol_item.symbol_icon,
                        symbol_description=symbol_item.symbol_description,
                        symbol_force=symbol_item.symbol_force,
                        symbol_level=symbol_item.symbol_level,
                        symbol_str=symbol_item.symbol_str,
                        symbol_dex=symbol_item.symbol_dex,
                        symbol_int=symbol_item.symbol_int,
                        symbol_luk=symbol_item.symbol_luk,
                        symbol_hp=symbol_item.symbol_hp,
                        symbol_drop_rate=symbol_item.symbol_drop_rate,
                        symbol_meso_rate=symbol_item.symbol_meso_rate,
                        symbol_exp_rate=symbol_item.symbol_exp_rate,
                        symbol_growth_count=symbol_item.symbol_growth_count,
                        symbol_require_growth_count=symbol_item.symbol_require_growth_count
                    )
                    # CharacterSymbolEquipment에 Symbol 추가
                    character_symbol_equipment.symbol.add(symbol)
                except Exception as e:
                    logger.error(f"심볼 데이터 저장 중 오류 발생: {str(e)}")
                    logger.error(f"문제가 발생한 심볼 데이터: {symbol_item.model_dump()}")

            return Response(self.format_response_data(
                validated_data.model_dump(),
                f"{character_name} 캐릭터의 심볼 정보를 조회했습니다."
            ))
        except Exception as e:
            logger.error(f"심볼 정보 조회 중 오류 발생: {str(e)}")
            # 오류 상세 정보 로깅
            if hasattr(e, 'errors'):
                for error in e.errors():
                    logger.error(
                        f"필드: {error['loc']}, 오류: {error['msg']}, 타입: {error['type']}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CharacterLinkSkillView(BaseAPIView):
    @swagger_auto_schema(
        operation_summary="캐릭터 링크 스킬 정보 조회",
        operation_description="캐릭터가 보유한 링크 스킬 정보를 조회합니다.",
        manual_parameters=[
            openapi.Parameter(
                'character_name',
                openapi.IN_QUERY,
                description="조회할 캐릭터 이름",
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'date',
                openapi.IN_QUERY,
                description="조회 기준일(YYYY-MM-DD 형식, 기본값: 오늘)",
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'force_refresh',
                openapi.IN_QUERY,
                description="캐시 무시하고 새로 조회할지 여부",
                type=openapi.TYPE_BOOLEAN,
                required=False
            ),
        ],
        responses={
            200: "성공적으로 조회됨",
            400: "잘못된 요청",
            404: "캐릭터를 찾을 수 없음",
            500: "서버 오류"
        }
    )
    def get(self, request):
        character_name = request.query_params.get('character_name')
        date = request.query_params.get('date')
        force_refresh = request.query_params.get('force_refresh', False)

        if not character_name:
            return Response({"error": "Character name is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # OCID 조회
            ocid = MapleAPIService.get_ocid(character_name)
            if not ocid:
                return Response({"error": "Character not found"}, status=status.HTTP_404_NOT_FOUND)

            # 기본 정보 조회
            character_basic, current_time = MapleAPIService.get_character_basic(
                ocid, date)

            # 날짜 변환
            local_time = self.convert_to_local_time(current_time)
            logger.info(f"링크 스킬 데이터 날짜 변환: {current_time} -> {local_time}")

            # 링크 스킬 API 호출
            link_skill_data = MapleAPIService.get_character_link_skill(
                ocid, date)

            # API 응답 데이터 로깅
            logger.info(f"링크 스킬 API 응답 데이터 키: {list(link_skill_data.keys())}")

            # 데이터 검증 전 필드 확인 및 초기화

            # 데이터 검증
            validated_data = CharacterLinkSkillSchema.model_validate(
                link_skill_data)

            # 날짜 정보가 없으면 현재 시간으로 설정
            if not validated_data.date:
                validated_data.date = local_time.isoformat()
                logger.info(f"링크 스킬 데이터에 날짜 추가: {validated_data.date}")

            # 데이터 저장 및 응답
            # CharacterLinkSkill 객체 생성
            character_link_skill = CharacterLinkSkill.objects.create(
                character=character_basic,
                date=local_time,
                character_class=validated_data.character_class
            )

            # character_link_skill 필드 처리 (리스트로 변경됨)
            if validated_data.character_link_skill:
                for skill_data in validated_data.character_link_skill:
                    # LinkSkill 객체 생성
                    link_skill = LinkSkill.objects.create(
                        skill_name=skill_data.skill_name,
                        skill_description=skill_data.skill_description,
                        skill_level=skill_data.skill_level,
                        skill_effect=skill_data.skill_effect,
                        skill_icon=skill_data.skill_icon
                    )
                    # character_link_skill에 추가 (첫 번째 항목만 사용)
                    if not hasattr(character_link_skill, 'character_link_skill'):
                        character_link_skill.character_link_skill = link_skill
                        character_link_skill.save()
                        break

            # 나머지 필드들도 필요에 따라 처리
            # character_link_skill_preset_2, character_link_skill_preset_3 등의 ManyToMany 필드 처리
            # character_owned_link_skill 등의 OneToOne 필드 처리

            return Response(self.format_response_data(
                validated_data.model_dump(),
                f"{character_name} 캐릭터의 링크 스킬 정보를 조회했습니다."
            ))
        except Exception as e:
            logger.error(f"링크 스킬 정보 조회 중 오류 발생: {str(e)}")
            # 오류 상세 정보 로깅
            if hasattr(e, 'errors'):
                for error in e.errors():
                    logger.error(
                        f"필드: {error['loc']}, 오류: {error['msg']}, 타입: {error['type']}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CharacterVMatrixView(BaseAPIView):
    @swagger_auto_schema(
        operation_summary="캐릭터 V매트릭스 정보 조회",
        operation_description="캐릭터의 V매트릭스 정보를 조회합니다.",
        manual_parameters=[
            openapi.Parameter(
                'character_name',
                openapi.IN_QUERY,
                description="조회할 캐릭터 이름",
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'date',
                openapi.IN_QUERY,
                description="조회 기준일(YYYY-MM-DD 형식, 기본값: 오늘)",
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'force_refresh',
                openapi.IN_QUERY,
                description="캐시 무시하고 새로 조회할지 여부",
                type=openapi.TYPE_BOOLEAN,
                required=False
            ),
        ],
        responses={
            200: "성공적으로 조회됨",
            400: "잘못된 요청",
            404: "캐릭터를 찾을 수 없음",
            500: "서버 오류"
        }
    )
    def get(self, request):
        character_name = request.query_params.get('character_name')
        date = request.query_params.get('date')
        force_refresh = request.query_params.get('force_refresh', False)

        if not character_name:
            return Response({"error": "Character name is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # OCID 조회
            ocid = MapleAPIService.get_ocid(character_name)
            if not ocid:
                return Response({"error": "Character not found"}, status=status.HTTP_404_NOT_FOUND)

            # 기본 정보 조회
            character_basic, current_time = MapleAPIService.get_character_basic(
                ocid, date)

            # 날짜 변환
            local_time = self.convert_to_local_time(current_time)
            logger.info(f"V매트릭스 데이터 날짜 변환: {current_time} -> {local_time}")

            # V매트릭스 API 호출 (5차 스킬)
            skill_data = MapleAPIService.get_character_skill(ocid, "5", date)

            # API 응답 데이터 로깅
            logger.info(f"V매트릭스 API 응답 데이터 키: {list(skill_data.keys())}")

            # API 응답 데이터 변환
            # character_skill 필드의 데이터를 character_v_core_equipment 형식으로 변환
            v_cores = []
            if 'character_skill' in skill_data and skill_data['character_skill']:
                for skill in skill_data['character_skill']:
                    v_core = {
                        'slot_id': str(len(v_cores) + 1),  # 임시 ID 생성
                        'slot_level': skill.get('skill_level', 1),
                        'v_core_name': skill.get('skill_name', ''),
                        'v_core_type': 'SKILL',  # 기본값
                        'v_core_level': skill.get('skill_level', 1),
                        'v_core_skill_1': skill.get('skill_name', ''),
                        'v_core_skill_2': None,
                        'v_core_skill_3': None
                    }
                    v_cores.append(v_core)

                # 변환된 데이터 추가
                skill_data['character_v_core_equipment'] = v_cores
                # 기본값
                skill_data['character_v_matrix_remain_slot_upgrade_point'] = 0

            # 데이터 검증
            validated_data = CharacterVMatrixSchema.model_validate(skill_data)

            # 날짜 정보가 없으면 현재 시간으로 설정
            if not validated_data.date:
                validated_data.date = local_time.isoformat()
                logger.info(f"V매트릭스 데이터에 날짜 추가: {validated_data.date}")

            # 데이터 저장 및 응답
            # CharacterVMatrix 객체 생성
            character_v_matrix = CharacterVMatrix.objects.create(
                character=character_basic,
                date=local_time,
                character_class=validated_data.character_class,
                character_v_matrix_remain_slot_upgrade_point=validated_data.character_v_matrix_remain_slot_upgrade_point
            )

            # v_core 데이터 저장
            for core_data in validated_data.character_v_core_equipment:
                v_core = VCore.objects.create(
                    slot_id=core_data.slot_id,
                    slot_level=core_data.slot_level,
                    v_core_name=core_data.v_core_name,
                    v_core_type=core_data.v_core_type,
                    v_core_level=core_data.v_core_level,
                    v_core_skill_1=core_data.v_core_skill_1,
                    v_core_skill_2=core_data.v_core_skill_2,
                    v_core_skill_3=core_data.v_core_skill_3
                )
                character_v_matrix.character_v_core_equipment.add(v_core)

            return Response(self.format_response_data(
                validated_data.model_dump(),
                f"{character_name} 캐릭터의 V매트릭스 정보를 조회했습니다."
            ))
        except Exception as e:
            logger.error(f"V매트릭스 정보 조회 중 오류 발생: {str(e)}")
            # 오류 상세 정보 로깅
            if hasattr(e, 'errors'):
                for error in e.errors():
                    logger.error(
                        f"필드: {error['loc']}, 오류: {error['msg']}, 타입: {error['type']}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CharacterHexaMatrixView(BaseAPIView):
    @swagger_auto_schema(
        operation_summary="캐릭터 HEXA 매트릭스 정보 조회",
        operation_description="캐릭터의 HEXA 매트릭스 정보를 조회합니다.",
        manual_parameters=[
            openapi.Parameter(
                'character_name',
                openapi.IN_QUERY,
                description="조회할 캐릭터 이름",
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'date',
                openapi.IN_QUERY,
                description="조회 기준일(YYYY-MM-DD 형식, 기본값: 오늘)",
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'force_refresh',
                openapi.IN_QUERY,
                description="캐시 무시하고 새로 조회할지 여부",
                type=openapi.TYPE_BOOLEAN,
                required=False
            ),
        ],
        responses={
            200: "성공적으로 조회됨",
            400: "잘못된 요청",
            404: "캐릭터를 찾을 수 없음",
            500: "서버 오류"
        }
    )
    def get(self, request):
        character_name = request.query_params.get('character_name')
        date = request.query_params.get('date')
        force_refresh = request.query_params.get('force_refresh', False)

        if not character_name:
            return Response({"error": "Character name is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # OCID 조회
            ocid = MapleAPIService.get_ocid(character_name)
            if not ocid:
                return Response({"error": "Character not found"}, status=status.HTTP_404_NOT_FOUND)

            # 기본 정보 조회
            character_basic, current_time = MapleAPIService.get_character_basic(
                ocid, date)

            # 날짜 변환
            local_time = self.convert_to_local_time(current_time)
            logger.info(f"HEXA 매트릭스 데이터 날짜 변환: {current_time} -> {local_time}")

            # HEXA 매트릭스 API 호출
            hexa_data = MapleAPIService.get_character_hexamatrix(ocid, date)
            validated_data = CharacterHexaMatrixSchema.model_validate(
                hexa_data)

            # 날짜 정보가 없으면 현재 시간으로 설정
            if not validated_data.date:
                validated_data.date = local_time.isoformat()
                logger.info(f"HEXA 매트릭스 데이터에 날짜 추가: {validated_data.date}")

            # 데이터 저장 및 응답
            # CharacterHexaMatrix 객체 생성
            character_hexa_matrix = CharacterHexaMatrix.objects.create(
                character=character_basic,
                date=local_time
            )

            # hexa_core_equipment 처리
            for core_data in validated_data.character_hexa_core_equipment:
                # HexaCore 객체 생성
                hexa_core = HexaCore.objects.create(
                    hexa_core_name=core_data.hexa_core_name,
                    hexa_core_level=core_data.hexa_core_level,
                    hexa_core_type=core_data.hexa_core_type
                )

                # linked_skill 관계 설정
                for skill_data in core_data.linked_skill:
                    # HexaSkill 객체 생성 또는 조회
                    hexa_skill, _ = HexaSkill.objects.get_or_create(
                        hexa_skill_id=skill_data.hexa_skill_id
                    )
                    # ManyToMany 관계 추가
                    hexa_core.linked_skill.add(hexa_skill)

                # CharacterHexaMatrix에 HexaCore 추가
                character_hexa_matrix.character_hexa_core_equipment.add(
                    hexa_core)

            return Response(self.format_response_data(
                validated_data.model_dump(),
                f"{character_name} 캐릭터의 HEXA 매트릭스 정보를 조회했습니다."
            ))
        except Exception as e:
            logger.error(f"HEXA 매트릭스 정보 조회 중 오류 발생: {str(e)}")
            # 오류 상세 정보 로깅
            if hasattr(e, 'errors'):
                for error in e.errors():
                    logger.error(
                        f"필드: {error['loc']}, 오류: {error['msg']}, 타입: {error['type']}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CharacterHexaStatView(BaseAPIView):
    @swagger_auto_schema(
        operation_summary="캐릭터 HEXA 스탯 정보 조회",
        operation_description="캐릭터의 HEXA 스탯 정보를 조회합니다.",
        manual_parameters=[
            openapi.Parameter(
                'character_name',
                openapi.IN_QUERY,
                description="조회할 캐릭터 이름",
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'date',
                openapi.IN_QUERY,
                description="조회 기준일(YYYY-MM-DD 형식, 기본값: 오늘)",
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'force_refresh',
                openapi.IN_QUERY,
                description="캐시 무시하고 새로 조회할지 여부",
                type=openapi.TYPE_BOOLEAN,
                required=False
            ),
        ],
        responses={
            200: "성공적으로 조회됨",
            400: "잘못된 요청",
            404: "캐릭터를 찾을 수 없음",
            500: "서버 오류"
        }
    )
    def get(self, request):
        character_name = request.query_params.get('character_name')
        date = self.get_date_param(request)
        force_refresh = request.query_params.get(
            'force_refresh', False) == 'true'

        if not character_name:
            return Response({"error": "Character name is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 공통 데이터 조회
            character_name, ocid, date = self.get_character_data(request)

            # 캐시된 데이터 확인 (force_refresh가 true가 아닐 경우)
            if not force_refresh:
                cached_data = self.get_cached_data(character_name)
                if cached_data:
                    # 캐시된 HEXA 스탯 데이터 확인
                    hexa_stat_data = cached_data.hexa_stats.order_by(
                        '-date').first()
                    if hexa_stat_data:
                        # 데이터 직렬화
                        serialized_data = self.serialize_hexa_stat_data(
                            hexa_stat_data)
                        return Response(self.format_response_data(
                            serialized_data,
                            "캐시된 HEXA 스탯 데이터를 반환합니다."
                        ))

            # 기본 정보 조회
            character_basic, current_time = MapleAPIService.get_character_basic(
                ocid, date)

            # 날짜 변환
            local_time = self.convert_to_local_time(current_time)
            logger.info(f"HEXA 스탯 데이터 날짜 변환: {current_time} -> {local_time}")

            # HEXA 스탯 API 호출
            hexa_stat_data = MapleAPIService.get_character_hexamatrix_stat(
                ocid, date)
            validated_data = CharacterHexaStatSchema.model_validate(
                hexa_stat_data)

            # 날짜 정보가 없으면 현재 시간으로 설정
            if not validated_data.date:
                validated_data.date = local_time.isoformat()
                logger.info(f"HEXA 스탯 데이터에 날짜 추가: {validated_data.date}")

            # 데이터 저장 및 응답
            hexa_stats = []

            # CharacterHexaMatrixStat 모델 생성
            stat = CharacterHexaMatrixStat.objects.create(
                character=character_basic,
                date=local_time,
                character_class=validated_data.character_class
            )
            hexa_stats.append(stat)

            # character_hexa_stat_core 처리
            for stat_data in validated_data.character_hexa_stat_core:
                hexa_stat_core = HexaStatCore.objects.create(
                    slot_id=stat_data.slot_id,
                    main_stat_name=stat_data.main_stat_name,
                    sub_stat_name_1=stat_data.sub_stat_name_1,
                    sub_stat_name_2=stat_data.sub_stat_name_2,
                    main_stat_level=stat_data.main_stat_level,
                    sub_stat_level_1=stat_data.sub_stat_level_1,
                    sub_stat_level_2=stat_data.sub_stat_level_2,
                    stat_grade=stat_data.stat_grade
                )
                stat.character_hexa_stat_core.add(hexa_stat_core)

            # character_hexa_stat_core_2 처리
            for stat_data in validated_data.character_hexa_stat_core_2:
                hexa_stat_core = HexaStatCore.objects.create(
                    slot_id=stat_data.slot_id,
                    main_stat_name=stat_data.main_stat_name,
                    sub_stat_name_1=stat_data.sub_stat_name_1,
                    sub_stat_name_2=stat_data.sub_stat_name_2,
                    main_stat_level=stat_data.main_stat_level,
                    sub_stat_level_1=stat_data.sub_stat_level_1,
                    sub_stat_level_2=stat_data.sub_stat_level_2,
                    stat_grade=stat_data.stat_grade
                )
                stat.character_hexa_stat_core_2.add(hexa_stat_core)

            # preset_hexa_stat_core 처리
            for stat_data in validated_data.preset_hexa_stat_core:
                hexa_stat_core = HexaStatCore.objects.create(
                    slot_id=stat_data.slot_id,
                    main_stat_name=stat_data.main_stat_name,
                    sub_stat_name_1=stat_data.sub_stat_name_1,
                    sub_stat_name_2=stat_data.sub_stat_name_2,
                    main_stat_level=stat_data.main_stat_level,
                    sub_stat_level_1=stat_data.sub_stat_level_1,
                    sub_stat_level_2=stat_data.sub_stat_level_2,
                    stat_grade=stat_data.stat_grade
                )
                stat.preset_hexa_stat_core.add(hexa_stat_core)

            # preset_hexa_stat_core_2 처리
            for stat_data in validated_data.preset_hexa_stat_core_2:
                hexa_stat_core = HexaStatCore.objects.create(
                    slot_id=stat_data.slot_id,
                    main_stat_name=stat_data.main_stat_name,
                    sub_stat_name_1=stat_data.sub_stat_name_1,
                    sub_stat_name_2=stat_data.sub_stat_name_2,
                    main_stat_level=stat_data.main_stat_level,
                    sub_stat_level_1=stat_data.sub_stat_level_1,
                    sub_stat_level_2=stat_data.sub_stat_level_2,
                    stat_grade=stat_data.stat_grade
                )
                stat.preset_hexa_stat_core_2.add(hexa_stat_core)

            return Response(self.format_response_data(
                validated_data.model_dump(),
                f"{character_name} 캐릭터의 HEXA 스탯 정보를 조회했습니다."
            ))
        except (InvalidParameterError, CharacterNotFoundError) as e:
            logger.warning(f"캐릭터 HEXA 스탯 정보 조회 실패: {e.message}")
            return Response(
                {"error": e.message, "detail": e.detail if hasattr(
                    e, 'detail') else None},
                status=e.status_code
            )
        except Exception as e:
            logger.error(f"예상치 못한 오류: {str(e)}")
            return Response(
                {"error": "서버에서 예상치 못한 오류가 발생했습니다.", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def get_cached_data(self, character_name):
        """캐시된 데이터 조회"""
        try:
            # 현재 시간에서 1시간 전 시간 계산 (서버 타임존 기준)
            one_hour_ago = timezone.now() - timedelta(hours=1)
            logger.info(f"현재 시간: {timezone.now()}, 1시간 전: {one_hour_ago}")

            # 캐릭터 이름과 시간으로 필터링하여 최신 데이터 반환
            latest_character = CharacterBasic.objects.filter(
                character_name=character_name,
                date__gte=one_hour_ago  # 서버 타임존 기준 1시간 이내 데이터만
            ).order_by('-date').first()  # 가장 최신 데이터 반환

            # 디버깅을 위한 로그 추가
            if latest_character:
                logger.info(
                    f"캐시된 데이터 찾음: {character_name}, 날짜: {latest_character.date}")
            else:
                # 시간 필터링 없이 다시 조회해보기
                any_character = CharacterBasic.objects.filter(
                    character_name=character_name
                ).order_by('-date').first()

                if any_character:
                    logger.info(
                        f"캐시된 데이터 있으나 1시간 초과: {character_name}, 날짜: {any_character.date}")
                else:
                    logger.info(f"캐시된 데이터 없음: {character_name}")

            return latest_character
        except CharacterBasic.DoesNotExist:
            logger.info(f"캐시된 데이터 조회 중 예외 발생: {character_name}")
            return None

    def serialize_hexa_stat_data(self, hexa_stat_data):
        """HEXA 스탯 데이터 직렬화"""
        result = {
            "date": hexa_stat_data.date.isoformat() if hexa_stat_data.date else None,
            "character_class": hexa_stat_data.character_class,
            "character_hexa_stat_core": [],
            "character_hexa_stat_core_2": [],
            "preset_hexa_stat_core": [],
            "preset_hexa_stat_core_2": []
        }

        # character_hexa_stat_core 직렬화
        for core in hexa_stat_data.character_hexa_stat_core.all():
            result["character_hexa_stat_core"].append({
                "slot_id": core.slot_id,
                "main_stat_name": core.main_stat_name,
                "sub_stat_name_1": core.sub_stat_name_1,
                "sub_stat_name_2": core.sub_stat_name_2,
                "main_stat_level": core.main_stat_level,
                "sub_stat_level_1": core.sub_stat_level_1,
                "sub_stat_level_2": core.sub_stat_level_2,
                "stat_grade": core.stat_grade
            })

        # character_hexa_stat_core_2 직렬화
        for core in hexa_stat_data.character_hexa_stat_core_2.all():
            result["character_hexa_stat_core_2"].append({
                "slot_id": core.slot_id,
                "main_stat_name": core.main_stat_name,
                "sub_stat_name_1": core.sub_stat_name_1,
                "sub_stat_name_2": core.sub_stat_name_2,
                "main_stat_level": core.main_stat_level,
                "sub_stat_level_1": core.sub_stat_level_1,
                "sub_stat_level_2": core.sub_stat_level_2,
                "stat_grade": core.stat_grade
            })

        # preset_hexa_stat_core 직렬화
        for core in hexa_stat_data.preset_hexa_stat_core.all():
            result["preset_hexa_stat_core"].append({
                "slot_id": core.slot_id,
                "main_stat_name": core.main_stat_name,
                "sub_stat_name_1": core.sub_stat_name_1,
                "sub_stat_name_2": core.sub_stat_name_2,
                "main_stat_level": core.main_stat_level,
                "sub_stat_level_1": core.sub_stat_level_1,
                "sub_stat_level_2": core.sub_stat_level_2,
                "stat_grade": core.stat_grade
            })

        # preset_hexa_stat_core_2 직렬화
        for core in hexa_stat_data.preset_hexa_stat_core_2.all():
            result["preset_hexa_stat_core_2"].append({
                "slot_id": core.slot_id,
                "main_stat_name": core.main_stat_name,
                "sub_stat_name_1": core.sub_stat_name_1,
                "sub_stat_name_2": core.sub_stat_name_2,
                "main_stat_level": core.main_stat_level,
                "sub_stat_level_1": core.sub_stat_level_1,
                "sub_stat_level_2": core.sub_stat_level_2,
                "stat_grade": core.stat_grade
            })

        return result
