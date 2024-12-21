from django.db import models


class CharacterBasic(models.Model):
    ocid = models.CharField(max_length=255, help_text="캐릭터 식별자")
    date = models.DateTimeField(
        help_text="조회 기준일 (KST)", null=True, blank=True)
    character_name = models.CharField(max_length=255, help_text="캐릭터 명")
    world_name = models.CharField(max_length=255, help_text="월드 명")
    character_gender = models.CharField(max_length=10, help_text="캐릭터 성별")
    character_class = models.CharField(max_length=255, help_text="캐릭터 직업")
    character_class_level = models.CharField(
        max_length=50, help_text="캐릭터 전직 차수")
    character_level = models.IntegerField(help_text="캐릭터 레벨")
    character_exp = models.BigIntegerField(help_text="현재 레벨에서 보유한 경험치")
    character_exp_rate = models.CharField(
        max_length=10, help_text="현재 레벨에서 경험치 퍼센트")
    character_guild_name = models.CharField(
        max_length=255, null=True, blank=True, help_text="캐릭터 소속 길드 명")
    character_image = models.URLField(help_text="캐릭터 외형 이미지")
    character_date_create = models.DateTimeField(
        help_text="캐릭터 생성일 (KST)", null=True, blank=True)
    access_flag = models.BooleanField(help_text="최근 7일간 접속 여부")
    liberation_quest_clear_flag = models.BooleanField(help_text="해방 퀘스트 완료 여부")

    def __str__(self):
        return f"{self.character_name} - Lv.{self.character_level} {self.character_class}"


class CharacterPopularity(models.Model):
    character = models.ForeignKey(
        CharacterBasic, on_delete=models.CASCADE, related_name="popularity")
    date = models.DateTimeField(help_text="조회 기준일", null=True, blank=True)
    popularity = models.BigIntegerField(help_text="캐릭터 인기도")

    def __str__(self):
        return f"Popularity: {self.popularity} on {self.date}"


class ItemTotalOption(models.Model):
    str = models.CharField(max_length=50, null=True, blank=True)
    dex = models.CharField(max_length=50, null=True, blank=True)
    int = models.CharField(max_length=50, null=True, blank=True)
    luk = models.CharField(max_length=50, null=True, blank=True)
    max_hp = models.CharField(max_length=50, null=True, blank=True)
    max_mp = models.CharField(max_length=50, null=True, blank=True)
    attack_power = models.CharField(max_length=50, null=True, blank=True)
    magic_power = models.CharField(max_length=50, null=True, blank=True)
    armor = models.CharField(max_length=50, null=True, blank=True)
    speed = models.CharField(max_length=50, null=True, blank=True)
    jump = models.CharField(max_length=50, null=True, blank=True)
    boss_damage = models.CharField(max_length=50, null=True, blank=True)
    ignore_monster_armor = models.CharField(
        max_length=50, null=True, blank=True)
    all_stat = models.CharField(max_length=50, null=True, blank=True)
    damage = models.CharField(max_length=50, null=True, blank=True)
    equipment_level_decrease = models.IntegerField(null=True, blank=True)
    max_hp_rate = models.CharField(max_length=50, null=True, blank=True)
    max_mp_rate = models.CharField(max_length=50, null=True, blank=True)


class ItemBaseOption(models.Model):
    str = models.CharField(max_length=50, null=True, blank=True)
    dex = models.CharField(max_length=50, null=True, blank=True)
    int = models.CharField(max_length=50, null=True, blank=True)
    luk = models.CharField(max_length=50, null=True, blank=True)
    max_hp = models.CharField(max_length=50, null=True, blank=True)
    max_mp = models.CharField(max_length=50, null=True, blank=True)
    attack_power = models.CharField(max_length=50, null=True, blank=True)
    magic_power = models.CharField(max_length=50, null=True, blank=True)
    armor = models.CharField(max_length=50, null=True, blank=True)
    speed = models.CharField(max_length=50, null=True, blank=True)
    jump = models.CharField(max_length=50, null=True, blank=True)
    boss_damage = models.CharField(max_length=50, null=True, blank=True)
    ignore_monster_armor = models.CharField(
        max_length=50, null=True, blank=True)
    all_stat = models.CharField(max_length=50, null=True, blank=True)
    max_hp_rate = models.CharField(max_length=50, null=True, blank=True)
    max_mp_rate = models.CharField(max_length=50, null=True, blank=True)
    base_equipment_level = models.IntegerField(null=True, blank=True)


