"""
Story 2.10: 크롤링 성공률 모니터링 테스트

테스트 커버리지:
- AC-2.10.1: Redis에 성공률 데이터 저장
- AC-2.10.2: 최근 24시간 성공률 계산
- AC-2.10.3: 95% 미만 시 이메일 알림
- AC-2.10.4: 80% 미만 시 긴급 알림 (Slack)
- AC-2.10.5: 관리자 대시보드 API
- AC-2.10.6: 에러 유형별 통계
"""
from django.test import TestCase, override_settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch, MagicMock
from datetime import timedelta

from accounts.services import MonitoringService
from accounts.notifications import AlertService
from accounts.tasks import check_crawl_success_rate, SUCCESS_RATE_WARNING_THRESHOLD, SUCCESS_RATE_CRITICAL_THRESHOLD
from accounts.exceptions import ErrorType

# 테스트용 인메모리 캐시 설정
TEST_CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'test-cache',
    }
}


@override_settings(CACHES=TEST_CACHES)
class MonitoringServiceTests(TestCase):
    """MonitoringService 단위 테스트"""

    def setUp(self):
        """각 테스트 전에 캐시 초기화"""
        cache.clear()

    def tearDown(self):
        """각 테스트 후에 캐시 정리"""
        cache.clear()

    def test_ac2_10_1_record_crawl_result_stores_in_redis_success(self):
        """
        AC-2.10.1: 성공 결과가 Redis에 저장되는지 확인
        """
        task_id = "test-task-123"

        MonitoringService.record_crawl_result(task_id, 'SUCCESS')

        # Redis 키 확인
        now = timezone.now()
        date_key = now.strftime('%Y-%m-%d')
        hour_key = now.strftime('%H')

        success_key = f"crawl:stats:{date_key}:success"
        hourly_key = f"crawl:stats:{date_key}:hourly:{hour_key}:success"

        self.assertEqual(cache.get(success_key), 1)
        self.assertEqual(cache.get(hourly_key), 1)

    def test_ac2_10_1_record_crawl_result_stores_in_redis_failure(self):
        """
        AC-2.10.1: 실패 결과가 Redis에 저장되는지 확인
        """
        task_id = "test-task-456"

        MonitoringService.record_crawl_result(task_id, 'FAILURE')

        now = timezone.now()
        date_key = now.strftime('%Y-%m-%d')
        hour_key = now.strftime('%H')

        failure_key = f"crawl:stats:{date_key}:failure"
        hourly_key = f"crawl:stats:{date_key}:hourly:{hour_key}:failure"

        self.assertEqual(cache.get(failure_key), 1)
        self.assertEqual(cache.get(hourly_key), 1)

    def test_ac2_10_1_record_crawl_result_with_error_type(self):
        """
        AC-2.10.1: 실패 시 에러 타입별 카운터 증가 확인
        """
        task_id = "test-task-789"
        error_type = ErrorType.NETWORK_ERROR.value

        MonitoringService.record_crawl_result(task_id, 'FAILURE', error_type=error_type)

        now = timezone.now()
        date_key = now.strftime('%Y-%m-%d')

        error_key = f"crawl:stats:{date_key}:error:{error_type}"
        self.assertEqual(cache.get(error_key), 1)

    def test_ac2_10_1_record_crawl_result_increments_counters(self):
        """
        AC-2.10.1: 여러 번 호출 시 카운터가 증가하는지 확인
        """
        for i in range(5):
            MonitoringService.record_crawl_result(f"task-{i}", 'SUCCESS')

        for i in range(3):
            MonitoringService.record_crawl_result(f"fail-task-{i}", 'FAILURE')

        stats = MonitoringService.get_success_rate(hours=1)
        self.assertEqual(stats['successful_tasks'], 5)
        self.assertEqual(stats['failed_tasks'], 3)
        self.assertEqual(stats['total_tasks'], 8)

    def test_ac2_10_2_get_success_rate_calculation(self):
        """
        AC-2.10.2: 성공률 계산 정확성 테스트
        (성공 / 전체) * 100
        """
        # 8개 성공, 2개 실패 = 80% (반복 횟수 최적화)
        for i in range(8):
            MonitoringService.record_crawl_result(f"success-{i}", 'SUCCESS')
        for i in range(2):
            MonitoringService.record_crawl_result(f"fail-{i}", 'FAILURE')

        stats = MonitoringService.get_success_rate(hours=1)

        self.assertEqual(stats['total_tasks'], 10)
        self.assertEqual(stats['successful_tasks'], 8)
        self.assertEqual(stats['failed_tasks'], 2)
        self.assertEqual(stats['success_rate'], 80.0)

    def test_ac2_10_2_get_success_rate_empty_data(self):
        """
        AC-2.10.2: 데이터 없을 때 100% 반환 확인
        """
        stats = MonitoringService.get_success_rate(hours=24)

        self.assertEqual(stats['total_tasks'], 0)
        self.assertEqual(stats['success_rate'], 100.0)

    def test_ac2_10_6_error_breakdown_counts_by_type(self):
        """
        AC-2.10.6: 에러 타입별 카운트 정확성 테스트
        """
        # 각 에러 타입별 실패 기록
        for i in range(5):
            MonitoringService.record_crawl_result(
                f"char-not-found-{i}", 'FAILURE',
                error_type=ErrorType.CHARACTER_NOT_FOUND.value
            )

        for i in range(3):
            MonitoringService.record_crawl_result(
                f"network-error-{i}", 'FAILURE',
                error_type=ErrorType.NETWORK_ERROR.value
            )

        for i in range(2):
            MonitoringService.record_crawl_result(
                f"maintenance-{i}", 'FAILURE',
                error_type=ErrorType.MAINTENANCE.value
            )

        MonitoringService.record_crawl_result(
            "unknown-1", 'FAILURE',
            error_type=ErrorType.UNKNOWN.value
        )

        breakdown = MonitoringService.get_error_breakdown(hours=1)

        self.assertEqual(breakdown[ErrorType.CHARACTER_NOT_FOUND.value], 5)
        self.assertEqual(breakdown[ErrorType.NETWORK_ERROR.value], 3)
        self.assertEqual(breakdown[ErrorType.MAINTENANCE.value], 2)
        self.assertEqual(breakdown[ErrorType.UNKNOWN.value], 1)

    def test_get_hourly_stats_returns_correct_format(self):
        """
        시간대별 통계가 올바른 형식으로 반환되는지 확인
        """
        # 테스트 데이터 생성
        for i in range(10):
            MonitoringService.record_crawl_result(f"success-{i}", 'SUCCESS')
        for i in range(2):
            MonitoringService.record_crawl_result(f"fail-{i}", 'FAILURE')

        hourly_stats = MonitoringService.get_hourly_stats(hours=24)

        self.assertEqual(len(hourly_stats), 24)

        # 첫 번째 항목은 24시간 전, 마지막 항목은 현재 시간
        for stat in hourly_stats:
            self.assertIn('hour', stat)
            self.assertIn('success', stat)
            self.assertIn('failure', stat)
            self.assertIn('rate', stat)

    def test_can_send_alert_returns_true_when_no_recent_alert(self):
        """
        최근 알림이 없을 때 can_send_alert가 True 반환
        """
        self.assertTrue(MonitoringService.can_send_alert('warning'))
        self.assertTrue(MonitoringService.can_send_alert('critical'))

    def test_can_send_alert_returns_false_after_alert_sent(self):
        """
        알림 발송 후 can_send_alert가 False 반환 (중복 방지)
        """
        MonitoringService.mark_alert_sent('warning')

        self.assertFalse(MonitoringService.can_send_alert('warning'))
        # 다른 타입은 영향 없음
        self.assertTrue(MonitoringService.can_send_alert('critical'))


