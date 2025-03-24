from django.db import models
from django.utils import timezone
from django.db import transaction


class CharacterBasic(models.Model):
    ocid = models.CharField(max_length=255, unique=True)
    character_name = models.CharField(max_length=255)
    world_name = models.CharField(max_length=255)
    character_gender = models.CharField(max_length=10)
    character_class = models.CharField(max_length=255)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['ocid']),
            models.Index(fields=['character_name'])
        ]

    def __str__(self):
        return f"{self.character_name} ({self.ocid})"


class CharacterBasicHistory(models.Model):
    character = models.ForeignKey(
        CharacterBasic, on_delete=models.CASCADE, related_name='history')
    date = models.DateTimeField()
    character_name = models.CharField(max_length=255)  # 닉네임 히스토리 추가
    character_class = models.CharField(max_length=255)
    character_class_level = models.CharField(max_length=50)
    character_level = models.IntegerField()
    character_exp = models.BigIntegerField()
    character_exp_rate = models.CharField(max_length=10)
    character_guild_name = models.CharField(
        max_length=255, null=True, blank=True)
    character_image = models.TextField()
    character_date_create = models.DateTimeField(null=True, blank=True)
    access_flag = models.BooleanField()
    liberation_quest_clear_flag = models.BooleanField()

    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['character', '-date']),
            models.Index(fields=['character_name'])  # 닉네임 검색을 위한 인덱스 추가
        ]

    def __str__(self):
        return f"{self.character_name} ({self.character.ocid}) - {self.date}"


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
    title_shape_name = models.CharField(max_length=255, null=True, blank=True)
    title_shape_icon = models.URLField(null=True, blank=True)
    title_shape_description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.title_name

    @classmethod
    def create_from_data(cls, title_data):
        if not title_data:
            return None

        return cls.objects.create(
            title_name=title_data.get('title_name'),
            title_icon=title_data.get('title_icon'),
            title_description=title_data.get('title_description'),
            date_expire=title_data.get('date_expire'),
            date_option_expire=title_data.get('date_option_expire'),
            title_shape_name=title_data.get('title_shape_name'),
            title_shape_icon=title_data.get('title_shape_icon'),
            title_shape_description=title_data.get('title_shape_description')
        )


class MedalShape(models.Model):
    medal_shape_name = models.CharField(max_length=255)
    medal_shape_icon = models.TextField()
    medal_shape_description = models.TextField()
    medal_shape_changed_name = models.CharField(
        max_length=255, null=True, blank=True)
    medal_shape_changed_icon = models.TextField(null=True, blank=True)
    medal_shape_changed_description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.medal_shape_name


class CharacterItemEquipment(models.Model):
    character = models.ForeignKey(
        CharacterBasic, on_delete=models.CASCADE, related_name='equipments')
    date = models.DateTimeField(help_text="조회 기준일", null=True, blank=True)
    character_gender = models.CharField(max_length=10)
    character_class = models.CharField(max_length=255)
    preset_no = models.IntegerField(null=True, blank=True)
    item_equipment = models.ManyToManyField(
        'ItemEquipment', related_name='character_equipments')
    item_equipment_preset_1 = models.ManyToManyField(
        'ItemEquipment', related_name='character_preset_1')
    item_equipment_preset_2 = models.ManyToManyField(
        'ItemEquipment', related_name='character_preset_2')
    item_equipment_preset_3 = models.ManyToManyField(
        'ItemEquipment', related_name='character_preset_3')
    title = models.ForeignKey(
        'Title', on_delete=models.SET_NULL, null=True, blank=True)
    medal_shape = models.OneToOneField(
        'MedalShape', on_delete=models.SET_NULL, null=True, blank=True, related_name='character_medal_shape')
    dragon_equipment = models.ManyToManyField(
        'ItemEquipment', related_name='character_dragon_equipment', blank=True)
    mechanic_equipment = models.ManyToManyField(
        'ItemEquipment', related_name='character_mechanic_equipment', blank=True)

    @classmethod
    def create_from_data(cls, character, data):
        """
        캐릭터 장비 정보를 생성하는 클래스 메서드

        Args:
            character (CharacterBasic): 캐릭터 객체
            data (dict): API로부터 받은 데이터

        Returns:
            CharacterItemEquipment: 생성된 장비 정보 객체
        """
        try:
            # 기본 객체 생성
            item_equipment = cls.objects.create(
                character=character,
                date=data.get('date'),
                character_gender=data.get('character_gender'),
                character_class=data.get('character_class'),
                preset_no=data.get('preset_no')
            )

            # Title 처리
            if 'title' in data and data['title']:
                title = Title.create_from_data(data['title'])
                item_equipment.title = title
                item_equipment.save()

            # 각 장비 세트 처리
            equipment_fields = [
                'item_equipment',
                'item_equipment_preset_1',
                'item_equipment_preset_2',
                'item_equipment_preset_3',
                'dragon_equipment',
                'mechanic_equipment'
            ]

            for field in equipment_fields:
                if field in data and data[field]:
                    # ItemEquipment의 bulk_create_from_data 활용
                    created_equipments = ItemEquipment.bulk_create_from_data(
                        data[field])
                    if created_equipments:
                        getattr(item_equipment, field).add(*created_equipments)

            return item_equipment

        except Exception as e:
            raise Exception(f"장비 정보 생성 중 오류 발생: {str(e)}")


