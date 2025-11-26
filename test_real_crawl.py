"""
실제 데이터 크롤링 테스트 - 식사동그놈 캐릭터

Story 2.3 Phase 6: 아이템 상세 정보 크롤링 실제 테스트
"""
import os
import django

# Django 설정 (ORM import 전에 먼저 설정)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maplestorage_backend.settings')
django.setup()

import asyncio
from asgiref.sync import sync_to_async
from characters.models import CharacterBasic, Inventory, ItemDetail
from characters.crawler_services import ItemDetailCrawler


async def main():
    """식사동그놈 캐릭터의 인벤토리 아이템 상세 크롤링 (async)"""

    character_name = "식사동그놈"

    print(f"\n{'='*60}")
    print(f"실제 크롤링 테스트: {character_name}")
    print(f"{'='*60}\n")

    # 1. CharacterBasic 조회 (sync_to_async 래핑)
    try:
        @sync_to_async
        def get_character_basic():
            return CharacterBasic.objects.filter(
                character_name=character_name
            ).first()

        character_basic = await get_character_basic()

        if not character_basic:
            print(f"❌ CharacterBasic not found for {character_name}")
            print("먼저 'inventory' 크롤링을 실행하여 CharacterBasic을 생성하세요.")
            return

        print(f"✅ CharacterBasic found: {character_basic.character_name}")
        print(f"   World: {character_basic.world_name}")
        print(f"   Class: {character_basic.character_class}\n")

    except Exception as e:
        print(f"❌ Error finding CharacterBasic: {e}")
        import traceback
        traceback.print_exc()
        return

    # 2. Inventory 아이템 조회 (detail_url이 있는 것만)
    @sync_to_async
    def get_inventory_items():
        items = Inventory.objects.filter(
            character_basic=character_basic,
            detail_url__isnull=False,
            has_detail=False  # 아직 상세 정보가 없는 것만
        ).order_by('id')[:10]  # 테스트용 10개만
        return list(items), items.count()

    inventory_items, total_items = await get_inventory_items()

    if total_items == 0:
        print("❌ No inventory items with detail_url found")
        print("먼저 'inventory' 크롤링을 실행하여 detail_url을 생성하세요.")
        return

    print(f"✅ Found {total_items} items to crawl (testing first 10)\n")

    # 3. 크롤링 시작
    print("🔄 Starting ItemDetailCrawler...")
    print(f"   Rate limiting: 2-3초/아이템")
    print(f"   Batch size: 50개")
    print(f"   Expected time: ~{total_items * 2.5 / 60:.1f}분\n")

    crawler = ItemDetailCrawler()

    # Progress 콜백
    def progress_callback(current, total):
        percentage = int((current / total) * 100)
        print(f"   Progress: [{current}/{total}] {percentage}%")

    try:
        # 크롤링 실행 (이미 async 함수이므로 await 사용)
        result = await crawler.crawl_item_details(
            inventory_items,
            progress_callback=progress_callback
        )

        print(f"\n{'='*60}")
        print(f"크롤링 완료!")
        print(f"{'='*60}")
        print(f"✅ 성공: {result['success_count']}/{total_items}")
        print(f"❌ 실패: {len(result['failed_items'])}/{total_items}")
        print(f"⏱️  소요 시간: {result['total_time']:.1f}초")

        if result['failed_items']:
            print(f"\n실패 아이템 목록:")
            for item_name in result['failed_items']:
                print(f"  - {item_name}")

        # 4. 저장된 데이터 확인
        print(f"\n{'='*60}")
        print(f"저장된 ItemDetail 데이터 확인")
        print(f"{'='*60}\n")

        @sync_to_async
        def get_item_details():
            # select_related로 관련 객체 미리 로드
            return list(ItemDetail.objects.filter(
                inventory_item__character_basic=character_basic
            ).select_related('inventory_item')[:5])  # 처음 5개만 출력

        item_details = await get_item_details()

        for detail in item_details:
            print(f"📦 {detail.inventory_item.item_name}")
            print(f"   Category: {detail.item_category}")
            print(f"   Required Level: {detail.required_level}")
            if detail.attack_power:
                print(f"   Attack: {detail.attack_power}")
            if detail.magic_power:
                print(f"   Magic: {detail.magic_power}")
            if detail.potential_grade:
                print(f"   Potential: {detail.potential_grade}")
                if detail.potential_option_1:
                    print(f"     - {detail.potential_option_1}")
                if detail.potential_option_2:
                    print(f"     - {detail.potential_option_2}")
                if detail.potential_option_3:
                    print(f"     - {detail.potential_option_3}")
            print()

        print(f"총 {len(item_details)}개 데이터 저장됨\n")

        # 5. 통계
        @sync_to_async
        def get_statistics():
            total_details = ItemDetail.objects.filter(
                inventory_item__character_basic=character_basic
            ).count()

            with_potential = ItemDetail.objects.filter(
                inventory_item__character_basic=character_basic,
                potential_grade__isnull=False
            ).count()

            with_additional = ItemDetail.objects.filter(
                inventory_item__character_basic=character_basic,
                additional_potential_grade__isnull=False
            ).count()

            return total_details, with_potential, with_additional

        total_details, with_potential, with_additional = await get_statistics()

        print(f"{'='*60}")
        print(f"통계")
        print(f"{'='*60}")
        print(f"총 ItemDetail: {total_details}개")
        print(f"잠재능력 있음: {with_potential}개")
        print(f"에디셔널 있음: {with_additional}개")
        print()

    except Exception as e:
        print(f"\n❌ 크롤링 실패: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    # async main 함수 실행
    asyncio.run(main())
