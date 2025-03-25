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
from util.rate_limiter import rate_limited
from util.redis_client import redis_client

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
    CharacterSymbolSchema, CharacterLinkSkillSchema, CharacterSkillSchema,
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
    CharacterSetEffectSerializer, CharacterSkillSerializer, CharacterStatSerializer, CharacterSymbolEquipmentSerializer, CharacterVMatrixSerializer
)

logger = logging.getLogger('maple_api')


class BaseCharacterView(MapleAPIClientMixin, APIViewMixin, CharacterDataMixin):
    model_class = None
    related_name = None
    schema_class = None  # Pydantic 스키마 클래스

    def validate_data(self, data):
        """API 응답 데이터를 Pydantic 스키마로 검증"""
        if not self.schema_class:
            return data

        try:
            validated_data = self.schema_class(**data)
            logger.info(f"{self.model_class.__name__} 데이터 검증 성공")
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
            if self.model_class != CharacterBasic:
                if not ocid:
                    logger.error("OCID가 필요한 모델에 OCID가 제공되지 않았습니다.")
                    return

                try:
                    character = CharacterBasic.objects.get(ocid=ocid)
                    defaults['character'] = character
                except CharacterBasic.DoesNotExist:
                    logger.error(
                        f"CharacterBasic 모델에서 OCID {ocid}를 찾을 수 없습니다.")
                    return

            # 모델별 특수 처리
            if self.model_class == CharacterBasic:
                # 기존 캐릭터 조회
                try:
                    character = self.model_class.objects.get(
                        ocid=validated_data.get('ocid') or ocid)
                except self.model_class.DoesNotExist:
                    character = None

                # 기본 정보 업데이트 또는 생성
                basic_defaults = {
                    'character_name': validated_data.get('character_name'),
                    'world_name': validated_data.get('world_name'),
                    'character_gender': validated_data.get('character_gender'),
                    'character_class': validated_data.get('character_class'),
                }

                if character:
                    for key, value in basic_defaults.items():
                        setattr(character, key, value)
                    character.save()
                else:
                    character = self.model_class.objects.create(
                        ocid=validated_data.get('ocid') or ocid,
                        **basic_defaults
                    )

                # 히스토리 저장
                history_data = {
                    # date가 없으면 현재 시간 사용
                    'date': validated_data.get('date') or timezone.now(),
                    'character_name': validated_data.get('character_name'),
                    'character_class': validated_data.get('character_class'),
                    'character_class_level': validated_data.get('character_class_level'),
                    'character_level': validated_data.get('character_level'),
                    'character_exp': validated_data.get('character_exp'),
                    'character_exp_rate': validated_data.get('character_exp_rate'),
                    'character_image': validated_data.get('character_image'),
                    'character_date_create': validated_data.get('character_date_create'),
                    'access_flag': True if validated_data.get('access_flag') == 'true' else False,
                    'liberation_quest_clear_flag': True if validated_data.get('liberation_quest_clear_flag') == 'true' else False,
                }
                try:
                    history_obj = CharacterBasicHistory.objects.create(
                        character=character, **history_data)
                except Exception as e:
                    logger.error(
                        f"CharacterBasicHistory 모델 생성 중 오류 발생: {str(e)}")
                    return
                return character

            elif self.model_class == CharacterPopularity:
                defaults.update({
                    'popularity': validated_data.get('popularity')
                })
                obj, created = self.model_class.objects.update_or_create(
                    character=defaults['character'],
                    date=defaults['date'],
                    defaults=defaults
                )

            elif self.model_class == CharacterAbility:
                # 기본 어빌리티 정보 저장
                defaults.update({
                    'ability_grade': validated_data.get('ability_grade'),
                    'remain_fame': validated_data.get('remain_fame'),
                    'preset_no': validated_data.get('preset_no', 1)
                })

                # 프리셋 처리 함수
                def create_ability_preset(preset_data):
                    if not preset_data:
                        return None

                    preset = AbilityPreset.objects.create(
                        ability_preset_grade=preset_data.get(
                            'ability_preset_grade', '')
                    )

                    if 'ability_info' in preset_data:
                        for ability in preset_data['ability_info']:
                            ability_obj = AbilityInfo.objects.create(
                                ability_no=ability.get('ability_no'),
                                ability_grade=ability.get('ability_grade'),
                                ability_value=ability.get('ability_value')
                            )
                            preset.ability_info.add(ability_obj)

                    return preset

                # 프리셋 1, 2, 3 먼저 생성
                presets = {}
                for i in range(1, 4):
                    preset_key = f'ability_preset_{i}'
                    if preset_key in validated_data:
                        presets[preset_key] = create_ability_preset(
                            validated_data[preset_key])
                    else:
                        # 프리셋이 없는 경우 빈 프리셋 생성
                        presets[preset_key] = AbilityPreset.objects.create(
                            ability_preset_grade='일반'
                        )

                # 모든 프리셋을 포함하여 CharacterAbility 객체 생성/업데이트
                defaults.update({
                    'ability_preset_1': presets['ability_preset_1'],
                    'ability_preset_2': presets['ability_preset_2'],
                    'ability_preset_3': presets['ability_preset_3']
                })

                obj, created = self.model_class.objects.update_or_create(
                    character=defaults['character'],
                    date=defaults['date'],
                    defaults=defaults
                )

                # 기본 어빌리티 정보 처리
                if 'ability_info' in validated_data:
                    obj.ability_info.clear()
                    for ability in validated_data['ability_info']:
                        ability_obj = AbilityInfo.objects.create(
                            ability_no=ability.get('ability_no'),
                            ability_grade=ability.get('ability_grade'),
                            ability_value=ability.get('ability_value')
                        )
                        obj.ability_info.add(ability_obj)

                obj.save()

            elif self.model_class == AndroidEquipment:
                try:

                    if validated_data:
                        # 안드로이드 기본 정보로 AndroidEquipment 생성
                        android = AndroidEquipment.objects.create(
                            character=defaults['character'],
                            date=defaults['date'],
                            android_name=validated_data.get(
                                'android_name', ''),
                            android_nickname=validated_data.get(
                                'android_nickname', ''),
                            android_icon=validated_data.get(
                                'android_icon', ''),
                            android_description=validated_data.get(
                                'android_description'),
                            android_gender=validated_data.get(
                                'android_gender'),
                            android_grade=validated_data.get('android_grade'),
                            android_non_humanoid_flag=validated_data.get(
                                'android_non_humanoid_flag'),
                            android_shop_usable_flag=validated_data.get(
                                'android_shop_usable_flag'),
                            preset_no=validated_data.get('preset_no'),

                        )

                        # 안드로이드 헤어/페이스 처리
                        if validated_data.get('android_hair'):
                            hair = Hair.objects.create(
                                **validated_data['android_hair'])
                            android.android_hair = hair

                        if validated_data.get('android_face'):
                            face = Face.objects.create(
                                **validated_data['android_face'])
                            android.android_face = face

                        if validated_data.get('android_skin'):
                            skin = Skin.objects.create(
                                **validated_data['android_skin'])
                            android.android_skin = skin

                        # 안드로이드 캐시 장비 처리
                        if validated_data.get('android_cash_item_equipment'):
                            cash_items = []
                            for item_data in validated_data['android_cash_item_equipment']:
                                # 캐시 아이템 옵션 처리
                                cash_item_option_data = item_data.pop(
                                    'cash_item_option', None)
                                # android_item_gender 삭제
                                item_data.pop('android_item_gender', None)
                                item = CashItemEquipment.objects.create(
                                    **item_data)

                                # 캐시 아이템 옵션 설정
                                if cash_item_option_data:
                                    cash_item_option = CashItemOption.objects.create(
                                        **cash_item_option_data)
                                    item.cash_item_option.add(cash_item_option)

                                cash_items.append(item)

                            android.android_cash_item_equipment.add(
                                *cash_items)

                        # 프리셋 처리는 별도의 안드로이드 객체로 생성
                        presets = {}
                        for i in range(1, 4):
                            preset_key = f'android_preset_{i}'
                            if preset_key in validated_data and validated_data[preset_key]:
                                preset_data = validated_data[preset_key]
                                preset_android = AndroidEquipmentPreset.objects.create(
                                    android_name=preset_data.get(
                                        'android_name', ''),
                                    android_nickname=preset_data.get(
                                        'android_nickname', ''),
                                    android_icon=preset_data.get(
                                        'android_icon', ''),
                                    android_description=preset_data.get(
                                        'android_description'),
                                    android_grade=preset_data.get(
                                        'android_grade'),
                                    android_gender=preset_data.get(
                                        'android_gender'),
                                    android_non_humanoid_flag=preset_data.get(
                                        'android_non_humanoid_flag'),
                                    android_shop_usable_flag=preset_data.get(
                                        'android_shop_usable_flag'),
                                )

                                # 프리셋 헤어/페이스 처리
                                if preset_data.get('android_hair'):
                                    hair = Hair.objects.create(
                                        **preset_data['android_hair'])
                                    preset_android.android_hair = hair

                                if preset_data.get('android_face'):
                                    face = Face.objects.create(
                                        **preset_data['android_face'])
                                    preset_android.android_face = face

                                if preset_data.get('android_skin'):
                                    skin = Skin.objects.create(
                                        **preset_data['android_skin'])
                                    preset_android.android_skin = skin

                                # 프리셋 캐시 장비 처리
                                if preset_data.get('android_cash_item_equipment'):
                                    cash_items = []
                                    for item_data in preset_data['android_cash_item_equipment']:
                                        # 캐시 아이템 옵션 처리
                                        cash_item_option_data = item_data.pop(
                                            'cash_item_option', None)
                                        item = CashItemEquipment.objects.create(
                                            **item_data)

                                        # 캐시 아이템 옵션 설정
                                        if cash_item_option_data:
                                            cash_item_option = CashItemOption.objects.create(
                                                **cash_item_option_data)
                                            item.cash_item_option.add(
                                                cash_item_option)

                                        cash_items.append(item)

                                    preset_android.android_cash_item_equipment.add(
                                        *cash_items)

                                preset_android.save()
                                presets[preset_key] = preset_android

                        # android에 preset 추가
                        for preset_key, preset in presets.items():
                            setattr(android, preset_key, preset)

                        android.save()
                        logger.info(
                            f"{self.model_class.__name__} 데이터 저장 완료: 생성됨")
                        return android
                    return None
                except Exception as e:
                    logger.error(f"안드로이드 데이터 저장 중 오류 발생: {str(e)}")
                    raise

            else:
                obj = self.model_class.create_from_data(
                    character, validated_data)
                if obj:
                    created = True

            logger.info(
                f"{self.model_class.__name__} 데이터 저장 완료: {'생성됨' if created else '업데이트됨'}")
            return obj

        except Exception as e:
            logger.error(f"데이터베이스 저장 중 오류 발생: {str(e)}")
            return None

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
                return Response(self.format_response_data(serializer.data))

            return Response(self.format_response_data(data))
        except Exception as e:
            return self.handle_exception(e)