class ItemEquipment(models.Model):
    item_equipment_part = models.CharField(max_length=50)
    item_equipment_slot = models.CharField(max_length=50)
    item_name = models.CharField(max_length=255)
    item_icon = models.URLField()
    item_description = models.TextField(null=True, blank=True)
    item_shape_name = models.CharField(max_length=255, null=True, blank=True)
    item_shape_icon = models.URLField(null=True, blank=True)
    item_gender = models.CharField(max_length=10, null=True, blank=True)
    item_total_option = models.OneToOneField(
        'ItemTotalOption', on_delete=models.CASCADE, null=True, blank=True)
    item_base_option = models.OneToOneField(
        'ItemBaseOption', on_delete=models.CASCADE, null=True, blank=True)
    potential_option_flag = models.CharField(
        max_length=10, null=True, blank=True)
    additional_potential_option_flag = models.CharField(
        max_length=10, null=True, blank=True)
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
        'ItemExceptionalOption', on_delete=models.SET_NULL, null=True, blank=True)
    item_add_option = models.OneToOneField(
        'ItemAddOption', on_delete=models.SET_NULL, null=True, blank=True)
    growth_exp = models.IntegerField(null=True, blank=True)
    growth_level = models.IntegerField(null=True, blank=True)
    scroll_upgrade = models.CharField(max_length=10, null=True, blank=True)
    cuttable_count = models.CharField(max_length=10, null=True, blank=True)
    golden_hammer_flag = models.CharField(max_length=10, null=True, blank=True)
    scroll_resilience_count = models.CharField(
        max_length=10, null=True, blank=True)
    scroll_upgradable_count = models.CharField(
        max_length=10, null=True, blank=True)
    soul_name = models.CharField(max_length=255, null=True, blank=True)
    soul_option = models.CharField(max_length=255, null=True, blank=True)
    item_etc_option = models.OneToOneField(
        'ItemEtcOption', on_delete=models.CASCADE, null=True, blank=True)
    starforce = models.CharField(max_length=10, null=True, blank=True)
    starforce_scroll_flag = models.CharField(
        max_length=10, null=True, blank=True)
    item_starforce_option = models.OneToOneField(
        'ItemStarforceOption', on_delete=models.CASCADE, null=True, blank=True)
    special_ring_level = models.IntegerField(null=True, blank=True)
    date_expire = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.item_name}"

    @classmethod
    @transaction.atomic
    def bulk_create_from_data(cls, equipment_data_list):
        """여러 장비 데이터를 한 번에 생성"""
        if not equipment_data_list:
            return []

        option_models = {
            'item_total_option': ItemTotalOption,
            'item_base_option': ItemBaseOption,
            'item_exceptional_option': ItemExceptionalOption,
            'item_add_option': ItemAddOption,
            'item_etc_option': ItemEtcOption,
            'item_starforce_option': ItemStarforceOption
        }

        created_equipments = []

        for equip_data in equipment_data_list:
            equip_data_copy = equip_data.copy()
            option_objects = {}

            # 각 옵션 객체 생성
            for option_name, model in option_models.items():
                if option_name in equip_data_copy and equip_data_copy[option_name]:
                    option_objects[option_name] = model.objects.create(
                        **equip_data_copy[option_name])
                    del equip_data_copy[option_name]

            # 장비 객체 생성 시 옵션 객체들을 함께 설정
            equipment = cls(**equip_data_copy)
            for option_name, option_obj in option_objects.items():
                setattr(equipment, option_name, option_obj)
            equipment.save()

            created_equipments.append(equipment)

        return created_equipments


class CharacterStat(models.Model):
    character = models.ForeignKey(
        CharacterBasic, on_delete=models.CASCADE, related_name="stats")
    date = models.DateTimeField(null=True, blank=True)
    character_class = models.CharField(max_length=255)
    remain_ap = models.IntegerField(default=0)
    final_stat = models.ManyToManyField(
        'StatDetail', related_name='character_final_stat', blank=True)

    def __str__(self):
        return f"{self.character_class} Stats on {self.date}"


class StatDetail(models.Model):
    character_stat = models.ForeignKey(
        CharacterStat, related_name='stat_details', on_delete=models.CASCADE)
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
    preset_no = models.IntegerField(null=True, blank=True)
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
    cash_item_icon = models.TextField()
    cash_item_description = models.TextField(null=True, blank=True)
    cash_item_option = models.ManyToManyField(CashItemOption)
    date_expire = models.DateTimeField(null=True, blank=True)
    date_option_expire = models.DateTimeField(null=True, blank=True)
    cash_item_label = models.CharField(max_length=50, null=True, blank=True)
    cash_item_coloring_prism = models.OneToOneField(
        CashItemColoringPrism, on_delete=models.CASCADE, null=True, blank=True)
    item_gender = models.CharField(max_length=10, null=True, blank=True)
    android_item_gender = models.CharField(
        max_length=10, null=True, blank=True)
    skill = models.JSONField(null=True, blank=True)  # 스킬 정보를 저장하기 위한 필드 추가


