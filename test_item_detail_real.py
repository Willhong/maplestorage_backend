"""
실제 데이터 테스트: 식사동그놈 캐릭터
Story 2.3 Phase 6 - ItemDetail 크롤링 실제 검증
"""
import os
import sys
import django
import asyncio
from datetime import datetime
from asgiref.sync import sync_to_async

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maplestorage_backend.settings')
django.setup()

from characters.models import CharacterBasic, Inventory, ItemDetail
from characters.crawler_services import ItemDetailCrawler, ItemDetailParser
from characters.schemas import ItemDetailSchema
from pydantic import ValidationError


async def test_item_detail_crawling():
    """식사동그놈 캐릭터로 ItemDetail 크롤링 테스트"""

    print("=" * 80)
    print("실제 데이터 테스트: 아이템 상세 정보 크롤링")
    print("=" * 80)
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # 1. CharacterBasic 확인
    try:
        character = await sync_to_async(CharacterBasic.objects.get)(character_name='식사동그놈')
        print(f"✅ 캐릭터 발견: {character.character_name}")
        print(f"   - OCID: {character.ocid}")
        print(f"   - 월드: {character.world_name}")
        print(f"   - 직업: {character.character_class}\n")
    except CharacterBasic.DoesNotExist:
        print("❌ '식사동그놈' 캐릭터를 찾을 수 없습니다.")
        print("   먼저 인벤토리 크롤링을 실행하여 캐릭터를 생성해주세요.\n")
        return

    # 2. Inventory 아이템 확인
    inventory_items = await sync_to_async(list)(
        Inventory.objects.filter(
            character_basic=character,
            detail_url__isnull=False
        ).order_by('-crawled_at')[:10]  # 최신 10개만
    )

    total_items = await sync_to_async(Inventory.objects.filter(character_basic=character).count)()
    items_with_url = await sync_to_async(
        Inventory.objects.filter(
            character_basic=character,
            detail_url__isnull=False
        ).count
    )()

    print(f"📦 인벤토리 상태:")
    print(f"   - 전체 아이템: {total_items}개")
    print(f"   - detail_url 있는 아이템: {items_with_url}개")
    print(f"   - 테스트 대상: {len(inventory_items)}개 (최신 10개)\n")

    if len(inventory_items) == 0:
        print("⚠️  detail_url이 있는 아이템이 없습니다.")
        print("   먼저 인벤토리 크롤링을 실행해주세요.\n")
        return

    # 3. ItemDetail 크롤링 실행
    print("🚀 ItemDetail 크롤링 시작...\n")

    crawler = ItemDetailCrawler()
    success_count = 0
    fail_count = 0
    validation_errors = 0

    for idx, item in enumerate(inventory_items, 1):
        print(f"[{idx}/{len(inventory_items)}] {item.item_name}")
        print(f"   URL: {item.detail_url}")

        try:
            # 크롤링 실행 (_crawl_single_item은 dict 또는 None 반환)
            detail_data = await crawler._crawl_single_item(item)

            if detail_data:
                # Pydantic 검증
                try:
                    schema = ItemDetailSchema(**detail_data)

                    # ItemDetail 저장
                    item_detail, created = await sync_to_async(ItemDetail.objects.update_or_create)(
                        inventory_item=item,
                        defaults=detail_data
                    )

                    print(f"   ✅ 성공 ({'생성' if created else '업데이트'})")
                    print(f"      - 카테고리: {detail_data.get('item_category', 'N/A')}")
                    print(f"      - 요구 레벨: {detail_data.get('required_level', 'N/A')}")
                    print(f"      - 공격력: {detail_data.get('attack_power', 'N/A')}")
                    print(f"      - 잠재능력: {detail_data.get('potential_grade', 'N/A')}")

                    success_count += 1

                except ValidationError as e:
                    print(f"   ⚠️  Pydantic 검증 실패:")
                    print(f"      {e}")
                    validation_errors += 1

            else:
                print(f"   ❌ 크롤링 실패: detail_data is None")
                fail_count += 1

        except Exception as e:
            print(f"   ❌ 예외 발생: {e}")
            fail_count += 1

        print()

    # 4. 결과 요약
    print("=" * 80)
    print("테스트 결과 요약")
    print("=" * 80)
    print(f"✅ 성공: {success_count}/{len(inventory_items)}")
    print(f"❌ 실패: {fail_count}/{len(inventory_items)}")
    print(f"⚠️  검증 오류: {validation_errors}/{len(inventory_items)}")

    success_rate = (success_count / len(inventory_items) * 100) if len(inventory_items) > 0 else 0
    print(f"\n성공률: {success_rate:.1f}%")

    # 5. DB 저장 확인
    stored_details = await sync_to_async(
        ItemDetail.objects.filter(
            inventory_item__character_basic=character
        ).count
    )()
    print(f"\nDB에 저장된 ItemDetail: {stored_details}개")

    print(f"\n종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)


if __name__ == '__main__':
    asyncio.run(test_item_detail_crawling())
