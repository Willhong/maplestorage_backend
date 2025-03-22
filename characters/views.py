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

logger = logging.getLogger('maple_api')


class BaseCharacterView(MapleAPIClientMixin, APIViewMixin, CharacterDataMixin):
    model_class = None
    related_name = None

    def save_to_database(self, data, ocid=None):
        """데이터베이스에 API 응답 데이터 저장"""
        try:
            if not self.model_class:
                return

            # 기본 데이터 준비
            defaults = {
                'date': data.get('date') or timezone.now(),
            }
            # CharacterId 모델인 경우, ocid 필드 업데이트
            if self.model_class == CharacterId:
                defaults['ocid'] = data.get('ocid')
                obj, created = self.model_class.objects.update_or_create(
                    ocid=data.get('ocid'),
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
                        ocid=data.get('ocid') or ocid)
                except self.model_class.DoesNotExist:
                    character = None

                # 기본 정보 업데이트 또는 생성
                basic_defaults = {
                    'character_name': data.get('character_name'),
                    'world_name': data.get('world_name'),
                    'character_gender': data.get('character_gender'),
                    'character_class': data.get('character_class'),
                }

                if character:
                    for key, value in basic_defaults.items():
                        setattr(character, key, value)
                    character.save()
                else:
                    character = self.model_class.objects.create(
                        ocid=data.get('ocid') or ocid,
                        **basic_defaults
                    )

                # 히스토리 저장
                history_data = {
                    # date가 없으면 현재 시간 사용
                    'date': data.get('date') or timezone.now(),
                    'character_name': data.get('character_name'),
                    'character_class': data.get('character_class'),
                    'character_class_level': data.get('character_class_level'),
                    'character_level': data.get('character_level'),
                    'character_exp': data.get('character_exp'),
                    'character_exp_rate': data.get('character_exp_rate'),
                    'character_image': data.get('character_image'),
                    'character_date_create': data.get('character_date_create'),
                    'access_flag': True if data.get('access_flag') == 'true' else False,
                    'liberation_quest_clear_flag': True if data.get('liberation_quest_clear_flag') == 'true' else False,
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
                    'popularity': data.get('popularity')
                })
                obj, created = self.model_class.objects.update_or_create(
                    character=defaults['character'],
                    date=defaults['date'],
                    defaults=defaults
                )

            elif self.model_class == CharacterStat:
                defaults.update({
                    'character_class': data.get('character_class'),
                    'remain_ap': data.get('remain_ap', 0)
                })
                obj, created = self.model_class.objects.update_or_create(
                    character=defaults['character'],
                    date=defaults['date'],
                    defaults=defaults
                )

                # StatDetail 처리
                if 'final_stat' in data:
                    for stat in data['final_stat']:
                        obj.final_stat.create(
                            stat_name=stat.get('stat_name'),
                            stat_value=stat.get('stat_value')
                        )

            elif self.model_class == CharacterAbility:
                # 기본 어빌리티 정보 저장
                defaults.update({
                    'ability_grade': data.get('ability_grade'),
                    'remain_fame': data.get('remain_fame'),
                    'preset_no': data.get('preset_no', 1)
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
                    if preset_key in data:
                        presets[preset_key] = create_ability_preset(
                            data[preset_key])
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
                if 'ability_info' in data:
                    obj.ability_info.clear()
                    for ability in data['ability_info']:
                        ability_obj = AbilityInfo.objects.create(
                            ability_no=ability.get('ability_no'),
                            ability_grade=ability.get('ability_grade'),
                            ability_value=ability.get('ability_value')
                        )
                        obj.ability_info.add(ability_obj)

                obj.save()

            elif self.model_class == CharacterHexaMatrix:
                character_hexa_matrix, created = CharacterHexaMatrix.objects.get_or_create(
                    character=character,
                    date=data.get('date')
                )

                # 헥사 코어 장비 처리
                if 'character_hexa_core_equipment' in data:
                    character_hexa_matrix.character_hexa_core_equipment.clear()  # 기존 데이터 삭제
                    for core_data in data['character_hexa_core_equipment']:
                        hexa_core = HexaCore.create_from_data(core_data)
                        character_hexa_matrix.character_hexa_core_equipment.add(
                            hexa_core)

                obj = character_hexa_matrix

            elif self.model_class == CharacterHexaMatrixStat:
                character_hexa_matrix_stat, created = CharacterHexaMatrixStat.objects.get_or_create(
                    character=character,
                    date=data.get('date'),
                    defaults={'character_class': data.get('character_class')}
                )

                # 헥사 스탯 코어 처리 함수
                def process_hexa_stat_cores(core_list):
                    cores = []
                    for core_data in core_list:
                        core = HexaStatCore.objects.create(
                            slot_id=core_data.get('slot_id'),
                            main_stat_name=core_data.get('main_stat_name'),
                            sub_stat_name_1=core_data.get('sub_stat_name_1'),
                            sub_stat_name_2=core_data.get('sub_stat_name_2'),
                            main_stat_level=core_data.get('main_stat_level'),
                            sub_stat_level_1=core_data.get('sub_stat_level_1'),
                            sub_stat_level_2=core_data.get('sub_stat_level_2'),
                            stat_grade=core_data.get('stat_grade')
                        )
                        cores.append(core)
                    return cores

                # 각 코어 타입별 처리
                core_fields = [
                    'character_hexa_stat_core',
                    'character_hexa_stat_core_2',
                    'character_hexa_stat_core_3',
                    'preset_hexa_stat_core',
                    'preset_hexa_stat_core_2',
                    'preset_hexa_stat_core_3'
                ]

                for field in core_fields:
                    if field in data and data[field]:
                        getattr(character_hexa_matrix_stat,
                                field).clear()  # 기존 데이터 삭제
                        cores = process_hexa_stat_cores(data[field])
                        getattr(character_hexa_matrix_stat, field).add(*cores)

                obj = character_hexa_matrix_stat

            elif self.model_class == CharacterItemEquipment:
                character_item_equipment, created = CharacterItemEquipment.objects.get_or_create(
                    character=character,
                    date=data.get('date'),
                    defaults={
                        'character_gender': data.get('character_gender'),
                        'character_class': data.get('character_class'),
                        'preset_no': data.get('preset_no')
                    }
                )

                # Title 처리
                if 'title' in data:
                    title = Title.create_from_data(data['title'])
                    character_item_equipment.title = title
                    character_item_equipment.save()

                # 나머지 장비 처리
                equipment_fields = [
                    'item_equipment',
                    'item_equipment_preset_1',
                    'item_equipment_preset_2',
                    'item_equipment_preset_3',
                    'dragon_equipment',
                    'mechanic_equipment'
                ]

                for field in equipment_fields:
                    if field in data and data[field]:
                        # 기존 데이터 삭제
                        getattr(character_item_equipment, field).clear()

                        # 장비 데이터 벌크 생성
                        created_equipments = ItemEquipment.bulk_create_from_data(
                            data[field])

                        # ManyToMany 관계 일괄 설정
                        getattr(character_item_equipment, field).add(
                            *created_equipments)

                obj = character_item_equipment

            elif self.model_class == CharacterLinkSkill:
                defaults.update({
                    'character_class': data.get('character_class'),
                    'preset_no': data.get('preset_no', 1)
                })

                # 기본 링크 스킬 처리
                if 'character_link_skill' in data and data['character_link_skill']:
                    skills = LinkSkill.bulk_create_from_data(
                        [data['character_link_skill']])
                    if skills:
                        defaults['character_link_skill'] = skills[0]

                # 보유 링크 스킬 처리
                if 'character_owned_link_skill' in data and data['character_owned_link_skill']:
                    owned_skills = LinkSkill.bulk_create_from_data(
                        [data['character_owned_link_skill']])
                    if owned_skills:
                        defaults['character_owned_link_skill'] = owned_skills[0]

                obj, created = self.model_class.objects.update_or_create(
                    character=defaults['character'],
                    date=defaults['date'],
                    defaults=defaults
                )

                # 프리셋 처리
                preset_fields = {
                    'character_link_skill_preset_1': 'preset_1',
                    'character_link_skill_preset_2': 'preset_2',
                    'character_link_skill_preset_3': 'preset_3'
                }

                for field, related_name in preset_fields.items():
                    if field in data and isinstance(data[field], list):
                        getattr(obj, field).clear()
                        skills = LinkSkill.bulk_create_from_data(data[field])
                        if skills:
                            getattr(obj, field).add(*skills)

                # 프리셋 보유 링크 스킬 처리
                preset_owned_fields = {
                    'character_owned_link_skill_preset_1': 'owned_preset_1',
                    'character_owned_link_skill_preset_2': 'owned_preset_2',
                    'character_owned_link_skill_preset_3': 'owned_preset_3'
                }

                for field, related_name in preset_owned_fields.items():
                    if field in data and isinstance(data[field], dict):
                        skills = LinkSkill.bulk_create_from_data([data[field]])
                        if skills:
                            setattr(obj, field, skills[0])
                            obj.save()

            elif self.model_class == CharacterVMatrix:
                defaults.update({
                    'character_class': data.get('character_class'),
                    'character_v_matrix_remain_slot_upgrade_point': data.get('character_v_matrix_remain_slot_upgrade_point', 0)
                })

                obj, created = self.model_class.objects.update_or_create(
                    character=defaults['character'],
                    date=defaults['date'],
                    defaults=defaults
                )

                # V코어 장비 처리
                if 'character_v_core_equipment' in data and data['character_v_core_equipment']:
                    obj.character_v_core_equipment.clear()
                    cores = VCore.bulk_create_from_data(
                        data['character_v_core_equipment'])
                    if cores:
                        obj.character_v_core_equipment.add(*cores)

            # 나머지 모델들에 대한 처리
            else:
                # 기본 필드 업데이트
                for field in self.model_class._meta.fields:
                    if field.name in data and field.name not in ['id', 'character', 'date']:
                        defaults[field.name] = data.get(field.name)

                obj, created = self.model_class.objects.update_or_create(
                    character=defaults.get('character'),
                    date=defaults.get('date'),
                    defaults=defaults
                )

                # ManyToMany 관계 처리
                for field in self.model_class._meta.many_to_many:
                    # 데이터가 있는 경우에만 처리
                    if field.name in data and data[field.name]:
                        related_manager = getattr(obj, field.name)
                        related_manager.clear()
                        for item in data[field.name]:
                            if item:  # 아이템이 비어있지 않은 경우에만 처리
                                try:
                                    # 빈 리스트인 필드 제거
                                    item_copy = item.copy()
                                    for key, value in item.items():
                                        if isinstance(value, list) and not value:
                                            del item_copy[key]

                                    related_model = field.related_model
                                    related_obj, _ = related_model.objects.get_or_create(
                                        **item_copy)
                                    related_manager.add(related_obj)
                                except Exception as e:
                                    logger.warning(
                                        f"ManyToMany 관계 처리 중 오류 발생: {str(e)}, 필드: {field.name}, 데이터: {item}")
                                    continue

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
            self.related_name
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
            self.save_to_database(data, ocid)

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


@swagger_auto_schema(tags=['캐릭터 인기도'])
class CharacterPopularityView(BaseCharacterView):
    model_class = CharacterPopularity
    api_url = CHARACTER_POPULARITY_URL
    related_name = 'popularity'


@swagger_auto_schema(tags=['캐릭터 스탯'])
class CharacterStatView(BaseCharacterView):
    model_class = CharacterStat
    api_url = CHARACTER_STAT_URL
    related_name = 'stats'


@swagger_auto_schema(tags=['캐릭터 어빌리티'])
class CharacterAbilityView(BaseCharacterView):
    model_class = CharacterAbility
    api_url = CHARACTER_ABILITY_URL
    related_name = 'abilities'


@swagger_auto_schema(tags=['캐릭터 장비'])
class CharacterItemEquipmentView(BaseCharacterView):
    model_class = CharacterItemEquipment
    api_url = CHARACTER_ITEM_EQUIPMENT_URL
    related_name = 'equipments'


@swagger_auto_schema(tags=['캐릭터 캐시 장비'])
class CharacterCashItemEquipmentView(BaseCharacterView):
    model_class = CharacterCashItemEquipment
    api_url = CHARACTER_CASHITEM_EQUIPMENT_URL
    related_name = 'cash_equipments'


@swagger_auto_schema(tags=['캐릭터 심볼'])
class CharacterSymbolView(BaseCharacterView):
    model_class = CharacterSymbolEquipment
    api_url = CHARACTER_SYMBOL_URL
    related_name = 'symbols'


@swagger_auto_schema(tags=['캐릭터 링크 스킬'])
class CharacterLinkSkillView(BaseCharacterView):
    model_class = CharacterLinkSkill
    api_url = CHARACTER_LINK_SKILL_URL
    related_name = 'link_skills'

    def save_to_database(self, data, ocid=None):
        try:
            if not self.model_class:
                return

            character = CharacterBasic.objects.get(ocid=ocid)
            return CharacterLinkSkill.create_from_data(character, data)
        except Exception as e:
            logger.error(f"데이터베이스 저장 중 오류 발생: {str(e)}")
            return None


@swagger_auto_schema(tags=['캐릭터 스킬'])
class CharacterSkillView(BaseCharacterView):
    model_class = CharacterSkill
    api_url = CHARACTER_SKILL_URL
    related_name = 'skills'


@swagger_auto_schema(tags=['캐릭터 HEXA 매트릭스'])
class CharacterHexaMatrixView(BaseCharacterView):
    model_class = CharacterHexaMatrix
    api_url = CHARACTER_HEXAMATRIX_URL
    related_name = 'hexa_matrix'


@swagger_auto_schema(tags=['캐릭터 HEXA 스탯'])
class CharacterHexaMatrixStatView(BaseCharacterView):
    model_class = CharacterHexaMatrixStat
    api_url = CHARACTER_HEXAMATRIX_STAT_URL
    related_name = 'hexa_stats'


@swagger_auto_schema(tags=['캐릭터 V매트릭스'])
class CharacterVMatrixView(BaseCharacterView):
    model_class = CharacterVMatrix
    api_url = CHARACTER_VMATRIX_URL
    related_name = 'v_matrix'


@swagger_auto_schema(tags=['캐릭터 무릉도장'])
class CharacterDojangView(BaseCharacterView):
    model_class = CharacterDojang
    api_url = CHARACTER_DOJANG_URL
    related_name = 'dojang'


@swagger_auto_schema(tags=['캐릭터 세트효과'])
class CharacterSetEffectView(BaseCharacterView):
    model_class = CharacterSetEffect
    api_url = CHARACTER_SET_EFFECT_URL
    related_name = 'set_effects'


@swagger_auto_schema(tags=['캐릭터 성형/헤어'])
class CharacterBeautyEquipmentView(BaseCharacterView):
    model_class = CharacterBeautyEquipment
    api_url = CHARACTER_BEAUTY_EQUIPMENT_URL
    related_name = 'beauty_equipments'


@swagger_auto_schema(tags=['캐릭터 안드로이드'])
class CharacterAndroidEquipmentView(BaseCharacterView):
    model_class = CharacterAndroidEquipment
    api_url = CHARACTER_ANDROID_EQUIPMENT_URL
    related_name = 'android_equipments'


@swagger_auto_schema(tags=['캐릭터 펫'])
class CharacterPetEquipmentView(BaseCharacterView):
    model_class = CharacterPetEquipment
    api_url = CHARACTER_PET_EQUIPMENT_URL
    related_name = 'pet_equipments'


@swagger_auto_schema(tags=['캐릭터 성향'])
class CharacterPropensityView(BaseCharacterView):
    model_class = CharacterPropensity
    api_url = CHARACTER_PROPENSITY_URL
    related_name = 'propensities'


@swagger_auto_schema(tags=['캐릭터 하이퍼스탯'])
class CharacterHyperStatView(BaseCharacterView):
    model_class = CharacterHyperStat
    api_url = CHARACTER_HYPER_STAT_URL
    related_name = 'hyper_stats'


@swagger_auto_schema(tags=['캐릭터 전체 정보'])
class CharacterAllDataView(BaseCharacterView):
    """캐릭터의 모든 정보를 조회하는 뷰"""

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
                CHARACTER_BASIC_URL: CharacterBasicView,
                CHARACTER_POPULARITY_URL: CharacterPopularityView,
                CHARACTER_STAT_URL: CharacterStatView,
                CHARACTER_ABILITY_URL: CharacterAbilityView,
                CHARACTER_ITEM_EQUIPMENT_URL: CharacterItemEquipmentView,
                CHARACTER_CASHITEM_EQUIPMENT_URL: CharacterCashItemEquipmentView,
                CHARACTER_SYMBOL_URL: CharacterSymbolView,
                CHARACTER_LINK_SKILL_URL: CharacterLinkSkillView,
                CHARACTER_SKILL_URL: CharacterSkillView,
                CHARACTER_HEXAMATRIX_URL: CharacterHexaMatrixView,
                CHARACTER_HEXAMATRIX_STAT_URL: CharacterHexaMatrixStatView,
                CHARACTER_VMATRIX_URL: CharacterVMatrixView,
                CHARACTER_DOJANG_URL: CharacterDojangView,
                CHARACTER_SET_EFFECT_URL: CharacterSetEffectView,
                CHARACTER_BEAUTY_EQUIPMENT_URL: CharacterBeautyEquipmentView,
                CHARACTER_ANDROID_EQUIPMENT_URL: CharacterAndroidEquipmentView,
                CHARACTER_PET_EQUIPMENT_URL: CharacterPetEquipmentView,
                CHARACTER_PROPENSITY_URL: CharacterPropensityView,
                CHARACTER_HYPER_STAT_URL: CharacterHyperStatView,
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
                    semaphore = asyncio.Semaphore(20)  # 동시에 최대 5개의 요청만 허용

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
                    view_class = api_endpoints[url]
                    view_instance = view_class()
                    view_instance.save_to_database(result, ocid)
                    endpoint_name = url.split('/')[-1]  # URL에서 엔드포인트 이름 추출
                    all_data[endpoint_name] = result

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
