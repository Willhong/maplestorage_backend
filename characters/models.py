from django.db import models


class CharacterBasic(models.Model):
    date = models.DateTimeField(help_text="조회 기준일 (KST)")
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

    class Meta:
        unique_together = ['character_name', 'world_name', 'date']
        indexes = [
            models.Index(fields=['character_name', 'world_name']),
            models.Index(fields=['date']),
        ]


class CharacterPopularity(models.Model):
    character = models.ForeignKey(
        CharacterBasic,
        on_delete=models.CASCADE,
        related_name="popularity",
        help_text="캐릭터 기본 정보"
    )
    date = models.DateTimeField(
        help_text="조회 기준일 (KST, 일 단위 데이터로 시, 분은 일괄 0으로 표기)", null=True, blank=True
    )
    popularity = models.BigIntegerField(help_text="캐릭터 인기도")

    class Meta:
        verbose_name = "Character Popularity"
        verbose_name_plural = "Character Popularities"

    def str(self):
        return f"Popularity: {self.popularity} on {self.date}"


class CharacterStat(models.Model):
    character = models.ForeignKey(
        CharacterBasic,
        on_delete=models.CASCADE,
        related_name="stats",
        help_text="캐릭터 기본 정보"
    )
    date = models.DateTimeField(null=True, blank=True, help_text="조회 기준일")
    character_class = models.CharField(max_length=255, help_text="캐릭터 직업")
    remain_ap = models.IntegerField(default=0, help_text="남은 AP")

    def __str__(self):
        return f"{self.character_class} Stats on {self.date}"


class StatDetail(models.Model):
    character_stat = models.ForeignKey(
        CharacterStat, related_name='final_stat', on_delete=models.CASCADE)
    stat_name = models.CharField(max_length=255, help_text="스탯 이름")
    stat_value = models.CharField(max_length=255, help_text="스탯 값")

    def __str__(self):
        return f"{self.stat_name}: {self.stat_value}"
