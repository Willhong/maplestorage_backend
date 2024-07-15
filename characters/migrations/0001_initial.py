# Generated by Django 5.0.7 on 2024-07-15 16:27

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='CharacterBasic',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField(help_text='조회 기준일 (KST)')),
                ('character_name', models.CharField(help_text='캐릭터 명', max_length=255)),
                ('world_name', models.CharField(help_text='월드 명', max_length=255)),
                ('character_gender', models.CharField(help_text='캐릭터 성별', max_length=10)),
                ('character_class', models.CharField(help_text='캐릭터 직업', max_length=255)),
                ('character_class_level', models.CharField(help_text='캐릭터 전직 차수', max_length=50)),
                ('character_level', models.IntegerField(help_text='캐릭터 레벨')),
                ('character_exp', models.BigIntegerField(help_text='현재 레벨에서 보유한 경험치')),
                ('character_exp_rate', models.CharField(help_text='현재 레벨에서 경험치 퍼센트', max_length=10)),
                ('character_guild_name', models.CharField(blank=True, help_text='캐릭터 소속 길드 명', max_length=255, null=True)),
                ('character_image', models.URLField(help_text='캐릭터 외형 이미지')),
                ('character_date_create', models.DateTimeField(help_text='캐릭터 생성일 (KST)')),
                ('access_flag', models.BooleanField(help_text='최근 7일간 접속 여부')),
                ('liberation_quest_clear_flag', models.BooleanField(help_text='해방 퀘스트 완료 여부')),
            ],
            options={
                'indexes': [models.Index(fields=['character_name', 'world_name'], name='characters__charact_f7fd35_idx'), models.Index(fields=['date'], name='characters__date_10db6c_idx')],
                'unique_together': {('character_name', 'world_name', 'date')},
            },
        ),
    ]