class CharacterCashItemEquipment(models.Model):
    character = models.ForeignKey(
        CharacterBasic, on_delete=models.CASCADE, related_name='cash_equipments')
    date = models.DateTimeField(null=True, blank=True)
    character_gender = models.CharField(max_length=10)
    character_class = models.CharField(max_length=255)
    character_look_mode = models.CharField(max_length=10)
    preset_no = models.IntegerField(null=True, blank=True)
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

    @classmethod
    def create_from_data(cls, character, data):
        """
        캐릭터 캐시 장비 정보를 생성하는 클래스 메서드

        Args:
            character (CharacterBasic): 캐릭터 객체
            data (dict): API로부터 받은 데이터

        Returns:
            CharacterCashItemEquipment: 생성된 캐시 장비 정보 객체
        """
        try:
            # 기본 객체 생성
            cash_equipment = cls.objects.create(
                character=character,
                date=data.get('date'),
                character_gender=data.get('character_gender'),
                character_class=data.get('character_class'),
                character_look_mode=data.get('character_look_mode'),
                preset_no=data.get('preset_no', 1)
            )

            # 캐시 장비 처리 함수
            def process_cash_items(items_data):
                if not items_data:
                    return []

                cash_items = []
                for item_data in items_data:
                    # 캐시 아이템 옵션 데이터 분리
                    cash_item_option_data = item_data.pop(
                        'cash_item_option', [])
                    cash_item_coloring_prism_data = item_data.pop(
                        'cash_item_coloring_prism', None)

                    # CashItemEquipment 생성
                    cash_item = CashItemEquipment.objects.create(**item_data)

                    # CashItemOption 처리
                    for option_data in cash_item_option_data:
                        option = CashItemOption.objects.create(**option_data)
                        cash_item.cash_item_option.add(option)

                    # CashItemColoringPrism 처리
                    if cash_item_coloring_prism_data:
                        coloring_prism = CashItemColoringPrism.objects.create(
                            **cash_item_coloring_prism_data)
                        cash_item.cash_item_coloring_prism = coloring_prism
                        cash_item.save()

                    cash_items.append(cash_item)
                return cash_items

            # 각 장비 세트 처리
            equipment_fields = {
                'cash_item_equipment_base': 'cash_item_equipment_base',
                'cash_item_equipment_preset_1': 'cash_item_equipment_preset_1',
                'cash_item_equipment_preset_2': 'cash_item_equipment_preset_2',
                'cash_item_equipment_preset_3': 'cash_item_equipment_preset_3',
                'additional_cash_item_equipment_base': 'additional_cash_item_equipment_base',
                'additional_cash_item_equipment_preset_1': 'additional_cash_item_equipment_preset_1',
                'additional_cash_item_equipment_preset_2': 'additional_cash_item_equipment_preset_2',
                'additional_cash_item_equipment_preset_3': 'additional_cash_item_equipment_preset_3'
            }

            for field_name, attr_name in equipment_fields.items():
                if field_name in data and data[field_name]:
                    cash_items = process_cash_items(data[field_name])
                    getattr(cash_equipment, attr_name).add(*cash_items)

            return cash_equipment

        except Exception as e:
            raise Exception(f"캐시 장비 정보 생성 중 오류 발생: {str(e)}")


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

    def __str__(self):
        return f"{self.symbol_name} Lv.{self.symbol_level}"


class CharacterSymbolEquipment(models.Model):
    character = models.ForeignKey(
        CharacterBasic, on_delete=models.CASCADE, related_name='symbols')
    date = models.DateTimeField(null=True, blank=True)
    character_class = models.CharField(max_length=255)
    symbol = models.ManyToManyField(Symbol)

    def __str__(self):
        return f"{self.character.character_name}의 심볼 장착 정보"


class Skill(models.Model):
    skill_name = models.CharField(max_length=255)
    skill_description = models.TextField()
    skill_level = models.IntegerField()
    skill_effect = models.TextField()
    skill_effect_next = models.TextField(null=True, blank=True)
    skill_icon = models.TextField()


class CharacterSkill(models.Model):
    character = models.ForeignKey(
        CharacterBasic, on_delete=models.CASCADE, related_name='skills')
    date = models.DateTimeField(null=True, blank=True)
    character_class = models.CharField(max_length=255, null=True, blank=True)
    character_skill_grade = models.CharField(
        max_length=50, null=True, blank=True)
    character_skill = models.ManyToManyField(
        Skill)


class LinkSkill(models.Model):
    skill_name = models.CharField(max_length=100)
    skill_description = models.TextField(null=True, blank=True)
    skill_level = models.IntegerField(null=True, blank=True)
    skill_effect = models.TextField(null=True, blank=True)
    skill_effect_next = models.TextField(null=True, blank=True)
    skill_icon = models.URLField(max_length=500, null=True, blank=True)

    @classmethod
    def bulk_create_from_data(cls, data_list):
        if not data_list:
            return []

        skills = []
        for data in data_list:
            skill = cls.objects.create(
                skill_name=data.get('skill_name', ''),
                skill_description=data.get('skill_description', ''),
                skill_level=data.get('skill_level', 0),
                skill_effect=data.get('skill_effect', ''),
                skill_effect_next=data.get('skill_effect_next'),
                skill_icon=data.get('skill_icon', '')
            )
            skills.append(skill)

        return skills


