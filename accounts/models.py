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


class Notification(models.Model):
    """
    사용자 알림 모델 (Story 5.2)

    만료 임박 아이템에 대한 알림 기록을 저장합니다.
    중복 알림 방지 및 알림 기록 관리에 사용됩니다.
    """

    NOTIFICATION_TYPE_CHOICES = [
        ('D7', 'D-7 (7일 전)'),
        ('D3', 'D-3 (3일 전)'),
        ('D1', 'D-1 (1일 전)'),
        ('EXPIRED', '만료됨'),
    ]

    CHANNEL_CHOICES = [
        ('EMAIL', 'Email'),
        ('PUSH', 'Push Notification'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    # Item reference (generic for both Inventory and Storage)
    item_id = models.IntegerField(help_text='아이템 ID (Inventory 또는 Storage)')
    item_source = models.CharField(
        max_length=20,
        help_text='아이템 출처 (inventory/storage)'
    )
    item_name = models.CharField(max_length=255, help_text='아이템 이름')
    character_name = models.CharField(max_length=255, help_text='캐릭터 이름')
    character_ocid = models.CharField(max_length=255, help_text='캐릭터 OCID')

    notification_type = models.CharField(
        max_length=10,
        choices=NOTIFICATION_TYPE_CHOICES,
        help_text='알림 타입 (D-7, D-3, D-1, EXPIRED)'
    )
    channel = models.CharField(
        max_length=10,
        choices=CHANNEL_CHOICES,
        default='EMAIL',
        help_text='알림 채널'
    )

    # Timestamps
    sent_at = models.DateTimeField(auto_now_add=True, help_text='알림 전송 시간')
    read_at = models.DateTimeField(null=True, blank=True, help_text='알림 읽음 시간')
    deleted_at = models.DateTimeField(null=True, blank=True, help_text='알림 삭제 시간 (soft delete)')

    # Metadata
    expiry_date = models.DateTimeField(help_text='아이템 만료 날짜')
    success = models.BooleanField(default=True, help_text='전송 성공 여부')
    error_message = models.TextField(null=True, blank=True, help_text='실패 시 에러 메시지')

    class Meta:
        ordering = ['-sent_at']
        indexes = [
            models.Index(fields=['user', '-sent_at']),
            models.Index(fields=['item_id', 'item_source', 'notification_type']),
            models.Index(fields=['user', 'read_at']),
        ]
        # Prevent duplicate notifications for same item+type
        constraints = [
            models.UniqueConstraint(
                fields=['item_id', 'item_source', 'notification_type'],
                name='unique_notification_per_item_type'
            )
        ]

    def __str__(self):
        return f"Notification {self.notification_type} for {self.item_name}"

    @property
    def is_read(self):
        return self.read_at is not None

    def mark_as_read(self):
        if not self.read_at:
            from django.utils import timezone
            self.read_at = timezone.now()
            self.save(update_fields=['read_at'])


class NotificationSettings(models.Model):
    """
    사용자 알림 설정 모델 (Story 5.3)

    알림 채널, 주기, 카테고리, 조용한 시간 등을 설정합니다.
    """

    CATEGORY_CHOICES = [
        ('ALL', '모든 아이템'),
        ('EQUIPMENT', '장비만'),
        ('CONSUMABLE', '소비 아이템만'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='notification_settings'
    )

    # 알림 채널 (AC-5.3.1)
    email_enabled = models.BooleanField(default=True, help_text='이메일 알림 ON/OFF')
    push_enabled = models.BooleanField(default=False, help_text='푸시 알림 ON/OFF')

    # 알림 주기 (AC-5.3.2) - JSONField로 개별 설정
    schedule = models.JSONField(
        default=dict,
        help_text='알림 주기 설정 {"d7": true, "d3": true, "d1": true}'
    )

    # 카테고리 필터 (AC-5.3.3)
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='ALL',
        help_text='알림 받을 아이템 카테고리'
    )

    # 조용한 시간 (AC-5.3.4)
    quiet_hours_enabled = models.BooleanField(default=False, help_text='조용한 시간 활성화')
    quiet_hours_start = models.TimeField(null=True, blank=True, help_text='조용한 시간 시작 (예: 23:00)')
    quiet_hours_end = models.TimeField(null=True, blank=True, help_text='조용한 시간 종료 (예: 08:00)')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Notification Settings'
        verbose_name_plural = 'Notification Settings'

    def __str__(self):
        return f"{self.user.username}'s notification settings"

    def save(self, *args, **kwargs):
        # 기본 schedule 값 설정
        if not self.schedule:
            self.schedule = {"d7": True, "d3": True, "d1": True}
        super().save(*args, **kwargs)

    @classmethod
    def get_or_create_for_user(cls, user):
        """사용자의 알림 설정을 가져오거나 기본값으로 생성"""
        settings, created = cls.objects.get_or_create(
            user=user,
            defaults={
                'email_enabled': True,
                'push_enabled': False,
                'schedule': {"d7": True, "d3": True, "d1": True},
                'category': 'ALL',
                'quiet_hours_enabled': False,
            }
        )
        return settings

    def is_notification_allowed(self, d_day: int, item_category: str = None) -> bool:
        """
        주어진 조건에서 알림이 허용되는지 확인

        Args:
            d_day: 만료까지 남은 일수 (7, 3, 1)
            item_category: 아이템 카테고리 (optional)

        Returns:
            bool: 알림 허용 여부
        """
        from django.utils import timezone
        import datetime

        # 1. 채널 체크 (이메일이나 푸시 중 하나라도 활성화)
        if not self.email_enabled and not self.push_enabled:
            return False

        # 2. 주기 체크
        d_day_key = f"d{d_day}"
        if not self.schedule.get(d_day_key, True):
            return False

        # 3. 카테고리 체크 (구현시 item_category와 비교)
        # 현재는 ALL이면 항상 허용
        if self.category != 'ALL' and item_category:
            if self.category == 'EQUIPMENT' and item_category != 'equipment':
                return False
            if self.category == 'CONSUMABLE' and item_category != 'consumable':
                return False

        # 4. 조용한 시간 체크
        if self.quiet_hours_enabled and self.quiet_hours_start and self.quiet_hours_end:
            now = timezone.localtime().time()
            start = self.quiet_hours_start
            end = self.quiet_hours_end

            # 자정을 넘는 경우 (예: 23:00 ~ 08:00)
            if start > end:
                if now >= start or now <= end:
                    return False
            else:
                if start <= now <= end:
                    return False

        return True
