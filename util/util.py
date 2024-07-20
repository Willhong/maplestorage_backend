from django.db import transaction

from accounts.models import Character
from characters.models import CharacterBasic, CharacterPopularity, CharacterStat, StatDetail
from characters.schemas import CharacterStatSchema, StatDetailSchema


class CharacterDataManager:
    @staticmethod
    @transaction.atomic
    def update_character_data(character_basic_data, popularity_data, stat_data, ocid):
        # CharacterBasic 업데이트 또는 생성
        character_basic, _ = CharacterBasic.objects.update_or_create(
            character_name=character_basic_data['character_name'],
            date=character_basic_data['date'],
            defaults=character_basic_data
        )

        # CharacterPopularity 업데이트 또는 생성
        popularity_data, _ = CharacterPopularity.objects.update_or_create(
            character=character_basic,
            date=popularity_data['date'],
            defaults=popularity_data
        )

        # Remove 'final_stat' from stat_data to avoid the error
        final_stat = stat_data.pop('final_stat', [])

        # Update or create CharacterStat
        stat_obj, created = CharacterStat.objects.update_or_create(
            character=character_basic,
            character_class=stat_data['character_class'],
            date=stat_data['date'],
            defaults=stat_data
        )

        # Update or create StatDetail objects
        for stat in final_stat:
            StatDetail.objects.update_or_create(
                character_stat=stat_obj,
                stat_name=stat['stat_name'],
                defaults={'stat_value': stat['stat_value']}
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


def pydantic_to_django(pydantic_obj: CharacterStatSchema) -> CharacterStat:
    character_stat = CharacterStat(
        date=pydantic_obj.date,
        character_class=pydantic_obj.character_class,
        remain_ap=pydantic_obj.remain_ap
    )
    character_stat.save()

    for stat in pydantic_obj.final_stat:
        StatDetail.objects.create(
            character_stat=character_stat,
            stat_name=stat.stat_name,
            stat_value=stat.stat_value
        )

    return character_stat


def django_to_pydantic(django_obj: CharacterStat) -> CharacterStatSchema:
    return CharacterStatSchema(
        date=django_obj.date,
        character_class=django_obj.character_class,
        final_stat=[StatDetailSchema(stat_name=stat.stat_name, stat_value=stat.stat_value)
                    for stat in django_obj.final_stat.all()],
        remain_ap=django_obj.remain_ap
    )