class ItemExceptionalOption(models.Model):
    str = models.CharField(max_length=50, null=True, blank=True)
    dex = models.CharField(max_length=50, null=True, blank=True)
    int = models.CharField(max_length=50, null=True, blank=True)
    luk = models.CharField(max_length=50, null=True, blank=True)
    max_hp = models.CharField(max_length=50, null=True, blank=True)
    max_mp = models.CharField(max_length=50, null=True, blank=True)
    attack_power = models.CharField(max_length=50, null=True, blank=True)
    magic_power = models.CharField(max_length=50, null=True, blank=True)
    exceptional_upgrade = models.IntegerField(null=True, blank=True)


class ItemAddOption(models.Model):
    str = models.CharField(max_length=50, null=True, blank=True)
    dex = models.CharField(max_length=50, null=True, blank=True)
    int = models.CharField(max_length=50, null=True, blank=True)
    luk = models.CharField(max_length=50, null=True, blank=True)
    max_hp = models.CharField(max_length=50, null=True, blank=True)
    max_mp = models.CharField(max_length=50, null=True, blank=True)
    attack_power = models.CharField(max_length=50, null=True, blank=True)
    magic_power = models.CharField(max_length=50, null=True, blank=True)
    armor = models.CharField(max_length=50, null=True, blank=True)
    speed = models.CharField(max_length=50, null=True, blank=True)
    jump = models.CharField(max_length=50, null=True, blank=True)
    boss_damage = models.CharField(max_length=50, null=True, blank=True)
    damage = models.CharField(max_length=50, null=True, blank=True)
    all_stat = models.CharField(max_length=50, null=True, blank=True)
    equipment_level_decrease = models.IntegerField(null=True, blank=True)


class ItemEtcOption(models.Model):
    str = models.CharField(max_length=50, null=True, blank=True)
    dex = models.CharField(max_length=50, null=True, blank=True)
    int = models.CharField(max_length=50, null=True, blank=True)
    luk = models.CharField(max_length=50, null=True, blank=True)
    max_hp = models.CharField(max_length=50, null=True, blank=True)
    max_mp = models.CharField(max_length=50, null=True, blank=True)
    attack_power = models.CharField(max_length=50, null=True, blank=True)
    magic_power = models.CharField(max_length=50, null=True, blank=True)
    armor = models.CharField(max_length=50, null=True, blank=True)
    speed = models.CharField(max_length=50, null=True, blank=True)
    jump = models.CharField(max_length=50, null=True, blank=True)


class ItemStarforceOption(models.Model):
    str = models.CharField(max_length=50, null=True, blank=True)
    dex = models.CharField(max_length=50, null=True, blank=True)
    int = models.CharField(max_length=50, null=True, blank=True)
    luk = models.CharField(max_length=50, null=True, blank=True)
    max_hp = models.CharField(max_length=50, null=True, blank=True)
    max_mp = models.CharField(max_length=50, null=True, blank=True)
    attack_power = models.CharField(max_length=50, null=True, blank=True)
    magic_power = models.CharField(max_length=50, null=True, blank=True)
    armor = models.CharField(max_length=50, null=True, blank=True)
    speed = models.CharField(max_length=50, null=True, blank=True)
    jump = models.CharField(max_length=50, null=True, blank=True)


class Title(models.Model):
    title_name = models.CharField(max_length=255)
    title_icon = models.URLField()
    title_description = models.TextField()
    date_expire = models.DateTimeField(null=True, blank=True)
    date_option_expire = models.DateTimeField(null=True, blank=True)


