from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta
import requests

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
from .schemas import *
from .serializers import CharacterAbilitySerializer, CharacterBasicSerializer


class BaseAPIView(APIView):
    def get_ocid_from_api(self, character_name):
        try:
            headers = {
                "accept": "application/json",
                "x-nxopen-api-key": APIKEY
            }
            response = requests.get(
                f"{CHARACTER_ID_URL}?character_name={character_name}",
                headers=headers
            )
            response.raise_for_status()
            data = response.json()
            return data.get('ocid')
        except Exception as e:
            print(f"Error fetching OCID: {str(e)}")
            return None

    def get_character_basic(self, ocid, date=None):
        """기본 정보 조회 및 CharacterBasic 데이터 생성"""
        try:
            headers = {
                "accept": "application/json",
                "x-nxopen-api-key": APIKEY
            }
            url = f"{CHARACTER_BASIC_URL}?ocid={ocid}{f'&date={date}' if date else ''}"
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            basic_data = response.json()

            # CharacterBasic 데이터 생성 또는 업데이트
            current_time = basic_data.get('date')
            if not current_time:
                current_time = timezone.now().strftime('%Y-%m-%dT%H:%M:%S+09:00')

            character_basic, created = CharacterBasic.objects.update_or_create(
                ocid=ocid,
                date=current_time,
                defaults={
                    'character_name': basic_data.get('character_name'),
                    'world_name': basic_data.get('world_name'),
                    'character_gender': basic_data.get('character_gender'),
                    'character_class': basic_data.get('character_class'),
                    'character_class_level': basic_data.get('character_class_level'),
                    'character_level': basic_data.get('character_level'),
                    'character_exp': basic_data.get('character_exp'),
                    'character_exp_rate': basic_data.get('character_exp_rate'),
                    'character_guild_name': basic_data.get('character_guild_name'),
                    'character_image': basic_data.get('character_image'),
                    'access_flag': True,
                    'liberation_quest_clear_flag': True
                }
            )
            return character_basic, current_time
        except Exception as e:
            print(f"Error fetching basic data: {str(e)}")
            raise e


