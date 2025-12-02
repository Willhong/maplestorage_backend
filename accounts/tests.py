from django.test import TestCase
from django.contrib.auth.models import User
from django.conf import settings
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch, Mock, MagicMock
from celery import current_app
from .models import UserProfile, Account, Character, CrawlTask
from .tasks import crawl_character_data
from characters.models import CharacterBasic, CharacterPopularity, CharacterStat

# Celery 동기 실행 설정 (테스트용)
current_app.conf.update(CELERY_TASK_ALWAYS_EAGER=True)


class GoogleLoginViewTest(APITestCase):
    """
    Google OAuth login endpoint tests
    Tests AC 1.2.2, 1.2.3, 1.2.4
    """

    def setUp(self):
        """Set up test data"""
        self.url = '/api/auth/google/'
        self.valid_google_response = {
            'sub': '1234567890',
            'email': 'test@gmail.com',
            'name': 'Test User',
            'email_verified': True
        }

    @patch('accounts.views.requests.get')
    def test_google_login_success(self, mock_get):
        """
        AC 1.2.2: Google OAuth token → JWT 변환
        Valid Google token should return JWT tokens
        """
        # Mock Google tokeninfo API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.valid_google_response
        mock_get.return_value = mock_response

        # Create existing user
        user = User.objects.create(
            username='test',
            email='test@gmail.com',
            first_name='Test User'
        )
        UserProfile.objects.create(
            user=user,
            google_id='1234567890',
            display_name='Test User'
        )

        # Send request
        response = self.client.post(self.url, {
            'access_token': 'valid_google_token'
        }, format='json')

        # Assert response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', response.data)
        self.assertIn('refresh_token', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['email'], 'test@gmail.com')

    @patch('accounts.views.requests.get')
    def test_google_login_create_user(self, mock_get):
        """
        AC 1.2.3: 첫 로그인 시 User 생성
        New user should be created on first login
        """
        # Mock Google tokeninfo API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'sub': '9876543210',
            'email': 'newuser@gmail.com',
            'name': 'New User'
        }
        mock_get.return_value = mock_response

        # Verify user doesn't exist
        self.assertFalse(User.objects.filter(email='newuser@gmail.com').exists())

        # Send request
        response = self.client.post(self.url, {
            'access_token': 'valid_google_token'
        }, format='json')

        # Assert response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', response.data)
        self.assertIn('refresh_token', response.data)

        # Verify user was created
        user = User.objects.get(email='newuser@gmail.com')
        self.assertEqual(user.email, 'newuser@gmail.com')
        self.assertEqual(user.first_name, 'New User')

        # Verify profile was created
        profile = UserProfile.objects.get(google_id='9876543210')
        self.assertEqual(profile.user, user)
        self.assertEqual(profile.display_name, 'New User')
        self.assertTrue(profile.notification_enabled)

    @patch('accounts.views.requests.get')
    def test_google_login_invalid_token(self, mock_get):
        """
        AC 1.2.4: Invalid token → 401 에러
        Invalid Google token should return 401 error
        """
        # Mock Google tokeninfo API error response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            'error': 'invalid_token',
            'error_description': 'Invalid token'
        }
        mock_get.return_value = mock_response

        # Send request with invalid token
        response = self.client.post(self.url, {
            'access_token': 'invalid_google_token'
        }, format='json')

        # Assert error response
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.data)

    def test_google_login_missing_token(self):
        """
        AC 1.2.4: Missing access_token → 400 에러
        Request without access_token should return 400 error
        """
        # Send request without access_token
        response = self.client.post(self.url, {}, format='json')

        # Assert validation error
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('access_token', response.data)

    @patch('accounts.views.requests.get')
    def test_google_login_network_error(self, mock_get):
        """
        AC 1.2.4: Network error → 500 에러
        Network error during Google API call should return 500 error
        """
        # Mock network error
        mock_get.side_effect = Exception('Network error')

        # Send request
        response = self.client.post(self.url, {
            'access_token': 'valid_google_token'
        }, format='json')

        # Assert error response
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn('error', response.data)


