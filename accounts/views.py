import requests
from datetime import timedelta
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
from rest_framework_simplejwt.views import TokenObtainPairView

from define.define import BASE_URL

from .models import MapleStoryAPIKey, Account, Character
from .serializers import (
    MapleStoryAPIKeySerializer, AccountSerializer,
    CharacterListSerializer, RegisterSerializer,
    CustomTokenObtainPairSerializer
)
from .schemas import CharacterListSchema, AccountSchema, CharacterSchema

CACHE_DURATION = timedelta(hours=1)  # 캐시 유효 기간


class APIKeyView(APIView):
    permission_classes = []

    def post(self, request):
        serializer = MapleStoryAPIKeySerializer(data=request.data)
        if serializer.is_valid():
            if request.user.is_authenticated:
                MapleStoryAPIKey.objects.update_or_create(
                    user=request.user,
                    defaults={
                        'api_key': serializer.validated_data['api_key']}
                )
            else:
                MapleStoryAPIKey.objects.update_or_create(
                    defaults={
                        'api_key': serializer.validated_data['api_key']}
                )

            return Response({"message": "API key saved successfully"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                "message": "회원가입이 성공적으로 완료되었습니다.",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email
                }
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class AccountListView(APIView):
    permission_classes = []

    def get(self, request):
        try:
            api_key = MapleStoryAPIKey.objects.get(user=request.user).api_key
        except MapleStoryAPIKey.DoesNotExist:
            return Response({"error": "API key not found"}, status=status.HTTP_404_NOT_FOUND)

        # 데이터베이스에서 캐시된 데이터 확인
        cached_data = self.get_cached_data(request.user)
        if cached_data:
            return Response(CharacterListSerializer.from_pydantic(cached_data))

        headers = {
            "accept": "application/json",
            "x-nxopen-api-key": api_key
        }

        try:
            response = requests.get(
                f"{BASE_URL}/character/list", headers=headers)
            response.raise_for_status()
            data = response.json()

            # Pydantic 모델을 사용하여 데이터 검증
            character_list = CharacterListSchema.model_validate(data)

            # 데이터베이스에 저장
            self.save_to_database(request.user, character_list)

            # Pydantic 모델을 DRF serializer로 변환
            serializer = CharacterListSerializer.from_pydantic(character_list)

            return Response(serializer)
        except requests.RequestException as e:
            return Response({"error": f"Failed to fetch data from MapleStory API: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except ValueError as e:
            return Response({"error": f"Invalid data format: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

    def get_cached_data(self, user):
        # 1시간 이내의 캐시된 데이터만 사용
        cache_time = timezone.now() - timedelta(hours=1)
        accounts = Account.objects.filter(
            user=user, last_updated__gte=cache_time)

        if accounts.exists():
            return CharacterListSchema(account_list=[
                AccountSchema(
                    account_id=account.account_id,
                    character_list=[
                        CharacterSchema(
                            ocid=char.ocid,
                            character_name=char.character_name,
                            world_name=char.world_name,
                            character_class=char.character_class,
                            character_level=char.character_level
                        ) for char in account.characters.all()
                    ]
                ) for account in accounts
            ])
        return None

    def save_to_database(self, user, character_list):
        for account_data in character_list.account_list:
            account, _ = Account.objects.update_or_create(
                user=user,
                account_id=account_data.account_id,
                defaults={'last_updated': timezone.now()}
            )
            for char_data in account_data.character_list:
                Character.objects.update_or_create(
                    account=account,
                    ocid=char_data.ocid,
                    defaults={
                        'character_name': char_data.character_name,
                        'world_name': char_data.world_name,
                        'character_class': char_data.character_class,
                        'character_level': char_data.character_level
                    }
                )
