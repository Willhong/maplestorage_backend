"""
Character registration service (Story 1.7)
Crawling task status management service (Story 2.1)
"""
import requests
import logging
import json
from datetime import datetime
from django.core.cache import cache
from django.conf import settings
from .models import Character, MapleStoryAPIKey

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
    """Service layer for Celery task status management (Story 2.1: AC #4, #5)"""

    @staticmethod
    def update_task_status(task_id, status, progress=0, error=None, message=None):
        """
        Update task status in Redis (Story 2.1: AC #4)

        Args:
            task_id: Celery task ID
            status: Task status (PENDING/STARTED/SUCCESS/FAILURE/RETRY)
            progress: Progress percentage (0-100)
            error: Error message if failure
            message: Custom status message

        Redis Key: task:{task_id}:status
        Redis Value: JSON {status, progress, message, error, updated_at}
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

        if error:
            status_data['error'] = error

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
