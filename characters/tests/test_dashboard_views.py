"""
Dashboard Views Tests (Stories 5.4, 5.6)

대시보드 통계 및 만료 예정 아이템 API 테스트
사용자의 대시보드 통계와 7일 이내 만료 예정 아이템 목록을 검증합니다.
"""
from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from datetime import timedelta

from accounts.models import Character
from characters.models import CharacterBasic, Inventory, Storage


class DashboardStatsViewTests(TestCase):
    """
    대시보드 통계 뷰 테스트 (Story 5.6)

    사용자의 전체 대시보드 통계 조회 API를 검증합니다.
    """

    def setUp(self):
        """테스트 데이터 설정"""
        # 사용자 생성
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            password='otherpass123'
        )

        # API 클라이언트 설정
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        # URL
        self.url = reverse('dashboard-stats')

        # 캐릭터 및 CharacterBasic 생성
        self.char1_ocid = 'test-ocid-001'
        self.char2_ocid = 'test-ocid-002'
        self.char3_ocid = 'test-ocid-003'

        # 사용자의 캐릭터 생성
        Character.objects.create(
            user=self.user,
            ocid=self.char1_ocid,
            character_name='윌홍',
            world_name='스카니아',
            character_class='나이트로드',
            character_level=250
        )
        Character.objects.create(
            user=self.user,
            ocid=self.char2_ocid,
            character_name='부캐',
            world_name='스카니아',
            character_class='아크',
            character_level=230
        )

        # 다른 사용자의 캐릭터
        Character.objects.create(
            user=self.other_user,
            ocid=self.char3_ocid,
            character_name='타인캐릭',
            world_name='베라',
            character_class='제로',
            character_level=200
        )

        # CharacterBasic 데이터 생성 (메소 포함)
        self.char1_basic = CharacterBasic.objects.create(
            ocid=self.char1_ocid,
            character_name='윌홍',
            world_name='스카니아',
            character_gender='남',
            character_class='나이트로드',
            character_level=250,
            meso=500_000_000  # 5억
        )
        self.char2_basic = CharacterBasic.objects.create(
            ocid=self.char2_ocid,
            character_name='부캐',
            world_name='스카니아',
            character_gender='여',
            character_class='아크',
            character_level=230,
            meso=300_000_000  # 3억
        )
        CharacterBasic.objects.create(
            ocid=self.char3_ocid,
            character_name='타인캐릭',
            world_name='베라',
            character_gender='남',
            character_class='제로',
            character_level=200,
            meso=1_000_000_000  # 10억 (다른 사용자)
        )

    def test_authentication_required(self):
        """인증되지 않은 사용자는 접근할 수 없음"""
        client = APIClient()  # 인증 없는 클라이언트
        response = client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_dashboard_stats_success(self):
        """정상적인 대시보드 통계 조회"""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # 필드 존재 확인
        self.assertIn('total_characters', data)
        self.assertIn('total_meso', data)
        self.assertIn('expiring_items_count', data)
        self.assertIn('recent_crawl', data)

        # 최근 크롤링 정보 필드 확인
        self.assertIn('last_crawled_at', data['recent_crawl'])
        self.assertIn('characters_updated', data['recent_crawl'])

    def test_total_characters_count(self):
        """총 캐릭터 수가 정확하게 집계됨"""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # 사용자의 캐릭터 2개만 카운트
        self.assertEqual(data['total_characters'], 2)

    def test_total_meso_aggregation(self):
        """총 메소가 정확하게 집계됨"""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # 총 메소 = 캐릭터 메소 합계
        expected_total = 500_000_000 + 300_000_000  # 8억
        self.assertEqual(data['total_meso'], expected_total)

    def test_null_meso_treated_as_zero(self):
        """NULL 메소는 0으로 처리됨"""
        # 메소가 NULL인 캐릭터 생성
        char4_ocid = 'test-ocid-004'
        Character.objects.create(
            user=self.user,
            ocid=char4_ocid,
            character_name='메소없는캐릭',
            world_name='스카니아'
        )
        CharacterBasic.objects.create(
            ocid=char4_ocid,
            character_name='메소없는캐릭',
            world_name='스카니아',
            character_gender='남',
            character_class='데몬슬레이어',
            character_level=100,
            meso=None  # NULL
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # NULL은 0으로 처리되어 합계에 영향 없음
        expected_total = 500_000_000 + 300_000_000 + 0
        self.assertEqual(data['total_meso'], expected_total)
        self.assertEqual(data['total_characters'], 3)

    def test_expiring_items_count(self):
        """7일 이내 만료 예정 아이템 수가 정확하게 집계됨"""
        # 만료 예정 아이템 생성 (7일 이내)
        now = timezone.now()

        # D-1 아이템
        Inventory.objects.create(
            character_basic=self.char1_basic,
            item_name='만료임박템',
            item_icon='https://example.com/icon1.png',
            expiry_date=now + timedelta(days=1),
            item_type='equip',
            slot_position=1
        )

        # D-5 아이템
        Storage.objects.create(
            character_basic=self.char2_basic,
            item_name='창고만료템',
            item_icon='https://example.com/icon2.png',
            expiry_date=now + timedelta(days=5),
            storage_type='shared',
            slot_position=1
        )

        # D-8 아이템 (7일 초과 - 카운트 안 됨)
        Inventory.objects.create(
            character_basic=self.char1_basic,
            item_name='여유템',
            item_icon='https://example.com/icon3.png',
            expiry_date=now + timedelta(days=8),
            item_type='use',
            slot_position=2
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # 7일 이내 아이템 2개만 카운트
        self.assertEqual(data['expiring_items_count'], 2)

    def test_no_expiring_items(self):
        """만료 예정 아이템이 없을 때 0 반환"""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertEqual(data['expiring_items_count'], 0)

    def test_recent_crawl_info(self):
        """최근 크롤링 정보가 올바르게 반환됨"""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # last_crawled_at은 CharacterBasic의 last_updated 최댓값
        self.assertIsNotNone(data['recent_crawl']['last_crawled_at'])

        # 24시간 내 업데이트된 캐릭터 수 (모든 캐릭터가 방금 생성됨)
        self.assertEqual(data['recent_crawl']['characters_updated'], 2)

    def test_only_user_data(self):
        """다른 사용자의 데이터는 제외됨"""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # 다른 사용자의 캐릭터와 메소는 제외됨
        self.assertEqual(data['total_characters'], 2)
        # 다른 사용자의 10억은 포함 안 됨
        self.assertEqual(data['total_meso'], 800_000_000)

    def test_empty_state(self):
        """캐릭터가 없는 사용자는 모든 값이 0 또는 null"""
        # 새로운 사용자 (캐릭터 없음)
        new_user = User.objects.create_user(
            username='newuser',
            password='newpass123'
        )
        client = APIClient()
        client.force_authenticate(user=new_user)

        response = client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertEqual(data['total_characters'], 0)
        self.assertEqual(data['total_meso'], 0)
        self.assertEqual(data['expiring_items_count'], 0)
        self.assertIsNone(data['recent_crawl']['last_crawled_at'])
        self.assertEqual(data['recent_crawl']['characters_updated'], 0)

    def test_recent_crawl_24h_window(self):
        """24시간 내 업데이트된 캐릭터 수 계산이 정확함"""
        # 과거 업데이트 캐릭터 생성 (25시간 전)
        char5_ocid = 'test-ocid-005'
        Character.objects.create(
            user=self.user,
            ocid=char5_ocid,
            character_name='과거캐릭',
            world_name='스카니아'
        )

        past_basic = CharacterBasic.objects.create(
            ocid=char5_ocid,
            character_name='과거캐릭',
            world_name='스카니아',
            character_gender='남',
            character_class='히어로',
            character_level=150,
            meso=100_000_000
        )

        # last_updated를 25시간 전으로 설정
        past_time = timezone.now() - timedelta(hours=25)
        CharacterBasic.objects.filter(ocid=char5_ocid).update(last_updated=past_time)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # 24시간 내 업데이트는 2개만 (char1, char2)
        self.assertEqual(data['recent_crawl']['characters_updated'], 2)

        # 총 캐릭터는 3개
        self.assertEqual(data['total_characters'], 3)


class ExpiringItemsViewTests(TestCase):
    """
    만료 예정 아이템 목록 뷰 테스트 (Story 5.1/5.4)

    사용자의 7일 이내 만료 예정 아이템 목록 조회 API를 검증합니다.
    """

    def setUp(self):
        """테스트 데이터 설정"""
        # 사용자 생성
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            password='otherpass123'
        )

        # API 클라이언트 설정
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        # URL
        self.url = reverse('expiring-items')

        # 캐릭터 및 CharacterBasic 생성
        self.char1_ocid = 'test-ocid-001'
        self.char2_ocid = 'test-ocid-002'
        self.char3_ocid = 'test-ocid-003'

        # 사용자의 캐릭터 생성
        Character.objects.create(
            user=self.user,
            ocid=self.char1_ocid,
            character_name='윌홍',
            world_name='스카니아'
        )
        Character.objects.create(
            user=self.user,
            ocid=self.char2_ocid,
            character_name='부캐',
            world_name='스카니아'
        )

        # 다른 사용자의 캐릭터
        Character.objects.create(
            user=self.other_user,
            ocid=self.char3_ocid,
            character_name='타인캐릭',
            world_name='베라'
        )

        # CharacterBasic 데이터 생성
        self.char1_basic = CharacterBasic.objects.create(
            ocid=self.char1_ocid,
            character_name='윌홍',
            world_name='스카니아',
            character_gender='남',
            character_class='나이트로드',
            character_level=250
        )
        self.char2_basic = CharacterBasic.objects.create(
            ocid=self.char2_ocid,
            character_name='부캐',
            world_name='스카니아',
            character_gender='여',
            character_class='아크',
            character_level=230
        )
        self.char3_basic = CharacterBasic.objects.create(
            ocid=self.char3_ocid,
            character_name='타인캐릭',
            world_name='베라',
            character_gender='남',
            character_class='제로',
            character_level=200
        )

    def test_authentication_required(self):
        """인증되지 않은 사용자는 접근할 수 없음"""
        client = APIClient()  # 인증 없는 클라이언트
        response = client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_expiring_items_list(self):
        """7일 이내 만료 예정 아이템 목록이 반환됨"""
        now = timezone.now()

        # 만료 예정 아이템 생성
        Inventory.objects.create(
            character_basic=self.char1_basic,
            item_name='만료임박템',
            item_icon='https://example.com/icon1.png',
            expiry_date=now + timedelta(days=2),
            item_type='equip',
            slot_position=1
        )

        Storage.objects.create(
            character_basic=self.char2_basic,
            item_name='창고만료템',
            item_icon='https://example.com/icon2.png',
            expiry_date=now + timedelta(days=5),
            storage_type='shared',
            slot_position=1
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # 아이템 수 확인
        self.assertEqual(data['count'], 2)
        self.assertEqual(len(data['items']), 2)

        # 첫 번째 아이템 필드 확인
        item = data['items'][0]
        self.assertIn('id', item)
        self.assertIn('item_name', item)
        self.assertIn('item_icon', item)
        self.assertIn('character_name', item)
        self.assertIn('character_ocid', item)
        self.assertIn('location', item)
        self.assertIn('expiry_date', item)
        self.assertIn('days_until_expiry', item)
        self.assertIn('urgency', item)

    def test_urgency_levels(self):
        """긴급도 레벨이 올바르게 계산됨"""
        now = timezone.now()

        # D-1 아이템 (danger)
        inv_danger = Inventory.objects.create(
            character_basic=self.char1_basic,
            item_name='위험템',
            item_icon='https://example.com/danger.png',
            expiry_date=now + timedelta(days=1),
            item_type='equip',
            slot_position=1
        )

        # D-3 아이템 (warning)
        inv_warning = Inventory.objects.create(
            character_basic=self.char1_basic,
            item_name='경고템',
            item_icon='https://example.com/warning.png',
            expiry_date=now + timedelta(days=3),
            item_type='use',
            slot_position=2
        )

        # D-7 아이템 (info)
        inv_info = Inventory.objects.create(
            character_basic=self.char1_basic,
            item_name='정보템',
            item_icon='https://example.com/info.png',
            expiry_date=now + timedelta(days=7),
            item_type='etc',
            slot_position=3
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # 아이템별 긴급도 확인
        items = {item['item_name']: item for item in data['items']}

        self.assertEqual(items['위험템']['urgency'], 'danger')
        self.assertEqual(items['위험템']['days_until_expiry'], 1)

        self.assertEqual(items['경고템']['urgency'], 'warning')
        self.assertEqual(items['경고템']['days_until_expiry'], 3)

        self.assertEqual(items['정보템']['urgency'], 'info')
        self.assertEqual(items['정보템']['days_until_expiry'], 7)

    def test_items_sorted_by_expiry(self):
        """아이템이 만료 임박 순으로 정렬됨"""
        now = timezone.now()

        # 아이템을 역순으로 생성
        Inventory.objects.create(
            character_basic=self.char1_basic,
            item_name='먼저만료',
            item_icon='https://example.com/icon1.png',
            expiry_date=now + timedelta(days=7),
            item_type='equip',
            slot_position=3
        )

        Inventory.objects.create(
            character_basic=self.char1_basic,
            item_name='중간만료',
            item_icon='https://example.com/icon2.png',
            expiry_date=now + timedelta(days=3),
            item_type='use',
            slot_position=2
        )

        Inventory.objects.create(
            character_basic=self.char1_basic,
            item_name='가장먼저만료',
            item_icon='https://example.com/icon3.png',
            expiry_date=now + timedelta(days=1),
            item_type='etc',
            slot_position=1
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # 만료 임박 순으로 정렬되었는지 확인
        self.assertEqual(data['items'][0]['item_name'], '가장먼저만료')
        self.assertEqual(data['items'][1]['item_name'], '중간만료')
        self.assertEqual(data['items'][2]['item_name'], '먼저만료')

    def test_inventory_and_storage_items(self):
        """인벤토리와 창고 아이템이 모두 포함됨"""
        now = timezone.now()

        # 인벤토리 아이템
        Inventory.objects.create(
            character_basic=self.char1_basic,
            item_name='인벤토리템',
            item_icon='https://example.com/inv.png',
            expiry_date=now + timedelta(days=2),
            item_type='equip',
            slot_position=1
        )

        # 창고 아이템
        Storage.objects.create(
            character_basic=self.char2_basic,
            item_name='창고템',
            item_icon='https://example.com/storage.png',
            expiry_date=now + timedelta(days=4),
            storage_type='shared',
            slot_position=1
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # 두 위치의 아이템 모두 포함
        self.assertEqual(data['count'], 2)

        items = {item['item_name']: item for item in data['items']}
        self.assertEqual(items['인벤토리템']['location'], 'inventory')
        self.assertEqual(items['창고템']['location'], 'storage')

    def test_no_expiring_items(self):
        """만료 예정 아이템이 없을 때 빈 목록 반환"""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertEqual(data['count'], 0)
        self.assertEqual(len(data['items']), 0)

    def test_only_user_items(self):
        """다른 사용자의 아이템은 제외됨"""
        now = timezone.now()

        # 본인 아이템
        Inventory.objects.create(
            character_basic=self.char1_basic,
            item_name='내아이템',
            item_icon='https://example.com/mine.png',
            expiry_date=now + timedelta(days=2),
            item_type='equip',
            slot_position=1
        )

        # 다른 사용자 아이템
        Inventory.objects.create(
            character_basic=self.char3_basic,
            item_name='남의아이템',
            item_icon='https://example.com/others.png',
            expiry_date=now + timedelta(days=2),
            item_type='equip',
            slot_position=1
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # 본인 아이템 1개만 포함
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['items'][0]['item_name'], '내아이템')

    def test_items_outside_7day_window_excluded(self):
        """7일 초과 아이템과 이미 만료된 아이템은 제외됨"""
        now = timezone.now()

        # 7일 초과 아이템
        Inventory.objects.create(
            character_basic=self.char1_basic,
            item_name='여유템',
            item_icon='https://example.com/future.png',
            expiry_date=now + timedelta(days=8),
            item_type='equip',
            slot_position=1
        )

        # 이미 만료된 아이템
        Inventory.objects.create(
            character_basic=self.char1_basic,
            item_name='만료된템',
            item_icon='https://example.com/expired.png',
            expiry_date=now - timedelta(days=1),
            item_type='use',
            slot_position=2
        )

        # 7일 이내 아이템 (포함되어야 함)
        Inventory.objects.create(
            character_basic=self.char1_basic,
            item_name='포함템',
            item_icon='https://example.com/included.png',
            expiry_date=now + timedelta(days=3),
            item_type='etc',
            slot_position=3
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # 7일 이내 아이템 1개만 포함
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['items'][0]['item_name'], '포함템')
