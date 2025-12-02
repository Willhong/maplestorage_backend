from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    """User profile extension for social login"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    google_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    display_name = models.CharField(max_length=100, blank=True)
    notification_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s profile"


class Account(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    account_id = models.CharField(max_length=255)
    last_updated = models.DateTimeField(auto_now=True)


class Character(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='characters', null=True)
    account = models.ForeignKey(
        Account, related_name='account_characters', on_delete=models.CASCADE, null=True, blank=True)
    ocid = models.CharField(max_length=255, unique=True)
    character_name = models.CharField(max_length=255)
    world_name = models.CharField(max_length=255, null=True, blank=True)
    character_class = models.CharField(max_length=255, null=True, blank=True)
    character_level = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)


class MapleStoryAPIKey(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='api_keys', null=True, blank=True)
    api_key = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class CrawlTask(models.Model):
    """크롤링 작업 추적 모델

    Story 1.8: character_basic을 CharacterBasic으로 변경하여 게스트 모드 지원
    Story 2.9: error_type, technical_error 필드 추가 (AC-2.9.2, AC-2.9.3)
    """

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('STARTED', 'Started'),
        ('SUCCESS', 'Success'),
        ('FAILURE', 'Failure'),
        ('RETRY', 'Retrying'),
    ]

    # Story 2.9: 에러 타입 선택지 (AC-2.9.2)
    ERROR_TYPE_CHOICES = [
        ('CHARACTER_NOT_FOUND', 'Character Not Found'),
        ('NETWORK_ERROR', 'Network Error'),
        ('MAINTENANCE', 'Maintenance'),
        ('UNKNOWN', 'Unknown'),
    ]

    task_id = models.CharField(max_length=255, unique=True)
    character_basic = models.ForeignKey(
        'characters.CharacterBasic',
        on_delete=models.CASCADE,
        related_name='crawl_tasks'
    )  # Story 1.8: Character → CharacterBasic (게스트 모드 지원)
    task_type = models.CharField(max_length=50)  # 'inventory', 'storage', 'meso', 'full'
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    progress = models.IntegerField(default=0)  # 0-100%
    error_message = models.TextField(null=True, blank=True)  # 사용자 친화적 메시지 (AC-2.9.1)
    # Story 2.9: 에러 처리 확장 (AC-2.9.2, AC-2.9.3)
    error_type = models.CharField(
        max_length=50,
        choices=ERROR_TYPE_CHOICES,
        null=True,
        blank=True
    )  # 에러 타입 코드
    technical_error = models.TextField(null=True, blank=True)  # 개발자용 기술적 에러 메시지
    retry_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['task_id']),
            models.Index(fields=['character_basic', '-created_at']),
        ]

    def __str__(self):
        return f"CrawlTask {self.task_id} - {self.status}"
