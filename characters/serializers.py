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
    """
    캐릭터 기본 정보 Serializer
    Story 2.8: last_crawled_at, last_crawl_status 필드 추가
    """
    history = CharacterBasicHistorySerializer(many=True, read_only=True)
    last_crawled_at = serializers.SerializerMethodField()
    last_crawl_status = serializers.SerializerMethodField()

    class Meta:
        model = CharacterBasic
        exclude = ['id']

    def get_last_crawled_at(self, obj):
        """
        마지막 크롤링 시간 조회 (Story 2.8: AC #1)

        Returns:
            str | None: ISO 8601 형식의 마지막 크롤링 시간 또는 None
        """
        from accounts.models import CrawlTask

        last_task = CrawlTask.objects.filter(
            character_basic=obj,
            status='SUCCESS'
        ).order_by('-updated_at').first()

        if last_task:
            return last_task.updated_at.isoformat()
        return None

    def get_last_crawl_status(self, obj):
        """
        마지막 크롤링 상태 조회 (Story 2.8: AC #5)

        Returns:
            str: 'SUCCESS' | 'FAILED' | 'NEVER_CRAWLED'
        """
        from accounts.models import CrawlTask

        last_task = CrawlTask.objects.filter(
            character_basic=obj
        ).order_by('-updated_at').first()

        if not last_task:
            return 'NEVER_CRAWLED'

        if last_task.status == 'SUCCESS':
            return 'SUCCESS'
        elif last_task.status in ('FAILURE', 'RETRY'):
            return 'FAILED'
        else:
            # PENDING, STARTED 상태인 경우 이전 성공 여부 확인
            previous_success = CrawlTask.objects.filter(
                character_basic=obj,
                status='SUCCESS'
            ).exists()
            if previous_success:
                return 'SUCCESS'
            return 'NEVER_CRAWLED'


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


# =============================================================================
# 크롤링 데이터 Serializers (인벤토리, 창고)
# =============================================================================

class InventoryItemSerializer(serializers.ModelSerializer):
    """인벤토리 아이템 Serializer"""
    days_until_expiry = serializers.ReadOnlyField()
    is_expirable = serializers.ReadOnlyField()

    class Meta:
        from .models import Inventory
        model = Inventory
        fields = [
            'id', 'item_name', 'item_icon', 'quantity', 'item_options',
            'slot_position', 'expiry_date', 'crawled_at', 'detail_url',
            'has_detail', 'is_expirable', 'days_until_expiry'
        ]


class StorageItemSerializer(serializers.ModelSerializer):
    """창고 아이템 Serializer"""
    days_until_expiry = serializers.ReadOnlyField()
    is_expirable = serializers.ReadOnlyField()

    class Meta:
        from .models import Storage
        model = Storage
        fields = [
            'id', 'storage_type', 'item_name', 'item_icon', 'quantity',
            'item_options', 'slot_position', 'expiry_date', 'crawled_at',
            'is_expirable', 'days_until_expiry'
        ]