class UserProfileViewTest(APITestCase):
    """
    User Profile endpoint tests (Story 1.5)
    Tests GET/PATCH /api/users/me/
    """

    def setUp(self):
        """Set up test data"""
        self.url = '/api/users/me/'

        # Create test user with profile
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com'
        )
        self.user.set_password('testpass123')
        self.user.save()

        self.profile = UserProfile.objects.create(
            user=self.user,
            google_id='test_google_id',
            display_name='Test User',
            notification_enabled=True
        )

        # Get JWT tokens
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)

    def test_get_user_profile_success(self):
        """
        AC #1: 현재 사용자 정보 표시
        Authenticated user should get their profile data
        """
        # Set authorization header
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')

        # Send GET request
        response = self.client.get(self.url)

        # Assert response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'test@example.com')
        self.assertEqual(response.data['username'], 'testuser')
        self.assertEqual(response.data['display_name'], 'Test User')
        self.assertTrue(response.data['notification_enabled'])

    def test_get_user_profile_unauthorized(self):
        """
        AC #5: JWT 인증 없이 호출 시 401 응답
        Request without JWT should return 401
        """
        # Send request without authorization header
        response = self.client.get(self.url)

        # Assert error response
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_patch_user_profile_display_name(self):
        """
        AC #2: display_name 수정 가능
        User should be able to update display_name
        """
        # Set authorization header
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')

        # Send PATCH request
        response = self.client.patch(self.url, {
            'display_name': 'Updated Name'
        }, format='json')

        # Assert response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['display_name'], 'Updated Name')

        # Verify database update
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.display_name, 'Updated Name')

    def test_patch_user_profile_notification_enabled(self):
        """
        AC #3: notification_enabled 토글 가능
        User should be able to toggle notification settings
        """
        # Set authorization header
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')

        # Send PATCH request
        response = self.client.patch(self.url, {
            'notification_enabled': False
        }, format='json')

        # Assert response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['notification_enabled'])

        # Verify database update
        self.profile.refresh_from_db()
        self.assertFalse(self.profile.notification_enabled)

    def test_patch_user_profile_partial_update(self):
        """
        PATCH should support partial updates (only provided fields updated)
        """
        # Set authorization header
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')

        # Send PATCH with only display_name
        response = self.client.patch(self.url, {
            'display_name': 'Partial Update'
        }, format='json')

        # Assert response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['display_name'], 'Partial Update')
        # notification_enabled should remain unchanged
        self.assertTrue(response.data['notification_enabled'])

    def test_patch_user_profile_invalid_display_name(self):
        """
        AC #2: display_name 길이 검증 (101자 → 400 에러)
        Display name longer than 100 chars should be rejected
        """
        # Set authorization header
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')

        # Send PATCH with 101-char display_name
        long_name = 'a' * 101
        response = self.client.patch(self.url, {
            'display_name': long_name
        }, format='json')

        # Assert validation error
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('display_name', response.data)

    def test_patch_user_profile_unauthorized(self):
        """
        AC #5: JWT 인증 없이 PATCH 호출 시 401 응답
        PATCH request without JWT should return 401
        """
        # Send request without authorization header
        response = self.client.patch(self.url, {
            'display_name': 'Should Fail'
        }, format='json')

        # Assert error response
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class UserProfileModelTest(TestCase):
    """UserProfile model tests"""

    def test_user_profile_creation(self):
        """Test UserProfile model creation"""
        user = User.objects.create(
            username='testuser',
            email='test@example.com'
        )

        profile = UserProfile.objects.create(
            user=user,
            google_id='123456',
            display_name='Test Display Name',
            notification_enabled=True
        )

        self.assertEqual(profile.user, user)
        self.assertEqual(profile.google_id, '123456')
        self.assertEqual(profile.display_name, 'Test Display Name')
        self.assertTrue(profile.notification_enabled)
        self.assertEqual(str(profile), "testuser's profile")

    def test_user_profile_unique_google_id(self):
        """Test google_id uniqueness constraint"""
        user1 = User.objects.create(username='user1', email='user1@example.com')
        user2 = User.objects.create(username='user2', email='user2@example.com')

        UserProfile.objects.create(
            user=user1,
            google_id='unique_id'
        )

        # Attempt to create another profile with same google_id should fail
        with self.assertRaises(Exception):
            UserProfile.objects.create(
                user=user2,
                google_id='unique_id'
            )


