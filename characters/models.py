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
    character_date_create = models.DateTimeField(help_text="캐릭터 생성일 (KST)")
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