class CharacterLinkSkill(models.Model):
    character = models.ForeignKey(
        CharacterBasic, on_delete=models.CASCADE, related_name='link_skills')
    date = models.DateTimeField(null=True, blank=True)
    character_class = models.CharField(max_length=255)
    character_link_skill = models.ManyToManyField(
        LinkSkill, related_name='main_link', blank=True)
    character_link_skill_preset_1 = models.ManyToManyField(
        LinkSkill, related_name='preset_1')
    character_link_skill_preset_2 = models.ManyToManyField(
        LinkSkill, related_name='preset_2')
    character_link_skill_preset_3 = models.ManyToManyField(
        LinkSkill, related_name='preset_3')
    character_owned_link_skill = models.OneToOneField(
        LinkSkill, on_delete=models.CASCADE, null=True, related_name='owned_link', blank=True)
    character_owned_link_skill_preset_1 = models.OneToOneField(
        LinkSkill, on_delete=models.CASCADE, null=True, blank=True, related_name='owned_preset_1')
    character_owned_link_skill_preset_2 = models.OneToOneField(
        LinkSkill, on_delete=models.CASCADE, null=True, blank=True, related_name='owned_preset_2')
    character_owned_link_skill_preset_3 = models.OneToOneField(
        LinkSkill, on_delete=models.CASCADE, null=True, blank=True, related_name='owned_preset_3')

    @classmethod
    def create_from_data(cls, character, data):
        """
        캐릭터 링크 스킬 정보를 생성하는 클래스 메서드

        Args:
            character (CharacterBasic): 캐릭터 객체
            data (dict): API로부터 받은 데이터

        Returns:
            CharacterLinkSkill: 생성된 링크 스킬 정보 객체
        """
        try:
            # 기존 데이터가 있으면 업데이트, 없으면 생성
            link_skill, created = cls.objects.get_or_create(
                character=character,
                date=data.get('date'),
                defaults={
                    'character_class': data.get('character_class')
                }
            )

            if not created:
                link_skill.character_class = data.get('character_class')
                link_skill.save()

            # 기본 링크 스킬 처리
            if 'character_link_skill' in data and data['character_link_skill']:
                link_skill.character_link_skill.clear()
                skills = LinkSkill.bulk_create_from_data(
                    data['character_link_skill'])
                if skills:
                    link_skill.character_link_skill.add(*skills)

            # 보유 링크 스킬 처리
            if 'character_owned_link_skill' in data and data['character_owned_link_skill']:
                owned_skills = LinkSkill.bulk_create_from_data(
                    [data['character_owned_link_skill']])
                if owned_skills:
                    link_skill.character_owned_link_skill = owned_skills[0]
                    link_skill.save()

            # 프리셋 처리
            preset_fields = {
                'character_link_skill_preset_1': 'character_link_skill_preset_1',
                'character_link_skill_preset_2': 'character_link_skill_preset_2',
                'character_link_skill_preset_3': 'character_link_skill_preset_3'
            }

            for field_name, attr_name in preset_fields.items():
                if field_name in data and isinstance(data[field_name], list):
                    getattr(link_skill, attr_name).clear()
                    skills = LinkSkill.bulk_create_from_data(data[field_name])
                    if skills:
                        getattr(link_skill, attr_name).add(*skills)

            # 프리셋 보유 링크 스킬 처리
            preset_owned_fields = {
                'character_owned_link_skill_preset_1': 'character_owned_link_skill_preset_1',
                'character_owned_link_skill_preset_2': 'character_owned_link_skill_preset_2',
                'character_owned_link_skill_preset_3': 'character_owned_link_skill_preset_3'
            }

            for field_name, attr_name in preset_owned_fields.items():
                if field_name in data and data[field_name]:
                    skills = LinkSkill.bulk_create_from_data(
                        [data[field_name]])
                    if skills:
                        setattr(link_skill, attr_name, skills[0])
                        link_skill.save()

            return link_skill

        except Exception as e:
            raise Exception(f"링크 스킬 정보 생성 중 오류 발생: {str(e)}")


class VCore(models.Model):
    slot_id = models.CharField(max_length=10, null=True, blank=True)
    slot_level = models.IntegerField(default=0)
    v_core_name = models.CharField(max_length=100, null=True, blank=True)
    v_core_level = models.IntegerField(default=0)
    v_core_type = models.CharField(max_length=50, null=True, blank=True)
    v_core_skill_1 = models.CharField(max_length=100, null=True, blank=True)
    v_core_skill_2 = models.CharField(max_length=100, null=True, blank=True)
    v_core_skill_3 = models.CharField(max_length=100, null=True, blank=True)

    @classmethod
    def bulk_create_from_data(cls, data_list):
        if not data_list:
            return []

        cores = []
        for data in data_list:
            if isinstance(data, dict) and data.get('v_core_name'):  # v_core_name이 있는 경우만 처리
                core = cls.objects.create(
                    slot_id=data.get('slot_id'),
                    slot_level=data.get('slot_level', 0),
                    v_core_name=data.get('v_core_name'),
                    v_core_level=data.get('v_core_level', 0),
                    v_core_type=data.get('v_core_type'),
                    v_core_skill_1=data.get('v_core_skill_1'),
                    v_core_skill_2=data.get('v_core_skill_2'),
                    v_core_skill_3=data.get('v_core_skill_3')
                )
                cores.append(core)

        return cores


class CharacterVMatrix(models.Model):
    character = models.ForeignKey(
        CharacterBasic, on_delete=models.CASCADE, related_name='v_matrix')
    date = models.DateTimeField(null=True, blank=True)
    character_class = models.CharField(max_length=255)
    character_v_core_equipment = models.ManyToManyField(VCore)
    character_v_matrix_remain_slot_upgrade_point = models.IntegerField()


class HexaSkill(models.Model):
    hexa_skill_id = models.CharField(max_length=255)

    def __str__(self):
        return self.hexa_skill_id

    @classmethod
    def get_or_create_from_data(cls, skill_data):
        skill_id = skill_data.get('hexa_skill_id')
        return cls.objects.get_or_create(hexa_skill_id=skill_id)[0]


class HexaCore(models.Model):
    hexa_core_name = models.CharField(max_length=255)
    hexa_core_level = models.IntegerField()
    hexa_core_type = models.CharField(max_length=50)
    linked_skill = models.ManyToManyField(HexaSkill)

    def __str__(self):
        return f"{self.hexa_core_name} Lv.{self.hexa_core_level}"


