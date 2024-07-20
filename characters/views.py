from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta
import requests

from accounts.models import Character
from define.define import APIKEY, BASE_URL
from util.util import CharacterDataManager
from .models import CharacterBasic
from .schemas import CharacterBasicSchema, CharacterPopularitySchema, CharacterStatSchema
from .serializers import CharacterBasicSerializer


class CharacterBasicView(APIView):
    def get(self, request):
        character_name = request.query_params.get('character_name')
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

    def get_ocid_from_api(self, character_name):
        try:
            headers = {
                "accept": "application/json",
                "x-nxopen-api-key": APIKEY
            }
            response = requests.get(
                f"{BASE_URL}/id?character_name={character_name}",
                headers=headers
            )
            response.raise_for_status()
            data = response.json()
            return data.get('ocid')
        except Exception as e:
            print(f"Error fetching OCID: {str(e)}")
            return None

    def get_character_data_from_api(self, ocid, date):
        try:
            headers = {
                "accept": "application/json",
                "x-nxopen-api-key": APIKEY
            }
            url = f"{BASE_URL}/character/basic?ocid={ocid}{f'&date={date}' if date else ''}"
            response = requests.get(
                url,
                headers=headers
            )
            response.raise_for_status()
            data = response.json()
            date = data.get('date')  # '2024-07-09T00:00+09:00' -> datetime
            if not date:
                data['date'] = timezone.now().replace(
                    hour=15, minute=0, second=0, microsecond=0).isoformat()

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
            url = f"{BASE_URL}/character/popularity?ocid={ocid}{f'&date={date}' if date else ''}"
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            if not date:
                data['date'] = timezone.now().replace(
                    hour=15, minute=0, second=0, microsecond=0).isoformat()
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
            url = f"{BASE_URL}/character/stat?ocid={ocid}{f'&date={date}' if date else ''}"
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            date = data.get('date')
            if not date:
                data['date'] = timezone.now().replace(
                    hour=15, minute=0, second=0, microsecond=0).isoformat()
            return CharacterStatSchema.model_validate(data)
        except Exception as e:
            print(f"Error fetching stat data: {str(e)}")

    def get_cached_data(self, character_name):
        cache_time = timezone.now() - timedelta(minutes=15)
        try:
            return CharacterBasic.objects.get(
                character_name=character_name,
                date__gte=cache_time
            )
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
