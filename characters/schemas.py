# schemas.py
from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any, Literal


class CharacterBasicSchema(BaseModel):
    date: Optional[datetime] = None
    character_name: str
    world_name: str
    character_gender: str
    character_class: str
    character_class_level: str
    character_level: int
    character_exp: int
    character_exp_rate: str
    character_guild_name: Optional[str] = None
    character_image: str
    character_date_create: Optional[str] = None
    access_flag: str
    liberation_quest_clear_flag: str = Field(default=None, validation_alias='liberation_quest_clear')


class CharacterPopularitySchema(BaseModel):
    date: Optional[datetime]
    popularity: int


class ItemTotalOptionSchema(BaseModel):
    strength: Optional[str] = Field(None, alias='str')
    dex: Optional[str]
    intelligence: Optional[str] = Field(None, alias='int')
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
    strength: Optional[str] = Field(None, alias='str')
    dex: Optional[str]
    intelligence: Optional[str] = Field(None, alias='int')
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
    strength: Optional[str] = Field(None, alias='str')
    dex: Optional[str]
    intelligence: Optional[str] = Field(None, alias='int')
    luk: Optional[str]
    max_hp: Optional[str]
    max_mp: Optional[str]
    attack_power: Optional[str]
    magic_power: Optional[str]
    exceptional_upgrade: Optional[int]


class ItemAddOptionSchema(BaseModel):
    strength: Optional[str] = Field(None, alias='str')
    dex: Optional[str]
    intelligence: Optional[str] = Field(None, alias='int')
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
    strength: Optional[str] = Field(None, alias='str')
    dex: Optional[str]
    intelligence: Optional[str] = Field(None, alias='int')
    luk: Optional[str]
    max_hp: Optional[str]
    max_mp: Optional[str]
    attack_power: Optional[str]
    magic_power: Optional[str]
    armor: Optional[str]
    speed: Optional[str]
    jump: Optional[str]


class ItemStarforceOptionSchema(BaseModel):
    strength: Optional[str] = Field(None, alias='str')
    dex: Optional[str]
    intelligence: Optional[str] = Field(None, alias='int')
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
    scroll_upgradable_count: Optional[str] = Field(default=None, validation_alias='scroll_upgradeable_count')
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
    date: Optional[datetime]
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
    date: Optional[datetime]
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
    option_type: Optional[str] = None
    option_value: Optional[str] = None


class CashItemColoringPrismSchema(BaseModel):
    color_range: str
    hue: int
    saturation: int
    value: int


class CashItemEquipmentSchema(BaseModel):
    cash_item_equipment_part: Optional[str]
    cash_item_equipment_slot: Optional[str]
    cash_item_name: Optional[str]
    cash_item_icon: Optional[str]
    cash_item_description: Optional[str]
    cash_item_option: Optional[List[CashItemOptionSchema]] = []
    date_expire: Optional[datetime]
    cash_item_coloring_prism: Optional[CashItemColoringPrismSchema] = None
    date_option_expire: Optional[datetime]
    cash_item_label: Optional[str]
    android_item_gender: Optional[str] = None


class CharacterCashItemEquipmentSchema(BaseModel):
    date: Optional[datetime] = None
    character_gender: Optional[str] = None
    character_class: Optional[str] = None
    character_look_mode: Optional[str] = None
    preset_no: Optional[int] = None
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
    character_class: str
    symbol: List[SymbolSchema]


class CharacterSymbolEquipmentSchema(BaseModel):
    date: Optional[datetime]
    character_class: str
    symbol: List[SymbolSchema]


class CharacterSkillGradeSchema(BaseModel):
    skill_name: str
    skill_description: str
    skill_level: int
    skill_effect: Optional[str]
    skill_effect_next: Optional[str]
    skill_icon: str


class CharacterSkillSchema(BaseModel):
    date: Optional[datetime]
    character_class: Optional[str] = None
    character_skill_grade: Optional[str] = None
    character_skill: Optional[List[CharacterSkillGradeSchema]] = None


class LinkSkillSchema(BaseModel):
    skill_name: str
    skill_description: str
    skill_level: int
    skill_effect: str
    skill_icon: str


class CharacterLinkSkillSchema(BaseModel):
    date: Optional[datetime]
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
    v_core_name: Optional[str]
    v_core_type: Optional[str]
    v_core_level: int
    v_core_skill_1: Optional[str]
    v_core_skill_2: Optional[str]
    v_core_skill_3: Optional[str]