class CharacterHexaMatrix(models.Model):
    character = models.ForeignKey(
        CharacterBasic, on_delete=models.CASCADE, related_name='hexa_matrix')
    date = models.DateTimeField(null=True, blank=True)
    character_hexa_core_equipment = models.ManyToManyField(HexaCore)

    @classmethod
    def create_from_data(cls, character, data):
        """
        캐릭터 헥사 매트릭스 정보를 생성하는 클래스 메서드

        Args:
            character (CharacterBasic): 캐릭터 객체
            data (dict): API로부터 받은 데이터

        Returns:
            CharacterHexaMatrix: 생성된 헥사 매트릭스 정보 객체
        """
        try:
            # 기존 데이터가 있으면 업데이트, 없으면 생성
            hexa_matrix, created = cls.objects.get_or_create(
                character=character,
                date=data.get('date')
            )

            # 헥사 코어 장비 처리
            if 'character_hexa_core_equipment' in data:
                # 기존 데이터 삭제
                hexa_matrix.character_hexa_core_equipment.clear()

                for core_data in data['character_hexa_core_equipment']:
                    # 헥사 코어 생성
                    core = HexaCore.objects.create(
                        hexa_core_name=core_data.get('hexa_core_name'),
                        hexa_core_level=core_data.get('hexa_core_level'),
                        hexa_core_type=core_data.get('hexa_core_type')
                    )

                    # linked_skill 처리
                    if 'linked_skill' in core_data:
                        for skill_data in core_data['linked_skill']:
                            skill = HexaSkill.objects.create(
                                hexa_skill_id=skill_data.get('hexa_skill_id')
                            )
                            core.linked_skill.add(skill)

                    hexa_matrix.character_hexa_core_equipment.add(core)

            return hexa_matrix

        except Exception as e:
            raise Exception(f"헥사 매트릭스 정보 생성 중 오류 발생: {str(e)}")


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
        HexaStatCore, related_name='core_1')
    character_hexa_stat_core_2 = models.ManyToManyField(
        HexaStatCore, related_name='core_2')
    character_hexa_stat_core_3 = models.ManyToManyField(
        HexaStatCore, related_name='core_3')
    preset_hexa_stat_core = models.ManyToManyField(
        HexaStatCore, related_name='preset_core_1')
    preset_hexa_stat_core_2 = models.ManyToManyField(
        HexaStatCore, related_name='preset_core_2')
    preset_hexa_stat_core_3 = models.ManyToManyField(
        HexaStatCore, related_name='preset_core_3')

    def __str__(self):
        return f"{self.character.character_name}의 헥사 스탯 코어 정보"

    @classmethod
    def create_from_data(cls, character, data):
        """
        캐릭터 헥사 스탯 정보를 생성하는 클래스 메서드

        Args:
            character (CharacterBasic): 캐릭터 객체
            data (dict): API로부터 받은 데이터

        Returns:
            CharacterHexaMatrixStat: 생성된 헥사 스탯 정보 객체
        """
        try:
            # 기본 객체 생성
            hexa_matrix_stat = cls.objects.create(
                character=character,
                date=data.get('date'),
                character_class=data.get('character_class')
            )

            # 헥사 스탯 코어 처리 함수
            def process_hexa_stat_cores(core_list):
                cores = []
                if not core_list:
                    return cores

                for core_data in core_list:
                    core = HexaStatCore.objects.create(
                        slot_id=core_data.get('slot_id'),
                        main_stat_name=core_data.get('main_stat_name'),
                        sub_stat_name_1=core_data.get('sub_stat_name_1'),
                        sub_stat_name_2=core_data.get('sub_stat_name_2'),
                        main_stat_level=core_data.get('main_stat_level'),
                        sub_stat_level_1=core_data.get('sub_stat_level_1'),
                        sub_stat_level_2=core_data.get('sub_stat_level_2'),
                        stat_grade=core_data.get('stat_grade')
                    )
                    cores.append(core)
                return cores

            # 각 코어 타입별 처리
            core_fields = [
                'character_hexa_stat_core',
                'character_hexa_stat_core_2',
                'character_hexa_stat_core_3',
                'preset_hexa_stat_core',
                'preset_hexa_stat_core_2',
                'preset_hexa_stat_core_3'
            ]

            for field in core_fields:
                if field in data and data[field]:
                    cores = process_hexa_stat_cores(data[field])
                    if cores:
                        getattr(hexa_matrix_stat, field).add(*cores)

            return hexa_matrix_stat

        except Exception as e:
            raise Exception(f"헥사 스탯 정보 생성 중 오류 발생: {str(e)}")


class CharacterDojang(models.Model):
    character = models.ForeignKey(
        CharacterBasic, on_delete=models.CASCADE, related_name='dojang')
    date = models.DateTimeField(null=True, blank=True)
    character_class = models.CharField(max_length=255)
    world_name = models.CharField(max_length=255)
    dojang_best_floor = models.IntegerField()
    date_dojang_record = models.DateTimeField(null=True, blank=True)
    dojang_best_time = models.IntegerField()

    @classmethod
    def create_from_data(cls, character, data):
        """
        캐릭터 무릉도장 정보를 생성하는 클래스 메서드

        Args:
            character (CharacterBasic): 캐릭터 객체
            data (dict): API로부터 받은 데이터

        Returns:
            CharacterDojang: 생성된 무릉도장 정보 객체
        """
        try:
            dojang = cls.objects.create(
                character=character,
                date=data.get('date'),
                character_class=data.get('character_class'),
                world_name=data.get('world_name'),
                dojang_best_floor=data.get('dojang_best_floor'),
                date_dojang_record=data.get('date_dojang_record'),
                dojang_best_time=data.get('dojang_best_time')
            )
            return dojang

        except Exception as e:
            raise Exception(f"무릉도장 정보 생성 중 오류 발생: {str(e)}")


