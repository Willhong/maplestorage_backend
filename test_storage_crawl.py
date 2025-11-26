"""
실제 창고 크롤링 테스트 스크립트
캐릭터: 식사동그놈

p 파라미터를 랭킹 페이지에서 새로 얻어온 후 창고 크롤링
"""
import os
import sys
import django
import asyncio

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maplestorage_backend.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from characters.crawler_services import CrawlerService, StorageParser

async def test_storage_crawl():
    character_name = "식사동그놈"

    print(f"\n{'='*60}")
    print(f"창고 크롤링 테스트: {character_name}")
    print(f"{'='*60}\n")

    crawler = CrawlerService()

    try:
        # 1. 랭킹 페이지에서 새로운 p 파라미터 얻기
        print("1. 랭킹 페이지에서 character_info_url 얻는 중...")
        character_info_url = await crawler.fetch_character_info_url(character_name)
        print(f"   ✅ URL: {character_info_url[:80]}...")

        # 2. 창고 크롤링 실행
        print("\n2. 창고 크롤링 시작...")
        result = await crawler.crawl_storage(character_info_url, character_name)

        print(f"\n{'='*60}")
        print(f"✅ 크롤링 완료!")
        print(f"{'='*60}")
        print(f"   - 캐릭터: {result['character_name']}")
        print(f"   - 크롤링 시간: {result['crawled_at']}")
        print(f"\n📦 창고: {len(result['items'])}개 아이템")
        for i, item in enumerate(result['items'][:10]):  # 처음 10개 표시
            print(f"   [{i+1}] {item['item_name']} x{item['quantity']} (슬롯 {item['slot_position']})")
        if len(result['items']) > 10:
            print(f"   ... 외 {len(result['items']) - 10}개")

    except Exception as e:
        print(f"\n❌ 크롤링 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_storage_crawl())