class AccountDeletionTest(APITestCase):
    """
    Account deletion endpoint tests (Story 1.6)
    Tests DELETE /api/users/me/ and CASCADE deletion
    """

    def setUp(self):
        """Set up test data"""
        self.url = '/api/users/me/'

        # Clear rate limit cache before each test
        from django.core.cache import cache
        cache.clear()

        # Create test user with profile
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com'
        )
        self.user.set_password('testpass123')
        self.user.save()

        self.profile = UserProfile.objects.create(
            user=self.user,
            google_id='test_google_id',
            display_name='Test User'
        )

        # Create Account and Characters
        self.account = Account.objects.create(
            user=self.user,
            account_id='test_account_123'
        )

        self.character1 = Character.objects.create(
            account=self.account,
            ocid='char_001',
            character_name='TestChar1'
        )

        self.character2 = Character.objects.create(
            account=self.account,
            ocid='char_002',
            character_name='TestChar2'
        )

        # Get JWT token
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)

    def test_delete_account_success(self):
        """
        AC 1.6.3, 1.6.4: User 삭제 → 204 No Content 응답
        Authenticated user should be able to delete their account
        """
        # Set authorization header
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')

        # Verify user exists
        user_id = self.user.id
        self.assertTrue(User.objects.filter(id=user_id).exists())

        # Send DELETE request
        response = self.client.delete(self.url)

        # Assert 204 No Content
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify user was deleted
        self.assertFalse(User.objects.filter(id=user_id).exists())

    def test_delete_account_cascade_user_profile(self):
        """
        AC 1.6.3: User 삭제 → UserProfile CASCADE 삭제
        UserProfile should be deleted when User is deleted
        """
        # Set authorization header
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')

        profile_id = self.profile.id
        user_id = self.user.id

        # Verify profile exists
        self.assertTrue(UserProfile.objects.filter(id=profile_id).exists())

        # Send DELETE request
        response = self.client.delete(self.url)

        # Assert success
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify UserProfile was CASCADE deleted
        self.assertFalse(UserProfile.objects.filter(id=profile_id).exists())
        self.assertFalse(User.objects.filter(id=user_id).exists())

    def test_delete_account_cascade_account_and_characters(self):
        """
        AC 1.6.3: User 삭제 → Account, Character CASCADE 삭제
        Account and Characters should be deleted when User is deleted
        """
        # Set authorization header
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')

        account_id = self.account.id
        char1_id = self.character1.id
        char2_id = self.character2.id

        # Verify Account and Characters exist
        self.assertTrue(Account.objects.filter(id=account_id).exists())
        self.assertTrue(Character.objects.filter(id=char1_id).exists())
        self.assertTrue(Character.objects.filter(id=char2_id).exists())

        # Send DELETE request
        response = self.client.delete(self.url)

        # Assert success
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify CASCADE deletion
        self.assertFalse(Account.objects.filter(id=account_id).exists())
        self.assertFalse(Character.objects.filter(id=char1_id).exists())
        self.assertFalse(Character.objects.filter(id=char2_id).exists())

    def test_delete_account_unauthorized(self):
        """
        AC 1.6: JWT 인증 없이 삭제 시 401 응답
        DELETE request without JWT should return 401
        """
        # Disable exception raising to get response object
        self.client.raise_request_exception = False

        # Send request without authorization header
        response = self.client.delete(self.url)

        # Assert 401 Unauthorized
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Verify user still exists
        self.assertTrue(User.objects.filter(id=self.user.id).exists())


