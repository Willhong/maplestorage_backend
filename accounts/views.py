import requests
from datetime import timedelta
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from django.utils import timezone
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator

from define.define import BASE_URL

from .models import MapleStoryAPIKey, Account, Character, UserProfile
from .serializers import (
    MapleStoryAPIKeySerializer, AccountSerializer,
    CharacterListSerializer, RegisterSerializer,
    CustomTokenObtainPairSerializer, GoogleLoginSerializer,
    UserProfileSerializer, CharacterCreateSerializer, CharacterResponseSerializer
)
from .schemas import CharacterListSchema, AccountSchema, CharacterSchema, GoogleLoginRequest, LoginResponse, UserSchema
from .services import CharacterService, MonitoringService

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


class GoogleLoginView(APIView):
    """
    Google OAuth login endpoint
    Validates Google OAuth access token and issues JWT tokens
    AC #2, #3: "로그인 상태 유지" 옵션에 따라 Refresh Token 유효기간 조정
    - remember_me=true → 30일
    - remember_me=false → 7일 (기본)
    """
    permission_classes = [AllowAny]

    def post(self, request):
        # Validate request data
        serializer = GoogleLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        access_token = serializer.validated_data['access_token']
        remember_me = request.data.get('remember_me', False)  # AC #2, #3

        # Verify Google OAuth token
        try:
            google_user_info = self.verify_google_token(access_token)
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_401_UNAUTHORIZED
            )
        except Exception as e:
            return Response(
                {"error": "Failed to verify Google token"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        google_id = google_user_info.get('sub')
        email = google_user_info.get('email')
        name = google_user_info.get('name', '')

        if not google_id or not email:
            return Response(
                {"error": "Invalid Google token response"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get or create user
        try:
            user_profile = UserProfile.objects.get(google_id=google_id)
            user = user_profile.user
        except UserProfile.DoesNotExist:
            # Create new user
            username = email.split('@')[0]
            # Ensure unique username
            base_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1

            user = User.objects.create(
                username=username,
                email=email,
                first_name=name
            )

            # Create UserProfile
            user_profile = UserProfile.objects.create(
                user=user,
                google_id=google_id,
                display_name=name,
                notification_enabled=True
            )

        # Generate JWT tokens with dynamic lifetime (AC #2, #3)
        refresh = RefreshToken.for_user(user)

        # Refresh Token 유효기간 설정
        if remember_me:
            # "로그인 상태 유지" 체크 시 30일
            from datetime import timedelta
            refresh.set_exp(lifetime=timedelta(days=30))
        # 기본값은 settings.py의 REFRESH_TOKEN_LIFETIME (7일) 사용

        # Prepare response using Pydantic schema
        response_data = LoginResponse(
            access_token=str(refresh.access_token),
            refresh_token=str(refresh),
            user=UserSchema(
                id=user.id,
                username=user.username,
                email=user.email,
                display_name=user_profile.display_name,
                notification_enabled=user_profile.notification_enabled
            )
        )

        return Response(response_data.model_dump(), status=status.HTTP_200_OK)

    def verify_google_token(self, access_token):
        """
        Verify Google OAuth access token
        Returns user info from Google
        """
        url = f"https://oauth2.googleapis.com/tokeninfo?access_token={access_token}"
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            raise ValueError("Invalid Google access token")

        data = response.json()

        # Check if token is valid
        if 'error' in data:
            raise ValueError(f"Google token error: {data.get('error_description', 'Unknown error')}")

        return data


class UserProfileView(APIView):
    """
    User profile endpoint
    GET /api/users/me/ - Get current user profile
    PATCH /api/users/me/ - Update user profile (display_name, notification_enabled)
    DELETE /api/users/me/ - Delete user account (AC 1.6)
    AC #1: 현재 사용자 정보 표시
    AC #2: display_name 수정
    AC #3: notification_enabled 토글
    AC #5: JWT 인증 필수
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Get current authenticated user's profile
        AC #1: display_name과 notification_enabled 필드 확인 가능
        """
        try:
            user_profile = request.user.profile
        except UserProfile.DoesNotExist:
            # Create profile if it doesn't exist
            user_profile = UserProfile.objects.create(
                user=request.user,
                display_name=request.user.get_full_name() or request.user.username
            )

        serializer = UserProfileSerializer(user_profile)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        """
        Partially update user profile
        AC #2: display_name 필드 수정 가능
        AC #3: notification_enabled 토글 가능
        AC #5: JWT 인증 없이 호출 시 401 응답
        """
        try:
            user_profile = request.user.profile
        except UserProfile.DoesNotExist:
            # Create profile if it doesn't exist
            user_profile = UserProfile.objects.create(
                user=request.user,
                display_name=request.user.get_full_name() or request.user.username
            )

        # Partial update (only provided fields will be updated)
        serializer = UserProfileSerializer(user_profile, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        # AC #2, #3: 잘못된 데이터 → 400 에러
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @method_decorator(ratelimit(key='user', rate='1/h', method='DELETE', block=True))
    def delete(self, request):
        """
        Delete user account and all related data (CASCADE)
        AC 1.6: 계정 삭제
        AC 1.6.3: User 삭제 → UserProfile, Account, Character CASCADE 삭제
        AC 1.6.5: Rate Limiting 시간당 1회 적용 (django-ratelimit)
        """
        user = request.user

        # CASCADE 삭제: User 삭제 시 관련된 모든 데이터 자동 삭제
        # - UserProfile: OneToOneField(on_delete=CASCADE)
        # - Account: ForeignKey(on_delete=CASCADE)
        # - Character: Account 삭제 시 CASCADE
        # - MapleStoryAPIKey: ForeignKey(on_delete=CASCADE)

        user.delete()

        # AC 1.6.4: 204 No Content 응답
        return Response(status=status.HTTP_204_NO_CONTENT)


class CharacterDetailView(APIView):
    """
    DELETE /api/characters/{id}/ - 캐릭터 연결 해제 (Story 3.2)
    AC-3.2.3: 캐릭터의 user 연결이 해제된다 (Character.user = None)
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        """
        캐릭터 연결 해제 (데이터 삭제 아님!)

        AC-3.2.3: character.user = None으로 연결 해제
        - 소유권 검증: character.user == request.user
        - 다른 사용자 캐릭터: 404 응답 (정보 노출 방지)
        - 존재하지 않는 캐릭터: 404 응답

        CharacterBasic, Inventory, Storage, Meso 데이터는 보존됨
        """
        try:
            character = Character.objects.get(id=pk, user=request.user)
        except Character.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        # 연결 해제 (데이터 삭제 아님!)
        character.user = None
        character.save()

        return Response(status=status.HTTP_204_NO_CONTENT)


class CharacterCreateView(APIView):
    """
    GET /api/characters/ - 캐릭터 목록 조회 (Story 1.7: AC #1)
    POST /api/characters/ - 캐릭터 등록 (Story 1.7)
    AC 1.7.5: 캐릭터 이름 입력 → Nexon API OCID 조회
    AC 1.7.6: OCID 획득 성공 → Character 모델 생성
    AC 1.7.7: 404 에러 → 공개 설정 안내
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Get user's characters (Story 1.7: AC #1, Story 3.1: AC #1, #4)
        Story 2.8: N+1 쿼리 방지를 위해 크롤링 상태 미리 조회
        Story 3.1: CharacterListSerializer 사용 (character_image, inventory_count, has_expiring_items 포함)
        """
        from characters.serializers import CharacterListSerializer

        # 본인 캐릭터만 조회 (AC-ownership)
        # AC-3.1.4: 최근 등록순 정렬
        characters = Character.objects.filter(user=request.user).order_by('-created_at')

        # Story 3.1: CharacterListSerializer 사용
        serializer = CharacterListSerializer(characters, many=True)

        # Story 3.1: count, results 형식으로 반환
        return Response({
            'count': characters.count(),
            'results': serializer.data
        }, status=status.HTTP_200_OK)

    @method_decorator(ratelimit(key='user', rate='10/h', method='POST', block=True))
    def post(self, request):
        """캐릭터 등록 (Layered Architecture: View → Service → Model)"""
        serializer = CharacterCreateSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        character_name = serializer.validated_data['character_name']

        try:
            # Service layer: Nexon API 호출 및 Character 생성
            character = CharacterService.register_character(request.user, character_name)

            # Response serializer
            response_serializer = CharacterResponseSerializer(character)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except ValueError as e:
            error_message = str(e)

            # AC 1.7.7: 404 에러 처리 (공개 설정 안내)
            if "공개 설정" in error_message:
                return Response(
                    {"error": "character_not_found", "message": error_message},
                    status=status.HTTP_404_NOT_FOUND
                )

            # 중복 등록 에러
            if "이미 등록" in error_message:
                return Response(
                    {"error": "character_already_registered", "message": error_message},
                    status=status.HTTP_409_CONFLICT
                )

            # 기타 에러 (API 타임아웃, 연결 오류 등)
            return Response(
                {"error": "service_unavailable", "message": error_message},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )


@method_decorator(ratelimit(key='ip', rate='10/m', method='POST'), name='post')
class CrawlStartView(APIView):
    """크롤링 시작 API (Story 2.1: AC #1, #2, Story 2.7: AC #3)

    Rate Limiting: IP 기반 분당 10회 (게스트 모드 지원 - Story 1.8)
    """
    permission_classes = [AllowAny]  # Story 1.8: 게스트 모드 지원

    def _check_recently_crawled(self, character_basic):
        """
        마지막 크롤링이 1시간 이내인지 확인 (Story 2.7: AC #3)

        Args:
            character_basic: CharacterBasic 객체

        Returns:
            bool: 1시간 이내 크롤링 여부
        """
        from characters.models import Inventory
        from .models import CrawlTask
        from datetime import timedelta

        one_hour_ago = timezone.now() - timedelta(hours=1)

        # 1. CharacterBasic의 last_updated 확인
        if character_basic.last_updated and character_basic.last_updated > one_hour_ago:
            return True

        # 2. Inventory의 최근 crawled_at 확인
        recent_inventory = Inventory.objects.filter(
            character_basic=character_basic,
            crawled_at__gte=one_hour_ago
        ).exists()

        if recent_inventory:
            return True

        # 3. CrawlTask의 최근 성공 작업 확인
        recent_success = CrawlTask.objects.filter(
            character_basic=character_basic,
            status='SUCCESS',
            updated_at__gte=one_hour_ago
        ).exists()

        return recent_success

    def post(self, request, ocid):
        """
        POST /api/characters/{ocid}/crawl/

        Request body:
        {
            "crawl_types": ["inventory", "storage", "meso"],  # optional
            "force_refresh": false  # optional
        }

        Response (202 Accepted):
        {
            "task_id": "abc123-def456",
            "status": "PENDING",
            "message": "크롤링 작업이 시작되었습니다",
            "estimated_time": 30,
            "recently_crawled": false  # Story 2.7: AC #3
        }
        """
        from .tasks import crawl_character_data
        from .models import CrawlTask
        from characters.models import CharacterBasic

        # CharacterBasic 존재 여부 확인 (Story 1.8: 게스트 모드 지원)
        try:
            character_basic = CharacterBasic.objects.get(ocid=ocid)
        except CharacterBasic.DoesNotExist:
            return Response(
                {"error": "character_not_found", "message": "캐릭터를 찾을 수 없습니다. 먼저 캐릭터를 조회해주세요."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Request body 파싱 및 검증
        VALID_CRAWL_TYPES = ['inventory', 'storage', 'meso']
        crawl_types = request.data.get('crawl_types', VALID_CRAWL_TYPES)

        # crawl_types 화이트리스트 검증 (Security: Input Validation)
        if not isinstance(crawl_types, list):
            return Response(
                {"error": "invalid_crawl_types", "message": "crawl_types는 배열이어야 합니다."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not all(ct in VALID_CRAWL_TYPES for ct in crawl_types):
            return Response(
                {
                    "error": "invalid_crawl_types",
                    "message": f"유효한 crawl_types: {', '.join(VALID_CRAWL_TYPES)}"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if len(crawl_types) == 0:
            return Response(
                {"error": "empty_crawl_types", "message": "최소 1개의 crawl_type이 필요합니다."},
                status=status.HTTP_400_BAD_REQUEST
            )

        force_refresh = request.data.get('force_refresh', False)

        # Story 2.7: AC #3 - 마지막 크롤링 시간 확인
        recently_crawled = self._check_recently_crawled(character_basic)

        # 1시간 이내 크롤링이 있고 강제 새로고침이 아니면 크롤링 시작 안 함
        # 프론트엔드에서 팝업으로 사용자 확인 후 force_refresh=true로 재요청
        if recently_crawled and not force_refresh:
            return Response(
                {
                    "task_id": None,
                    "status": "RECENTLY_CRAWLED",
                    "message": "1시간 이내에 크롤링한 기록이 있습니다",
                    "estimated_time": 0,
                    "recently_crawled": True
                },
                status=status.HTTP_200_OK
            )

        # Celery task 등록 (AC #1) - Story 1.8: ocid 기반으로 변경
        task = crawl_character_data.delay(ocid, crawl_types)
        task_id = task.id

        # CrawlTask 모델에 레코드 생성 (AC #2)
        CrawlTask.objects.create(
            task_id=task_id,
            character_basic=character_basic,
            task_type=','.join(crawl_types),
            status='PENDING',
            progress=0
        )

        # 202 Accepted 응답 (AC #2, Story 2.7: AC #3)
        return Response(
            {
                "task_id": task_id,
                "status": "PENDING",
                "message": "크롤링 작업이 시작되었습니다",
                "estimated_time": 30,  # seconds
                "recently_crawled": False
            },
            status=status.HTTP_202_ACCEPTED
        )


class CrawlStatusView(APIView):
    """크롤링 상태 조회 API (Story 2.1: AC #5, Story 2.9: AC #3, #5)"""
    permission_classes = [AllowAny]  # Story 1.8: 게스트 모드 지원
    throttle_classes = []  # 상태 폴링을 위해 throttling 비활성화

    def get(self, request, task_id):
        """
        GET /api/crawl-tasks/{task_id}/

        Response (200 OK):
        {
            "task_id": "abc123",
            "status": "STARTED",
            "progress": 50,
            "message": "인벤토리 수집 중...",
            "created_at": "2025-11-23T10:00:00Z",
            "updated_at": "2025-11-23T10:00:15Z"
        }

        Story 2.9 - FAILURE 상태 시 추가 필드:
        {
            "task_id": "abc123",
            "status": "FAILURE",
            "progress": 0,
            "error_type": "NETWORK_ERROR",                              // AC-2.9.2
            "error_message": "일시적인 네트워크 오류입니다...",           // AC-2.9.1
            "technical_error": "TimeoutError: Connection timed out...", // AC-2.9.3
            "updated_at": "2025-11-30T10:30:00Z"                        // AC-2.9.5
        }
        """
        from .services import TaskStatusService
        from .models import CrawlTask

        # CrawlTask 모델 조회
        try:
            crawl_task = CrawlTask.objects.get(task_id=task_id)
        except CrawlTask.DoesNotExist:
            return Response(
                {"error": "task_not_found", "message": "작업을 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Redis에서 실시간 상태 조회 (AC #5)
        redis_status = TaskStatusService.get_task_status(task_id)

        if redis_status:
            # Redis 데이터가 있으면 Redis 우선
            response_data = {
                "task_id": task_id,
                "status": redis_status.get('status'),
                "progress": redis_status.get('progress', 0),
                "message": redis_status.get('message', ''),
                "created_at": crawl_task.created_at.isoformat(),
                "updated_at": redis_status.get('updated_at')
            }

            # Story 2.9: 에러 정보 추가 (AC-2.9.1, AC-2.9.2, AC-2.9.3)
            if redis_status.get('error'):
                response_data['error_message'] = redis_status.get('error')
            if redis_status.get('error_type'):
                response_data['error_type'] = redis_status.get('error_type')
            if redis_status.get('technical_error'):
                response_data['technical_error'] = redis_status.get('technical_error')
        else:
            # Redis 데이터가 없으면 DB 데이터 사용
            response_data = {
                "task_id": task_id,
                "status": crawl_task.status,
                "progress": crawl_task.progress,
                "message": "",
                "created_at": crawl_task.created_at.isoformat(),
                "updated_at": crawl_task.updated_at.isoformat()
            }

            # Story 2.9: DB에서 에러 정보 조회 (AC-2.9.1, AC-2.9.2, AC-2.9.3)
            if crawl_task.error_message:
                response_data['error_message'] = crawl_task.error_message
            if crawl_task.error_type:
                response_data['error_type'] = crawl_task.error_type
            if crawl_task.technical_error:
                response_data['technical_error'] = crawl_task.technical_error

        # SUCCESS일 때 크롤링 결과 데이터 포함 (추가 API 호출 없이 바로 UI 업데이트)
        if response_data.get('status') == 'SUCCESS':
            response_data['crawl_data'] = self._get_crawl_result_data(crawl_task)

        return Response(response_data, status=status.HTTP_200_OK)

    def _get_crawl_result_data(self, crawl_task):
        """크롤링 결과 데이터 조회 (inventory, storage, meso)"""
        from characters.models import Inventory, Storage, CharacterBasic
        from characters.serializers import InventoryItemSerializer, StorageItemSerializer

        character_basic = crawl_task.character_basic
        if not character_basic:
            return None

        result = {}

        # 최근 인벤토리 데이터
        latest_inventory = character_basic.inventory_items.order_by('-crawled_at').first()
        if latest_inventory:
            items = character_basic.inventory_items.filter(
                crawled_at=latest_inventory.crawled_at
            ).order_by('slot_position')
            result['inventory'] = {
                'crawled_at': latest_inventory.crawled_at.isoformat(),
                'items': InventoryItemSerializer(items, many=True).data,
                'total_count': items.count()
            }

        # 최근 창고 데이터
        latest_storage = character_basic.storage_items.order_by('-crawled_at').first()
        if latest_storage:
            items = character_basic.storage_items.filter(
                crawled_at=latest_storage.crawled_at
            ).order_by('slot_position')
            result['storage'] = {
                'crawled_at': latest_storage.crawled_at.isoformat(),
                'items': StorageItemSerializer(items, many=True).data,
                'total_count': items.count()
            }

        # 메소 데이터
        result['meso'] = character_basic.meso

        return result


class CrawlStatsAdminView(APIView):
    """
    관리자 전용 크롤링 통계 API (Story 2.10: AC-2.10.5, AC-2.10.6)

    GET /api/admin/crawl-stats/
    - IsAdminUser 권한 필요 (is_staff=True 또는 Django Admin)
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        """
        관리자 크롤링 통계 조회 (AC-2.10.5, AC-2.10.6)

        Response:
        {
            "success_rate_24h": 96.5,
            "total_tasks_24h": 1250,
            "successful_tasks": 1206,
            "failed_tasks": 44,
            "error_breakdown": {
                "CHARACTER_NOT_FOUND": 20,
                "NETWORK_ERROR": 15,
                "MAINTENANCE": 0,
                "UNKNOWN": 9
            },
            "hourly_stats": [...],
            "last_updated": "2025-11-30T10:30:00Z"
        }
        """
        # 최근 24시간 성공률 (AC-2.10.5)
        stats = MonitoringService.get_success_rate(hours=24)

        # 에러 유형별 통계 (AC-2.10.6)
        error_breakdown = MonitoringService.get_error_breakdown(hours=24)

        # 시간대별 통계 (차트용)
        hourly_stats = MonitoringService.get_hourly_stats(hours=24)

        response_data = {
            "success_rate_24h": stats['success_rate'],
            "total_tasks_24h": stats['total_tasks'],
            "successful_tasks": stats['successful_tasks'],
            "failed_tasks": stats['failed_tasks'],
            "error_breakdown": error_breakdown,
            "hourly_stats": hourly_stats,
            "last_updated": timezone.now().isoformat()
        }

        return Response(response_data, status=status.HTTP_200_OK)


# =============================================================================
# Story 3.10: 일괄 캐릭터 등록 Views
# =============================================================================

class LinkedCharactersView(APIView):
    """
    연동 캐릭터 목록 조회 API (Story 3.10: AC #1, #4, #7)

    GET /api/characters/linked/
    - 현재 사용자의 모든 등록된 캐릭터 기반으로 계정 내 전체 캐릭터 목록 조회
    - is_registered 필드로 이미 등록된 캐릭터 표시
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        계정 내 연동 캐릭터 목록 조회 (AC-3.10.1, AC-3.10.4, AC-3.10.7)

        Response (200 OK):
        {
            "characters": [
                {
                    "ocid": "abc123...",
                    "character_name": "캐릭터1",
                    "world_name": "스카니아",
                    "character_class": "히어로",
                    "character_level": 260,
                    "is_registered": true
                },
                ...
            ],
            "registered_count": 3,
            "total_count": 10
        }
        """
        from .services import CharacterService, BatchCharacterService
        from .serializers import LinkedCharacterSerializer

        try:
            # Nexon API에서 연동 캐릭터 목록 조회 (AC-3.10.1, AC-3.10.7)
            linked_characters = CharacterService.get_linked_characters(ocid=None)

            # 이미 등록된 캐릭터 OCID 목록 조회 (AC-3.10.4)
            registered_ocids = BatchCharacterService.get_registered_ocids(request.user)

            # is_registered 필드 추가
            for char in linked_characters:
                char['is_registered'] = char.get('ocid') in registered_ocids

            # Serializer로 직렬화
            serializer = LinkedCharacterSerializer(linked_characters, many=True)

            return Response({
                'characters': serializer.data,
                'registered_count': len(registered_ocids),
                'total_count': len(linked_characters)
            }, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response(
                {"error": "api_error", "message": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )


class BatchCharacterRegistrationView(APIView):
    """
    일괄 캐릭터 등록 API (Story 3.10: AC #3, #5, #6)

    POST /api/characters/batch/
    - 선택한 캐릭터들을 순차적으로 등록
    - Rate Limiting을 고려한 순차 처리
    - 부분 성공 허용 (트랜잭션 분리)
    """
    permission_classes = [IsAuthenticated]

    @method_decorator(ratelimit(key='user', rate='5/h', method='POST', block=True))
    def post(self, request):
        """
        선택한 캐릭터들을 일괄 등록 (AC-3.10.3, AC-3.10.5, AC-3.10.6)

        Request body:
        {
            "character_names": ["캐릭터1", "캐릭터2", "캐릭터3"]
        }

        Response (200 OK):
        {
            "total": 3,
            "success_count": 2,
            "failure_count": 1,
            "results": [
                {"character_name": "캐릭터1", "ocid": "abc123", "success": true, "error": null},
                {"character_name": "캐릭터2", "ocid": "def456", "success": true, "error": null},
                {"character_name": "캐릭터3", "ocid": null, "success": false, "error": "이미 등록된 캐릭터입니다."}
            ]
        }
        """
        from .services import BatchCharacterService
        from .serializers import (
            BatchRegistrationRequestSerializer,
            BatchRegistrationResponseSerializer
        )

        # Request 검증
        request_serializer = BatchRegistrationRequestSerializer(data=request.data)
        if not request_serializer.is_valid():
            return Response(request_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        character_names = request_serializer.validated_data['character_names']

        # 일괄 등록 실행 (AC-3.10.3, AC-3.10.5, AC-3.10.6)
        result = BatchCharacterService.batch_register(request.user, character_names)

        # Response 직렬화
        response_serializer = BatchRegistrationResponseSerializer(result)

        return Response(response_serializer.data, status=status.HTTP_200_OK)
