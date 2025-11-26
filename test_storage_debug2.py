"""
창고 페이지 디버깅 스크립트 v2
캐릭터 정보 페이지의 전체 HTML 구조를 분석하여 Storage 링크 찾기
"""
import asyncio
from playwright.async_api import async_playwright

async def debug_storage_page_v2():
    # 캐릭터명
    character_name = "식사동그놈"

    # 캐릭터 정보 페이지 URL (공개 페이지)
    base_url = f"https://maplestory.nexon.com/Common/Character/Detail/{character_name}"

    print(f"{'='*70}")
    print(f"창고 크롤링 디버깅 v2: {character_name}")
    print(f"{'='*70}")
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
        print("\n1. 캐릭터 정보 페이지 접속 중...")
        try:
            response = await page.goto(base_url, wait_until='networkidle', timeout=30000)
            print(f"   응답 상태: {response.status if response else 'N/A'}")
            print(f"   최종 URL: {page.url}")
        except Exception as e:
            print(f"   접속 실패: {e}")
            await browser.close()
            return

        await asyncio.sleep(3)

        # 2. 페이지 전체 HTML 저장
        print("\n2. 페이지 HTML 분석 중...")
        html_content = await page.content()

        # HTML 파일로 저장
        with open('debug_character_page.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"   HTML 저장됨: debug_character_page.html ({len(html_content)} bytes)")

        # 3. 네비게이션 영역 분석
        print("\n3. 네비게이션/탭 영역 분석...")

        # 다양한 selector로 네비게이션 찾기
        nav_selectors = [
            '.snb',           # 서브 네비게이션
            '.lnb',           # 로컬 네비게이션
            '.tab',           # 탭
            '.menu',          # 메뉴
            'nav',            # HTML5 nav
            '.navigation',    # 네비게이션 클래스
            '.sub_menu',      # 서브메뉴
            '.char_info_tab', # 캐릭터 정보 탭
        ]

        for selector in nav_selectors:
            try:
                elements = await page.query_selector_all(selector)
                if elements:
                    print(f"\n   '{selector}' 발견: {len(elements)}개")
                    for i, el in enumerate(elements[:3]):  # 처음 3개만
                        html = await el.inner_html()
                        if len(html) > 300:
                            html = html[:300] + '...'
                        print(f"   [{i}] HTML: {html[:200]}")
            except Exception as e:
                pass

        # 4. 모든 링크 분석 (특히 Storage, Inventory 관련)
        print("\n4. 모든 링크 분석...")
        all_links = await page.query_selector_all('a')
        print(f"   총 링크 수: {len(all_links)}개")

        storage_related = []
        inventory_related = []
        p_param_links = []

        for link in all_links:
            try:
                href = await link.get_attribute('href')
                text = await link.inner_text()
                text = text.strip().replace('\n', ' ')[:50]

                if href:
                    if 'Storage' in href:
                        storage_related.append({'href': href, 'text': text})
                    if 'Inventory' in href:
                        inventory_related.append({'href': href, 'text': text})
                    if '?p=' in href or '&p=' in href:
                        p_param_links.append({'href': href, 'text': text})
            except:
                pass

        print(f"\n   Storage 관련 링크: {len(storage_related)}개")
        for item in storage_related[:10]:
            print(f"      [{item['text']}] {item['href']}")

        print(f"\n   Inventory 관련 링크: {len(inventory_related)}개")
        for item in inventory_related[:10]:
            print(f"      [{item['text']}] {item['href']}")

        print(f"\n   p 파라미터 포함 링크: {len(p_param_links)}개")
        for item in p_param_links[:20]:
            print(f"      [{item['text']}] {item['href']}")

        # 5. 특정 class를 가진 요소들 분석
        print("\n5. 캐릭터 정보 관련 요소 분석...")

        info_selectors = [
            '.my_info',
            '.char_info',
            '.character_info',
            '.info_cont',
            '.detail_info',
        ]

        for selector in info_selectors:
            try:
                el = await page.query_selector(selector)
                if el:
                    # 해당 요소 내의 링크 찾기
                    inner_links = await el.query_selector_all('a')
                    print(f"\n   '{selector}' 발견 - 내부 링크 {len(inner_links)}개")
                    for link in inner_links[:5]:
                        href = await link.get_attribute('href')
                        text = await link.inner_text()
                        text = text.strip()[:30]
                        if href:
                            print(f"      [{text}] {href}")
            except:
                pass

        # 6. onclick 이벤트가 있는 요소 분석
        print("\n6. onclick 이벤트 요소 분석...")
        onclick_elements = await page.query_selector_all('[onclick]')
        print(f"   onclick 요소 수: {len(onclick_elements)}개")

        for el in onclick_elements[:10]:
            try:
                onclick = await el.get_attribute('onclick')
                text = await el.inner_text()
                text = text.strip()[:30]
                if onclick and ('Storage' in onclick or 'storage' in onclick.lower()):
                    print(f"      [{text}] onclick: {onclick[:100]}")
            except:
                pass

        # 7. JavaScript에서 URL 생성 확인
        print("\n7. 페이지 내 스크립트 분석...")
        scripts = await page.query_selector_all('script')
        storage_scripts = []
        for script in scripts:
            try:
                content = await script.inner_html()
                if 'Storage' in content or 'storage' in content.lower():
                    # 관련 부분만 추출
                    lines = content.split('\n')
                    for line in lines:
                        if 'Storage' in line or 'storage' in line.lower():
                            storage_scripts.append(line.strip()[:150])
            except:
                pass

        if storage_scripts:
            print(f"   Storage 관련 스크립트 라인:")
            for line in storage_scripts[:10]:
                print(f"      {line}")

        # 8. 브라우저에서 수동 확인용 대기
        print("\n" + "="*70)
        print("브라우저에서 수동으로 확인하세요.")
        print("창고 탭/링크가 어디 있는지 확인해주세요.")
        print("="*70)
        print("\n30초 대기 중...")
        await asyncio.sleep(30)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_storage_page_v2())