@override_settings(CACHES=TEST_CACHES)
class AlertServiceTests(TestCase):
    """AlertService 단위 테스트"""

    @patch('accounts.notifications.send_mail')
    def test_ac2_10_3_email_alert_triggered(self, mock_send_mail):
        """
        AC-2.10.3: 이메일 알림 전송 테스트
        """
        with override_settings(ALERT_EMAIL='admin@test.com', DEFAULT_FROM_EMAIL='noreply@test.com'):
            result = AlertService.send_email_alert("Test Subject", "Test Message")

            mock_send_mail.assert_called_once()
            self.assertTrue(result)

    @patch('accounts.notifications.send_mail')
    def test_email_alert_not_sent_without_config(self, mock_send_mail):
        """
        ALERT_EMAIL 미설정 시 이메일 전송 안 함
        """
        with override_settings(ALERT_EMAIL=''):
            result = AlertService.send_email_alert("Test Subject", "Test Message")

            mock_send_mail.assert_not_called()
            self.assertFalse(result)

    @patch('requests.post')
    def test_ac2_10_4_slack_alert_triggered(self, mock_post):
        """
        AC-2.10.4: Slack 알림 전송 테스트
        """
        mock_post.return_value.raise_for_status = MagicMock()

        with override_settings(SLACK_WEBHOOK_URL='https://hooks.slack.com/test'):
            result = AlertService.send_slack_alert("Test Message")

            mock_post.assert_called_once()
            self.assertTrue(result)

    @patch('requests.post')
    def test_slack_alert_not_sent_without_config(self, mock_post):
        """
        SLACK_WEBHOOK_URL 미설정 시 Slack 전송 안 함
        """
        with override_settings(SLACK_WEBHOOK_URL=''):
            result = AlertService.send_slack_alert("Test Message")

            mock_post.assert_not_called()
            self.assertFalse(result)

    @patch('accounts.notifications.AlertService.send_email_alert')
    def test_send_warning_alert(self, mock_email):
        """
        경고 알림 (95% 미만) 전송 테스트
        """
        mock_email.return_value = True

        result = AlertService.send_warning_alert(90.5, 1000)

        mock_email.assert_called_once()
        self.assertTrue(result)
        # 제목에 '경고' 포함 확인
        call_args = mock_email.call_args[0]
        self.assertIn('경고', call_args[0])

    @patch('accounts.notifications.AlertService.send_slack_alert')
    @patch('accounts.notifications.AlertService.send_email_alert')
    def test_send_critical_alert(self, mock_email, mock_slack):
        """
        긴급 알림 (80% 미만) 전송 테스트 - 이메일 + Slack
        """
        mock_email.return_value = True
        mock_slack.return_value = True

        error_breakdown = {
            'CHARACTER_NOT_FOUND': 10,
            'NETWORK_ERROR': 5,
            'MAINTENANCE': 0,
            'UNKNOWN': 5
        }

        result = AlertService.send_critical_alert(75.0, 500, error_breakdown)

        mock_email.assert_called_once()
        mock_slack.assert_called_once()
        self.assertTrue(result)

        # 제목에 '긴급' 포함 확인
        email_call_args = mock_email.call_args[0]
        self.assertIn('긴급', email_call_args[0])


