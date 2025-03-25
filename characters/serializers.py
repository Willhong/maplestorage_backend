from rest_framework import serializers
from .models import (
    Hair, Face, Skin, CashItemEquipment, CashItemOption,
    CashItemColoringPrism, AndroidEquipmentPreset, AndroidEquipment,
    AbilityInfo, AbilityPreset, CharacterAbility,
    CharacterBasic, CharacterBasicHistory, CharacterBeautyEquipment,
    CharacterCashItemEquipment, CharacterDojang, HexaStatCore,
    CharacterHexaMatrixStat, HexaSkill, HexaCore, CharacterHexaMatrix,
    HyperStatPreset, CharacterHyperStat, ItemTotalOption, ItemBaseOption,
    ItemExceptionalOption, ItemAddOption, ItemEtcOption, ItemStarforceOption,
    Title, ItemEquipment, CharacterItemEquipment,
    LinkSkill, CharacterLinkSkill, PetItemEquipment, PetAutoSkill,
    PetEquipment, CharacterPetEquipment, CharacterPopularity, CharacterPropensity,
    CharacterSetEffect, Skill, CharacterSkill, StatDetail, CharacterStat,
    Symbol, CharacterSymbolEquipment, VCore, CharacterVMatrix
)


class HairSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hair
        exclude = ['id']


class FaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Face
        exclude = ['id']


class SkinSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skin
        exclude = ['id']


class CashItemColoringPrismSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashItemColoringPrism
        exclude = ['id']


class CashItemOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashItemOption
        exclude = ['id']


class CashItemEquipmentSerializer(serializers.ModelSerializer):
    cash_item_option = CashItemOptionSerializer(many=True, read_only=True)
    cash_item_coloring_prism = CashItemColoringPrismSerializer(read_only=True)

    class Meta:
        model = CashItemEquipment
        exclude = ['id']


class AndroidEquipmentPresetSerializer(serializers.ModelSerializer):
    android_hair = HairSerializer(read_only=True)
    android_face = FaceSerializer(read_only=True)
    android_skin = SkinSerializer(read_only=True)

    class Meta:
        model = AndroidEquipmentPreset
        exclude = ['id']


class AndroidEquipmentSerializer(serializers.ModelSerializer):
    android_hair = HairSerializer(read_only=True)
    android_face = FaceSerializer(read_only=True)
    android_skin = SkinSerializer(read_only=True)
    android_cash_item_equipment = CashItemEquipmentSerializer(
        many=True, read_only=True)
    android_preset_1 = AndroidEquipmentPresetSerializer(read_only=True)
    android_preset_2 = AndroidEquipmentPresetSerializer(read_only=True)
    android_preset_3 = AndroidEquipmentPresetSerializer(read_only=True)

    class Meta:
        model = AndroidEquipment
        exclude = ['id', 'character']  # character 필드 제외


class AbilityInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = AbilityInfo
        exclude = ['id']


class AbilityPresetSerializer(serializers.ModelSerializer):
    ability_info = AbilityInfoSerializer(many=True, read_only=True)

    class Meta:
        model = AbilityPreset
        exclude = ['id']


class CharacterAbilitySerializer(serializers.ModelSerializer):
    ability_info = AbilityInfoSerializer(many=True, read_only=True)
    ability_preset_1 = AbilityPresetSerializer(read_only=True)
    ability_preset_2 = AbilityPresetSerializer(read_only=True)
    ability_preset_3 = AbilityPresetSerializer(read_only=True)

    class Meta:
        model = CharacterAbility
        exclude = ['id', 'character']


class CharacterBasicHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = CharacterBasicHistory
        exclude = ['id', 'character']


class CharacterBasicSerializer(serializers.ModelSerializer):
    history = CharacterBasicHistorySerializer(many=True, read_only=True)

    class Meta:
        model = CharacterBasic
        exclude = ['id']


class CharacterBeautyEquipmentSerializer(serializers.ModelSerializer):
    character_hair = HairSerializer(read_only=True)
    character_face = FaceSerializer(read_only=True)
    character_skin = SkinSerializer(read_only=True)
    additional_character_hair = HairSerializer(read_only=True)
    additional_character_face = FaceSerializer(read_only=True)
    additional_character_skin = SkinSerializer(read_only=True)

    class Meta:
        model = CharacterBeautyEquipment
        exclude = ['id', 'character']


