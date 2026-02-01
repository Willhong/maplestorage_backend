"""
Comprehensive tests for notification-related views (Stories 5.3, 5.5)

Tests:
- NotificationSettingsView (GET/PATCH)
- TestNotificationView (POST)
- NotificationListView (GET with filters)
- NotificationReadView (PATCH)
- NotificationMarkAllReadView (POST)
- NotificationDeleteView (DELETE)
"""

from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch
from datetime import timedelta

from accounts.models import Notification, NotificationSettings


class NotificationSettingsViewTests(TestCase):
    """Test suite for NotificationSettingsView (Story 5.3)"""

    def setUp(self):
        """Set up test fixtures"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.url = reverse('notification-settings')

    def test_get_settings_creates_default(self):
        """Test that first GET creates default settings"""
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email_enabled'], True)
        self.assertEqual(response.data['push_enabled'], False)
        self.assertEqual(response.data['schedule'], {"d7": True, "d3": True, "d1": True})
        self.assertEqual(response.data['category'], 'ALL')
        self.assertEqual(response.data['quiet_hours_enabled'], False)

        # Verify settings were created in database
        settings = NotificationSettings.objects.get(user=self.user)
        self.assertTrue(settings.email_enabled)

    def test_get_settings_returns_existing(self):
        """Test that GET returns existing settings"""
        # Create custom settings
        NotificationSettings.objects.create(
            user=self.user,
            email_enabled=False,
            push_enabled=True,
            schedule={"d7": False, "d3": True, "d1": True},
            category='EQUIPMENT'
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email_enabled'], False)
        self.assertEqual(response.data['push_enabled'], True)
        self.assertEqual(response.data['category'], 'EQUIPMENT')

    def test_patch_email_enabled(self):
        """Test toggling email notifications"""
        NotificationSettings.objects.create(user=self.user)

        self.client.force_authenticate(user=self.user)
        response = self.client.patch(self.url, {'email_enabled': False})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email_enabled'], False)

        # Verify database update
        settings = NotificationSettings.objects.get(user=self.user)
        self.assertFalse(settings.email_enabled)

    def test_patch_schedule(self):
        """Test updating notification schedule"""
        NotificationSettings.objects.create(user=self.user)

        self.client.force_authenticate(user=self.user)
        new_schedule = {"d7": False, "d3": False, "d1": True}
        response = self.client.patch(self.url, {'schedule': new_schedule})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['schedule'], new_schedule)

        settings = NotificationSettings.objects.get(user=self.user)
        self.assertEqual(settings.schedule, new_schedule)

    def test_patch_category(self):
        """Test changing category filter"""
        NotificationSettings.objects.create(user=self.user)

        self.client.force_authenticate(user=self.user)
        response = self.client.patch(self.url, {'category': 'CONSUMABLE'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['category'], 'CONSUMABLE')

    def test_patch_quiet_hours(self):
        """Test setting quiet hours"""
        NotificationSettings.objects.create(user=self.user)

        self.client.force_authenticate(user=self.user)
        response = self.client.patch(self.url, {
            'quiet_hours_enabled': True,
            'quiet_hours_start': '23:00:00',
            'quiet_hours_end': '08:00:00'
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['quiet_hours_enabled'])
        self.assertEqual(response.data['quiet_hours_start'], '23:00:00')
        self.assertEqual(response.data['quiet_hours_end'], '08:00:00')

    def test_authentication_required_get(self):
        """Test that GET requires authentication"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authentication_required_patch(self):
        """Test that PATCH requires authentication"""
        response = self.client.patch(self.url, {'email_enabled': False})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestNotificationViewTests(TestCase):
    """Test suite for TestNotificationView (Story 5.3)"""

    def setUp(self):
        """Set up test fixtures"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.url = reverse('test-notification')

    @patch('django.core.mail.send_mail')
    def test_send_test_notification(self, mock_send_mail):
        """Test sending test notification email"""
        self.client.force_authenticate(user=self.user)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('전송되었습니다', response.data['message'])

        # Verify send_mail was called
        mock_send_mail.assert_called_once()
        args, kwargs = mock_send_mail.call_args
        self.assertIn('테스트 알림', kwargs['subject'])
        self.assertIn(self.user.email, kwargs['recipient_list'])

    @patch('django.core.mail.send_mail', side_effect=Exception('SMTP Error'))
    def test_send_test_notification_failure(self, mock_send_mail):
        """Test handling of email sending failure"""
        self.client.force_authenticate(user=self.user)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertFalse(response.data['success'])
        self.assertIn('실패', response.data['message'])

    def test_test_notification_auth_required(self):
        """Test that authentication is required"""
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class NotificationListViewTests(TestCase):
    """Test suite for NotificationListView (Story 5.5)"""

    def setUp(self):
        """Set up test fixtures"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        self.url = reverse('notification-list')

        # Create test notifications
        expiry_date = timezone.now() + timedelta(days=3)
        self.notification1 = Notification.objects.create(
            user=self.user,
            item_id=1,
            item_source='inventory',
            item_name='Test Item 1',
            character_name='Char1',
            character_ocid='ocid1',
            notification_type='D3',
            channel='EMAIL',
            expiry_date=expiry_date,
            success=True
        )
        self.notification2 = Notification.objects.create(
            user=self.user,
            item_id=2,
            item_source='storage',
            item_name='Test Item 2',
            character_name='Char2',
            character_ocid='ocid2',
            notification_type='D7',
            channel='EMAIL',
            expiry_date=expiry_date,
            success=True
        )

    def test_list_notifications_all(self):
        """Test listing all notifications"""
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url, {'status': 'all'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['results']), 2)

    def test_list_notifications_unread(self):
        """Test filtering unread notifications"""
        # Mark one notification as read
        self.notification1.read_at = timezone.now()
        self.notification1.save()

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url, {'status': 'unread'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], self.notification2.id)

    def test_list_notifications_read(self):
        """Test filtering read notifications"""
        # Mark one notification as read
        self.notification1.read_at = timezone.now()
        self.notification1.save()

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url, {'status': 'read'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], self.notification1.id)

    def test_list_excludes_deleted(self):
        """Test that soft-deleted notifications are excluded"""
        # Soft delete one notification
        self.notification1.deleted_at = timezone.now()
        self.notification1.save()

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url, {'status': 'all'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], self.notification2.id)

    def test_list_only_user_notifications(self):
        """Test that other user's notifications are excluded"""
        # Create notification for other user
        Notification.objects.create(
            user=self.other_user,
            item_id=3,
            item_source='inventory',
            item_name='Other User Item',
            character_name='OtherChar',
            character_ocid='ocid3',
            notification_type='D3',
            channel='EMAIL',
            expiry_date=timezone.now() + timedelta(days=3),
            success=True
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url, {'status': 'all'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        # Verify only this user's notifications are returned
        for result in response.data['results']:
            self.assertIn(result['id'], [self.notification1.id, self.notification2.id])

    def test_list_pagination(self):
        """Test pagination of notification list"""
        # Create 25 notifications to test pagination (page_size=20)
        expiry_date = timezone.now() + timedelta(days=3)
        for i in range(23):  # Already have 2
            Notification.objects.create(
                user=self.user,
                item_id=100 + i,
                item_source='inventory',
                item_name=f'Item {i}',
                character_name=f'Char {i}',
                character_ocid=f'ocid{i}',
                notification_type='D1',
                channel='EMAIL',
                expiry_date=expiry_date,
                success=True
            )

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 25)
        self.assertEqual(len(response.data['results']), 20)  # First page

        # Test second page
        response_page2 = self.client.get(self.url, {'page': 2})
        self.assertEqual(len(response_page2.data['results']), 5)  # Remaining items


class NotificationReadViewTests(TestCase):
    """Test suite for NotificationReadView (Story 5.5)"""

    def setUp(self):
        """Set up test fixtures"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        expiry_date = timezone.now() + timedelta(days=3)
        self.notification = Notification.objects.create(
            user=self.user,
            item_id=1,
            item_source='inventory',
            item_name='Test Item',
            character_name='TestChar',
            character_ocid='ocid1',
            notification_type='D3',
            channel='EMAIL',
            expiry_date=expiry_date,
            success=True
        )

    def test_mark_notification_read(self):
        """Test marking a notification as read"""
        self.assertIsNone(self.notification.read_at)

        self.client.force_authenticate(user=self.user)
        url = reverse('notification-read', kwargs={'pk': self.notification.pk})
        response = self.client.patch(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify read_at is set
        self.notification.refresh_from_db()
        self.assertIsNotNone(self.notification.read_at)

    def test_mark_already_read_notification(self):
        """Test marking an already read notification (should be idempotent)"""
        # Mark as read
        original_read_at = timezone.now()
        self.notification.read_at = original_read_at
        self.notification.save()

        self.client.force_authenticate(user=self.user)
        url = reverse('notification-read', kwargs={'pk': self.notification.pk})
        response = self.client.patch(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify read_at didn't change
        self.notification.refresh_from_db()
        self.assertEqual(self.notification.read_at, original_read_at)

    def test_read_nonexistent_notification(self):
        """Test marking non-existent notification returns 404"""
        self.client.force_authenticate(user=self.user)
        url = reverse('notification-read', kwargs={'pk': 99999})
        response = self.client.patch(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_read_deleted_notification(self):
        """Test marking deleted notification returns 404"""
        self.notification.deleted_at = timezone.now()
        self.notification.save()

        self.client.force_authenticate(user=self.user)
        url = reverse('notification-read', kwargs={'pk': self.notification.pk})
        response = self.client.patch(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_read_other_user_notification(self):
        """Test marking another user's notification returns 404"""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )

        self.client.force_authenticate(user=other_user)
        url = reverse('notification-read', kwargs={'pk': self.notification.pk})
        response = self.client.patch(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class NotificationMarkAllReadViewTests(TestCase):
    """Test suite for NotificationMarkAllReadView (Story 5.5)"""

    def setUp(self):
        """Set up test fixtures"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.url = reverse('notification-mark-all-read')

        # Create multiple unread notifications
        expiry_date = timezone.now() + timedelta(days=3)
        for i in range(5):
            Notification.objects.create(
                user=self.user,
                item_id=i,
                item_source='inventory',
                item_name=f'Item {i}',
                character_name='TestChar',
                character_ocid=f'ocid{i}',
                notification_type='D3',
                channel='EMAIL',
                expiry_date=expiry_date,
                success=True
            )

    def test_mark_all_read(self):
        """Test marking all notifications as read"""
        # Verify all are unread
        unread_count = Notification.objects.filter(
            user=self.user,
            read_at__isnull=True
        ).count()
        self.assertEqual(unread_count, 5)

        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 5)

        # Verify all are now read
        unread_count = Notification.objects.filter(
            user=self.user,
            read_at__isnull=True
        ).count()
        self.assertEqual(unread_count, 0)

    def test_mark_all_read_with_some_already_read(self):
        """Test marking all read when some are already read"""
        # Mark 2 as read
        notifications = Notification.objects.filter(user=self.user)[:2]
        for notif in notifications:
            notif.read_at = timezone.now()
            notif.save()

        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3)  # Only 3 were unread

    def test_mark_all_read_excludes_deleted(self):
        """Test that deleted notifications are not marked as read"""
        # Delete one notification
        notif = Notification.objects.filter(user=self.user).first()
        notif.deleted_at = timezone.now()
        notif.save()

        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 4)  # Deleted one excluded


class NotificationDeleteViewTests(TestCase):
    """Test suite for NotificationDeleteView (Story 5.5)"""

    def setUp(self):
        """Set up test fixtures"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        expiry_date = timezone.now() + timedelta(days=3)
        self.notification = Notification.objects.create(
            user=self.user,
            item_id=1,
            item_source='inventory',
            item_name='Test Item',
            character_name='TestChar',
            character_ocid='ocid1',
            notification_type='D3',
            channel='EMAIL',
            expiry_date=expiry_date,
            success=True
        )

    def test_delete_notification(self):
        """Test soft deleting a notification"""
        self.assertIsNone(self.notification.deleted_at)

        self.client.force_authenticate(user=self.user)
        url = reverse('notification-delete', kwargs={'pk': self.notification.pk})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify soft delete (deleted_at is set)
        self.notification.refresh_from_db()
        self.assertIsNotNone(self.notification.deleted_at)

        # Verify record still exists in database
        self.assertTrue(Notification.objects.filter(pk=self.notification.pk).exists())

    def test_delete_nonexistent_notification(self):
        """Test deleting non-existent notification returns 404"""
        self.client.force_authenticate(user=self.user)
        url = reverse('notification-delete', kwargs={'pk': 99999})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_already_deleted_notification(self):
        """Test deleting already deleted notification returns 404"""
        self.notification.deleted_at = timezone.now()
        self.notification.save()

        self.client.force_authenticate(user=self.user)
        url = reverse('notification-delete', kwargs={'pk': self.notification.pk})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_other_user_notification(self):
        """Test deleting another user's notification returns 404"""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )

        self.client.force_authenticate(user=other_user)
        url = reverse('notification-delete', kwargs={'pk': self.notification.pk})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
