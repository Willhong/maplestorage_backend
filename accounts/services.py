"""
Character registration service (Story 1.7)
Crawling task status management service (Story 2.1)
Crawling monitoring service (Story 2.10)
"""
import requests
import logging
import json
from datetime import datetime, timedelta
from typing import Optional
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from .models import Character, MapleStoryAPIKey
from .exceptions import ErrorType

logger = logging.getLogger(__name__)

NEXON_API_BASE = "https://open.api.nexon.com"
CHARACTER_ID_URL = f"{NEXON_API_BASE}/maplestory/v1/id"
CACHE_TTL = 3600  # 1 hour


class CharacterService:
    """Service layer for character registration (Story 1.7: AC #5, #6, #7)"""

    @staticmethod
    def get_api_key():
        """Get Nexon API key from database"""
        api_key_obj = MapleStoryAPIKey.objects.first()
        if not api_key_obj:
            raise ValueError("Nexon API 키가 설정되지 않았습니다.")
        return api_key_obj.api_key

    @staticmethod
    def get_ocid_from_nexon(character_name):
        """
        Get OCID from Nexon API (Story 1.7: AC #5)

        Args:
            character_name: Character name to lookup

        Returns:
            str: OCID if found

        Raises:
            ValueError: If character not found (404) or API error
        """
        # Check Redis cache first
        cache_key = f"character:ocid:{character_name}"
        cached_ocid = cache.get(cache_key)
        if cached_ocid:
            logger.info(f"Cache hit for character: {character_name}")
            return cached_ocid

        # Call Nexon API
        api_key = CharacterService.get_api_key()
        headers = {"x-nxopen-api-key": api_key}
        params = {"character_name": character_name}

        try:
            response = requests.get(CHARACTER_ID_URL, headers=headers, params=params, timeout=10)

            if response.status_code == 404:
                # Story 1.7: AC #7 - 공개 설정 안 된 캐릭터
                raise ValueError("캐릭터 정보를 찾을 수 없습니다. 공개 설정을 확인해주세요.")

            response.raise_for_status()
            data = response.json()
            ocid = data.get('ocid')

            if not ocid:
                raise ValueError("OCID를 가져올 수 없습니다.")

            # Cache OCID for 1 hour
            cache.set(cache_key, ocid, CACHE_TTL)
            logger.info(f"OCID cached for character: {character_name}")

            return ocid

        except requests.exceptions.Timeout:
            logger.error(f"Nexon API timeout for character: {character_name}")
            raise ValueError("Nexon API 응답 시간이 초과되었습니다. 잠시 후 다시 시도해주세요.")
        except requests.exceptions.RequestException as e:
            logger.error(f"Nexon API error for character: {character_name} - {str(e)}")
            raise ValueError("현재 캐릭터 등록을 사용할 수 없습니다. 잠시 후 다시 시도해주세요.")

    @staticmethod
    def register_character(user, character_name):
        """
        Register new character (Story 1.7: AC #5, #6)

        Args:
            user: Authenticated user
            character_name: Character name to register

        Returns:
            Character: Created character object

        Raises:
            ValueError: If character not found or already registered
        """
        # Check if character already registered (unique constraint)
        ocid = CharacterService.get_ocid_from_nexon(character_name)

        if Character.objects.filter(ocid=ocid).exists():
            raise ValueError("이미 등록된 캐릭터입니다.")

        # Create Character model (Story 1.7: AC #6)
        character = Character.objects.create(
            user=user,
            ocid=ocid,
            character_name=character_name
        )

        logger.info(f"Character registered: {character_name} (OCID: {ocid}) for user: {user.id}")
        return character