class CharacterSetEffect(models.Model):
    character = models.ForeignKey(
        CharacterBasic, on_delete=models.CASCADE, related_name='set_effects')
    date = models.DateTimeField(null=True, blank=True)
    set_effect = models.JSONField()  # 세트 효과는 동적 필드가 많아 JSONField로 저장

    def __str__(self):
        return f"{self.character.character_name}의 세트 효과"


class Hair(models.Model):
    hair_name = models.CharField(max_length=255, null=True, blank=True)
    base_color = models.CharField(max_length=50, null=True, blank=True)
    mix_color = models.CharField(max_length=50, null=True, blank=True)
    mix_rate = models.IntegerField(null=True, blank=True)


class Face(models.Model):
    face_name = models.CharField(max_length=255, null=True, blank=True)
    base_color = models.CharField(max_length=50, null=True, blank=True)
    mix_color = models.CharField(max_length=50, null=True, blank=True)
    mix_rate = models.IntegerField(null=True, blank=True)


class Skin(models.Model):
    skin_name = models.CharField(max_length=255, null=True, blank=True)
    color_style = models.CharField(max_length=50, null=True, blank=True)
    hue = models.IntegerField(null=True, blank=True)
    saturation = models.IntegerField(null=True, blank=True)
    brightness = models.IntegerField(null=True, blank=True)


class CharacterBeautyEquipment(models.Model):
    character = models.ForeignKey(
        CharacterBasic, on_delete=models.CASCADE, related_name='beauty_equipments')
    date = models.DateTimeField(null=True, blank=True)
    character_gender = models.CharField(max_length=10)
    character_class = models.CharField(max_length=255)
    character_hair = models.OneToOneField(
        Hair, on_delete=models.SET_NULL, null=True, blank=True, related_name='character_hair')
    character_face = models.OneToOneField(
        Face, on_delete=models.SET_NULL, null=True, blank=True, related_name='character_face')
    character_skin = models.OneToOneField(
        Skin, on_delete=models.SET_NULL, null=True, blank=True, related_name='character_skin')
    additional_character_hair = models.OneToOneField(
        Hair, on_delete=models.SET_NULL, null=True, blank=True, related_name='additional_character_hair')
    additional_character_face = models.OneToOneField(
        Face, on_delete=models.SET_NULL, null=True, blank=True, related_name='additional_character_face')
    additional_character_skin = models.OneToOneField(
        Skin, on_delete=models.SET_NULL, null=True, blank=True, related_name='additional_character_skin')

    def __str__(self):
        return f"{self.character.character_name}의 성형/헤어 정보"

    @classmethod
    def create_from_data(cls, character, data):
        """
        캐릭터 성형/헤어 정보를 생성하는 클래스 메서드

        Args:
            character (CharacterBasic): 캐릭터 객체
            data (dict): API로부터 받은 데이터

        Returns:
            CharacterBeautyEquipment: 생성된 성형/헤어 정보 객체
        """
        try:
            # 기본 객체 생성
            beauty_equipment = cls.objects.create(
                character=character,
                date=data.get('date'),
                character_gender=data.get('character_gender'),
                character_class=data.get('character_class')
            )

            # Hair, Face, Skin 객체 생성 및 연결
            if data.get('character_hair'):
                hair = Hair.objects.create(**data['character_hair'])
                beauty_equipment.character_hair = hair

            if data.get('character_face'):
                face = Face.objects.create(**data['character_face'])
                beauty_equipment.character_face = face

            if data.get('character_skin'):
                skin = Skin.objects.create(**data['character_skin'])
                beauty_equipment.character_skin = skin

            # 추가 Hair, Face, Skin 객체 생성 및 연결
            if data.get('additional_character_hair'):
                additional_hair = Hair.objects.create(
                    **data['additional_character_hair'])
                beauty_equipment.additional_character_hair = additional_hair

            if data.get('additional_character_face'):
                additional_face = Face.objects.create(
                    **data['additional_character_face'])
                beauty_equipment.additional_character_face = additional_face

            if data.get('additional_character_skin'):
                additional_skin = Skin.objects.create(
                    **data['additional_character_skin'])
                beauty_equipment.additional_character_skin = additional_skin

            beauty_equipment.save()
            return beauty_equipment

        except Exception as e:
            raise Exception(f"성형/헤어 정보 생성 중 오류 발생: {str(e)}")


class AndroidEquipmentPreset(models.Model):
    android_name = models.CharField(max_length=255)
    android_nickname = models.CharField(max_length=255)
    android_icon = models.TextField()
    android_description = models.TextField(null=True, blank=True)
    android_gender = models.CharField(max_length=50, null=True, blank=True)
    android_grade = models.CharField(max_length=50, null=True, blank=True)
    android_hair = models.OneToOneField(
        Hair, on_delete=models.SET_NULL, null=True, blank=True, related_name='preset_android_hair')
    android_face = models.OneToOneField(
        Face, on_delete=models.SET_NULL, null=True, blank=True, related_name='preset_android_face')
    android_skin = models.OneToOneField(
        Skin, on_delete=models.SET_NULL, null=True, blank=True, related_name='preset_android_skin')
    android_ear_sensor_clip_flag = models.CharField(
        max_length=50, null=True, blank=True)
    android_non_humanoid_flag = models.CharField(
        max_length=50, null=True, blank=True)
    android_shop_usable_flag = models.CharField(
        max_length=50, null=True, blank=True)


