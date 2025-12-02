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