class CharacterIdView(BaseCharacterView):
    model_class = CharacterId
    api_url = CHARACTER_ID_URL

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
        char_name = request.query_params.get('character_name')
        if not char_name:
            return Response({'error': '캐릭터 이름이 필요합니다.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # OCID 조회
            data = self.get_api_data(
                CHARACTER_ID_URL, {'character_name': char_name})
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

            return Response(self.format_response_data(data))
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
            self.serializer_class
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
    def get(self, request, ocid):
        try:
            # API 엔드포인트와 뷰 클래스 매핑
            api_endpoints = {
                CHARACTER_BASIC_URL: ('basic', CharacterBasicView),
                CHARACTER_POPULARITY_URL: ('popularity', CharacterPopularityView),
                CHARACTER_STAT_URL: ('stat', CharacterStatView),
                CHARACTER_ABILITY_URL: ('ability', CharacterAbilityView),
                CHARACTER_ITEM_EQUIPMENT_URL: ('item_equipment', CharacterItemEquipmentView),
                CHARACTER_CASHITEM_EQUIPMENT_URL: ('cashitem_equipment', CharacterCashItemEquipmentView),
                CHARACTER_SYMBOL_URL: ('symbol', CharacterSymbolView),
                CHARACTER_LINK_SKILL_URL: ('link_skill', CharacterLinkSkillView),
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

            all_data = {}

            @rate_limited(max_calls=500)
            async def fetch_api_data(session, url, params):
                try:
                    headers = {'x-nxopen-api-key': APIKEY}
                    async with session.get(url, params=params, headers=headers) as response:
                        return url, await response.json()
                except Exception as e:
                    logger.error(f"API 호출 실패 ({url}): {str(e)}")
                    return url, None

            async def fetch_all_data():
                async with aiohttp.ClientSession() as session:
                    urls = list(api_endpoints.keys())
                    semaphore = asyncio.Semaphore(20)  # 동시에 최대 20개의 요청만 허용

                    async def fetch_with_semaphore(url):
                        async with semaphore:  # 세마포어로 동시 실행 제한
                            return await fetch_api_data(session, url, {'ocid': ocid})

                    tasks = [fetch_with_semaphore(url) for url in urls]
                    return await asyncio.gather(*tasks)

            # 비동기 호출 실행
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            results = loop.run_until_complete(fetch_all_data())
            loop.close()

            now = timezone.now()
            # 결과 처리 및 데이터베이스 저장
            for url, result in results:
                if result:
                    if result.get('date') is None:
                        result['date'] = now
                    endpoint_name, view_class = api_endpoints[url]
                    validated_data = self.validate_and_save_data(
                        endpoint_name, result, ocid, view_class)
                    if validated_data:
                        all_data[endpoint_name] = validated_data

            return Response(all_data)

        except Exception as e:
            logger.error(f"전체 데이터 조회 중 오류 발생: {str(e)}")
            return Response(
                {'error': f'데이터 조회 중 오류가 발생했습니다: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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