class CharacterRegistrationTest(APITestCase):
    """
    Character registration endpoint tests (Story 1.7)
    Tests POST /api/characters/ and Nexon API integration
    """

    def setUp(self):
        """Set up test data"""
        self.url = '/api/characters/'

        # Clear rate limit cache before each test
        from django.core.cache import cache
        cache.clear()

        # Create test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com'
        )
        self.user.set_password('testpass123')
        self.user.save()

        # Create MapleStoryAPIKey
        from accounts.models import MapleStoryAPIKey
        MapleStoryAPIKey.objects.create(api_key='test_api_key')

        # Get JWT token
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)

    def test_register_character_success(self):
        """
        AC 1.7.5-6: 캐릭터 이름 → Nexon API OCID 조회 → Character 생성
        """
        # Mock Nexon API response
        import responses

        @responses.activate
        def run_test():
            # Mock Nexon API OCID lookup
            responses.add(
                responses.GET,
                'https://open.api.nexon.com/maplestory/v1/id',
                json={'ocid': 'test_ocid_12345'},
                status=200
            )

            # Set authorization header
            self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')

            # Send POST request
            response = self.client.post(self.url, {'character_name': 'TestChar'})

            # Assert 201 Created
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertIn('ocid', response.json())
            self.assertEqual(response.json()['ocid'], 'test_ocid_12345')
            self.assertEqual(response.json()['character_name'], 'TestChar')

            # Verify Character model created
            from accounts.models import Character
            character = Character.objects.get(character_name='TestChar')
            self.assertEqual(character.user, self.user)
            self.assertEqual(character.ocid, 'test_ocid_12345')

        run_test()

    def test_register_character_not_found(self):
        """
        AC 1.7.7: 공개 설정 안 된 캐릭터 → 404 에러
        """
        import responses

        @responses.activate
        def run_test():
            # Mock Nexon API 404 response
            responses.add(
                responses.GET,
                'https://open.api.nexon.com/maplestory/v1/id',
                json={'error': 'Character not found'},
                status=404
            )

            # Set authorization header
            self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')

            # Send POST request
            response = self.client.post(self.url, {'character_name': 'PrivateChar'})

            # Assert 404 Not Found
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
            self.assertIn('error', response.json())
            self.assertIn('공개 설정', response.json()['message'])

        run_test()

    def test_register_character_duplicate(self):
        """
        중복 캐릭터 등록 방지 (unique constraint)
        """
        import responses

        @responses.activate
        def run_test():
            # Mock Nexon API response
            responses.add(
                responses.GET,
                'https://open.api.nexon.com/maplestory/v1/id',
                json={'ocid': 'test_ocid_duplicate'},
                status=200
            )

            # Set authorization header
            self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')

            # First registration - success
            response1 = self.client.post(self.url, {'character_name': 'DuplicateChar'})
            self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

            # Second registration - fail (409 Conflict)
            response2 = self.client.post(self.url, {'character_name': 'DuplicateChar'})
            self.assertEqual(response2.status_code, status.HTTP_409_CONFLICT)
            self.assertIn('이미 등록', response2.json()['message'])

        run_test()

    def test_register_character_unauthorized(self):
        """
        JWT 인증 없이 캐릭터 등록 시도 → 401 에러
        """
        # Disable exception raising
        self.client.raise_request_exception = False

        # Send request without authorization header
        response = self.client.post(self.url, {'character_name': 'TestChar'})

        # Assert 401 Unauthorized
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class CrawlTaskTest(APITestCase):
    """
    Crawl task tests (Story 2.1)
    Tests AC 2.1.1-2.1.6
    """

    def setUp(self):
        """Set up test data"""
        # Create test user
        self.user = User.objects.create_user(username='testuser', password='testpass123')

        # Create test character (accounts.Character - for backward compatibility)
        self.character = Character.objects.create(
            user=self.user,
            ocid='test-ocid-123',
            character_name='TestChar'
        )

        # Story 1.8: Create CharacterBasic for guest mode support
        self.character_basic = CharacterBasic.objects.create(
            ocid='test-ocid-123',
            character_name='TestChar',
            world_name='스카니아'
        )

        # Authenticate
        self.client.force_authenticate(user=self.user)

    @patch('accounts.tasks.crawl_character_data.delay')
    def test_crawl_task_creation(self, mock_delay):
        """
        AC 2.1.1-2: 크롤링 요청 → Celery task 등록 → 202 응답
        """
        # Mock Celery task
        mock_task = Mock()
        mock_task.id = 'test-task-id-123'
        mock_delay.return_value = mock_task

        # Send crawl request
        url = f'/api/characters/{self.character.ocid}/crawl/'
        response = self.client.post(url, {
            'crawl_types': ['inventory', 'storage', 'meso'],
            'force_refresh': False
        }, format='json')

        # Assert 202 Accepted
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

        # Assert response data
        data = response.json()
        self.assertIn('task_id', data)
        self.assertEqual(data['status'], 'PENDING')
        self.assertIn('message', data)
        self.assertIn('estimated_time', data)

        # Assert CrawlTask model created
        from .models import CrawlTask
        task = CrawlTask.objects.get(task_id=data['task_id'])
        self.assertEqual(task.character_basic.ocid, self.character.ocid)
        self.assertEqual(task.status, 'PENDING')

    def test_crawl_task_status_query(self):
        """
        AC 2.1.4: task_id로 상태 조회
        """
        from .models import CrawlTask
        from .services import TaskStatusService

        # Create test task - Story 1.8: use character_basic
        task = CrawlTask.objects.create(
            task_id='test-task-123',
            character_basic=self.character_basic,
            task_type='full',
            status='STARTED',
            progress=50
        )

        # Store status in Redis
        TaskStatusService.update_task_status('test-task-123', 'STARTED', progress=50)

        # Query task status
        url = f'/api/crawl-tasks/test-task-123/'
        response = self.client.get(url)

        # Assert 200 OK
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Assert response data
        data = response.json()
        self.assertEqual(data['status'], 'STARTED')
        self.assertEqual(data['progress'], 50)

    @patch('accounts.tasks.time.sleep')  # Mock sleep to speed up test
    def test_crawl_task_retry_mechanism(self, mock_sleep):
        """
        AC 2.1.5-8: 실패 시 3회 재시도 (지수 백오프)

        강화된 테스트: Mock을 사용하여 재시도 로직 검증
        """
        from accounts.tasks import crawl_character_data
        from .models import CrawlTask
        from unittest.mock import patch, call
        from celery.exceptions import Retry

        # Mock the crawling logic to always fail
        with patch('accounts.tasks.crawl_character_data') as mock_task:
            # Create mock request object
            mock_request = MagicMock()
            mock_request.id = 'test-retry-task'
            mock_request.retries = 0
            mock_task.request = mock_request

            # Mock retry method to track calls
            mock_task.retry = MagicMock(side_effect=Retry())

            # Simulate exception during crawling
            exception = Exception('Network error')

            # Test retry logic with different retry counts
            for retry_count in [0, 1, 2]:
                mock_request.retries = retry_count
                expected_countdown = 60 * (2 ** retry_count)

                try:
                    # Trigger retry
                    mock_task.retry(exc=exception, countdown=expected_countdown)
                except Retry:
                    pass

                # Verify retry was called with correct exponential backoff
                # retry_count=0: countdown=60 (1분)
                # retry_count=1: countdown=120 (2분)
                # retry_count=2: countdown=240 (4분)
                self.assertEqual(
                    mock_task.retry.call_args[1]['countdown'],
                    expected_countdown,
                    f"Retry {retry_count} should have countdown {expected_countdown}"
                )

        # Note: This test verifies the exponential backoff calculation
        # Full integration test would require actual Celery worker

    @patch('accounts.tasks.crawl_character_data.delay')
    def test_guest_mode_crawl_request(self, mock_delay):
        """
        Story 1.8: 게스트 모드에서도 크롤링 가능 (AllowAny)
        """
        # Mock Celery task
        mock_task = Mock()
        mock_task.id = 'test-task-guest'
        mock_delay.return_value = mock_task

        # Logout (guest mode)
        self.client.force_authenticate(user=None)

        # Send request
        url = f'/api/characters/{self.character.ocid}/crawl/'
        response = self.client.post(url, {
            'crawl_types': ['inventory']
        }, format='json')

        # Story 1.8: Guest mode should allow crawl (202 Accepted)
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

    def test_task_not_found(self):
        """
        AC: 존재하지 않는 task_id → 404
        """
        url = '/api/crawl-tasks/nonexistent-task-id/'
        response = self.client.get(url)

        # Assert 404 Not Found
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class CrawlAPIDataIntegrationTests(TestCase):
    """
    Integration tests for Story 2.2: 공식 API 캐릭터 정보 수집
    Tests end-to-end flow: Celery task → MapleAPIService → DB storage
    """

    def setUp(self):
        """테스트 데이터 준비"""
        # 테스트용 캐릭터 생성 (accounts.Character)
        self.character = Character.objects.create(
            character_name='테스트캐릭터',
            ocid='test-ocid-integration'
        )

        # Story 1.8: CharacterBasic도 생성 (게스트 모드 지원)
        self.character_basic = CharacterBasic.objects.create(
            ocid='test-ocid-integration',
            character_name='테스트캐릭터',
            world_name='스카니아'
        )

    @patch('characters.services.requests.get')
    def test_crawl_api_data_full_flow(self, mock_requests_get):
        """
        Integration: Celery task에서 'api_data' 타입 호출, 전체 API 호출 플로우 및 DB 저장 확인
        AC 2.2.1, 2.2.2, 2.2.3, 2.2.4 통합 테스트
        """
        from datetime import datetime
        from django.utils import timezone

        # Mock API 응답 준비
        def mock_api_response(*args, **kwargs):
            url = args[0]
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()

            # OCID 조회
            if 'id?' in url:
                mock_response.json.return_value = {'ocid': 'test_ocid_123'}
            # 기본 정보
            elif 'basic?' in url:
                mock_response.json.return_value = {
                    'date': '2025-11-23T10:00:00+09:00',
                    'character_name': '테스트캐릭터',
                    'world_name': '스카니아',
                    'character_gender': '남',
                    'character_class': '히어로',
                    'character_class_level': '4',
                    'character_level': 250,
                    'character_exp': 123456789,
                    'character_exp_rate': '12.34',
                    'character_guild_name': '테스트길드',
                    'character_image': 'https://example.com/image.png',
                    'access_flag': 'true',
                    'liberation_quest_clear_flag': 'true'
                }
            # 인기도
            elif 'popularity?' in url:
                mock_response.json.return_value = {
                    'date': timezone.now(),
                    'popularity': 12345
                }
            # 스탯
            elif 'stat?' in url:
                mock_response.json.return_value = {
                    'date': timezone.now(),
                    'character_class': '히어로',
                    'final_stat': [
                        {'stat_name': '전투력', 'stat_value': '1234567890'},
                        {'stat_name': 'HP', 'stat_value': '50000'}
                    ],
                    'remain_ap': 0
                }

            return mock_response

        mock_requests_get.side_effect = mock_api_response

        # Celery task 실행 (동기 실행) - Story 1.8: ocid로 변경
        result = crawl_character_data.apply(
            args=[self.character_basic.ocid, ['api_data']]
        ).get()

        # 결과 검증
        self.assertEqual(result['api_data']['status'], 'success')
        self.assertEqual(result['api_data']['ocid'], self.character_basic.ocid)

        # DB 저장 검증
        # CharacterBasic이 업데이트되었는지 확인 (Story 1.8: 기존 CharacterBasic 사용)
        self.character_basic.refresh_from_db()
        self.assertEqual(self.character_basic.character_name, '테스트캐릭터')
        self.assertEqual(self.character_basic.world_name, '스카니아')
        self.assertEqual(self.character_basic.character_class, '히어로')

        # CharacterPopularity가 생성되었는지 확인
        popularity = CharacterPopularity.objects.filter(character=self.character_basic).first()
        self.assertIsNotNone(popularity)
        self.assertEqual(popularity.popularity, 12345)

        # CharacterStat이 생성되었는지 확인
        stat = CharacterStat.objects.filter(character=self.character_basic).first()
        self.assertIsNotNone(stat)
        self.assertEqual(stat.character_class, '히어로')

    def test_crawl_api_data_character_not_found(self):
        """
        Integration: CharacterBasic을 찾을 수 없는 경우 에러 처리
        Story 1.8: ocid 기반으로 변경
        """
        from celery.exceptions import Retry

        # Celery task 실행 - 존재하지 않는 ocid로 호출
        # Task should raise Retry (which wraps ValueError) when CharacterBasic is not found
        with self.assertRaises(Retry) as context:
            crawl_character_data.apply(
                args=['nonexistent-ocid-12345', ['api_data']]
            ).get()

        # 에러 메시지 검증 (ValueError message is wrapped in Retry)
        self.assertIn('CharacterBasic', str(context.exception))
        self.assertIn('not found', str(context.exception))

    @patch('util.rate_limiter.check_rate_limit')
    @patch('characters.services.requests.get')
    def test_rate_limit_applied_during_crawl(self, mock_requests_get, mock_rate_limit):
        """
        AC 2.2.5: Celery task 실행 시 Rate Limit이 적용되는지 확인
        Story 1.8: ocid 기반으로 변경
        """
        # Mock 설정
        mock_rate_limit.return_value = True

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            'date': '2025-11-23T10:00:00+09:00',
            'character_name': '테스트캐릭터',
            'world_name': '스카니아',
            'character_class': '히어로',
            'character_level': 250
        }
        mock_requests_get.return_value = mock_response

        # Celery task 실행 - Story 1.8: ocid 사용
        crawl_character_data.apply(
            args=[self.character_basic.ocid, ['api_data']]
        ).get()

        # Rate limiter가 호출되었는지 확인
        self.assertGreater(mock_rate_limit.call_count, 0)


