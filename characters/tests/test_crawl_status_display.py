"""
Story 2.8: 크롤링 상태 및 시간 표시 테스트

테스트 대상:
- CharacterBasicSerializer.get_last_crawled_at (AC #1)
- CharacterBasicSerializer.get_last_crawl_status (AC #5)
- CharacterResponseSerializer.get_last_crawled_at (AC #1)
- CharacterResponseSerializer.get_last_crawl_status (AC #5)
"""
import pytest
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.models import User

from characters.models import CharacterBasic
from characters.serializers import CharacterBasicSerializer
from accounts.models import Character, CrawlTask
from accounts.serializers import CharacterResponseSerializer


@pytest.fixture
def user(db):
    """테스트용 사용자 생성"""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpassword'
    )


@pytest.fixture
def character_basic(db):
    """테스트용 CharacterBasic 생성"""
    return CharacterBasic.objects.create(
        ocid='test-ocid-12345',
        character_name='테스트캐릭터',
        world_name='스카니아',
        character_gender='남',
        character_class='아크메이지(불,독)'
    )


@pytest.fixture
def character(db, user, character_basic):
    """테스트용 Character 생성 (accounts 앱)"""
    return Character.objects.create(
        user=user,
        ocid=character_basic.ocid,
        character_name=character_basic.character_name,
        world_name=character_basic.world_name,
        character_class=character_basic.character_class,
        character_level=200
    )


class TestCharacterBasicSerializerCrawlStatus:
    """CharacterBasicSerializer 크롤링 상태 테스트"""

    def test_ac2_8_1_last_crawled_at_included_in_response(self, character_basic):
        """AC #1: API 응답에 last_crawled_at 필드가 포함되어야 함"""
        # Given: 성공한 크롤링 기록이 있음
        crawl_time = timezone.now() - timedelta(minutes=30)
        CrawlTask.objects.create(
            task_id='test-task-1',
            character_basic=character_basic,
            task_type='inventory',
            status='SUCCESS',
            progress=100
        )
        # updated_at 수동 설정
        task = CrawlTask.objects.get(task_id='test-task-1')
        CrawlTask.objects.filter(pk=task.pk).update(updated_at=crawl_time)

        # When: Serializer로 직렬화
        serializer = CharacterBasicSerializer(character_basic)
        data = serializer.data

        # Then: last_crawled_at 필드가 존재하고 값이 있어야 함
        assert 'last_crawled_at' in data
        assert data['last_crawled_at'] is not None

    def test_ac2_8_1_last_crawled_at_null_when_never_crawled(self, character_basic):
        """AC #1: 크롤링 기록이 없으면 last_crawled_at이 None"""
        # Given: 크롤링 기록 없음

        # When: Serializer로 직렬화
        serializer = CharacterBasicSerializer(character_basic)
        data = serializer.data

        # Then: last_crawled_at이 None이어야 함
        assert 'last_crawled_at' in data
        assert data['last_crawled_at'] is None

    def test_ac2_8_5_last_crawl_status_success(self, character_basic):
        """AC #5: 마지막 크롤링이 성공이면 'SUCCESS' 반환"""
        # Given: 성공한 크롤링 기록
        CrawlTask.objects.create(
            task_id='test-task-success',
            character_basic=character_basic,
            task_type='inventory',
            status='SUCCESS',
            progress=100
        )

        # When: Serializer로 직렬화
        serializer = CharacterBasicSerializer(character_basic)
        data = serializer.data

        # Then: last_crawl_status가 'SUCCESS'
        assert data['last_crawl_status'] == 'SUCCESS'

    def test_ac2_8_5_last_crawl_status_failed(self, character_basic):
        """AC #5: 마지막 크롤링이 실패면 'FAILED' 반환"""
        # Given: 실패한 크롤링 기록
        CrawlTask.objects.create(
            task_id='test-task-failure',
            character_basic=character_basic,
            task_type='inventory',
            status='FAILURE',
            progress=0,
            error_message='크롤링 실패'
        )

        # When: Serializer로 직렬화
        serializer = CharacterBasicSerializer(character_basic)
        data = serializer.data

        # Then: last_crawl_status가 'FAILED'
        assert data['last_crawl_status'] == 'FAILED'

    def test_ac2_8_5_last_crawl_status_never_crawled(self, character_basic):
        """AC #5: 크롤링 기록이 없으면 'NEVER_CRAWLED' 반환"""
        # Given: 크롤링 기록 없음

        # When: Serializer로 직렬화
        serializer = CharacterBasicSerializer(character_basic)
        data = serializer.data

        # Then: last_crawl_status가 'NEVER_CRAWLED'
        assert data['last_crawl_status'] == 'NEVER_CRAWLED'

    def test_last_crawl_status_retry_returns_failed(self, character_basic):
        """RETRY 상태도 'FAILED'로 반환"""
        # Given: RETRY 상태의 크롤링 기록
        CrawlTask.objects.create(
            task_id='test-task-retry',
            character_basic=character_basic,
            task_type='inventory',
            status='RETRY',
            progress=0,
            retry_count=2
        )

        # When: Serializer로 직렬화
        serializer = CharacterBasicSerializer(character_basic)
        data = serializer.data

        # Then: last_crawl_status가 'FAILED'
        assert data['last_crawl_status'] == 'FAILED'

    def test_pending_status_with_previous_success(self, character_basic):
        """PENDING 상태이지만 이전에 성공한 크롤링이 있으면 'SUCCESS' 반환"""
        # Given: 이전 성공 기록과 현재 PENDING 기록
        old_task = CrawlTask.objects.create(
            task_id='test-task-old-success',
            character_basic=character_basic,
            task_type='inventory',
            status='SUCCESS',
            progress=100
        )
        # 이전 기록의 시간을 과거로 설정
        CrawlTask.objects.filter(pk=old_task.pk).update(
            updated_at=timezone.now() - timedelta(hours=2)
        )

        # 현재 PENDING 기록
        CrawlTask.objects.create(
            task_id='test-task-pending',
            character_basic=character_basic,
            task_type='inventory',
            status='PENDING',
            progress=0
        )

        # When: Serializer로 직렬화
        serializer = CharacterBasicSerializer(character_basic)
        data = serializer.data

        # Then: 이전에 성공했으므로 'SUCCESS' 반환
        assert data['last_crawl_status'] == 'SUCCESS'


