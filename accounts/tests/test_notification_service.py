"""
Comprehensive tests for UserNotificationService (Story 5.2)

Tests cover:
- Static methods (_get_redis_key, _get_notification_type)
- Duplicate checking (Redis + DB)
- Notification sending (email, record creation, Redis key setting)
- UserProfile.notification_enabled checks
- NotificationSettings.is_notification_allowed() checks
- Retry logic on email failures
- Edge cases (expired items, missing profiles)
"""
from django.test import TestCase
from django.contrib.auth.models import User
from django.conf import settings
from django.utils import timezone
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from accounts.notifications import UserNotificationService
from accounts.models import Notification, UserProfile, NotificationSettings


class UserNotificationServiceStaticMethodsTest(TestCase):
    """Tests for static helper methods"""

    def test_get_redis_key_format(self):
        """
        Test _get_redis_key returns correct format: notif:{source}:{id}:{d_day}
        """
        key = UserNotificationService._get_redis_key(
            item_id=123,
            item_source='inventory',
            d_day=7
        )
        self.assertEqual(key, 'notif:inventory:123:7')

    def test_get_notification_type_d7(self):
        """d_day=7 should return 'D7'"""
        result = UserNotificationService._get_notification_type(7)
        self.assertEqual(result, 'D7')

    def test_get_notification_type_d3(self):
        """d_day=3 should return 'D3'"""
        result = UserNotificationService._get_notification_type(3)
        self.assertEqual(result, 'D3')

    def test_get_notification_type_d1(self):
        """d_day=1 should return 'D1'"""
        result = UserNotificationService._get_notification_type(1)
        self.assertEqual(result, 'D1')

    def test_get_notification_type_expired(self):
        """d_day=0 or negative should return 'EXPIRED'"""
        self.assertEqual(UserNotificationService._get_notification_type(0), 'EXPIRED')
        self.assertEqual(UserNotificationService._get_notification_type(-1), 'EXPIRED')
        self.assertEqual(UserNotificationService._get_notification_type(-5), 'EXPIRED')