class AndroidEquipment(models.Model):
    character = models.ForeignKey(
        CharacterBasic, on_delete=models.CASCADE, related_name='android_equipments')
    date = models.DateTimeField(null=True, blank=True)
    android_name = models.CharField(max_length=255)
    android_nickname = models.CharField(max_length=255)
    android_icon = models.TextField()
    android_description = models.TextField(null=True, blank=True)
    android_hair = models.OneToOneField(
        Hair, on_delete=models.SET_NULL, null=True, blank=True, related_name='android_hair')
    android_face = models.OneToOneField(
        Face, on_delete=models.SET_NULL, null=True, blank=True, related_name='android_face')
    android_skin = models.OneToOneField(
        Skin, on_delete=models.SET_NULL, null=True, blank=True, related_name='android_skin')
    android_cash_item_equipment = models.ManyToManyField(CashItemEquipment)
    android_ear_sensor_clip_flag = models.CharField(
        max_length=50, null=True, blank=True)
    android_gender = models.CharField(max_length=50, null=True, blank=True)
    android_grade = models.CharField(max_length=50, null=True, blank=True)
    android_non_humanoid_flag = models.CharField(
        max_length=50, null=True, blank=True)
    android_shop_usable_flag = models.CharField(
        max_length=50, null=True, blank=True)
    preset_no = models.IntegerField(default=1)
    android_preset_1 = models.ForeignKey(
        AndroidEquipmentPreset, on_delete=models.SET_NULL, null=True, blank=True, related_name='preset_1')
    android_preset_2 = models.ForeignKey(
        AndroidEquipmentPreset, on_delete=models.SET_NULL, null=True, blank=True, related_name='preset_2')
    android_preset_3 = models.ForeignKey(
        AndroidEquipmentPreset, on_delete=models.SET_NULL, null=True, blank=True, related_name='preset_3')

    def __str__(self):
        return f"{self.character.character_name}의 안드로이드 정보"


class PetItemEquipment(models.Model):
    item_name = models.CharField(max_length=255)
    item_icon = models.TextField()
    item_description = models.TextField(null=True, blank=True)
    item_option = models.JSONField(null=True, blank=True)
    item_shape = models.CharField(max_length=50, null=True, blank=True)
    item_shape_icon = models.TextField(null=True, blank=True)


class PetAutoSkill(models.Model):
    skill_1 = models.CharField(max_length=255)
    skill_1_icon = models.TextField(null=True, blank=True)
    skill_2 = models.CharField(max_length=255)
    skill_2_icon = models.TextField(null=True, blank=True)


class PetEquipment(models.Model):
    pet_name = models.CharField(max_length=255)
    pet_nickname = models.CharField(max_length=255)
    pet_icon = models.TextField()
    pet_description = models.TextField(null=True, blank=True)
    pet_equipment = models.OneToOneField(
        PetItemEquipment, on_delete=models.SET_NULL, null=True, blank=True)
    pet_auto_skill = models.OneToOneField(
        PetAutoSkill, on_delete=models.SET_NULL, null=True, blank=True)
    pet_pet_type = models.CharField(max_length=50, null=True, blank=True)
    pet_skill = models.JSONField(null=True, blank=True)
    pet_date_expire = models.DateTimeField(null=True, blank=True)
    pet_appearance = models.CharField(max_length=50, null=True, blank=True)
    pet_appearance_icon = models.TextField(null=True, blank=True)


class CharacterPetEquipment(models.Model):
    character = models.ForeignKey(
        CharacterBasic, on_delete=models.CASCADE, related_name='pet_equipments')
    date = models.DateTimeField(null=True, blank=True)
    pet_equipment = models.ManyToManyField(PetEquipment)

    def __str__(self):
        return f"{self.character.character_name}의 펫 정보"

    @classmethod
    def create_from_data(cls, character, data):
        """
        캐릭터 펫 장비 정보를 생성하는 클래스 메서드

        Args:
            character (CharacterBasic): 캐릭터 객체
            data (dict): API로부터 받은 데이터

        Returns:
            CharacterPetEquipment: 생성된 펫 장비 정보 객체
        """
        try:
            # 기본 객체 생성
            pet_equipment = cls.objects.create(
                character=character,
                date=data.get('date')
            )

            # 펫 1~3 처리
            for i in range(1, 4):
                prefix = f'pet_{i}'

                # 필수 필드가 없으면 건너뛰기
                if f'{prefix}_name' not in data:
                    continue

                # PetItemEquipment 생성
                pet_item_equipment = None
                if f'{prefix}_equipment' in data and data[f'{prefix}_equipment']:
                    pet_item_data = data[f'{prefix}_equipment']
                    pet_item_equipment = PetItemEquipment.objects.create(
                        item_name=pet_item_data.get('item_name'),
                        item_icon=pet_item_data.get('item_icon'),
                        item_description=pet_item_data.get('item_description'),
                        item_option=pet_item_data.get('item_option'),
                        item_shape=pet_item_data.get('item_shape'),
                        item_shape_icon=pet_item_data.get('item_shape_icon')
                    )

                # PetAutoSkill 생성 (자동 스킬 정보가 있는 경우)
                pet_auto_skill = None
                if f'{prefix}_auto_skill' in data and data[f'{prefix}_auto_skill']:
                    auto_skill_data = data[f'{prefix}_auto_skill']
                    pet_auto_skill = PetAutoSkill.objects.create(
                        skill_1=auto_skill_data.get('skill_1'),
                        skill_1_icon=auto_skill_data.get('skill_1_icon'),
                        skill_2=auto_skill_data.get('skill_2'),
                        skill_2_icon=auto_skill_data.get('skill_2_icon')
                    )

                # PetEquipment 생성
                pet = PetEquipment.objects.create(
                    pet_name=data.get(f'{prefix}_name'),
                    pet_nickname=data.get(f'{prefix}_nickname'),
                    pet_icon=data.get(f'{prefix}_icon'),
                    pet_description=data.get(f'{prefix}_description'),
                    pet_equipment=pet_item_equipment,
                    pet_auto_skill=pet_auto_skill,
                    pet_pet_type=data.get(f'{prefix}_pet_type'),
                    pet_skill=data.get(f'{prefix}_skill'),
                    pet_date_expire=data.get(f'{prefix}_date_expire'),
                    pet_appearance=data.get(f'{prefix}_appearance'),
                    pet_appearance_icon=data.get(f'{prefix}_appearance_icon')
                )

                pet_equipment.pet_equipment.add(pet)

            return pet_equipment

        except Exception as e:
            raise Exception(f"펫 장비 정보 생성 중 오류 발생: {str(e)}")