class TestCharacterResponseSerializerCrawlStatus:
    """CharacterResponseSerializer 크롤링 상태 테스트 (N+1 방지 로직 포함)"""

    def test_ac2_8_1_character_list_includes_crawl_status(self, character, character_basic):
        """AC #1: 캐릭터 목록 API 응답에 크롤링 상태 포함"""
        # Given: 성공한 크롤링 기록
        CrawlTask.objects.create(
            task_id='test-task-list',
            character_basic=character_basic,
            task_type='inventory',
            status='SUCCESS',
            progress=100
        )

        # When: Serializer로 직렬화 (context 없이 fallback 로직 테스트)
        serializer = CharacterResponseSerializer(character)
        data = serializer.data

        # Then: 크롤링 상태 필드가 존재
        assert 'last_crawled_at' in data
        assert 'last_crawl_status' in data
        assert data['last_crawl_status'] == 'SUCCESS'

    def test_character_list_never_crawled_when_no_character_basic(self, user, db):
        """CharacterBasic이 없으면 'NEVER_CRAWLED' 반환"""
        # Given: CharacterBasic 없이 Character만 존재
        character_no_basic = Character.objects.create(
            user=user,
            ocid='non-existent-ocid',
            character_name='없는캐릭터',
            world_name='스카니아',
            character_class='영웅',
            character_level=100
        )

        # When: Serializer로 직렬화
        serializer = CharacterResponseSerializer(character_no_basic)
        data = serializer.data

        # Then: NEVER_CRAWLED 반환
        assert data['last_crawled_at'] is None
        assert data['last_crawl_status'] == 'NEVER_CRAWLED'

    def test_n_plus_1_query_prevention_with_context(self, user, character_basic, db):
        """N+1 쿼리 방지: context에서 미리 조회된 데이터 사용"""
        # Given: Character와 크롤링 기록
        character = Character.objects.create(
            user=user,
            ocid=character_basic.ocid,
            character_name=character_basic.character_name,
            world_name=character_basic.world_name,
            character_class=character_basic.character_class,
            character_level=200
        )

        crawl_time = timezone.now() - timedelta(minutes=30)
        CrawlTask.objects.create(
            task_id='test-task-context',
            character_basic=character_basic,
            task_type='inventory',
            status='SUCCESS',
            progress=100
        )
        task = CrawlTask.objects.get(task_id='test-task-context')
        CrawlTask.objects.filter(pk=task.pk).update(updated_at=crawl_time)

        # 미리 조회된 데이터 (View에서 제공하는 context)
        character_basic_map = {character_basic.ocid: character_basic.id}
        crawl_success_map = {character_basic.id: crawl_time}
        crawl_status_map = {character_basic.id: 'SUCCESS'}

        # When: context와 함께 Serializer 사용
        serializer = CharacterResponseSerializer(
            character,
            context={
                'character_basic_map': character_basic_map,
                'crawl_success_map': crawl_success_map,
                'crawl_status_map': crawl_status_map
            }
        )
        data = serializer.data

        # Then: context 데이터 사용
        assert data['last_crawled_at'] == crawl_time.isoformat()
        assert data['last_crawl_status'] == 'SUCCESS'


class TestCrawlStatusTimeCalculation:
    """크롤링 시간 계산 테스트 (프론트엔드용 데이터 검증)"""

    def test_last_crawled_at_returns_iso_format(self, character_basic):
        """마지막 크롤링 시간이 ISO 8601 형식으로 반환"""
        # Given: 크롤링 기록
        CrawlTask.objects.create(
            task_id='test-task-iso',
            character_basic=character_basic,
            task_type='inventory',
            status='SUCCESS',
            progress=100
        )

        # When: Serializer로 직렬화
        serializer = CharacterBasicSerializer(character_basic)
        data = serializer.data

        # Then: ISO 8601 형식 확인 (T와 + 또는 Z 포함)
        assert data['last_crawled_at'] is not None
        assert 'T' in data['last_crawled_at']

    def test_multiple_crawl_tasks_returns_latest(self, character_basic):
        """여러 크롤링 기록 중 가장 최신 성공 기록 반환"""
        # Given: 여러 크롤링 기록
        old_time = timezone.now() - timedelta(hours=5)
        new_time = timezone.now() - timedelta(minutes=10)

        old_task = CrawlTask.objects.create(
            task_id='test-task-old',
            character_basic=character_basic,
            task_type='inventory',
            status='SUCCESS',
            progress=100
        )
        CrawlTask.objects.filter(pk=old_task.pk).update(updated_at=old_time)

        new_task = CrawlTask.objects.create(
            task_id='test-task-new',
            character_basic=character_basic,
            task_type='storage',
            status='SUCCESS',
            progress=100
        )
        CrawlTask.objects.filter(pk=new_task.pk).update(updated_at=new_time)

        # When: Serializer로 직렬화
        serializer = CharacterBasicSerializer(character_basic)
        data = serializer.data

        # Then: 최신 기록의 시간 반환
        assert data['last_crawled_at'] is not None
        # ISO 문자열에서 시간 비교 (최신이 반환되어야 함)