class UserNotificationServiceDuplicateCheckTest(TestCase):
    """Tests for duplicate notification checking"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    @patch('accounts.notifications.redis_client')
    def test_check_duplicate_redis_hit(self, mock_redis):
        """Should return True when Redis key exists"""
        mock_redis.exists.return_value = True

        result = UserNotificationService.check_duplicate(
            item_id=123,
            item_source='inventory',
            d_day=7
        )

        self.assertTrue(result)
        mock_redis.exists.assert_called_once_with('notif:inventory:123:7')

    @patch('accounts.notifications.redis_client')
    def test_check_duplicate_db_hit(self, mock_redis):
        """Should return True when DB record exists (Redis miss)"""
        mock_redis.exists.return_value = False

        # Create existing notification in DB
        Notification.objects.create(
            user=self.user,
            item_id=456,
            item_source='storage',
            item_name='Test Item',
            character_name='TestChar',
            character_ocid='test-ocid',
            notification_type='D3',
            expiry_date=timezone.now() + timedelta(days=3)
        )

        result = UserNotificationService.check_duplicate(
            item_id=456,
            item_source='storage',
            d_day=3
        )

        self.assertTrue(result)

    @patch('accounts.notifications.redis_client')
    def test_check_duplicate_no_match(self, mock_redis):
        """Should return False for new notification"""
        mock_redis.exists.return_value = False

        result = UserNotificationService.check_duplicate(
            item_id=999,
            item_source='inventory',
            d_day=7
        )

        self.assertFalse(result)


class UserNotificationServiceSendNotificationTest(TestCase):
    """Tests for send_expiry_notification method"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        # Create UserProfile with notification enabled
        UserProfile.objects.create(
            user=self.user,
            notification_enabled=True
        )
        
        # Create NotificationSettings with default settings
        NotificationSettings.objects.create(
            user=self.user,
            email_enabled=True,
            schedule={"d7": True, "d3": True, "d1": True}
        )

        self.item_data = {
            'item_id': 123,
            'item_name': '테스트 아이템',
            'item_source': 'inventory',
            'character_name': '테스트 캐릭터',
            'character_ocid': 'test-ocid-001',
            'expiry_date': '2026-02-05T00:00:00+09:00',
        }

    @patch('accounts.notifications.redis_client')
    @patch('accounts.notifications.send_mail')
    def test_send_success(self, mock_send_mail, mock_redis):
        """Email sent, record created, Redis key set"""
        mock_redis.exists.return_value = False
        mock_send_mail.return_value = 1

        result = UserNotificationService.send_expiry_notification(
            user=self.user,
            item_data=self.item_data,
            d_day=7
        )

        # Check success
        self.assertTrue(result)
        
        # Check email was sent
        mock_send_mail.assert_called_once()
        call_args = mock_send_mail.call_args
        self.assertIn('테스트 아이템', call_args.kwargs['subject'])
        self.assertEqual(call_args.kwargs['recipient_list'], ['test@example.com'])
        
        # Check DB record was created
        notification = Notification.objects.get(item_id=123)
        self.assertEqual(notification.item_name, '테스트 아이템')
        self.assertEqual(notification.notification_type, 'D7')
        self.assertTrue(notification.success)
        
        # Check Redis key was set
        mock_redis.setex.assert_called_once()

    @patch('accounts.notifications.redis_client')
    def test_send_disabled_by_profile(self, mock_redis):
        """Should return False when notification_enabled=False"""
        # Disable notifications in profile
        self.user.profile.notification_enabled = False
        self.user.profile.save()

        result = UserNotificationService.send_expiry_notification(
            user=self.user,
            item_data=self.item_data,
            d_day=7
        )

        self.assertFalse(result)
        # No DB record should be created
        self.assertEqual(Notification.objects.count(), 0)

    @patch('accounts.notifications.redis_client')
    def test_send_blocked_by_notification_settings(self, mock_redis):
        """Should return False when NotificationSettings disallows"""
        mock_redis.exists.return_value = False
        
        # Disable D7 notifications in settings
        settings_obj = self.user.notification_settings
        settings_obj.schedule = {"d7": False, "d3": True, "d1": True}
        settings_obj.save()

        result = UserNotificationService.send_expiry_notification(
            user=self.user,
            item_data=self.item_data,
            d_day=7
        )

        self.assertFalse(result)
        # No DB record should be created
        self.assertEqual(Notification.objects.count(), 0)

    @patch('accounts.notifications.redis_client')
    def test_send_duplicate_skipped(self, mock_redis):
        """Should return False for duplicate notification"""
        mock_redis.exists.return_value = True

        result = UserNotificationService.send_expiry_notification(
            user=self.user,
            item_data=self.item_data,
            d_day=7
        )

        self.assertFalse(result)

    @patch('accounts.notifications.redis_client')
    @patch('accounts.notifications.send_mail')
    def test_send_email_failure_retry(self, mock_send_mail, mock_redis):
        """Should retry on email exception"""
        mock_redis.exists.return_value = False
        # Fail on first attempt, succeed on second
        mock_send_mail.side_effect = [
            Exception('SMTP error'),
            1  # success
        ]

        result = UserNotificationService.send_expiry_notification(
            user=self.user,
            item_data=self.item_data,
            d_day=7,
            retry_count=0
        )

        # Should succeed after retry
        self.assertTrue(result)
        # send_mail should be called twice (original + 1 retry)
        self.assertEqual(mock_send_mail.call_count, 2)

    @patch('accounts.notifications.redis_client')
    @patch('accounts.notifications.send_mail')
    def test_send_creates_notification_record(self, mock_send_mail, mock_redis):
        """Notification record should be saved in DB"""
        mock_redis.exists.return_value = False
        mock_send_mail.return_value = 1

        UserNotificationService.send_expiry_notification(
            user=self.user,
            item_data=self.item_data,
            d_day=3
        )

        notification = Notification.objects.get(item_id=123)
        self.assertEqual(notification.user, self.user)
        self.assertEqual(notification.item_id, 123)
        self.assertEqual(notification.item_source, 'inventory')
        self.assertEqual(notification.notification_type, 'D3')
        self.assertEqual(notification.channel, 'EMAIL')
        self.assertTrue(notification.success)
        self.assertIsNone(notification.error_message)

    @patch('accounts.notifications.redis_client')
    @patch('accounts.notifications.send_mail')
    def test_send_expired_item_message(self, mock_send_mail, mock_redis):
        """Correct message for expired items (d_day <= 0)"""
        mock_redis.exists.return_value = False
        mock_send_mail.return_value = 1

        UserNotificationService.send_expiry_notification(
            user=self.user,
            item_data=self.item_data,
            d_day=0
        )

        # Check email subject contains "만료되었습니다"
        call_args = mock_send_mail.call_args
        subject = call_args.kwargs['subject']
        message = call_args.kwargs['message']
        
        self.assertIn('만료되었습니다', subject)
        self.assertIn('만료되었습니다', message)
        
        # Check notification type is EXPIRED
        notification = Notification.objects.get(item_id=123)
        self.assertEqual(notification.notification_type, 'EXPIRED')

    @patch('accounts.notifications.redis_client')
    @patch('accounts.notifications.send_mail')
    def test_send_sets_redis_key(self, mock_send_mail, mock_redis):
        """Redis setex should be called with 7-day TTL"""
        mock_redis.exists.return_value = False
        mock_send_mail.return_value = 1

        UserNotificationService.send_expiry_notification(
            user=self.user,
            item_data=self.item_data,
            d_day=7
        )

        # Check Redis setex was called with correct TTL (7 days in seconds)
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        redis_key = call_args[0][0]
        ttl = call_args[0][1]
        
        self.assertEqual(redis_key, 'notif:inventory:123:7')
        self.assertEqual(ttl, 7 * 24 * 60 * 60)  # 7 days in seconds

    @patch('accounts.notifications.redis_client')
    @patch('accounts.notifications.send_mail')
    def test_send_email_failure_creates_failed_record(self, mock_send_mail, mock_redis):
        """Failed email should create notification record with success=False"""
        mock_redis.exists.return_value = False
        mock_send_mail.side_effect = Exception('SMTP connection failed')

        # Retry 3 times (max)
        result = UserNotificationService.send_expiry_notification(
            user=self.user,
            item_data=self.item_data,
            d_day=7,
            retry_count=0
        )

        # Should fail after max retries
        self.assertFalse(result)
        
        # Check notification record with failure
        notification = Notification.objects.get(item_id=123)
        self.assertFalse(notification.success)
        self.assertIsNotNone(notification.error_message)
        self.assertIn('SMTP', notification.error_message)
        
        # Redis key should NOT be set
        mock_redis.setex.assert_not_called()

    @patch('accounts.notifications.redis_client')
    @patch('accounts.notifications.send_mail')
    def test_send_without_user_profile(self, mock_send_mail, mock_redis):
        """Should succeed if UserProfile doesn't exist (default enabled)"""
        # Create user without profile
        user_no_profile = User.objects.create_user(
            username='noprofile',
            email='noprofile@example.com',
            password='test123'
        )
        # NotificationSettings will be auto-created by get_or_create_for_user
        
        mock_redis.exists.return_value = False
        mock_send_mail.return_value = 1

        result = UserNotificationService.send_expiry_notification(
            user=user_no_profile,
            item_data=self.item_data,
            d_day=7
        )

        # Should succeed (no profile means default enabled)
        self.assertTrue(result)
        mock_send_mail.assert_called_once()

    @patch('accounts.notifications.redis_client')
    @patch('accounts.notifications.send_mail')
    def test_send_quiet_hours_blocking(self, mock_send_mail, mock_redis):
        """Should block notification during quiet hours"""
        mock_redis.exists.return_value = False
        
        # Set quiet hours to current time
        current_time = timezone.localtime().time()
        settings_obj = self.user.notification_settings
        settings_obj.quiet_hours_enabled = True
        settings_obj.quiet_hours_start = current_time
        settings_obj.quiet_hours_end = current_time
        settings_obj.save()

        result = UserNotificationService.send_expiry_notification(
            user=self.user,
            item_data=self.item_data,
            d_day=7
        )

        # Should be blocked by quiet hours
        self.assertFalse(result)
        mock_send_mail.assert_not_called()