class CharacterPropensity(models.Model):
    character = models.ForeignKey(
        CharacterBasic, on_delete=models.CASCADE, related_name='propensities')
    date = models.DateTimeField(null=True, blank=True)
    charisma_level = models.IntegerField()
    sensibility_level = models.IntegerField()
    insight_level = models.IntegerField()
    willingness_level = models.IntegerField()
    handicraft_level = models.IntegerField()
    charm_level = models.IntegerField()

    def __str__(self):
        return f"{self.character.character_name}의 성향 정보"


class HyperStatPreset(models.Model):
    stat_type = models.CharField(max_length=50)
    stat_point = models.IntegerField(
        null=True, blank=True, default=0)  # NULL 허용
    stat_level = models.IntegerField(default=0)
    stat_increase = models.CharField(
        max_length=50, null=True, blank=True)  # NULL 허용

    def __str__(self):
        return f"{self.stat_type} Lv.{self.stat_level} ({self.stat_point} 포인트)"


class CharacterHyperStat(models.Model):
    character = models.ForeignKey(
        CharacterBasic, on_delete=models.CASCADE, related_name='hyper_stats')
    date = models.DateTimeField(null=True, blank=True)
    character_class = models.CharField(max_length=255)
    use_preset_no = models.IntegerField(null=True, blank=True)
    use_available_hyper_stat = models.IntegerField(null=True, blank=True)
    hyper_stat_preset_1 = models.ManyToManyField(
        HyperStatPreset, related_name='preset_1')
    hyper_stat_preset_2 = models.ManyToManyField(
        HyperStatPreset, related_name='preset_2')
    hyper_stat_preset_3 = models.ManyToManyField(
        HyperStatPreset, related_name='preset_3')
    hyper_stat_preset_1_remain_point = models.IntegerField()
    hyper_stat_preset_2_remain_point = models.IntegerField()
    hyper_stat_preset_3_remain_point = models.IntegerField()

    def __str__(self):
        return f"{self.character.character_name}의 하이퍼스탯 정보"

    @classmethod
    def create_from_data(cls, character, data):
        """
        캐릭터 하이퍼스탯 정보를 생성하는 클래스 메서드

        Args:
            character (CharacterBasic): 캐릭터 객체
            data (dict): API로부터 받은 데이터

        Returns:
            CharacterHyperStat: 생성된 하이퍼스탯 정보 객체
        """
        try:
            # 기본 객체 생성
            hyper_stat = cls.objects.create(
                character=character,
                date=data.get('date'),
                character_class=data.get('character_class'),
                use_preset_no=data.get('use_preset_no'),
                use_available_hyper_stat=data.get('use_available_hyper_stat'),
                hyper_stat_preset_1_remain_point=data.get(
                    'hyper_stat_preset_1_remain_point', 0),
                hyper_stat_preset_2_remain_point=data.get(
                    'hyper_stat_preset_2_remain_point', 0),
                hyper_stat_preset_3_remain_point=data.get(
                    'hyper_stat_preset_3_remain_point', 0)
            )

            # 하이퍼스탯 프리셋 처리 함수
            def process_hyper_stat_preset(preset_data):
                if not preset_data:
                    return []

                presets = []
                for stat_data in preset_data:
                    preset = HyperStatPreset.objects.create(
                        stat_type=stat_data.get('stat_type'),
                        stat_point=stat_data.get('stat_point', 0),
                        stat_level=stat_data.get('stat_level', 0),
                        stat_increase=stat_data.get('stat_increase')
                    )
                    presets.append(preset)
                return presets

            # 각 프리셋 처리
            preset_fields = {
                'hyper_stat_preset_1': 'hyper_stat_preset_1',
                'hyper_stat_preset_2': 'hyper_stat_preset_2',
                'hyper_stat_preset_3': 'hyper_stat_preset_3'
            }

            for field_name, attr_name in preset_fields.items():
                if field_name in data and data[field_name]:
                    presets = process_hyper_stat_preset(data[field_name])
                    if presets:
                        getattr(hyper_stat, attr_name).add(*presets)

            return hyper_stat

        except Exception as e:
            raise Exception(f"하이퍼스탯 정보 생성 중 오류 발생: {str(e)}")


class Account(models.Model):
    account_id = models.CharField(max_length=255)
    character_list = models.ManyToManyField(CharacterBasic)


class AccountList(models.Model):
    account_list = models.ManyToManyField(Account)


class CharacterId(models.Model):
    ocid = models.CharField(max_length=255, unique=True)
    date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.ocid
