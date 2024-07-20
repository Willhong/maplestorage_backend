from rest_framework import serializers
from .models import CharacterBasic, CharacterPopularity, CharacterStat, StatDetail


class CharacterPopularitySerializer(serializers.ModelSerializer):
    class Meta:
        model = CharacterPopularity
        fields = ['date', 'popularity']


class CharacterBasicSerializer(serializers.ModelSerializer):
    popularity = serializers.SerializerMethodField()
    stats = serializers.SerializerMethodField()

    class Meta:
        model = CharacterBasic
        fields = ['date', 'character_name', 'world_name', 'character_gender',
                  'character_class', 'character_class_level', 'character_level',
                  'character_exp', 'character_exp_rate', 'character_guild_name',
                  'character_image', 'character_date_create', 'access_flag',
                  'liberation_quest_clear_flag', 'popularity', 'stats']

    def get_popularity(self, obj):
        popularity = obj.popularity.order_by('-date').first()
        if popularity:
            return CharacterPopularitySerializer(popularity).data
        return None

    def get_stats(self, obj):
        date = obj.date
        stats = obj.stats.filter(date=date).first()
        if stats:
            return CharacterStatSerializer(stats).data
        return None


class StatDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = StatDetail
        fields = ['stat_name', 'stat_value']


class CharacterStatSerializer(serializers.ModelSerializer):
    final_stat = StatDetailSerializer(many=True, read_only=True)

    class Meta:
        model = CharacterStat
        fields = ['date', 'character_class', 'final_stat', 'remain_ap']