class UserNotificationServiceIntegrationTest(TestCase):
    """Integration tests with real models"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='integration_test',
            email='integration@example.com',
            password='testpass123'
        )
        UserProfile.objects.create(user=self.user, notification_enabled=True)
        NotificationSettings.objects.create(
            user=self.user,
            email_enabled=True,
            schedule={"d7": True, "d3": True, "d1": True}
        )

    @patch('accounts.notifications.redis_client')
    @patch('accounts.notifications.send_mail')
    def test_multiple_notifications_different_d_days(self, mock_send_mail, mock_redis):
        """Should allow multiple notifications for same item with different d_days"""
        mock_redis.exists.return_value = False
        mock_send_mail.return_value = 1

        item_data = {
            'item_id': 777,
            'item_name': 'Multi-notify Item',
            'item_source': 'inventory',
            'character_name': 'TestChar',
            'character_ocid': 'test-ocid',
            'expiry_date': (timezone.now() + timedelta(days=7)).isoformat(),
        }

        # Send D7 notification
        result1 = UserNotificationService.send_expiry_notification(
            user=self.user,
            item_data=item_data,
            d_day=7
        )
        self.assertTrue(result1)

        # Send D3 notification (should succeed - different d_day)
        result2 = UserNotificationService.send_expiry_notification(
            user=self.user,
            item_data=item_data,
            d_day=3
        )
        self.assertTrue(result2)

        # Check 2 separate records
        notifications = Notification.objects.filter(item_id=777)
        self.assertEqual(notifications.count(), 2)
        types = set(n.notification_type for n in notifications)
        self.assertEqual(types, {'D7', 'D3'})
