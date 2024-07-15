from rest_framework import serializers
from .models import CharacterBasic


class CharacterBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = CharacterBasic
        fields = '__all__'
