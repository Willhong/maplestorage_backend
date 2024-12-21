from django.db import transaction

from accounts.models import Character
from characters.models import AbilityInfo, AbilityPreset, CharacterAbility, CharacterBasic, CharacterPopularity, CharacterStat, StatDetail


class CharacterDataManager:
    @staticmethod
    @transaction.atomic
    def create_character_data(character_name, ocid):
        character = Character.objects.create(
            character_name=character_name,
            ocid=ocid
        )
        return character

    @staticmethod
    @transaction.atomic
    def update_character_data(character_basic_data, popularity_data, stat_data, ocid):
        # CharacterBasic 생성
        character_basic = CharacterBasic.objects.create(
            character_name=character_basic_data['character_name'],
            date=character_basic_data['date'],
            world_name=character_basic_data['world_name'],
            character_gender=character_basic_data['character_gender'],
            character_class=character_basic_data['character_class'],
            character_class_level=character_basic_data['character_class_level'],
            character_level=character_basic_data['character_level'],
            character_exp=character_basic_data['character_exp'],
            character_exp_rate=character_basic_data['character_exp_rate'],
            character_guild_name=character_basic_data['character_guild_name'],
            character_image=character_basic_data['character_image'],
            access_flag=True,
            liberation_quest_clear_flag=True
        )

        # CharacterPopularity 생성
        popularity_obj = CharacterPopularity.objects.create(
            character=character_basic,
            date=popularity_data['date'],
            popularity=popularity_data['popularity']
        )

        # Remove 'final_stat' from stat_data to avoid the error
        final_stat = stat_data.pop('final_stat', [])

        # Create CharacterStat
        stat_obj = CharacterStat.objects.create(
            character=character_basic,
            character_class=stat_data['character_class'],
            date=stat_data['date'],
            remain_ap=stat_data['remain_ap']
        )

        # Create StatDetail objects
        for stat in final_stat:
            StatDetail.objects.create(
                character_stat=stat_obj,
                stat_name=stat['stat_name'],
                stat_value=stat['stat_value']
            )

        # Character 모델도 함께 업데이트 (이 부분은 update_or_create 유지)
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

    @staticmethod
    # @transaction.atomic
    def create_ability_data(ability_data, character_basic):
        date = ability_data.date

        if date is None:
            date = character_basic.date

        ability_presets = []
        for key, value in ability_data.model_dump().items():
            if key.startswith('ability_preset_'):
                ability_preset_grade = value['ability_preset_grade']
                ability_preset = AbilityPreset.objects.create(
                    ability_preset_grade=ability_preset_grade
                )
                ability_presets.append(ability_preset)
                ability_info_list = []
                for ability in value['ability_info']:
                    ability_info = AbilityInfo.objects.create(
                        ability_no=ability['ability_no'],
                        ability_grade=ability['ability_grade'],
                        ability_value=ability['ability_value']
                    )
                    ability_info_list.append(ability_info)

                ability_preset.ability_info.set(ability_info_list)
                ability_preset.save()

        character_ability = CharacterAbility.objects.create(
            character=character_basic,
            date=date,
            ability_grade=ability_data.ability_grade,
            remain_fame=ability_data.remain_fame,
            preset_no=ability_data.preset_no,
            ability_preset_1=ability_presets[0],
            ability_preset_2=ability_presets[1],
            ability_preset_3=ability_presets[2]
        )
        character_ability.ability_info.set(ability_info_list)
        character_ability.save()


# def pydantic_to_django(pydantic_obj: CharacterStatSchema) -> CharacterStat:
#     character_stat = CharacterStat(
#         date=pydantic_obj.date,
#         character_class=pydantic_obj.character_class,
#         remain_ap=pydantic_obj.remain_ap
#     )
#     character_stat.save()

#     for stat in pydantic_obj.final_stat:
#         StatDetail.objects.create(
#             character_stat=character_stat,
#             stat_name=stat.stat_name,
#             stat_value=stat.stat_value
#         )

#     return character_stat


# def django_to_pydantic(django_obj: CharacterStat) -> CharacterStatSchema:
#     return CharacterStatSchema(
#         date=django_obj.date,
#         character_class=django_obj.character_class,
#         final_stat=[StatDetailSchema(stat_name=stat.stat_name, stat_value=stat.stat_value)
#                     for stat in django_obj.final_stat.all()],
#         remain_ap=django_obj.remain_ap
#     )
