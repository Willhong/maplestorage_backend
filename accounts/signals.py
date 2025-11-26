"""
Django Signals for account deletion audit logging
AC 1.6: 계정 삭제 시 감사 로그 기록
"""
import logging
from django.contrib.auth.models import User
from django.db.models.signals import pre_delete
from django.dispatch import receiver

# 감사 로그용 logger 설정
audit_logger = logging.getLogger('audit')


@receiver(pre_delete, sender=User)
def log_user_deletion(sender, instance, **kwargs):
    """
    User 삭제 전에 감사 로그 기록
    AC 1.6: 삭제 시점, 사용자 ID, 사용자 이메일 기록

    Note: IP 주소와 User-Agent는 View 레벨에서 기록하는 것이 더 적합하나,
    간단한 구현을 위해 시그널에서 기본 정보만 기록
    """
    audit_logger.info(
        f"User deletion | "
        f"user_id={instance.id} | "
        f"username={instance.username} | "
        f"email={instance.email} | "
        f"action=account_deleted"
    )
