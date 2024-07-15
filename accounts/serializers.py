from rest_framework import serializers
from .models import MapleStoryAPIKey


class MapleStoryAPIKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = MapleStoryAPIKey
        fields = ['api_key']


class PydanticSerializer(serializers.Serializer):
    @classmethod
    def from_pydantic(cls, pydantic_model):
        return cls().to_representation(pydantic_model.dict())


class CharacterSerializer(PydanticSerializer):
    ocid = serializers.CharField()
    character_name = serializers.CharField()
    world_name = serializers.CharField()
    character_class = serializers.CharField()
    character_level = serializers.IntegerField()


class AccountSerializer(PydanticSerializer):
    account_id = serializers.CharField()
    character_list = CharacterSerializer(many=True)


class CharacterListSerializer(PydanticSerializer):
    account_list = AccountSerializer(many=True)
