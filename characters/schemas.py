# schemas.py
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime


class CharacterBasicSchema(BaseModel):
    date: Optional[str]
    character_name: str
    world_name: str
    character_gender: str
    character_class: str
    character_class_level: str
    character_level: int
    character_exp: int
    character_exp_rate: str
    character_guild_name: str
    character_image: str
    character_date_create: Optional[str]
    access_flag: str
    liberation_quest_clear_flag: str


class CharacterPopularitySchema(BaseModel):
    date: Optional[str]
    popularity: int


class ItemTotalOptionSchema(BaseModel):
    str: Optional[str]
    dex: Optional[str]
    int: Optional[str]
    luk: Optional[str]
    max_hp: Optional[str]
    max_mp: Optional[str]
    attack_power: Optional[str]
    magic_power: Optional[str]
    armor: Optional[str]
    speed: Optional[str]
    jump: Optional[str]
    boss_damage: Optional[str]
    ignore_monster_armor: Optional[str]
    all_stat: Optional[str]
    damage: Optional[str]
    equipment_level_decrease: Optional[int]
    max_hp_rate: Optional[str]
    max_mp_rate: Optional[str]


class ItemBaseOptionSchema(BaseModel):
    str: Optional[str]
    dex: Optional[str]
    int: Optional[str]
    luk: Optional[str]
    max_hp: Optional[str]
    max_mp: Optional[str]
    attack_power: Optional[str]
    magic_power: Optional[str]
    armor: Optional[str]
    speed: Optional[str]
    jump: Optional[str]
    boss_damage: Optional[str]
    ignore_monster_armor: Optional[str]
    all_stat: Optional[str]
    max_hp_rate: Optional[str]
    max_mp_rate: Optional[str]
    base_equipment_level: Optional[int]


class ItemExceptionalOptionSchema(BaseModel):
    str: Optional[str]
    dex: Optional[str]
    int: Optional[str]
    luk: Optional[str]
    max_hp: Optional[str]
    max_mp: Optional[str]
    attack_power: Optional[str]
    magic_power: Optional[str]
    exceptional_upgrade: Optional[int]


class ItemAddOptionSchema(BaseModel):
    str: Optional[str]
    dex: Optional[str]
    int: Optional[str]
    luk: Optional[str]
    max_hp: Optional[str]
    max_mp: Optional[str]
    attack_power: Optional[str]
    magic_power: Optional[str]
    armor: Optional[str]
    speed: Optional[str]
    jump: Optional[str]
    boss_damage: Optional[str]
    damage: Optional[str]
    all_stat: Optional[str]
    equipment_level_decrease: Optional[int]


class ItemEtcOptionSchema(BaseModel):
    str: Optional[str]
    dex: Optional[str]
    int: Optional[str]
    luk: Optional[str]
    max_hp: Optional[str]
    max_mp: Optional[str]
    attack_power: Optional[str]
    magic_power: Optional[str]
    armor: Optional[str]
    speed: Optional[str]
    jump: Optional[str]


class ItemStarforceOptionSchema(BaseModel):
    str: Optional[str]
    dex: Optional[str]
    int: Optional[str]
    luk: Optional[str]
    max_hp: Optional[str]
    max_mp: Optional[str]
    attack_power: Optional[str]
    magic_power: Optional[str]
    armor: Optional[str]
    speed: Optional[str]
    jump: Optional[str]


