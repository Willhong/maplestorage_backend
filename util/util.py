from django.db import transaction

from accounts.models import Character
from characters.models import CharacterBasic


class CharacterDataManager:
    @staticmethod
    @transaction.atomic
    def update_character_data(character_basic_data, ocid):
        # CharacterBasic 업데이트 또는 생성
        character_basic, _ = CharacterBasic.objects.update_or_create(
            character_name=character_basic_data['character_name'],
            date=character_basic_data['date'],
            defaults=character_basic_data
        )

        # Character 모델도 함께 업데이트
        Character.objects.update_or_create(
            ocid=ocid,
            defaults={
                'character_name': character_basic_data['character_name'],
                'world_name': character_basic_data['world_name'],
                'character_class': character_basic_data['character_class'],
                'character_level': character_basic_data['character_level']
            }
        )

        return character_basic