class TaskStatusService:
    """Service layer for Celery task status management (Story 2.1: AC #4, #5, Story 2.9: AC #1-5)"""

    @staticmethod
    def update_task_status(
        task_id,
        status,
        progress=0,
        error=None,
        message=None,
        error_type=None,
        technical_error=None
    ):
        """
        Update task status in Redis (Story 2.1: AC #4, Story 2.9: AC #1-5)

        Args:
            task_id: Celery task ID
            status: Task status (PENDING/STARTED/SUCCESS/FAILURE/RETRY)
            progress: Progress percentage (0-100)
            error: Error message if failure (사용자 친화적 메시지)
            message: Custom status message
            error_type: Error type code (Story 2.9: AC #2)
                - CHARACTER_NOT_FOUND, NETWORK_ERROR, MAINTENANCE, UNKNOWN
            technical_error: Technical error message for developers (Story 2.9: AC #3)

        Redis Key: task:{task_id}:status
        Redis Value: JSON {status, progress, message, error, error_type, technical_error, updated_at}
        TTL: 1 hour (3600 seconds)
        """
        cache_key = f"task:{task_id}:status"

        status_data = {
            'status': status,
            'progress': progress,
            'updated_at': datetime.now().isoformat()
        }

        if message:
            status_data['message'] = message

        # Story 2.9: 에러 정보 추가
        if error:
            status_data['error'] = error

        if error_type:
            status_data['error_type'] = error_type

        if technical_error:
            status_data['technical_error'] = technical_error

        # Store in Redis with 1 hour TTL
        cache.set(cache_key, json.dumps(status_data), CACHE_TTL)
        logger.info(f"Task {task_id} status updated: {status} ({progress}%)")

    @staticmethod
    def get_task_status(task_id):
        """
        Get task status from Redis (Story 2.1: AC #5)

        Args:
            task_id: Celery task ID

        Returns:
            dict: Task status data or None if not found
        """
        cache_key = f"task:{task_id}:status"
        status_json = cache.get(cache_key)

        if status_json:
            return json.loads(status_json)

        return None