class ItemEquipmentSchema(BaseModel):
    item_equipment_part: str
    item_equipment_slot: str
    item_name: str
    item_icon: str
    item_description: Optional[str]
    item_shape_name: Optional[str]
    item_shape_icon: Optional[str]
    item_gender: Optional[str]
    item_total_option: ItemTotalOptionSchema
    item_base_option: ItemBaseOptionSchema
    potential_option_flag: Optional[str]
    additional_potential_option_flag: Optional[str]
    potential_option_grade: Optional[str]
    additional_potential_option_grade: Optional[str]
    potential_option_1: Optional[str]
    potential_option_2: Optional[str]
    potential_option_3: Optional[str]
    additional_potential_option_1: Optional[str]
    additional_potential_option_2: Optional[str]
    additional_potential_option_3: Optional[str]
    equipment_level_increase: Optional[int]
    item_exceptional_option: Optional[ItemExceptionalOptionSchema]
    item_add_option: Optional[ItemAddOptionSchema]
    growth_exp: Optional[int]
    growth_level: Optional[int]
    scroll_upgrade: Optional[str]
    cuttable_count: Optional[str]
    golden_hammer_flag: Optional[str]
    scroll_resilience_count: Optional[str]
    scroll_upgradable_count: Optional[str] = None
    soul_name: Optional[str] = None
    soul_option: Optional[str] = None
    item_etc_option: Optional[ItemEtcOptionSchema]
    starforce: Optional[str]
    starforce_scroll_flag: Optional[str]
    item_starforce_option: Optional[ItemStarforceOptionSchema]
    special_ring_level: Optional[int]
    date_expire: Optional[str]


class TitleSchema(BaseModel):
    title_name: str
    title_icon: str
    title_description: str
    date_expire: Optional[str]
    date_option_expire: Optional[str]


class CharacterItemEquipmentSchema(BaseModel):
    date: Optional[str]
    character_gender: str
    character_class: str
    preset_no: int
    item_equipment: List[ItemEquipmentSchema]
    item_equipment_preset_1: List[ItemEquipmentSchema]
    item_equipment_preset_2: List[ItemEquipmentSchema]
    item_equipment_preset_3: List[ItemEquipmentSchema]
    title: Optional[TitleSchema]
    dragon_equipment: Optional[List[ItemEquipmentSchema]]
    mechanic_equipment: Optional[List[ItemEquipmentSchema]]


class StatInfoSchema(BaseModel):
    stat_name: str
    stat_value: str


class CharacterStatSchema(BaseModel):
    date: Optional[str]
    character_class: str
    final_stat: List[StatInfoSchema]
    remain_ap: int


class AbilityInfoSchema(BaseModel):
    ability_no: str
    ability_grade: str
    ability_value: str


class AbilityPresetSchema(BaseModel):
    ability_preset_grade: str
    ability_info: List[AbilityInfoSchema]


class CharacterAbilitySchema(BaseModel):
    date: Optional[datetime]
    ability_grade: str
    ability_info: List[AbilityInfoSchema]
    remain_fame: int
    preset_no: int
    ability_preset_1: AbilityPresetSchema
    ability_preset_2: AbilityPresetSchema
    ability_preset_3: AbilityPresetSchema


class CashItemOptionSchema(BaseModel):
    option_type: str
    option_value: str


class CashItemColoringPrismSchema(BaseModel):
    color_range: str
    hue: int
    saturation: int
    value: int


class CashItemEquipmentSchema(BaseModel):
    cash_item_equipment_part: str
    cash_item_equipment_slot: str
    cash_item_name: str
    cash_item_icon: str
    cash_item_description: Optional[str] = None
    cash_item_option: List[CashItemOptionSchema]
    date_expire: Optional[str] = None
    date_option_expire: Optional[str] = None
    cash_item_label: Optional[str] = None
    cash_item_coloring_prism: Optional[CashItemColoringPrismSchema] = None
    item_gender: Optional[str] = None
    skill: Optional[List[str]] = None


class CharacterCashItemEquipmentSchema(BaseModel):
    date: Optional[str] = None
    character_gender: str
    character_class: str
    character_look_mode: str
    preset_no: int
    cash_item_equipment_base: List[CashItemEquipmentSchema]
    cash_item_equipment_preset_1: List[CashItemEquipmentSchema]
    cash_item_equipment_preset_2: List[CashItemEquipmentSchema]
    cash_item_equipment_preset_3: List[CashItemEquipmentSchema]
    additional_cash_item_equipment_base: Optional[List[CashItemEquipmentSchema]] = None
    additional_cash_item_equipment_preset_1: Optional[List[CashItemEquipmentSchema]] = None
    additional_cash_item_equipment_preset_2: Optional[List[CashItemEquipmentSchema]] = None
    additional_cash_item_equipment_preset_3: Optional[List[CashItemEquipmentSchema]] = None