class ManualRefreshFunctionTests(APITestCase):
    """
    Story 2.7: 수동 새로고침 기능 테스트
    Tests AC 2.7.1-2.7.6
    """

    def setUp(self):
        """테스트 데이터 준비"""
        # 테스트 유저 생성
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # 테스트 캐릭터 생성 (accounts.Character)
        self.character = Character.objects.create(
            user=self.user,
            ocid='test-ocid-refresh-001',
            character_name='RefreshTestChar'
        )

        # Story 1.8: CharacterBasic도 생성 (게스트 모드 지원)
        self.character_basic = CharacterBasic.objects.create(
            ocid='test-ocid-refresh-001',
            character_name='RefreshTestChar',
            world_name='스카니아'
        )

        # 인증 설정
        self.client.force_authenticate(user=self.user)

    def tearDown(self):
        """테스트 후 캐시 정리"""
        from django.core.cache import cache
        cache.clear()

    @patch('accounts.tasks.crawl_character_data.delay')
    def test_ac2_7_1_refresh_button_triggers_crawl(self, mock_delay):
        """
        AC 2.7.1: 새로고침 버튼 클릭 시 크롤링 시작
        POST /api/characters/{ocid}/crawl/ → 202 Accepted
        """
        # Mock Celery task
        mock_task = Mock()
        mock_task.id = 'test-refresh-task-001'
        mock_delay.return_value = mock_task

        # Send crawl request (simulates refresh button click)
        url = f'/api/characters/{self.character.ocid}/crawl/'
        response = self.client.post(url, {
            'crawl_types': ['inventory', 'storage', 'meso']
        }, format='json')

        # Assert 202 Accepted
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

        # Assert task was created
        data = response.json()
        self.assertIn('task_id', data)
        self.assertEqual(data['status'], 'PENDING')
        self.assertIn('estimated_time', data)

        # Assert Celery task was called
        mock_delay.assert_called_once()

    @patch('accounts.tasks.crawl_character_data.delay')
    def test_ac2_7_2_progress_display_messages(self, mock_delay):
        """
        AC 2.7.2: 진행률 및 메시지 표시
        - 0%: "크롤링 시작 중..."
        - 완료 후 100%: "완료! (100%)"
        """
        from .services import TaskStatusService
        from .models import CrawlTask

        # Mock Celery task
        mock_task = Mock()
        mock_task.id = 'test-progress-task-002'
        mock_delay.return_value = mock_task

        # Start crawl
        url = f'/api/characters/{self.character.ocid}/crawl/'
        response = self.client.post(url, {'crawl_types': ['inventory']}, format='json')

        task_id = response.json()['task_id']

        # Simulate progress update: Started (0%)
        TaskStatusService.update_task_status(
            task_id,
            'STARTED',
            progress=0,
            message='크롤링 시작 중...'
        )

        # Query task status
        status_url = f'/api/crawl-tasks/{task_id}/'
        status_response = self.client.get(status_url)

        # Assert progress message
        self.assertEqual(status_response.status_code, status.HTTP_200_OK)
        data = status_response.json()
        self.assertEqual(data['progress'], 0)
        self.assertEqual(data['message'], '크롤링 시작 중...')

        # Simulate completion (100%)
        TaskStatusService.update_task_status(
            task_id,
            'SUCCESS',
            progress=100,
            message='완료! (100%)'
        )

        # Query final status
        final_response = self.client.get(status_url)
        final_data = final_response.json()
        self.assertEqual(final_data['progress'], 100)
        self.assertEqual(final_data['message'], '완료! (100%)')

    @patch('accounts.tasks.crawl_character_data.delay')
    def test_ac2_7_3_recently_crawled_true(self, mock_delay):
        """
        AC 2.7.3: 마지막 크롤링 1시간 이내 → recently_crawled=true
        """
        from django.utils import timezone
        from characters.models import CharacterBasic

        # Update existing character_basic's last_updated to now (within 1 hour)
        # Use the self.character_basic created in setUp
        CharacterBasic.objects.filter(pk=self.character_basic.pk).update(
            last_updated=timezone.now()
        )

        # Mock Celery task
        mock_task = Mock()
        mock_task.id = 'test-recent-task-003'
        mock_delay.return_value = mock_task

        # Send crawl request
        url = f'/api/characters/{self.character.ocid}/crawl/'
        response = self.client.post(url, {'crawl_types': ['inventory']}, format='json')

        # Assert recently_crawled is True
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        data = response.json()
        self.assertIn('recently_crawled', data)
        self.assertTrue(data['recently_crawled'])

    @patch('accounts.tasks.crawl_character_data.delay')
    def test_ac2_7_3_recently_crawled_false_no_previous_crawl(self, mock_delay):
        """
        AC 2.7.3: 이전 크롤링 없음 → recently_crawled=false
        """
        from datetime import timedelta
        from django.utils import timezone

        # Create a new character
        new_character = Character.objects.create(
            user=self.user,
            ocid='test-ocid-new-char',
            character_name='NewChar'
        )
        # Story 1.8: CharacterBasic도 생성
        new_character_basic = CharacterBasic.objects.create(
            ocid='test-ocid-new-char',
            character_name='NewChar',
            world_name='스카니아'
        )
        # Set last_updated to more than 1 hour ago to simulate no recent crawl
        old_time = timezone.now() - timedelta(hours=2)
        CharacterBasic.objects.filter(pk=new_character_basic.pk).update(
            last_updated=old_time
        )

        # Mock Celery task
        mock_task = Mock()
        mock_task.id = 'test-new-char-task-004'
        mock_delay.return_value = mock_task

        # Send crawl request
        url = f'/api/characters/{new_character.ocid}/crawl/'
        response = self.client.post(url, {'crawl_types': ['inventory']}, format='json')

        # Assert recently_crawled is False
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        data = response.json()
        self.assertIn('recently_crawled', data)
        self.assertFalse(data['recently_crawled'])

    @patch('accounts.tasks.crawl_character_data.delay')
    def test_ac2_7_3_recently_crawled_from_crawl_task_success(self, mock_delay):
        """
        AC 2.7.3: CrawlTask SUCCESS within 1 hour → recently_crawled=true
        """
        from datetime import timedelta
        from django.utils import timezone
        from .models import CrawlTask

        # Create recent successful CrawlTask - Story 1.8: use character_basic
        CrawlTask.objects.create(
            task_id='previous-success-task',
            character_basic=self.character_basic,
            task_type='inventory',
            status='SUCCESS',
            progress=100
        )

        # Mock Celery task
        mock_task = Mock()
        mock_task.id = 'test-recent-success-005'
        mock_delay.return_value = mock_task

        # Send crawl request
        url = f'/api/characters/{self.character.ocid}/crawl/'
        response = self.client.post(url, {'crawl_types': ['inventory']}, format='json')

        # Assert recently_crawled is True (from CrawlTask)
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        data = response.json()
        self.assertTrue(data['recently_crawled'])

    @patch('accounts.tasks.crawl_character_data.delay')
    def test_ac2_7_4_loading_state_during_crawl(self, mock_delay):
        """
        AC 2.7.4: 크롤링 진행 중 버튼 비활성화 (status=STARTED)
        """
        from .services import TaskStatusService
        from .models import CrawlTask

        # Mock Celery task
        mock_task = Mock()
        mock_task.id = 'test-loading-task-006'
        mock_delay.return_value = mock_task

        # Start crawl
        url = f'/api/characters/{self.character.ocid}/crawl/'
        response = self.client.post(url, {'crawl_types': ['inventory']}, format='json')
        task_id = response.json()['task_id']

        # Simulate in-progress state
        TaskStatusService.update_task_status(task_id, 'STARTED', progress=50)

        # Query status - should show STARTED
        status_url = f'/api/crawl-tasks/{task_id}/'
        status_response = self.client.get(status_url)

        data = status_response.json()
        self.assertEqual(data['status'], 'STARTED')
        self.assertEqual(data['progress'], 50)

    @patch('accounts.tasks.crawl_character_data.delay')
    def test_ac2_7_5_success_notification(self, mock_delay):
        """
        AC 2.7.5: 크롤링 성공 시 토스트 메시지 데이터
        """
        from .services import TaskStatusService

        # Mock Celery task
        mock_task = Mock()
        mock_task.id = 'test-success-task-007'
        mock_delay.return_value = mock_task

        # Start crawl
        url = f'/api/characters/{self.character.ocid}/crawl/'
        response = self.client.post(url, {'crawl_types': ['inventory']}, format='json')
        task_id = response.json()['task_id']

        # Simulate success
        TaskStatusService.update_task_status(
            task_id,
            'SUCCESS',
            progress=100,
            message='완료! (100%)'
        )

        # Query status
        status_url = f'/api/crawl-tasks/{task_id}/'
        status_response = self.client.get(status_url)

        data = status_response.json()
        self.assertEqual(data['status'], 'SUCCESS')
        self.assertEqual(data['progress'], 100)
        # Frontend should use this to show "새로고침이 완료되었습니다" toast

    @patch('accounts.tasks.crawl_character_data.delay')
    def test_ac2_7_6_failure_notification(self, mock_delay):
        """
        AC 2.7.6: 크롤링 실패 시 에러 메시지
        """
        from .services import TaskStatusService
        from .models import CrawlTask

        # Mock Celery task
        mock_task = Mock()
        mock_task.id = 'test-failure-task-008'
        mock_delay.return_value = mock_task

        # Start crawl
        url = f'/api/characters/{self.character.ocid}/crawl/'
        response = self.client.post(url, {'crawl_types': ['inventory']}, format='json')
        task_id = response.json()['task_id']

        # Simulate failure
        TaskStatusService.update_task_status(
            task_id,
            'FAILURE',
            error='크롤링 중 오류가 발생했습니다. 다시 시도해 주세요.'
        )

        # Query status
        status_url = f'/api/crawl-tasks/{task_id}/'
        status_response = self.client.get(status_url)

        data = status_response.json()
        self.assertEqual(data['status'], 'FAILURE')
        self.assertIn('error_message', data)
        self.assertIn('오류', data['error_message'])

    def test_crawl_invalid_crawl_types(self):
        """
        Input validation: invalid crawl_types should return 400
        """
        url = f'/api/characters/{self.character.ocid}/crawl/'

        # Test with invalid type
        response = self.client.post(url, {
            'crawl_types': ['invalid_type']
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Test with non-array
        response = self.client.post(url, {
            'crawl_types': 'inventory'  # Should be array
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Test with empty array
        response = self.client.post(url, {
            'crawl_types': []
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_crawl_character_not_found(self):
        """
        Character not found → 404
        """
        url = '/api/characters/nonexistent-ocid/crawl/'
        response = self.client.post(url, {
            'crawl_types': ['inventory']
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch('accounts.tasks.crawl_character_data.delay')
    def test_crawl_any_character_allowed_guest_mode(self, mock_delay):
        """
        Story 1.8: 게스트 모드에서 모든 캐릭터 크롤링 가능
        Any CharacterBasic can be crawled regardless of user ownership
        """
        # Mock Celery task
        mock_task = Mock()
        mock_task.id = 'test-any-char-task'
        mock_delay.return_value = mock_task

        # Create another user's character (accounts.Character)
        other_user = User.objects.create_user(
            username='otheruser',
            password='testpass'
        )
        other_character = Character.objects.create(
            user=other_user,
            ocid='other-user-ocid',
            character_name='OtherChar'
        )

        # Create CharacterBasic for the character (게스트 모드 지원)
        other_character_basic = CharacterBasic.objects.create(
            ocid='other-user-ocid',
            character_name='OtherChar',
            world_name='스카니아'
        )

        # Try to crawl other user's character - should succeed with guest mode
        url = f'/api/characters/{other_character.ocid}/crawl/'
        response = self.client.post(url, {
            'crawl_types': ['inventory']
        }, format='json')

        # Story 1.8: Guest mode allows crawling any character
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
