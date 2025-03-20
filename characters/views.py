import requests
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.utils import timezone
import logging

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
from .models import (
    CharacterBasic, CharacterId, CharacterPopularity, CharacterStat, CharacterAbility,
    CharacterItemEquipment, CharacterCashItemEquipment, CharacterSymbolEquipment,
    CharacterLinkSkill, CharacterSkill, CharacterHexaMatrix, CharacterHexaMatrixStat,
    CharacterVMatrix, CharacterDojang, CharacterSetEffect, CharacterBeautyEquipment,
    CharacterAndroidEquipment, CharacterPetEquipment, CharacterPropensity, CharacterHyperStat,
    AbilityPreset, AbilityInfo
)

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
                'date': timezone.now(),
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
                # CharacterBasic 모델 처리
                defaults.update({
                    'ocid': data.get('ocid', ocid),
                    'date': data.get('date', timezone.now()),
                    'character_name': data.get('character_name'),
                    'world_name': data.get('world_name'),
                    'character_gender': data.get('character_gender'),
                    'character_class': data.get('character_class'),
                    'character_class_level': data.get('character_class_level'),
                    'character_level': data.get('character_level'),
                    'character_exp': data.get('character_exp'),
                    'character_exp_rate': data.get('character_exp_rate'),
                    'character_image': data.get('character_image'),
                    'character_date_create': data.get('character_date_create'),
                    'access_flag': True if data.get('access_flag') == 'true' else False,
                    'liberation_quest_clear_flag': True if data.get('liberation_quest_clear_flag') == 'true' else False,
                })
                obj, created = self.model_class.objects.update_or_create(
                    ocid=data.get('ocid'),
                    defaults=defaults
                )

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
                    if field.name in data:
                        related_manager = getattr(obj, field.name)
                        related_manager.clear()
                        for item in data[field.name]:
                            related_model = field.related_model
                            related_obj, _ = related_model.objects.get_or_create(
                                **item)
                            related_manager.add(related_obj)

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