class MonitoringService:
    """
    크롤링 성공률 모니터링 서비스 (Story 2.10)

    AC-2.10.1: 크롤링 결과를 Redis에 저장
    AC-2.10.2: 최근 24시간 성공률 계산
    AC-2.10.6: 에러 유형별 통계 제공

    Redis Key Structure:
    - crawl:stats:{YYYY-MM-DD}:success - 일별 성공 카운트
    - crawl:stats:{YYYY-MM-DD}:failure - 일별 실패 카운트
    - crawl:stats:{YYYY-MM-DD}:error:{type} - 에러 타입별 카운트
    - crawl:stats:{YYYY-MM-DD}:hourly:{HH}:success - 시간별 성공
    - crawl:stats:{YYYY-MM-DD}:hourly:{HH}:failure - 시간별 실패
    - crawl:alert:last_sent:{type} - 알림 중복 방지 (1시간 TTL)

    TTL: 7일 (604800 seconds)
    """

    STATS_TTL = 604800  # 7일
    ALERT_TTL = 3600  # 1시간 (알림 중복 방지)

    @staticmethod
    def _get_date_key(dt: Optional[datetime] = None) -> str:
        """날짜 키 생성 (YYYY-MM-DD)"""
        if dt is None:
            dt = timezone.now()
        return dt.strftime('%Y-%m-%d')

    @staticmethod
    def _get_hour_key(dt: Optional[datetime] = None) -> str:
        """시간 키 생성 (HH)"""
        if dt is None:
            dt = timezone.now()
        return dt.strftime('%H')

    @classmethod
    def record_crawl_result(
        cls,
        task_id: str,
        status: str,
        error_type: Optional[str] = None
    ) -> None:
        """
        크롤링 결과 기록 (AC-2.10.1)

        Args:
            task_id: Celery task ID
            status: 'SUCCESS' 또는 'FAILURE'
            error_type: 실패 시 에러 타입 (CHARACTER_NOT_FOUND, NETWORK_ERROR, MAINTENANCE, UNKNOWN)
        """
        now = timezone.now()
        date_key = cls._get_date_key(now)
        hour_key = cls._get_hour_key(now)

        # 일별 카운터 증가
        if status == 'SUCCESS':
            daily_key = f"crawl:stats:{date_key}:success"
            hourly_key = f"crawl:stats:{date_key}:hourly:{hour_key}:success"
        else:
            daily_key = f"crawl:stats:{date_key}:failure"
            hourly_key = f"crawl:stats:{date_key}:hourly:{hour_key}:failure"

            # 에러 타입별 카운터 (실패 시에만)
            if error_type:
                error_key = f"crawl:stats:{date_key}:error:{error_type}"
                cls._increment_counter(error_key)

        cls._increment_counter(daily_key)
        cls._increment_counter(hourly_key)

        logger.info(f"Recorded crawl result: task={task_id}, status={status}, error_type={error_type}")

    @classmethod
    def _increment_counter(cls, key: str) -> int:
        """
        Redis 카운터 증가 (django-redis를 통해)

        Note: django.core.cache는 incr를 직접 지원하지 않으므로
        get/set으로 구현. race condition 가능성이 있으나 통계 용도로 허용
        """
        current_value = cache.get(key, 0)
        new_value = current_value + 1
        cache.set(key, new_value, cls.STATS_TTL)
        return new_value

    @classmethod
    def get_success_rate(cls, hours: int = 24) -> dict:
        """
        성공률 계산 (AC-2.10.2)

        Args:
            hours: 계산할 시간 범위 (기본 24시간)

        Returns:
            dict: {
                'success_rate': float (0-100),
                'total_tasks': int,
                'successful_tasks': int,
                'failed_tasks': int
            }
        """
        now = timezone.now()
        success_count = 0
        failure_count = 0

        # 최근 hours 시간 내의 데이터 집계
        for hour_offset in range(hours):
            target_time = now - timedelta(hours=hour_offset)
            date_key = cls._get_date_key(target_time)
            hour_key = cls._get_hour_key(target_time)

            success_key = f"crawl:stats:{date_key}:hourly:{hour_key}:success"
            failure_key = f"crawl:stats:{date_key}:hourly:{hour_key}:failure"

            success_count += cache.get(success_key, 0)
            failure_count += cache.get(failure_key, 0)

        total_tasks = success_count + failure_count

        # 성공률 계산 (데이터 없으면 100% 반환)
        if total_tasks == 0:
            success_rate = 100.0
        else:
            success_rate = round((success_count / total_tasks) * 100, 2)

        return {
            'success_rate': success_rate,
            'total_tasks': total_tasks,
            'successful_tasks': success_count,
            'failed_tasks': failure_count
        }

    @classmethod
    def get_error_breakdown(cls, hours: int = 24) -> dict:
        """
        에러 유형별 통계 (AC-2.10.6)

        Args:
            hours: 계산할 시간 범위 (기본 24시간)

        Returns:
            dict: {
                'CHARACTER_NOT_FOUND': int,
                'NETWORK_ERROR': int,
                'MAINTENANCE': int,
                'UNKNOWN': int
            }
        """
        now = timezone.now()
        error_counts = {
            ErrorType.CHARACTER_NOT_FOUND.value: 0,
            ErrorType.NETWORK_ERROR.value: 0,
            ErrorType.MAINTENANCE.value: 0,
            ErrorType.UNKNOWN.value: 0,
        }

        # 최근 hours 시간 내의 에러 데이터 집계 (일별 집계)
        # 최대 2일 분량 확인 (24시간이 날짜 경계를 넘을 수 있음)
        days_to_check = (hours // 24) + 2

        for day_offset in range(days_to_check):
            target_date = now - timedelta(days=day_offset)
            date_key = cls._get_date_key(target_date)

            for error_type in error_counts.keys():
                error_key = f"crawl:stats:{date_key}:error:{error_type}"
                count = cache.get(error_key, 0)
                error_counts[error_type] += count

        return error_counts

    @classmethod
    def get_hourly_stats(cls, hours: int = 24) -> list:
        """
        시간대별 성공률 통계 (차트용)

        Args:
            hours: 조회할 시간 범위

        Returns:
            list: [{'hour': 'YYYY-MM-DD HH:00', 'success': int, 'failure': int, 'rate': float}, ...]
        """
        now = timezone.now()
        hourly_stats = []

        for hour_offset in range(hours):
            target_time = now - timedelta(hours=hour_offset)
            date_key = cls._get_date_key(target_time)
            hour_key = cls._get_hour_key(target_time)

            success_key = f"crawl:stats:{date_key}:hourly:{hour_key}:success"
            failure_key = f"crawl:stats:{date_key}:hourly:{hour_key}:failure"

            success = cache.get(success_key, 0)
            failure = cache.get(failure_key, 0)
            total = success + failure

            rate = round((success / total) * 100, 2) if total > 0 else 100.0

            hourly_stats.append({
                'hour': target_time.strftime('%Y-%m-%d %H:00'),
                'success': success,
                'failure': failure,
                'rate': rate
            })

        # 오래된 것부터 정렬 (차트에서 왼쪽→오른쪽)
        hourly_stats.reverse()
        return hourly_stats

    @classmethod
    def can_send_alert(cls, alert_type: str) -> bool:
        """
        알림 중복 방지 체크 (AC-2.10.3, AC-2.10.4)

        Args:
            alert_type: 'warning' (95% 미만) 또는 'critical' (80% 미만)

        Returns:
            bool: True면 알림 발송 가능, False면 이미 최근 발송됨
        """
        alert_key = f"crawl:alert:last_sent:{alert_type}"
        if cache.get(alert_key):
            return False
        return True

    @classmethod
    def mark_alert_sent(cls, alert_type: str) -> None:
        """
        알림 발송 기록 (중복 방지용)

        Args:
            alert_type: 'warning' 또는 'critical'
        """
        alert_key = f"crawl:alert:last_sent:{alert_type}"
        cache.set(alert_key, True, cls.ALERT_TTL)
