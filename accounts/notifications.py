"""
Alert notification service (Story 2.10)

AC-2.10.3: 성공률 95% 미만 시 이메일 알림
AC-2.10.4: 성공률 80% 미만 시 긴급 알림 (Slack)
"""
import logging
import requests
from typing import Optional
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


class AlertService:
    """
    알림 서비스 클래스 (Story 2.10)

    이메일: Django send_mail (Sendgrid 또는 SMTP 설정)
    Slack: Webhook URL로 POST 요청
    """

    @staticmethod
    def send_email_alert(subject: str, message: str) -> bool:
        """
        관리자 이메일 알림 전송 (AC-2.10.3)

        Args:
            subject: 이메일 제목
            message: 이메일 본문

        Returns:
            bool: 전송 성공 여부
        """
        alert_email = getattr(settings, 'ALERT_EMAIL', None)

        if not alert_email:
            logger.warning("ALERT_EMAIL not configured, skipping email alert")
            return False

        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[alert_email],
                fail_silently=False,
            )
            logger.info(f"Email alert sent: {subject}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            return False

    @staticmethod
    def send_slack_alert(message: str) -> bool:
        """
        Slack 긴급 알림 전송 (AC-2.10.4)

        Args:
            message: Slack 메시지 내용

        Returns:
            bool: 전송 성공 여부
        """
        webhook_url = getattr(settings, 'SLACK_WEBHOOK_URL', None)

        if not webhook_url:
            logger.warning("SLACK_WEBHOOK_URL not configured, skipping Slack alert")
            return False

        try:
            payload = {
                "text": message,
                "username": "MapleStorage Alert Bot",
                "icon_emoji": ":warning:",
            }

            response = requests.post(
                webhook_url,
                json=payload,
                timeout=10
            )
            response.raise_for_status()

            logger.info("Slack alert sent successfully")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Slack alert: {e}")
            return False

    @classmethod
    def send_warning_alert(cls, success_rate: float, total_tasks: int) -> bool:
        """
        경고 알림 전송 (95% 미만, AC-2.10.3)

        Args:
            success_rate: 현재 성공률
            total_tasks: 총 작업 수

        Returns:
            bool: 알림 전송 성공 여부
        """
        subject = "[MapleStorage] 크롤링 성공률 경고"
        message = f"""크롤링 성공률이 95% 미만으로 떨어졌습니다.

현재 성공률: {success_rate:.1f}%
최근 24시간 총 작업 수: {total_tasks}

대시보드에서 상세 정보를 확인해주세요.
"""
        return cls.send_email_alert(subject, message)

    @classmethod
    def send_critical_alert(
        cls,
        success_rate: float,
        total_tasks: int,
        error_breakdown: Optional[dict] = None
    ) -> bool:
        """
        긴급 알림 전송 (80% 미만, AC-2.10.4)

        Args:
            success_rate: 현재 성공률
            total_tasks: 총 작업 수
            error_breakdown: 에러 유형별 통계 (선택)

        Returns:
            bool: 알림 전송 성공 여부
        """
        subject = "[MapleStorage] 크롤링 성공률 긴급 알림"

        error_details = ""
        if error_breakdown:
            error_details = "\n에러 유형별 통계:\n"
            for error_type, count in error_breakdown.items():
                if count > 0:
                    error_details += f"  - {error_type}: {count}건\n"

        message = f"""[긴급] 크롤링 성공률이 80% 미만으로 급락했습니다!

현재 성공률: {success_rate:.1f}%
최근 24시간 총 작업 수: {total_tasks}
{error_details}
즉시 확인이 필요합니다.
"""

        # 이메일 전송
        email_sent = cls.send_email_alert(subject, message)

        # Slack 전송
        slack_message = f":rotating_light: *크롤링 성공률 긴급 알림* :rotating_light:\n\n" \
                       f"현재 성공률: *{success_rate:.1f}%*\n" \
                       f"총 작업 수: {total_tasks}\n" \
                       f"{error_details}\n" \
                       f"즉시 확인이 필요합니다!"

        slack_sent = cls.send_slack_alert(slack_message)

        return email_sent or slack_sent


class UserNotificationService:
    """
    사용자 알림 서비스 (Story 5.2)

    만료 임박 아이템에 대한 알림을 사용자에게 전송합니다.
    - 이메일 알림
    - 중복 알림 방지 (Redis + DB 체크)
    - 알림 기록 저장
    """

    @staticmethod
    def _get_redis_key(item_id: int, item_source: str, d_day: int) -> str:
        """Redis 중복 체크 키 생성"""
        return f"notif:{item_source}:{item_id}:{d_day}"

    @staticmethod
    def _get_notification_type(d_day: int) -> str:
        """D-day를 notification_type으로 변환"""
        if d_day <= 0:
            return 'EXPIRED'
        elif d_day == 1:
            return 'D1'
        elif d_day <= 3:
            return 'D3'
        else:
            return 'D7'

    @classmethod
    def check_duplicate(cls, item_id: int, item_source: str, d_day: int) -> bool:
        """
        중복 알림 체크 (AC-5.2.6: 같은 아이템에 대해 중복 알림 전송 안함)

        Returns:
            bool: True if already sent (duplicate), False if new
        """
        from util.redis_client import redis_client
        from .models import Notification

        # 1. Redis 체크 (빠른 체크)
        redis_key = cls._get_redis_key(item_id, item_source, d_day)
        if redis_client.exists(redis_key):
            return True

        # 2. DB 체크 (백업)
        notification_type = cls._get_notification_type(d_day)
        exists = Notification.objects.filter(
            item_id=item_id,
            item_source=item_source,
            notification_type=notification_type
        ).exists()

        return exists

    @classmethod
    def send_expiry_notification(
        cls,
        user,
        item_data: dict,
        d_day: int,
        retry_count: int = 0
    ) -> bool:
        """
        만료 임박 아이템 알림 전송 (AC-5.2.1 ~ AC-5.2.5)

        Args:
            user: Django User instance
            item_data: dict with item_id, item_name, item_source, character_name,
                       character_ocid, expiry_date
            d_day: 만료까지 남은 일수
            retry_count: 재시도 횟수 (최대 3회)

        Returns:
            bool: 전송 성공 여부
        """
        from util.redis_client import redis_client
        from .models import Notification, UserProfile

        # 0. 알림 설정 체크
        try:
            profile = user.profile
            if not profile.notification_enabled:
                logger.info(f"Notifications disabled for user {user.id}")
                return False
        except UserProfile.DoesNotExist:
            pass  # 프로필 없으면 기본 알림 활성화로 간주

        # 0.5. 세부 알림 설정 체크 (Story 5.3: 주기/카테고리/조용한 시간)
        from .models import NotificationSettings
        notification_settings = NotificationSettings.get_or_create_for_user(user)
        item_category = item_data.get('item_category')  # optional field
        if not notification_settings.is_notification_allowed(d_day, item_category):
            logger.info(f"Notification blocked by settings for user {user.id}, d_day={d_day}")
            return False

        # 1. 중복 체크
        if cls.check_duplicate(item_data['item_id'], item_data['item_source'], d_day):
            logger.info(f"Duplicate notification skipped: item {item_data['item_id']}, d_day {d_day}")
            return False

        # 2. 이메일 알림 전송
        notification_type = cls._get_notification_type(d_day)
        success = False
        error_message = None

        try:
            # 이메일 내용 구성 (AC-5.2.4, AC-5.2.5)
            if d_day <= 0:
                d_day_text = "만료되었습니다"
                subject = f"[메이플스토리지] '{item_data['item_name']}' 아이템이 만료되었습니다 (캐릭터: {item_data['character_name']})"
            else:
                d_day_text = f"{d_day}일 후 만료됩니다"
                subject = f"[메이플스토리지] '{item_data['item_name']}' 아이템이 {d_day_text} (캐릭터: {item_data['character_name']})"

            message = f"""안녕하세요, {user.username}님!

등록하신 캐릭터의 기간제 아이템이 곧 만료됩니다.

아이템 정보:
- 아이템: {item_data['item_name']}
- 캐릭터: {item_data['character_name']}
- 만료일: {item_data['expiry_date']}
- 남은 기간: {d_day_text}
- 위치: {'인벤토리' if item_data['item_source'] == 'inventory' else '창고'}

만료 전에 아이템을 사용하거나 조치를 취해주세요.

메이플스토리지에서 확인하기:
https://maplestorage.com/characters/{item_data['character_ocid']}

---
이 알림은 메이플스토리지에서 자동으로 발송되었습니다.
알림 설정은 메이플스토리지 설정에서 변경할 수 있습니다.
"""

            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            success = True
            logger.info(f"Expiry notification sent to {user.email}: {item_data['item_name']}")

        except Exception as e:
            error_message = str(e)
            logger.error(f"Failed to send expiry notification: {e}")

            # AC-5.2.7: 재시도 (최대 3회)
            if retry_count < 3:
                logger.info(f"Retrying notification (attempt {retry_count + 1}/3)")
                return cls.send_expiry_notification(user, item_data, d_day, retry_count + 1)

        # 3. 알림 기록 저장
        try:
            from django.utils import timezone
            from datetime import datetime

            expiry_date = item_data['expiry_date']
            if isinstance(expiry_date, str):
                expiry_date = datetime.fromisoformat(expiry_date.replace('Z', '+00:00'))

            Notification.objects.create(
                user=user,
                item_id=item_data['item_id'],
                item_source=item_data['item_source'],
                item_name=item_data['item_name'],
                character_name=item_data['character_name'],
                character_ocid=item_data['character_ocid'],
                notification_type=notification_type,
                channel='EMAIL',
                expiry_date=expiry_date,
                success=success,
                error_message=error_message
            )
        except Exception as e:
            logger.error(f"Failed to save notification record: {e}")

        # 4. Redis에 중복 방지 키 설정 (7일 TTL)
        if success:
            redis_key = cls._get_redis_key(item_data['item_id'], item_data['item_source'], d_day)
            try:
                redis_client.setex(redis_key, 7 * 24 * 60 * 60, "1")
            except Exception as e:
                logger.error(f"Failed to set Redis key: {e}")

        return success