class SymbolSchema(BaseModel):
    symbol_name: str
    symbol_icon: str
    symbol_description: str
    symbol_force: str
    symbol_level: int
    symbol_str: Optional[str]
    symbol_dex: Optional[str]
    symbol_int: Optional[str]
    symbol_luk: Optional[str]
    symbol_hp: Optional[str]
    symbol_drop_rate: Optional[str]
    symbol_meso_rate: Optional[str]
    symbol_exp_rate: Optional[str]
    symbol_growth_count: int
    symbol_require_growth_count: int


class CharacterSymbolSchema(BaseModel):
    date: Optional[str]
    character_class: str
    symbol: List[SymbolSchema]


class CharacterSymbolEquipmentSchema(BaseModel):
    date: Optional[str]
    character_class: str
    symbol: List[SymbolSchema]


class CharacterSkillGradeSchema(BaseModel):
    skill_name: str
    skill_description: str
    skill_level: int
    skill_effect: str
    skill_effect_next: Optional[str]
    skill_icon: str


class CharacterSkillSchema(BaseModel):
    date: Optional[str]
    character_class: str
    character_skill_grade: str
    character_skill: List[CharacterSkillGradeSchema]


class LinkSkillSchema(BaseModel):
    skill_name: str
    skill_description: str
    skill_level: int
    skill_effect: str
    skill_icon: str


class CharacterLinkSkillSchema(BaseModel):
    date: Optional[str]
    character_class: str
    character_link_skill: List[LinkSkillSchema] = []
    character_link_skill_preset_1: List[LinkSkillSchema]
    character_link_skill_preset_2: List[LinkSkillSchema]
    character_link_skill_preset_3: List[LinkSkillSchema]
    character_owned_link_skill: Optional[LinkSkillSchema]
    character_owned_link_skill_preset_1: Optional[LinkSkillSchema]
    character_owned_link_skill_preset_2: Optional[LinkSkillSchema]
    character_owned_link_skill_preset_3: Optional[LinkSkillSchema]


class VCoreSchema(BaseModel):
    slot_id: str
    slot_level: int
    v_core_name: str
    v_core_type: str
    v_core_level: int
    v_core_skill_1: str
    v_core_skill_2: Optional[str]
    v_core_skill_3: Optional[str]


class CharacterVMatrixSchema(BaseModel):
    date: Optional[str]
    character_class: str
    character_v_core_equipment: List[VCoreSchema] = []
    character_v_matrix_remain_slot_upgrade_point: int = 0
    character_skill_grade: Optional[str] = None
    character_skill: Optional[List[CharacterSkillGradeSchema]] = None


class HexaSkillSchema(BaseModel):
    hexa_skill_id: str


class HexaCoreSchema(BaseModel):
    hexa_core_name: str
    hexa_core_level: int
    hexa_core_type: str
    linked_skill: List[HexaSkillSchema]


class CharacterHexaMatrixSchema(BaseModel):
    date: Optional[str]
    character_hexa_core_equipment: List[HexaCoreSchema]


class HexaStatCoreSchema(BaseModel):
    slot_id: str
    main_stat_name: str
    sub_stat_name_1: str
    sub_stat_name_2: str
    main_stat_level: int
    sub_stat_level_1: int
    sub_stat_level_2: int
    stat_grade: int


class CharacterHexaStatSchema(BaseModel):
    date: Optional[str]
    character_class: str
    character_hexa_stat_core: List[HexaStatCoreSchema]
    character_hexa_stat_core_2: List[HexaStatCoreSchema]
    preset_hexa_stat_core: List[HexaStatCoreSchema]
    preset_hexa_stat_core_2: List[HexaStatCoreSchema]


class CharacterHexaMatrixStatSchema(BaseModel):
    date: Optional[str]
    character_class: str
    character_hexa_stat_core: List[HexaStatCoreSchema]
    character_hexa_stat_core_2: List[HexaStatCoreSchema]
    preset_hexa_stat_core: List[HexaStatCoreSchema]
    preset_hexa_stat_core_2: List[HexaStatCoreSchema]


class CharacterDojangSchema(BaseModel):
    date: Optional[str]
    character_class: str
    world_name: str
    dojang_best_floor: int
    date_dojang_record: Optional[str]
    dojang_best_time: int