class CharacterAllDataSerializer(serializers.ModelSerializer):
    basic = serializers.SerializerMethodField()
    popularity = serializers.SerializerMethodField()
    stats = serializers.SerializerMethodField()
    abilities = serializers.SerializerMethodField()
    equipments = serializers.SerializerMethodField()
    cash_equipments = serializers.SerializerMethodField()
    symbols = serializers.SerializerMethodField()
    link_skills = serializers.SerializerMethodField()
    skills = serializers.SerializerMethodField()
    hexa_matrix = serializers.SerializerMethodField()
    hexa_stats = serializers.SerializerMethodField()
    v_matrix = serializers.SerializerMethodField()
    dojang = serializers.SerializerMethodField()
    set_effects = serializers.SerializerMethodField()
    beauty_equipments = serializers.SerializerMethodField()
    android_equipments = serializers.SerializerMethodField()
    pet_equipments = serializers.SerializerMethodField()
    propensities = serializers.SerializerMethodField()
    hyper_stats = serializers.SerializerMethodField()
    # 크롤링 데이터 필드
    inventory = serializers.SerializerMethodField()
    storage = serializers.SerializerMethodField()
    meso = serializers.SerializerMethodField()

    class Meta:
        model = CharacterBasic
        fields = [
            'basic', 'popularity', 'stats', 'abilities', 'equipments',
            'cash_equipments', 'symbols', 'link_skills', 'skills',
            'hexa_matrix', 'hexa_stats', 'v_matrix', 'dojang',
            'set_effects', 'beauty_equipments', 'android_equipments',
            'pet_equipments', 'propensities', 'hyper_stats',
            # 크롤링 데이터
            'inventory', 'storage', 'meso'
        ]

    def get_basic(self, obj):
        return CharacterBasicSerializer(obj).data

    def get_popularity(self, obj):
        popularity = obj.popularity.order_by('-date').first()
        if popularity:
            return CharacterPopularitySerializer(popularity).data
        return None

    def get_stats(self, obj):
        stats = obj.stats.order_by('-date').first()
        if stats:
            return CharacterStatSerializer(stats).data
        return None

    def get_abilities(self, obj):
        abilities = obj.abilities.order_by('-date').first()
        if abilities:
            return CharacterAbilitySerializer(abilities).data
        return None

    def get_equipments(self, obj):
        equipments = obj.equipments.order_by('-date').first()
        if equipments:
            return CharacterItemEquipmentSerializer(equipments).data
        return None

    def get_cash_equipments(self, obj):
        cash_equipments = obj.cash_equipments.order_by('-date').first()
        if cash_equipments:
            return CharacterCashItemEquipmentSerializer(cash_equipments).data
        return None

    def get_symbols(self, obj):
        symbols = obj.symbols.order_by('-date').first()
        if symbols:
            return CharacterSymbolEquipmentSerializer(symbols).data
        return None

    def get_link_skills(self, obj):
        link_skills = obj.link_skills.order_by('-date').first()
        if link_skills:
            return CharacterLinkSkillSerializer(link_skills).data
        return None

    def get_skills(self, obj):
        skills = obj.skills.order_by('-date').first()
        if skills:
            return CharacterSkillSerializer(skills).data
        return None

    def get_hexa_matrix(self, obj):
        hexa_matrix = obj.hexa_matrix.order_by('-date').first()
        if hexa_matrix:
            return CharacterHexaMatrixSerializer(hexa_matrix).data
        return None

    def get_hexa_stats(self, obj):
        hexa_stats = obj.hexa_stats.order_by('-date').first()
        if hexa_stats:
            return CharacterHexaMatrixStatSerializer(hexa_stats).data
        return None

    def get_v_matrix(self, obj):
        v_matrix = obj.v_matrix.order_by('-date').first()
        if v_matrix:
            return CharacterVMatrixSerializer(v_matrix).data
        return None

    def get_dojang(self, obj):
        dojang = obj.dojang.order_by('-date').first()
        if dojang:
            return CharacterDojangSerializer(dojang).data
        return None

    def get_set_effects(self, obj):
        set_effects = obj.set_effects.order_by('-date').first()
        if set_effects:
            return CharacterSetEffectSerializer(set_effects).data
        return None

    def get_beauty_equipments(self, obj):
        beauty_equipments = obj.beauty_equipments.order_by('-date').first()
        if beauty_equipments:
            return CharacterBeautyEquipmentSerializer(beauty_equipments).data
        return None

    def get_android_equipments(self, obj):
        android_equipments = obj.android_equipments.order_by('-date').first()
        if android_equipments:
            return AndroidEquipmentSerializer(android_equipments).data
        return None

    def get_pet_equipments(self, obj):
        pet_equipments = obj.pet_equipments.order_by('-date').first()
        if pet_equipments:
            return CharacterPetEquipmentSerializer(pet_equipments).data
        return None

    def get_propensities(self, obj):
        propensities = obj.propensities.order_by('-date').first()
        if propensities:
            return CharacterPropensitySerializer(propensities).data
        return None

    def get_hyper_stats(self, obj):
        hyper_stats = obj.hyper_stats.order_by('-date').first()
        if hyper_stats:
            return CharacterHyperStatSerializer(hyper_stats).data
        return None

    # 크롤링 데이터 get 메서드
    def get_inventory(self, obj):
        """최근 크롤링된 인벤토리 아이템 목록"""
        # 가장 최근 크롤링 시점의 아이템들만 반환
        latest_crawled = obj.inventory_items.order_by('-crawled_at').first()
        if not latest_crawled:
            return None

        # 해당 크롤링 시점의 모든 아이템 반환
        items = obj.inventory_items.filter(
            crawled_at=latest_crawled.crawled_at
        ).order_by('slot_position')

        return {
            'crawled_at': latest_crawled.crawled_at.isoformat(),
            'items': InventoryItemSerializer(items, many=True).data,
            'total_count': items.count()
        }

    def get_storage(self, obj):
        """최근 크롤링된 창고 아이템 목록"""
        latest_crawled = obj.storage_items.order_by('-crawled_at').first()
        if not latest_crawled:
            return None

        # 해당 크롤링 시점의 아이템들
        items = obj.storage_items.filter(
            crawled_at=latest_crawled.crawled_at
        ).order_by('slot_position')

        return {
            'crawled_at': latest_crawled.crawled_at.isoformat(),
            'items': StorageItemSerializer(items, many=True).data,
            'total_count': items.count()
        }

    def get_meso(self, obj):
        """캐릭터 보유 메소"""
        return obj.meso
