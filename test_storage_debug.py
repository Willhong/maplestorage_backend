"""
창고 페이지 디버깅 스크립트 (headless=False)
p 파라미터는 캐릭터 정보 페이지에서 크롤링해야 함
"""
import asyncio
from playwright.async_api import async_playwright

async def debug_storage_page():
    # 캐릭터명 (URL 인코딩 필요)
    character_name = "식사동그놈"

    # 기본 캐릭터 정보 페이지 (p 파라미터 없이)
    base_url = f"https://maplestory.nexon.com/Common/Character/Detail/{character_name}"

    print(f"{'='*60}")
    print(f"🔍 창고 크롤링 디버깅: {character_name}")
    print(f"{'='*60}")
    print(f"\n기본 URL: {base_url}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,  # 브라우저 표시
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )

        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )

        page = await context.new_page()

        # 1. 캐릭터 정보 페이지 접속
        print("\n1️⃣ 캐릭터 정보 페이지 접속 중...")
        try:
            response = await page.goto(base_url, wait_until='domcontentloaded', timeout=30000)
            print(f"   응답 상태: {response.status if response else 'N/A'}")
            print(f"   최종 URL: {page.url}")
        except Exception as e:
            print(f"   ❌ 접속 실패: {e}")
            await browser.close()
            return

        await asyncio.sleep(2)

        # 2. Storage 링크 찾기 (p 파라미터 포함)
        print("\n2️⃣ Storage 링크 찾는 중...")
        storage_url = None

        # Storage 링크를 찾는 다양한 방법 시도
        selectors = [
            'a[href*="/Storage?p="]',
            'a[href*="Storage"]',
        ]

        for selector in selectors:
            try:
                elements = await page.query_selector_all(selector)
                if elements:
                    print(f"   ✅ '{selector}': {len(elements)}개 찾음")
                    for el in elements:
                        href = await el.get_attribute('href')
                        text = await el.inner_text()
                        print(f"      - {text.strip()}: {href}")
                        if href and '/Storage' in href and '?p=' in href:
                            storage_url = href
                            if not storage_url.startswith('http'):
                                storage_url = f"https://maplestory.nexon.com{storage_url}"
                            break
                    if storage_url:
                        break
            except Exception as e:
                print(f"   ❌ '{selector}': {e}")

        if storage_url:
            print(f"\n✅ Storage URL 발견: {storage_url}")

            # 3. Storage 페이지 접속
            print("\n3️⃣ Storage 페이지 접속 중...")
            await page.goto(storage_url, wait_until='domcontentloaded', timeout=30000)
            print(f"   최종 URL: {page.url}")

            await asyncio.sleep(2)

            # 4. 창고 아이템 확인
            print("\n4️⃣ 창고 아이템 확인 중...")

            # 아이템 목록 찾기
            item_selectors = [
                '.inven_list',
                '.storage_list',
                '.my_info',
                '.item_list',
            ]

            for sel in item_selectors:
                area = await page.query_selector(sel)
                if area:
                    html = await area.inner_html()
                    print(f"   ✅ {sel} 영역: {len(html)} bytes")
                    # 처음 500자만 출력
                    if len(html) > 500:
                        print(f"   HTML (처음 500자):\n{html[:500]}...")
                    else:
                        print(f"   HTML:\n{html}")
                    break

        else:
            print("\n❌ Storage URL을 찾지 못했습니다.")
            print("   페이지 HTML에서 링크 확인 중...")

            # 모든 링크 출력
            all_links = await page.query_selector_all('a')
            storage_links = []
            for link in all_links:
                href = await link.get_attribute('href')
                if href and 'Storage' in href:
                    storage_links.append(href)

            if storage_links:
                print(f"   Storage 관련 링크 {len(storage_links)}개:")
                for link in storage_links[:5]:
                    print(f"      - {link}")

        # 잠시 대기 (수동 확인용)
        print("\n⏳ 15초 대기 (브라우저에서 확인하세요)...")
        await asyncio.sleep(15)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_storage_page())