class CharacterItemEquipment(models.Model):
    character = models.ForeignKey(
        CharacterBasic, on_delete=models.CASCADE, related_name='equipments')
    date = models.DateTimeField(help_text="조회 기준일", null=True, blank=True)
    character_gender = models.CharField(max_length=10)
    character_class = models.CharField(max_length=255)
    preset_no = models.IntegerField()
    item_equipment_part = models.CharField(max_length=50)
    item_equipment_slot = models.CharField(max_length=50)
    item_name = models.CharField(max_length=255)
    item_icon = models.URLField()
    item_description = models.TextField(null=True, blank=True)
    item_shape_name = models.CharField(max_length=255, null=True, blank=True)
    item_shape_icon = models.URLField(null=True, blank=True)
    item_gender = models.CharField(max_length=10, null=True, blank=True)
    item_total_option = models.OneToOneField(
        ItemTotalOption, on_delete=models.CASCADE)
    item_base_option = models.OneToOneField(
        ItemBaseOption, on_delete=models.CASCADE)
    potential_option_flag = models.CharField(max_length=10)
    additional_potential_option_flag = models.CharField(max_length=10)
    potential_option_grade = models.CharField(
        max_length=50, null=True, blank=True)
    additional_potential_option_grade = models.CharField(
        max_length=50, null=True, blank=True)
    potential_option_1 = models.CharField(
        max_length=255, null=True, blank=True)
    potential_option_2 = models.CharField(
        max_length=255, null=True, blank=True)
    potential_option_3 = models.CharField(
        max_length=255, null=True, blank=True)
    additional_potential_option_1 = models.CharField(
        max_length=255, null=True, blank=True)
    additional_potential_option_2 = models.CharField(
        max_length=255, null=True, blank=True)
    additional_potential_option_3 = models.CharField(
        max_length=255, null=True, blank=True)
    equipment_level_increase = models.IntegerField(null=True, blank=True)
    item_exceptional_option = models.OneToOneField(
        ItemExceptionalOption, on_delete=models.CASCADE, null=True, blank=True)
    item_add_option = models.OneToOneField(
        ItemAddOption, on_delete=models.CASCADE, null=True, blank=True)
    growth_exp = models.IntegerField(null=True, blank=True)
    growth_level = models.IntegerField(null=True, blank=True)
    scroll_upgrade = models.CharField(max_length=10)
    cuttable_count = models.CharField(max_length=10)
    golden_hammer_flag = models.CharField(max_length=10)
    scroll_resilience_count = models.CharField(max_length=10)
    scroll_upgradable_count = models.CharField(max_length=10)
    soul_name = models.CharField(max_length=255, null=True, blank=True)
    soul_option = models.CharField(max_length=255, null=True, blank=True)
    item_etc_option = models.OneToOneField(
        ItemEtcOption, on_delete=models.CASCADE)
    starforce = models.CharField(max_length=10)
    starforce_scroll_flag = models.CharField(max_length=10)
    item_starforce_option = models.OneToOneField(
        ItemStarforceOption, on_delete=models.CASCADE)
    special_ring_level = models.IntegerField(null=True, blank=True)
    date_expire = models.DateTimeField(null=True, blank=True)
    title = models.OneToOneField(
        Title, on_delete=models.CASCADE, null=True, blank=True)
    is_dragon_equipment = models.BooleanField(default=False)
    is_mechanic_equipment = models.BooleanField(default=False)


class CharacterStat(models.Model):
    character = models.ForeignKey(
        CharacterBasic, on_delete=models.CASCADE, related_name="stats")
    date = models.DateTimeField(null=True, blank=True)
    character_class = models.CharField(max_length=255)
    remain_ap = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.character_class} Stats on {self.date}"


class StatDetail(models.Model):
    character_stat = models.ForeignKey(
        CharacterStat, related_name='final_stat', on_delete=models.CASCADE)
    stat_name = models.CharField(max_length=255)
    stat_value = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"{self.stat_name}: {self.stat_value}"


class AbilityInfo(models.Model):
    ability_no = models.CharField(max_length=10)
    ability_grade = models.CharField(max_length=50)
    ability_value = models.CharField(max_length=255)


class AbilityPreset(models.Model):
    ability_preset_grade = models.CharField(max_length=50)
    ability_info = models.ManyToManyField(AbilityInfo)


class CharacterAbility(models.Model):
    character = models.ForeignKey(
        CharacterBasic, on_delete=models.CASCADE, related_name='abilities')
    date = models.DateTimeField(null=True, blank=True)
    ability_grade = models.CharField(max_length=50)
    ability_info = models.ManyToManyField(AbilityInfo)
    remain_fame = models.IntegerField()
    preset_no = models.IntegerField()
    ability_preset_1 = models.OneToOneField(
        AbilityPreset, on_delete=models.CASCADE, related_name='preset_1')
    ability_preset_2 = models.OneToOneField(
        AbilityPreset, on_delete=models.CASCADE, related_name='preset_2')
    ability_preset_3 = models.OneToOneField(
        AbilityPreset, on_delete=models.CASCADE, related_name='preset_3')


class CashItemOption(models.Model):
    option_type = models.CharField(max_length=50)
    option_value = models.CharField(max_length=255)


class CashItemColoringPrism(models.Model):
    color_range = models.CharField(max_length=50)
    hue = models.IntegerField()
    saturation = models.IntegerField()
    value = models.IntegerField()


