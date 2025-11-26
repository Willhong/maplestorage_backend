"""
인벤토리 크롤링 테스트 - 식사동그놈 캐릭터

detail_url을 생성하기 위한 inventory 크롤링 실행
"""
import os
import django

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maplestorage_backend.settings')
django.setup()

import asyncio
from asgiref.sync import sync_to_async
from characters.models import CharacterBasic, Inventory
from characters.crawler_services import CrawlerService
from characters.schemas import InventoryItemSchema
from pydantic import ValidationError


async def main():
    """식사동그놈 캐릭터의 인벤토리 크롤링"""

    character_name = "식사동그놈"

    print(f"\n{'='*60}")
    print(f"인벤토리 크롤링: {character_name}")
    print(f"{'='*60}\n")

    # 1. CharacterBasic 조회
    @sync_to_async
    def get_character_basic():
        return CharacterBasic.objects.filter(
            character_name=character_name
        ).first()

    character_basic = await get_character_basic()

    if not character_basic:
        print(f"❌ CharacterBasic not found for {character_name}")
        return

    print(f"✅ CharacterBasic found: {character_basic.character_name}")
    print(f"   World: {character_basic.world_name}")
    print(f"   Class: {character_basic.character_class}")

    # character_info_url 확인
    if not character_basic.character_info_url:
        print(f"\n⚠️  character_info_url이 없습니다.")
        print(f"임시 URL을 생성합니다...")
        character_info_url = f"https://maplestory.nexon.com/MyMaple/Character/Detail/{character_name}"

        # character_info_url 업데이트
        @sync_to_async
        def update_character_info_url():
            character_basic.character_info_url = character_info_url
            character_basic.save()

        await update_character_info_url()
        print(f"✅ character_info_url 업데이트 완료")
    else:
        character_info_url = character_basic.character_info_url

    print(f"   URL: {character_info_url}\n")

    # 2. 인벤토리 크롤링 실행
    print("🔄 인벤토리 크롤링 시작...")
    print("   Playwright로 실제 웹사이트 접속")
    print("   예상 소요 시간: 10-30초\n")

    try:
        crawler = CrawlerService()
        crawled_data = await crawler.crawl_inventory(
            character_info_url,
            character_name
        )

        print(f"\n✅ 크롤링 완료!")
        print(f"   파싱된 아이템 수: {len(crawled_data['items'])}개")
        print(f"   크롤링 시간: {crawled_data.get('crawled_at', 'N/A')}\n")

        # 3. 데이터 검증 및 저장
        print("💾 데이터 검증 및 DB 저장 중...")

        saved_count = 0
        detail_url_count = 0

        @sync_to_async
        def save_inventory_items(items_data):
            nonlocal saved_count, detail_url_count
            for item_data in items_data:
                try:
                    # Pydantic 검증
                    validated_item = InventoryItemSchema(**item_data)

                    # DB 저장
                    Inventory.objects.create(
                        character_basic=character_basic,
                        item_name=validated_item.item_name,
                        item_icon=validated_item.item_icon,
                        quantity=validated_item.quantity,
                        item_options=validated_item.item_options,
                        slot_position=validated_item.slot_position,
                        expiry_date=validated_item.expiry_date,
                        detail_url=validated_item.detail_url,
                        has_detail=False
                    )
                    saved_count += 1

                    # detail_url이 있는 아이템 카운트
                    if validated_item.detail_url:
                        detail_url_count += 1

                except ValidationError as ve:
                    print(f"⚠️  검증 실패: slot {item_data.get('slot_position')}")
                    continue

        await save_inventory_items(crawled_data['items'])

        print(f"\n✅ 저장 완료!")
        print(f"   총 저장: {saved_count}개")
        print(f"   detail_url 있음: {detail_url_count}개")
        print(f"   detail_url 없음: {saved_count - detail_url_count}개\n")

        # 4. 샘플 출력 (detail_url이 있는 첫 5개)
        print(f"{'='*60}")
        print("샘플 아이템 (detail_url 있음)")
        print(f"{'='*60}\n")

        @sync_to_async
        def get_sample_items():
            return list(Inventory.objects.filter(
                character_basic=character_basic,
                detail_url__isnull=False
            ).order_by('-id')[:5])

        sample_items = await get_sample_items()

        for item in sample_items:
            print(f"📦 {item.item_name} (x{item.quantity})")
            print(f"   Icon: {item.item_icon[:50]}...")
            print(f"   Detail URL: {item.detail_url[:60]}...")
            if item.item_options:
                print(f"   Options: {item.item_options}")
            print()

        print(f"{'='*60}")
        print("✅ 인벤토리 크롤링 완료!")
        print("이제 test_real_crawl.py를 실행할 수 있습니다.")
        print(f"{'='*60}\n")

    except Exception as e:
        print(f"\n❌ 크롤링 실패: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    asyncio.run(main())