class CharacterCashItemEquipmentSerializer(serializers.ModelSerializer):
    cash_item_equipment_base = CashItemEquipmentSerializer(
        many=True, read_only=True)
    cash_item_equipment_preset_1 = CashItemEquipmentSerializer(
        many=True, read_only=True)
    cash_item_equipment_preset_2 = CashItemEquipmentSerializer(
        many=True, read_only=True)
    cash_item_equipment_preset_3 = CashItemEquipmentSerializer(
        many=True, read_only=True)
    additional_cash_item_equipment_base = CashItemEquipmentSerializer(
        many=True, read_only=True)
    additional_cash_item_equipment_preset_1 = CashItemEquipmentSerializer(
        many=True, read_only=True)
    additional_cash_item_equipment_preset_2 = CashItemEquipmentSerializer(
        many=True, read_only=True)
    additional_cash_item_equipment_preset_3 = CashItemEquipmentSerializer(
        many=True, read_only=True)

    class Meta:
        model = CharacterCashItemEquipment
        exclude = ['id', 'character']


class CharacterDojangSerializer(serializers.ModelSerializer):
    class Meta:
        model = CharacterDojang
        exclude = ['id', 'character']


class HexaStatCoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = HexaStatCore
        exclude = ['id']


class CharacterHexaMatrixStatSerializer(serializers.ModelSerializer):
    character_hexa_stat_core = HexaStatCoreSerializer(
        many=True, read_only=True)
    character_hexa_stat_core_2 = HexaStatCoreSerializer(
        many=True, read_only=True)
    character_hexa_stat_core_3 = HexaStatCoreSerializer(
        many=True, read_only=True)
    preset_hexa_stat_core = HexaStatCoreSerializer(many=True, read_only=True)
    preset_hexa_stat_core_2 = HexaStatCoreSerializer(many=True, read_only=True)
    preset_hexa_stat_core_3 = HexaStatCoreSerializer(many=True, read_only=True)

    class Meta:
        model = CharacterHexaMatrixStat
        exclude = ['id', 'character']


class HexaSkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = HexaSkill
        exclude = ['id']


class HexaCoreSerializer(serializers.ModelSerializer):
    linked_skill = HexaSkillSerializer(many=True, read_only=True)

    class Meta:
        model = HexaCore
        exclude = ['id']


class CharacterHexaMatrixSerializer(serializers.ModelSerializer):
    character_hexa_core_equipment = HexaCoreSerializer(
        many=True, read_only=True)

    class Meta:
        model = CharacterHexaMatrix
        exclude = ['id', 'character']


class HyperStatPresetSerializer(serializers.ModelSerializer):
    class Meta:
        model = HyperStatPreset
        exclude = ['id']


class CharacterHyperStatSerializer(serializers.ModelSerializer):
    hyper_stat_preset_1 = HyperStatPresetSerializer(many=True, read_only=True)
    hyper_stat_preset_2 = HyperStatPresetSerializer(many=True, read_only=True)
    hyper_stat_preset_3 = HyperStatPresetSerializer(many=True, read_only=True)

    class Meta:
        model = CharacterHyperStat
        exclude = ['id', 'character']


class ItemTotalOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemTotalOption
        exclude = ['id']


class ItemBaseOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemBaseOption
        exclude = ['id']


class ItemExceptionalOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemExceptionalOption
        exclude = ['id']


class ItemAddOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemAddOption
        exclude = ['id']


class ItemEtcOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemEtcOption
        exclude = ['id']


class ItemStarforceOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemStarforceOption
        exclude = ['id']


class TitleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Title
        exclude = ['id']


class ItemEquipmentSerializer(serializers.ModelSerializer):
    item_total_option = ItemTotalOptionSerializer(read_only=True)
    item_base_option = ItemBaseOptionSerializer(read_only=True)
    item_exceptional_option = ItemExceptionalOptionSerializer(read_only=True)
    item_add_option = ItemAddOptionSerializer(read_only=True)
    item_etc_option = ItemEtcOptionSerializer(read_only=True)
    item_starforce_option = ItemStarforceOptionSerializer(read_only=True)

    class Meta:
        model = ItemEquipment
        exclude = ['id']


class CharacterItemEquipmentSerializer(serializers.ModelSerializer):
    item_equipment = ItemEquipmentSerializer(many=True, read_only=True)
    item_equipment_preset_1 = ItemEquipmentSerializer(
        many=True, read_only=True)
    item_equipment_preset_2 = ItemEquipmentSerializer(
        many=True, read_only=True)
    item_equipment_preset_3 = ItemEquipmentSerializer(
        many=True, read_only=True)
    dragon_equipment = ItemEquipmentSerializer(many=True, read_only=True)
    mechanic_equipment = ItemEquipmentSerializer(many=True, read_only=True)
    title = TitleSerializer(read_only=True)

    class Meta:
        model = CharacterItemEquipment
        exclude = ['id', 'character']


class LinkSkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = LinkSkill
        fields = [
            'skill_name',
            'skill_description',
            'skill_level',
            'skill_effect',
            'skill_effect_next',
            'skill_icon'
        ]


class CharacterLinkSkillSerializer(serializers.ModelSerializer):
    character_link_skill = LinkSkillSerializer(many=True)
    character_link_skill_preset_1 = LinkSkillSerializer(many=True)
    character_link_skill_preset_2 = LinkSkillSerializer(many=True)
    character_link_skill_preset_3 = LinkSkillSerializer(many=True)
    character_owned_link_skill = LinkSkillSerializer()
    character_owned_link_skill_preset_1 = LinkSkillSerializer()
    character_owned_link_skill_preset_2 = LinkSkillSerializer()
    character_owned_link_skill_preset_3 = LinkSkillSerializer()

    class Meta:
        model = CharacterLinkSkill
        fields = [
            'date',
            'character_class',
            'character_link_skill',
            'character_link_skill_preset_1',
            'character_link_skill_preset_2',
            'character_link_skill_preset_3',
            'character_owned_link_skill',
            'character_owned_link_skill_preset_1',
            'character_owned_link_skill_preset_2',
            'character_owned_link_skill_preset_3'
        ]


class PetItemEquipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PetItemEquipment
        exclude = ['id']


class PetAutoSkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = PetAutoSkill
        exclude = ['id']


class PetEquipmentSerializer(serializers.ModelSerializer):
    pet_equipment = PetItemEquipmentSerializer(read_only=True)
    pet_auto_skill = PetAutoSkillSerializer(read_only=True)

    class Meta:
        model = PetEquipment
        exclude = ['id']


class CharacterPetEquipmentSerializer(serializers.ModelSerializer):
    pet_equipment = PetEquipmentSerializer(many=True, read_only=True)

    class Meta:
        model = CharacterPetEquipment
        exclude = ['id', 'character']


class CharacterPopularitySerializer(serializers.ModelSerializer):
    class Meta:
        model = CharacterPopularity
        fields = ['date', 'popularity']


class CharacterPropensitySerializer(serializers.ModelSerializer):
    class Meta:
        model = CharacterPropensity
        fields = [
            'date',
            'charisma_level',
            'sensibility_level',
            'insight_level',
            'willingness_level',
            'handicraft_level',
            'charm_level'
        ]


class CharacterSetEffectSerializer(serializers.ModelSerializer):
    class Meta:
        model = CharacterSetEffect
        fields = ['date', 'set_effect']


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ['skill_name', 'skill_description', 'skill_level',
                  'skill_effect', 'skill_effect_next', 'skill_icon']


class CharacterSkillSerializer(serializers.ModelSerializer):
    character_skill = SkillSerializer(many=True, read_only=True)

    class Meta:
        model = CharacterSkill
        fields = ['date', 'character_class',
                  'character_skill_grade', 'character_skill']


class StatDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = StatDetail
        fields = ['stat_name', 'stat_value']


class CharacterStatSerializer(serializers.ModelSerializer):
    final_stat = StatDetailSerializer(many=True, read_only=True)

    class Meta:
        model = CharacterStat
        exclude = ['id', 'character']


class SymbolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Symbol
        fields = [
            'symbol_name',
            'symbol_icon',
            'symbol_description',
            'symbol_force',
            'symbol_level',
            'symbol_dex',
            'symbol_int',
            'symbol_luk',
            'symbol_hp',
            'symbol_drop_rate',
            'symbol_meso_rate',
            'symbol_exp_rate',
            'symbol_growth_count',
            'symbol_require_growth_count'
        ]


class CharacterSymbolEquipmentSerializer(serializers.ModelSerializer):
    symbol = SymbolSerializer(many=True, read_only=True)

    class Meta:
        model = CharacterSymbolEquipment
        fields = ['date', 'character_class', 'symbol']


class VCoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = VCore
        exclude = ['id']


class CharacterVMatrixSerializer(serializers.ModelSerializer):
    character_v_core_equipment = VCoreSerializer(many=True, read_only=True)

    class Meta:
        model = CharacterVMatrix
        exclude = ['id', 'character']