class CashItemEquipment(models.Model):
    cash_item_equipment_part = models.CharField(max_length=50)
    cash_item_equipment_slot = models.CharField(max_length=50)
    cash_item_name = models.CharField(max_length=255)
    cash_item_icon = models.URLField()
    cash_item_description = models.TextField()
    cash_item_option = models.ManyToManyField(CashItemOption)
    date_expire = models.DateTimeField(null=True, blank=True)
    date_option_expire = models.DateTimeField(null=True, blank=True)
    cash_item_label = models.CharField(max_length=50, null=True, blank=True)
    cash_item_coloring_prism = models.OneToOneField(
        CashItemColoringPrism, on_delete=models.CASCADE, null=True, blank=True)
    item_gender = models.CharField(max_length=10, null=True, blank=True)


class CharacterCashItemEquipment(models.Model):
    character = models.ForeignKey(
        CharacterBasic, on_delete=models.CASCADE, related_name='cash_equipments')
    date = models.DateTimeField(null=True, blank=True)
    character_gender = models.CharField(max_length=10)
    character_class = models.CharField(max_length=255)
    character_look_mode = models.CharField(max_length=10)
    preset_no = models.IntegerField()
    cash_item_equipment_base = models.ManyToManyField(
        CashItemEquipment, related_name='base_equipment')
    cash_item_equipment_preset_1 = models.ManyToManyField(
        CashItemEquipment, related_name='preset_1')
    cash_item_equipment_preset_2 = models.ManyToManyField(
        CashItemEquipment, related_name='preset_2')
    cash_item_equipment_preset_3 = models.ManyToManyField(
        CashItemEquipment, related_name='preset_3')
    additional_cash_item_equipment_base = models.ManyToManyField(
        CashItemEquipment, related_name='additional_base')
    additional_cash_item_equipment_preset_1 = models.ManyToManyField(
        CashItemEquipment, related_name='additional_preset_1')
    additional_cash_item_equipment_preset_2 = models.ManyToManyField(
        CashItemEquipment, related_name='additional_preset_2')
    additional_cash_item_equipment_preset_3 = models.ManyToManyField(
        CashItemEquipment, related_name='additional_preset_3')


class Symbol(models.Model):
    symbol_name = models.CharField(max_length=255)
    symbol_icon = models.URLField()
    symbol_description = models.TextField()
    symbol_force = models.CharField(max_length=50)
    symbol_level = models.IntegerField()
    symbol_str = models.CharField(max_length=50, null=True, blank=True)
    symbol_dex = models.CharField(max_length=50, null=True, blank=True)
    symbol_int = models.CharField(max_length=50, null=True, blank=True)
    symbol_luk = models.CharField(max_length=50, null=True, blank=True)
    symbol_hp = models.CharField(max_length=50, null=True, blank=True)
    symbol_drop_rate = models.CharField(max_length=50, null=True, blank=True)
    symbol_meso_rate = models.CharField(max_length=50, null=True, blank=True)
    symbol_exp_rate = models.CharField(max_length=50, null=True, blank=True)
    symbol_growth_count = models.IntegerField()
    symbol_require_growth_count = models.IntegerField()


class CharacterSymbolEquipment(models.Model):
    character = models.ForeignKey(
        CharacterBasic, on_delete=models.CASCADE, related_name='symbols')
    date = models.DateTimeField(null=True, blank=True)
    character_class = models.CharField(max_length=255)
    symbol = models.ManyToManyField(Symbol)


class CharacterSkillGrade(models.Model):
    skill_name = models.CharField(max_length=255)
    skill_description = models.TextField()
    skill_level = models.IntegerField()
    skill_effect = models.TextField()
    skill_effect_next = models.TextField(null=True, blank=True)
    skill_icon = models.URLField()


class CharacterSkill(models.Model):
    character = models.ForeignKey(
        CharacterBasic, on_delete=models.CASCADE, related_name='skills')
    date = models.DateTimeField(null=True, blank=True)
    character_class = models.CharField(max_length=255)
    character_skill_grade = models.CharField(max_length=50)
    character_skill = models.ManyToManyField(CharacterSkillGrade)


class LinkSkill(models.Model):
    skill_name = models.CharField(max_length=255)
    skill_description = models.TextField()
    skill_level = models.IntegerField()
    skill_effect = models.TextField()
    skill_icon = models.URLField()