class CharacterVMatrixSchema(BaseModel):
    date: Optional[datetime]
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
    date: Optional[datetime]
    character_hexa_core_equipment: Optional[List[HexaCoreSchema]] = None


class HexaStatCoreSchema(BaseModel):
    slot_id: str
    main_stat_name: Optional[str] = None
    sub_stat_name_1: Optional[str] = None
    sub_stat_name_2: Optional[str] = None
    main_stat_level: Optional[int] = None
    sub_stat_level_1: Optional[int] = None
    sub_stat_level_2: Optional[int] = None
    stat_grade: Optional[int] = None


class CharacterHexaStatSchema(BaseModel):
    date: Optional[datetime]
    character_class: str
    character_hexa_stat_core: List[HexaStatCoreSchema]
    character_hexa_stat_core_2: List[HexaStatCoreSchema]
    preset_hexa_stat_core: List[HexaStatCoreSchema]
    preset_hexa_stat_core_2: List[HexaStatCoreSchema]


class CharacterHexaMatrixStatSchema(BaseModel):
    date: Optional[datetime]
    character_class: Optional[str] = None
    character_hexa_stat_core: Optional[List[HexaStatCoreSchema]] = None
    character_hexa_stat_core_2: Optional[List[HexaStatCoreSchema]] = None
    preset_hexa_stat_core: Optional[List[HexaStatCoreSchema]] = None
    preset_hexa_stat_core_2: Optional[List[HexaStatCoreSchema]] = None


class CharacterDojangSchema(BaseModel):
    date: Optional[datetime]
    character_class: str
    world_name: str
    dojang_best_floor: int
    date_dojang_record: Optional[str]
    dojang_best_time: int


class CharacterSetEffectSchema(BaseModel):
    date: Optional[datetime]
    set_effect: List[Dict[str, Any]]


class BeautyEquipmentSchema(BaseModel):
    hair_name: Optional[str] = None
    face_name: Optional[str] = None
    skin_name: Optional[str] = None
    base_color: Optional[str] = None
    mix_color: Optional[str] = None
    mix_rate: Optional[str] = None


class HairSchema(BaseModel):
    hair_name: Optional[str]
    base_color: Optional[str]
    mix_color: Optional[str]
    mix_rate: Optional[str]


class FaceSchema(BaseModel):
    face_name: Optional[str]
    base_color: Optional[str]
    mix_color: Optional[str]
    mix_rate: Optional[str]


class SkinSchema(BaseModel):
    skin_name: Optional[str]
    color_style: Optional[str]
    hue: Optional[int]
    saturation: Optional[int]
    brightness: Optional[int]


class CharacterBeautyEquipmentSchema(BaseModel):
    date: Optional[datetime]
    character_gender: str
    character_class: str
    character_hair: HairSchema
    character_face: FaceSchema
    character_skin: SkinSchema


class AndroidEquipmentPresetSchema(BaseModel):
    android_name: Optional[str] = ''
    android_nickname: Optional[str] = ''
    android_icon: Optional[str] = ''
    android_description: Optional[str] = None
    android_gender: Optional[str] = None
    android_grade: Optional[str] = None
    android_skin: Optional[SkinSchema] = None
    android_hair: Optional[HairSchema] = None
    android_face: Optional[FaceSchema] = None
    android_ear_sensor_clip_flag: Optional[str] = None
    android_non_humanoid_flag: Optional[str] = None
    android_shop_usable_flag: Optional[str] = None


class AndroidEquipmentSchema(BaseModel):
    date: Optional[datetime]
    android_name: Optional[str] = ''
    android_nickname: Optional[str] = ''
    android_icon: Optional[str] = ''
    android_description: Optional[str] = None
    android_hair: Optional[HairSchema] = None
    android_face: Optional[FaceSchema] = None
    android_skin: Optional[SkinSchema] = None
    android_cash_item_equipment: Optional[List[CashItemEquipmentSchema]] = []
    android_ear_sensor_clip_flag: Optional[str]
    android_gender: Optional[str]
    android_grade: Optional[str]
    android_non_humanoid_flag: Optional[str]
    android_shop_usable_flag: Optional[str]
    preset_no: Optional[int] = 1
    android_preset_1: Optional[AndroidEquipmentPresetSchema] = None
    android_preset_2: Optional[AndroidEquipmentPresetSchema] = None
    android_preset_3: Optional[AndroidEquipmentPresetSchema] = None


class PetSkillSchema(BaseModel):
    skill_name: str


