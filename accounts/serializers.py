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
    """
    Character response serializer (Story 1.7)
    Story 2.8: last_crawled_at, last_crawl_status 필드 추가
    """
    last_crawled_at = serializers.SerializerMethodField()
    last_crawl_status = serializers.SerializerMethodField()

    class Meta:
        model = Character
        fields = [
            'id', 'ocid', 'character_name', 'world_name',
            'character_class', 'character_level', 'created_at',
            'last_crawled_at', 'last_crawl_status'
        ]
        read_only_fields = [
            'id', 'ocid', 'world_name', 'character_class',
            'character_level', 'created_at'
        ]

    def get_last_crawled_at(self, obj):
        """
        마지막 크롤링 시간 조회 (Story 2.8: AC #1)
        N+1 쿼리 방지: context에서 미리 조회된 데이터 사용

        Returns:
            str | None: ISO 8601 형식의 마지막 크롤링 시간 또는 None
        """
        # context에서 미리 조회된 데이터 사용 (N+1 방지)
        character_basic_map = self.context.get('character_basic_map', {})
        crawl_success_map = self.context.get('crawl_success_map', {})

        if character_basic_map and crawl_success_map:
            basic_id = character_basic_map.get(obj.ocid)
            if basic_id:
                last_updated = crawl_success_map.get(basic_id)
                if last_updated:
                    return last_updated.isoformat()
            return None

        # Fallback: 개별 조회 (context 없는 경우)
        from characters.models import CharacterBasic
        from .models import CrawlTask

        try:
            character_basic = CharacterBasic.objects.get(ocid=obj.ocid)
        except CharacterBasic.DoesNotExist:
            return None

        last_task = CrawlTask.objects.filter(
            character_basic=character_basic,
            status='SUCCESS'
        ).order_by('-updated_at').first()

        if last_task:
            return last_task.updated_at.isoformat()
        return None

    def get_last_crawl_status(self, obj):
        """
        마지막 크롤링 상태 조회 (Story 2.8: AC #5)
        N+1 쿼리 방지: context에서 미리 조회된 데이터 사용

        Returns:
            str: 'SUCCESS' | 'FAILED' | 'NEVER_CRAWLED'
        """
        # context에서 미리 조회된 데이터 사용 (N+1 방지)
        character_basic_map = self.context.get('character_basic_map', {})
        crawl_status_map = self.context.get('crawl_status_map', {})

        if character_basic_map and crawl_status_map:
            basic_id = character_basic_map.get(obj.ocid)
            if basic_id:
                return crawl_status_map.get(basic_id, 'NEVER_CRAWLED')
            return 'NEVER_CRAWLED'

        # Fallback: 개별 조회 (context 없는 경우)
        from characters.models import CharacterBasic
        from .models import CrawlTask

        try:
            character_basic = CharacterBasic.objects.get(ocid=obj.ocid)
        except CharacterBasic.DoesNotExist:
            return 'NEVER_CRAWLED'

        last_task = CrawlTask.objects.filter(
            character_basic=character_basic
        ).order_by('-updated_at').first()

        if not last_task:
            return 'NEVER_CRAWLED'

        if last_task.status == 'SUCCESS':
            return 'SUCCESS'
        elif last_task.status in ('FAILURE', 'RETRY'):
            return 'FAILED'
        else:
            previous_success = CrawlTask.objects.filter(
                character_basic=character_basic,
                status='SUCCESS'
            ).exists()
            if previous_success:
                return 'SUCCESS'
            return 'NEVER_CRAWLED'
