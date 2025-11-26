from rest_framework import serializers
from .models import MapleStoryAPIKey, UserProfile, Character
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


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


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ('username', 'password', 'password2',
                  'email', 'first_name', 'last_name')
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
            'email': {'required': True}
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "비밀번호가 일치하지 않습니다."})
        return attrs

    def create(self, validated_data):
        user = User.objects.create(
            username=validated_data['username'],
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name']
        )
        user.set_password(validated_data['password'])
        user.save()
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # 토큰에 사용자 정보 추가
        token['username'] = user.username
        token['email'] = user.email
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        # access 토큰 추가
        data['access'] = str(self.get_token(self.user).access_token)
        data['username'] = self.user.username
        data['email'] = self.user.email
        return data


class GoogleLoginSerializer(serializers.Serializer):
    """Google OAuth login serializer"""
    access_token = serializers.CharField(required=True)

    def validate_access_token(self, value):
        """Validate Google OAuth access token"""
        if not value:
            raise serializers.ValidationError("Access token is required")
        return value


class UserProfileSerializer(serializers.ModelSerializer):
    """User profile serializer for GET/PATCH /api/users/me/"""
    email = serializers.EmailField(source='user.email', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = UserProfile
        fields = ['email', 'username', 'display_name', 'notification_enabled']
        extra_kwargs = {
            'display_name': {'required': False},
            'notification_enabled': {'required': False}
        }

    def validate_display_name(self, value):
        """Validate display_name length"""
        if value and len(value) > 100:
            raise serializers.ValidationError("표시 이름은 100자를 초과할 수 없습니다.")
        return value


class CharacterCreateSerializer(serializers.Serializer):
    """Character registration request serializer (Story 1.7)"""
    character_name = serializers.CharField(min_length=1, max_length=100)

    def validate_character_name(self, value):
        """Validate character name"""
        if not value or not value.strip():
            raise serializers.ValidationError("캐릭터 이름은 필수입니다.")
        return value.strip()


class CharacterResponseSerializer(serializers.ModelSerializer):
    """Character response serializer (Story 1.7)"""
    class Meta:
        model = Character
        fields = ['id', 'ocid', 'character_name', 'world_name', 'character_class', 'character_level', 'created_at']
        read_only_fields = ['id', 'ocid', 'world_name', 'character_class', 'character_level', 'created_at']