class PetEquipmentSchema(BaseModel):
    item_name: Optional[str]
    item_icon: Optional[str]
    item_description: Optional[str] = None


class CharacterPetEquipmentSchema(BaseModel):
    date: Optional[datetime]
    pet_1_name: Optional[str]
    pet_1_nickname: Optional[str]
    pet_1_icon: Optional[str]
    pet_1_description: Optional[str]
    pet_1_equipment: Optional[PetEquipmentSchema]
    pet_1_skill: Optional[List[str]]
    pet_1_pet_type: Optional[str]
    pet_1_date_expire: Optional[str]

    pet_2_name: Optional[str]
    pet_2_nickname: Optional[str]
    pet_2_icon: Optional[str]
    pet_2_description: Optional[str]
    pet_2_equipment: Optional[PetEquipmentSchema]
    pet_2_skill: Optional[List[str]]
    pet_2_pet_type: Optional[str]
    pet_2_date_expire: Optional[str]

    pet_3_name: Optional[str]
    pet_3_nickname: Optional[str]
    pet_3_icon: Optional[str]
    pet_3_description: Optional[str]
    pet_3_equipment: Optional[PetEquipmentSchema]
    pet_3_skill: Optional[List[str]]
    pet_3_pet_type: Optional[str]
    pet_3_date_expire: Optional[str]


class CharacterPropensitySchema(BaseModel):
    date: Optional[datetime]
    charisma_level: int
    sensibility_level: int
    insight_level: int
    willingness_level: int
    handicraft_level: int
    charm_level: int


class CharacterHyperStatSchema(BaseModel):
    date: Optional[datetime]
    character_class: str
    use_preset_no: str
    use_available_hyper_stat: int
    hyper_stat_preset_1: List[Dict[str, Any]]
    hyper_stat_preset_1_remain_point: int
    hyper_stat_preset_2: List[Dict[str, Any]]
    hyper_stat_preset_2_remain_point: int
    hyper_stat_preset_3: List[Dict[str, Any]]
    hyper_stat_preset_3_remain_point: int


class CharacterAllDataSchema(BaseModel):
    basic: Optional[CharacterBasicSchema]
    popularity: Optional[CharacterPopularitySchema]
    stat: Optional[CharacterStatSchema]
    ability: Optional[CharacterAbilitySchema]
    item_equipment: Optional[CharacterItemEquipmentSchema]
    cashitem_equipment: Optional[CharacterCashItemEquipmentSchema]
    symbol: Optional[CharacterSymbolSchema]
    link_skill: Optional[CharacterLinkSkillSchema]
    skill: Optional[CharacterSkillSchema]
    hexamatrix: Optional[CharacterHexaMatrixSchema]
    hexamatrix_stat: Optional[CharacterHexaMatrixStatSchema]
    vmatrix: Optional[CharacterVMatrixSchema]
    dojang: Optional[CharacterDojangSchema]
    set_effect: Optional[CharacterSetEffectSchema]
    beauty_equipment: Optional[CharacterBeautyEquipmentSchema]
    android_equipment: Optional[AndroidEquipmentSchema]
    pet_equipment: Optional[CharacterPetEquipmentSchema]
    propensity: Optional[CharacterPropensitySchema]
    hyper_stat: Optional[CharacterHyperStatSchema]


class InventoryItemSchema(BaseModel):
    """
    인벤토리 아이템 스키마

    크롤링된 인벤토리 아이템 데이터를 검증합니다.
    """
    item_type: Literal['equips', 'consumables', 'miscs', 'installables', 'cashes'] = Field(
        default='miscs',
        description='아이템 유형 (장비/소비/기타/설치/캐시)'
    )
    item_name: str = Field(..., min_length=1, max_length=255, description='아이템 이름')
    item_icon: str = Field(..., pattern=r'^https?://.+', description='아이템 아이콘 URL')
    quantity: int = Field(default=1, ge=1, description='아이템 수량 (1개 이상)')
    item_options: Optional[Dict[str, Any]] = Field(None, description='아이템 옵션 (강화, 잠재능력 등)')
    slot_position: int = Field(..., ge=0, description='슬롯 위치 (0부터 시작)')
    expiry_date: Optional[datetime] = Field(None, description='기간제 아이템 만료 날짜')
    detail_url: Optional[str] = Field(None, description='아이템 상세 페이지 URL (AC 2.3.8)')

    class Config:
        json_schema_extra = {
            "example": {
                "item_name": "엘릭서",
                "item_icon": "https://maplestory.io/api/item/2000005/icon",
                "quantity": 100,
                "slot_position": 0,
                "item_options": {
                    "enhancement": 0,
                    "potential": None
                },
                "expiry_date": None
            }
        }