@override_settings(CACHES=TEST_CACHES)
class CheckCrawlSuccessRateTaskTests(TestCase):
    """check_crawl_success_rate Celery Task 테스트"""

    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def _set_stats_directly(self, success_count: int, failure_count: int):
        """
        테스트용 헬퍼: 캐시에 직접 통계 설정
        반복 호출 대신 한 번에 값 설정하여 테스트 속도 개선
        """
        now = timezone.now()
        date_key = now.strftime('%Y-%m-%d')
        hour_key = now.strftime('%H')

        # 일별 통계
        cache.set(f"crawl:stats:{date_key}:success", success_count, timeout=604800)
        cache.set(f"crawl:stats:{date_key}:failure", failure_count, timeout=604800)

        # 시간별 통계
        cache.set(f"crawl:stats:{date_key}:hourly:{hour_key}:success", success_count, timeout=604800)
        cache.set(f"crawl:stats:{date_key}:hourly:{hour_key}:failure", failure_count, timeout=604800)

    @patch('accounts.notifications.AlertService.send_warning_alert')
    def test_ac2_10_3_email_alert_triggered_below_95_percent(self, mock_send_warning):
        """
        AC-2.10.3: 95% 미만 시 이메일 알림 전송
        """
        # 90% 성공률: 90 성공, 10 실패
        self._set_stats_directly(90, 10)

        mock_send_warning.return_value = True

        result = check_crawl_success_rate()

        self.assertEqual(result['status'], 'alert_sent')
        self.assertEqual(result['alert_type'], 'warning')
        mock_send_warning.assert_called_once()

    @patch('accounts.notifications.AlertService.send_warning_alert')
    @patch('accounts.notifications.AlertService.send_critical_alert')
    def test_ac2_10_3_email_alert_not_triggered_above_95_percent(self, mock_critical, mock_warning):
        """
        AC-2.10.3: 95% 이상 시 알림 안 감
        """
        # 97% 성공률: 97 성공, 3 실패
        self._set_stats_directly(97, 3)

        result = check_crawl_success_rate()

        self.assertEqual(result['status'], 'ok')
        mock_warning.assert_not_called()
        mock_critical.assert_not_called()

    @patch('accounts.notifications.AlertService.send_critical_alert')
    def test_ac2_10_4_slack_alert_triggered_below_80_percent(self, mock_send_critical):
        """
        AC-2.10.4: 80% 미만 시 Slack 긴급 알림 전송
        """
        # 75% 성공률: 75 성공, 25 실패
        self._set_stats_directly(75, 25)

        mock_send_critical.return_value = True

        result = check_crawl_success_rate()

        self.assertEqual(result['status'], 'alert_sent')
        self.assertEqual(result['alert_type'], 'critical')
        mock_send_critical.assert_called_once()

    @patch('accounts.notifications.AlertService.send_critical_alert')
    def test_alert_duplicate_prevention(self, mock_send_critical):
        """
        알림 중복 방지 테스트 - 1시간 내 중복 알림 방지
        """
        # 70% 성공률: 70 성공, 30 실패
        self._set_stats_directly(70, 30)

        mock_send_critical.return_value = True

        # 첫 번째 호출 - 알림 발송
        result1 = check_crawl_success_rate()
        self.assertEqual(result1['status'], 'alert_sent')

        # 두 번째 호출 - 중복 방지로 스킵
        result2 = check_crawl_success_rate()
        self.assertEqual(result2['status'], 'alert_skipped')
        self.assertEqual(result2['reason'], 'duplicate_prevention')

    def test_no_data_skips_check(self):
        """
        데이터가 없을 때 체크 스킵
        """
        result = check_crawl_success_rate()

        self.assertEqual(result['status'], 'skipped')
        self.assertEqual(result['reason'], 'no_data')