class CharacterLinkSkill(models.Model):
    character = models.ForeignKey(
        CharacterBasic, on_delete=models.CASCADE, related_name='link_skills')
    date = models.DateTimeField(null=True, blank=True)
    character_class = models.CharField(max_length=255)
    character_link_skill = models.OneToOneField(
        LinkSkill, on_delete=models.CASCADE, null=True, blank=True, related_name='main_link')
    character_link_skill_preset_1 = models.ManyToManyField(
        LinkSkill, related_name='preset_1')
    character_link_skill_preset_2 = models.ManyToManyField(
        LinkSkill, related_name='preset_2')
    character_link_skill_preset_3 = models.ManyToManyField(
        LinkSkill, related_name='preset_3')
    character_owned_link_skill = models.OneToOneField(
        LinkSkill, on_delete=models.CASCADE, null=True, blank=True, related_name='owned_link')
    character_owned_link_skill_preset_1 = models.OneToOneField(
        LinkSkill, on_delete=models.CASCADE, null=True, blank=True, related_name='owned_preset_1')
    character_owned_link_skill_preset_2 = models.OneToOneField(
        LinkSkill, on_delete=models.CASCADE, null=True, blank=True, related_name='owned_preset_2')
    character_owned_link_skill_preset_3 = models.OneToOneField(
        LinkSkill, on_delete=models.CASCADE, null=True, blank=True, related_name='owned_preset_3')


class VCore(models.Model):
    slot_id = models.CharField(max_length=50)
    slot_level = models.IntegerField()
    v_core_name = models.CharField(max_length=255)
    v_core_type = models.CharField(max_length=50)
    v_core_level = models.IntegerField()
    v_core_skill_1 = models.CharField(max_length=255)
    v_core_skill_2 = models.CharField(max_length=255, null=True, blank=True)
    v_core_skill_3 = models.CharField(max_length=255, null=True, blank=True)


class CharacterVMatrix(models.Model):
    character = models.ForeignKey(
        CharacterBasic, on_delete=models.CASCADE, related_name='v_matrix')
    date = models.DateTimeField(null=True, blank=True)
    character_class = models.CharField(max_length=255)
    character_v_core_equipment = models.ManyToManyField(VCore)
    character_v_matrix_remain_slot_upgrade_point = models.IntegerField()


class HexaSkill(models.Model):
    hexa_skill_id = models.CharField(max_length=255)


class HexaCore(models.Model):
    hexa_core_name = models.CharField(max_length=255)
    hexa_core_level = models.IntegerField()
    hexa_core_type = models.CharField(max_length=50)
    linked_skill = models.ManyToManyField(HexaSkill)


class CharacterHexaMatrix(models.Model):
    character = models.ForeignKey(
        CharacterBasic, on_delete=models.CASCADE, related_name='hexa_matrix')
    date = models.DateTimeField(null=True, blank=True)
    character_hexa_core_equipment = models.ManyToManyField(HexaCore)


class HexaStatCore(models.Model):
    slot_id = models.CharField(max_length=50)
    main_stat_name = models.CharField(max_length=255)
    sub_stat_name_1 = models.CharField(max_length=255)
    sub_stat_name_2 = models.CharField(max_length=255)
    main_stat_level = models.IntegerField()
    sub_stat_level_1 = models.IntegerField()
    sub_stat_level_2 = models.IntegerField()
    stat_grade = models.IntegerField()


class CharacterHexaMatrixStat(models.Model):
    character = models.ForeignKey(
        CharacterBasic, on_delete=models.CASCADE, related_name='hexa_stats')
    date = models.DateTimeField(null=True, blank=True)
    character_class = models.CharField(max_length=255)
    character_hexa_stat_core = models.ManyToManyField(
        HexaStatCore, related_name='main_stats')
    character_hexa_stat_core_2 = models.ManyToManyField(
        HexaStatCore, related_name='secondary_stats')
    preset_hexa_stat_core = models.ManyToManyField(
        HexaStatCore, related_name='preset_stats')
    preset_hexa_stat_core_2 = models.ManyToManyField(
        HexaStatCore, related_name='preset_secondary_stats')


class CharacterDojang(models.Model):
    character = models.ForeignKey(
        CharacterBasic, on_delete=models.CASCADE, related_name='dojang')
    date = models.DateTimeField(null=True, blank=True)
    character_class = models.CharField(max_length=255)
    world_name = models.CharField(max_length=255)
    dojang_best_floor = models.IntegerField()
    date_dojang_record = models.DateTimeField(null=True, blank=True)
    dojang_best_time = models.IntegerField()