class StorageItemSchema(BaseModel):
    """
    창고 아이템 스키마 (Story 2.4)

    크롤링된 창고 아이템 데이터를 검증합니다.
    """
    storage_type: str = Field(default='storage', description='창고 유형')
    item_name: str = Field(..., min_length=1, max_length=255, description='아이템 이름')
    item_icon: str = Field(..., pattern=r'^https?://.+', description='아이템 아이콘 URL')
    quantity: int = Field(default=1, ge=1, description='아이템 수량 (1개 이상)')
    item_options: Optional[Dict[str, Any]] = Field(None, description='아이템 옵션 (강화, 잠재능력 등)')
    slot_position: int = Field(..., ge=0, description='슬롯 위치 (0부터 시작)')
    expiry_date: Optional[datetime] = Field(None, description='기간제 아이템 만료 날짜')

    class Config:
        json_schema_extra = {
            "example": {
                "storage_type": "storage",
                "item_name": "엘릭서",
                "item_icon": "https://maplestory.io/api/item/2000005/icon",
                "quantity": 200,
                "slot_position": 0,
                "item_options": None,
                "expiry_date": None
            }
        }


class ItemDetailSchema(BaseModel):
    """
    아이템 상세 정보 스키마

    크롤링된 아이템 상세 정보를 검증합니다.
    """
    # 기본 정보
    item_category: Optional[str] = Field(None, description='장비 분류')
    required_level: Optional[int] = Field(None, ge=0, le=300, description='착용 가능 레벨')
    required_job: Optional[str] = Field(None, description='착용 가능 직업')

    # 스탯
    attack_power: Optional[int] = Field(None, ge=0, description='공격력')
    magic_power: Optional[int] = Field(None, ge=0, description='마력')
    str_stat: Optional[int] = Field(None, ge=0, description='STR')
    dex_stat: Optional[int] = Field(None, ge=0, description='DEX')
    int_stat: Optional[int] = Field(None, ge=0, description='INT')
    luk_stat: Optional[int] = Field(None, ge=0, description='LUK')
    hp_stat: Optional[int] = Field(None, ge=0, description='HP')
    mp_stat: Optional[int] = Field(None, ge=0, description='MP')
    defense: Optional[int] = Field(None, ge=0, description='방어력')
    all_stat: Optional[int] = Field(None, ge=0, description='올스탯')
    boss_damage: Optional[int] = Field(None, ge=0, le=100, description='보스 공격력 증가 (%)')
    ignore_defense: Optional[int] = Field(None, ge=0, le=100, description='방어율 무시 (%)')

    # 강화
    upgrade_count: Optional[int] = Field(None, ge=0, description='업그레이드 가능 횟수')
    upgrades_used: Optional[int] = Field(None, ge=0, description='사용한 업그레이드 횟수')

    # 잠재능력
    potential_grade: Optional[str] = Field(None, description='잠재능력 등급')
    potential_option_1: Optional[str] = Field(None, description='잠재능력 옵션 1')
    potential_option_2: Optional[str] = Field(None, description='잠재능력 옵션 2')
    potential_option_3: Optional[str] = Field(None, description='잠재능력 옵션 3')

    # 에디셔널 잠재능력
    additional_potential_grade: Optional[str] = Field(None, description='에디셔널 잠재능력 등급')
    additional_potential_option_1: Optional[str] = Field(None, description='에디셔널 잠재능력 옵션 1')
    additional_potential_option_2: Optional[str] = Field(None, description='에디셔널 잠재능력 옵션 2')
    additional_potential_option_3: Optional[str] = Field(None, description='에디셔널 잠재능력 옵션 3')

    # 소울
    soul_name: Optional[str] = Field(None, description='소울 이름')
    soul_option: Optional[str] = Field(None, description='소울 옵션')

    class Config:
        json_schema_extra = {
            "example": {
                "item_category": "무기",
                "required_level": 200,
                "attack_power": 171,
                "magic_power": 283,
                "str_stat": 0,
                "int_stat": 150,
                "boss_damage": 30,
                "ignore_defense": 15,
                "potential_grade": "유니크",
                "potential_option_1": "INT +9%",
                "potential_option_2": "마력 +9%",
                "potential_option_3": "보스 공격력 +30%"
            }
        }