@override_settings(CACHES=TEST_CACHES)
class CrawlStatsAdminViewTests(APITestCase):
    """관리자 API 엔드포인트 테스트"""

    def setUp(self):
        cache.clear()
        # 일반 사용자 생성
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        # 관리자 생성
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='adminpass123'
        )

    def tearDown(self):
        cache.clear()

    def _set_stats_directly(self, success_count: int, failure_count: int):
        """테스트용 헬퍼: 캐시에 직접 통계 설정"""
        now = timezone.now()
        date_key = now.strftime('%Y-%m-%d')
        hour_key = now.strftime('%H')

        cache.set(f"crawl:stats:{date_key}:success", success_count, timeout=604800)
        cache.set(f"crawl:stats:{date_key}:failure", failure_count, timeout=604800)
        cache.set(f"crawl:stats:{date_key}:hourly:{hour_key}:success", success_count, timeout=604800)
        cache.set(f"crawl:stats:{date_key}:hourly:{hour_key}:failure", failure_count, timeout=604800)

    def test_ac2_10_5_admin_crawl_stats_api_returns_correct_data(self):
        """
        AC-2.10.5: API가 올바른 데이터를 반환하는지 확인
        """
        # 테스트 데이터: 80 성공, 20 실패 = 80%
        self._set_stats_directly(80, 20)

        self.client.force_authenticate(user=self.admin_user)

        response = self.client.get('/api/admin/crawl-stats/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIn('success_rate_24h', data)
        self.assertIn('total_tasks_24h', data)
        self.assertIn('successful_tasks', data)
        self.assertIn('failed_tasks', data)
        self.assertIn('error_breakdown', data)
        self.assertIn('hourly_stats', data)
        self.assertIn('last_updated', data)

        # 값 검증
        self.assertEqual(data['total_tasks_24h'], 100)
        self.assertEqual(data['successful_tasks'], 80)
        self.assertEqual(data['failed_tasks'], 20)
        self.assertEqual(data['success_rate_24h'], 80.0)

    def test_ac2_10_5_admin_crawl_stats_requires_admin_permission(self):
        """
        AC-2.10.5: 비관리자 403 확인
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.get('/api/admin/crawl-stats/')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_crawl_stats_requires_authentication(self):
        """
        인증되지 않은 요청 401 확인
        """
        response = self.client.get('/api/admin/crawl-stats/')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_ac2_10_6_error_breakdown_in_api_response(self):
        """
        AC-2.10.6: API 응답에 에러 유형별 통계 포함 확인
        """
        # 다양한 에러 타입으로 실패 기록
        MonitoringService.record_crawl_result(
            "fail-1", 'FAILURE',
            error_type=ErrorType.CHARACTER_NOT_FOUND.value
        )
        MonitoringService.record_crawl_result(
            "fail-2", 'FAILURE',
            error_type=ErrorType.NETWORK_ERROR.value
        )

        self.client.force_authenticate(user=self.admin_user)

        response = self.client.get('/api/admin/crawl-stats/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        error_breakdown = data['error_breakdown']

        self.assertIn('CHARACTER_NOT_FOUND', error_breakdown)
        self.assertIn('NETWORK_ERROR', error_breakdown)
        self.assertIn('MAINTENANCE', error_breakdown)
        self.assertIn('UNKNOWN', error_breakdown)