class CharacterBasicView(BaseAPIView):
    def get(self, request):
        character_name = request.query_params.get('character_name')
        if not character_name:
            return Response({"error": "Character name is required"}, status=status.HTTP_400_BAD_REQUEST)
        character_name = character_name.strip()
        date = request.query_params.get('date')  # 조회 기준일 (KST, YYYY-MM-DD)
        force_refresh = request.query_params.get('force_refresh', False)

        if not character_name:
            return Response({"error": "Character name is required"}, status=status.HTTP_400_BAD_REQUEST)

        # 먼저 local Character 모델에서 확인
        try:
            local_character = Character.objects.get(
                character_name=character_name)
            ocid = local_character.ocid
        except Character.DoesNotExist:
            # local에 없으면 API로 ocid 조회
            ocid = self.get_ocid_from_api(character_name)
            if not ocid:
                return Response({"error": "Character not found"}, status=status.HTTP_404_NOT_FOUND)
        if not date and (force_refresh == False):
            # 캐시된 CharacterBasic 데이터 확인
            cached_data = self.get_cached_data(character_name)
            if cached_data:
                return Response(CharacterBasicSerializer(cached_data).data)
        # 캐시된 데이터가 없으면 API에서 가져오기
        character_data = self.get_character_data_from_api(ocid, date)
        popularity_data = self.get_popularity_data_from_api(ocid, date)
        stat_data = self.get_stat_data_from_api(ocid, date)
        if date is None:
            date = timezone.now().isoformat()
            character_data.date = date
            popularity_data.date = date
            stat_data.date = date

        if character_data:
            saved_data = CharacterDataManager.update_character_data(
                character_data.model_dump(), popularity_data.model_dump(), stat_data.model_dump(), ocid)
            return Response(CharacterBasicSerializer(saved_data).data)
        if not character_data:
            return Response({"error": "Failed to fetch character data"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 데이터베이스에 저장
        saved_data = self.save_to_database(character_data, ocid)

        # Django 모델을 DRF serializer로 변환
        serializer = CharacterBasicSerializer(saved_data)

        return Response(serializer.data)

    def get_character_data_from_api(self, ocid, date):
        try:
            headers = {
                "accept": "application/json",
                "x-nxopen-api-key": APIKEY
            }
            url = f"{CHARACTER_BASIC_URL}?ocid={ocid}{f'&date={date}' if date else ''}"
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            return CharacterBasicSchema.model_validate(data)
        except Exception as e:
            print(f"Error fetching character data: {str(e)}")
            return None

    def get_popularity_data_from_api(self, ocid, date):
        try:
            headers = {
                "accept": "application/json",
                "x-nxopen-api-key": APIKEY
            }
            url = f"{CHARACTER_POPULARITY_URL}?ocid={ocid}{f'&date={date}' if date else ''}"
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            return CharacterPopularitySchema.model_validate(data)
        except Exception as e:
            print(f"Error fetching popularity data: {str(e)}")
            return None

    def get_stat_data_from_api(self, ocid, date):
        try:
            headers = {
                "accept": "application/json",
                "x-nxopen-api-key": APIKEY
            }
            url = f"{CHARACTER_STAT_URL}?ocid={ocid}{f'&date={date}' if date else ''}"
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            return CharacterStatSchema.model_validate(data)
        except Exception as e:
            print(f"Error fetching stat data: {str(e)}")
            return None

    def get_cached_data(self, character_name):
        """캐시된 데이터 조회"""
        try:
            return CharacterBasic.objects.filter(
                character_name=character_name,
                date__gte=timezone.now() - timedelta(hours=1)  # 1시간 이내 데이터만
            ).latest('date')  # 가장 최신 데이터 반환
        except CharacterBasic.DoesNotExist:
            return None

    def save_to_database(self, character_basic, ocid):
        char_basic, created = CharacterBasic.objects.update_or_create(
            ocid=ocid,
            defaults={
                'date': character_basic.date,
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
    def get(self, request):
        character_name = request.query_params.get('character_name')
        date = request.query_params.get('date')
        force_refresh = request.query_params.get('force_refresh', False)
        character_exist = False
        if not character_name:
            return Response({"error": "Character name is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            local_character = Character.objects.get(
                character_name=character_name)
            ocid = local_character.ocid
            character_exist = True
        except Character.DoesNotExist:
            ocid = self.get_ocid_from_api(character_name)
            CharacterDataManager.create_character_data(character_name, ocid)
            if not ocid:
                return Response({"error": "Character not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            headers = {
                "accept": "application/json",
                "x-nxopen-api-key": APIKEY
            }

            if character_exist:
                character_basic = CharacterBasic.objects.filter(
                    ocid=ocid).order_by('-date').first()
                current_time = character_basic.date.isoformat()
            else:
                character_basic, current_time = self.get_character_basic(
                    ocid, date)

            # 어빌리티 API 호출
            if character_exist:
                ability_data = character_basic.abilities.order_by(
                    '-date').first()
                if ability_data:
                    return Response(CharacterAbilitySerializer(ability_data).data)

            ability_url = f"{CHARACTER_ABILITY_URL}?ocid={ocid}{f'&date={date}' if date else ''}"
            ability_response = requests.get(ability_url, headers=headers)
            ability_response.raise_for_status()
            ability_data = ability_response.json()

            # 스키마로 검증
            validated_data = CharacterAbilitySchema.model_validate(
                ability_data)

            if date is None:
                date = timezone.now().isoformat()

            CharacterDataManager.create_ability_data(
                validated_data, character_basic)
            validated_data.date = date

            return Response(validated_data.model_dump())
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CharacterItemEquipmentView(BaseAPIView):
    def get(self, request):
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

            # 장비 정보 API 호출
            url = f"{CHARACTER_ITEM_EQUIPMENT_URL}?ocid={ocid}{f'&date={date}' if date else ''}"
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            datas = response.json()

            # 장비 정보 검증

            for key, value in datas.items():
                if key.startswith('item_equipment'):
                    validated_data = ItemEquipmentSchema.model_validate(
                        value)

            for datad in data['dragon_equipment']:
                val_data_ItemEquipmentSchema = ItemEquipmentSchema.model_validate(
                    datad)
                print(val_data_ItemEquipmentSchema)

            for datad in data['mechanic_equipment']:
                val_data_ItemEquipmentSchema = ItemEquipmentSchema.model_validate(
                    datad)
                print(val_data_ItemEquipmentSchema)

            val_data_TitleSchema = TitleSchema.model_validate(
                data['title'])

            # 스키마로 검증
            validated_data = CharacterItemEquipmentSchema.model_validate(data)

            # 데이터 저장 및 응답
            equipments = []
            for item_data in validated_data.item_equipment:
                equipment = CharacterItemEquipment.objects.create(
                    character=character_basic,
                    date=current_time,
                    item_equipment_part=item_data.item_equipment_part,
                    item_equipment_slot=item_data.item_equipment_slot,
                    item_name=item_data.item_name,
                    item_icon=item_data.item_icon,
                    item_description=item_data.item_description,
                    item_option=item_data.item_option.model_dump(),
                    starforce=item_data.starforce,
                    potential_option_grade=item_data.potential_option_grade,
                    additional_potential_option_grade=item_data.additional_potential_option_grade,
                    potential_options=item_data.potential_options,
                    additional_potential_options=item_data.additional_potential_options
                )
                equipments.append(equipment)

            return Response(validated_data.model_dump())
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CharacterCashItemEquipmentView(BaseAPIView):
    def get(self, request):
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

            # 캐시 장비 정보 API 호출
            url = f"{CHARACTER_CASHITEM_EQUIPMENT_URL}?ocid={ocid}{f'&date={date}' if date else ''}"
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            # 스키마로 검증
            validated_data = CharacterCashItemEquipmentSchema.model_validate(
                data)

            # 데이터 저장 및 응답
            cash_equipments = []
            for item_data in validated_data.cash_item_equipment:
                cash_equipment = CharacterCashItemEquipment.objects.create(
                    character=character_basic,
                    date=current_time,
                    cash_item_equipment_part=item_data.cash_item_equipment_part,
                    cash_item_equipment_slot=item_data.cash_item_equipment_slot,
                    cash_item_name=item_data.cash_item_name,
                    cash_item_icon=item_data.cash_item_icon,
                    cash_item_description=item_data.cash_item_description,
                    cash_item_option=item_data.cash_item_option,
                    date_expire=item_data.date_expire,
                    date_option_expire=item_data.date_option_expire
                )
                cash_equipments.append(cash_equipment)

            return Response(validated_data.model_dump())
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CharacterSymbolView(BaseAPIView):
    def get(self, request):
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

            # 심볼 정보 API 호출
            url = f"{CHARACTER_SYMBOL_URL}?ocid={ocid}{f'&date={date}' if date else ''}"
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            # 스키마로 검증
            validated_data = CharacterSymbolSchema.model_validate(data)

            # 데이터 저장 및 응답
            symbols = []
            for symbol_data in validated_data.symbol:
                symbol = CharacterSymbol.objects.create(
                    character=character_basic,
                    date=current_time,
                    symbol_name=symbol_data.symbol_name,
                    symbol_icon=symbol_data.symbol_icon,
                    symbol_description=symbol_data.symbol_description,
                    symbol_force=symbol_data.symbol_force,
                    symbol_level=symbol_data.symbol_level,
                    symbol_exp=symbol_data.symbol_exp,
                    symbol_exp_required=symbol_data.symbol_exp_required
                )
                symbols.append(symbol)

            return Response(validated_data.model_dump())
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CharacterLinkSkillView(BaseAPIView):
    def get(self, request):
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

            # 링크 스킬 API 호출
            url = f"{CHARACTER_LINK_SKILL_URL}?ocid={ocid}{f'&date={date}' if date else ''}"
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            # 스키마로 검증
            validated_data = CharacterLinkSkillSchema.model_validate(data)

            # 데이터 저장 및 응답
            link_skills = []
            for skill_data in validated_data.link_skill:
                link_skill = CharacterLinkSkill.objects.create(
                    character=character_basic,
                    date=current_time,
                    link_skill_name=skill_data.link_skill_name,
                    link_skill_description=skill_data.link_skill_description,
                    link_skill_level=skill_data.link_skill_level,
                    link_skill_effect=skill_data.link_skill_effect,
                    link_skill_icon=skill_data.link_skill_icon
                )
                link_skills.append(link_skill)

            return Response(validated_data.model_dump())
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CharacterVMatrixView(BaseAPIView):
    def get(self, request):
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

            # V매트릭스 API 호출
            url = f"{CHARACTER_SKILL_URL}?ocid={ocid}{f'&date={date}' if date else ''}"
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            # 스키마로 검증
            validated_data = CharacterVMatrixSchema.model_validate(data)

            # 데이터 저장 및 응답
            v_matrix = []
            for skill_data in validated_data.v_core:
                matrix = CharacterVMatrix.objects.create(
                    character=character_basic,
                    date=current_time,
                    slot_id=skill_data.slot_id,
                    slot_level=skill_data.slot_level,
                    skill_name=skill_data.skill_name,
                    skill_description=skill_data.skill_description,
                    skill_level=skill_data.skill_level,
                    skill_effect=skill_data.skill_effect,
                    skill_icon=skill_data.skill_icon
                )
                v_matrix.append(matrix)

            return Response(validated_data.model_dump())
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CharacterHexaMatrixView(BaseAPIView):
    def get(self, request):
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

            # HEXA 매트릭스 API 호출
            url = f"{CHARACTER_HEXAMATRIX_URL}?ocid={ocid}{f'&date={date}' if date else ''}"
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            # 스키마로 검증
            validated_data = CharacterHexaMatrixSchema.model_validate(data)

            # 데이터 저장 및 응답
            hexa_matrix = []
            for core_data in validated_data.hexa_core_equipment:
                matrix = CharacterHexaMatrix.objects.create(
                    character=character_basic,
                    date=current_time,
                    hexa_core_name=core_data.hexa_core_name,
                    hexa_core_level=core_data.hexa_core_level,
                    hexa_core_type=core_data.hexa_core_type,
                    linked_skill=core_data.linked_skill
                )
                hexa_matrix.append(matrix)

            return Response(validated_data.model_dump())
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CharacterHexaStatView(BaseAPIView):
    def get(self, request):
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

            # HEXA 스탯 API 호출
            url = f"{CHARACTER_HEXAMATRIX_STAT_URL}?ocid={ocid}{f'&date={date}' if date else ''}"
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            # 스키마로 검증
            validated_data = CharacterHexaStatSchema.model_validate(data)

            # 데이터 저장 및 응답
            hexa_stats = []
            for stat_data in validated_data.character_hexa_stat_core:
                stat = CharacterHexaStat.objects.create(
                    character=character_basic,
                    date=current_time,
                    hexa_stat_name=stat_data.hexa_stat_name,
                    hexa_stat_level=stat_data.hexa_stat_level,
                    hexa_stat_increase=stat_data.hexa_stat_increase,
                    hexa_stat_type=stat_data.hexa_stat_type
                )
                hexa_stats.append(stat)

            return Response(validated_data.model_dump())
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
