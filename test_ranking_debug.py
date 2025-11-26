"""
랭킹 페이지 디버깅 스크립트
p 파라미터 포함 링크 찾기
"""
import asyncio
import urllib.parse
from playwright.async_api import async_playwright

async def debug_ranking_page():
    character_name = "식사동그놈"
    encoded_name = urllib.parse.quote(character_name)
    ranking_url = f"https://maplestory.nexon.com/Ranking/World/Total?c={encoded_name}"

    print(f"{'='*70}")
    print(f"랭킹 페이지 디버깅: {character_name}")
    print(f"{'='*70}")
    print(f"\nURL: {ranking_url}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,  # 브라우저 표시
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )

        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )

        page = await context.new_page()

        print("\n1. 랭킹 페이지 접속 중...")
        try:
            response = await page.goto(ranking_url, wait_until='networkidle', timeout=30000)
            print(f"   응답 상태: {response.status if response else 'N/A'}")
            print(f"   최종 URL: {page.url}")
        except Exception as e:
            print(f"   접속 실패: {e}")
            await browser.close()
            return

        await asyncio.sleep(3)

        # HTML 저장
        html = await page.content()
        with open('debug_ranking_page.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"\n2. HTML 저장됨: debug_ranking_page.html ({len(html)} bytes)")

        # 모든 링크 분석
        print("\n3. 모든 링크 분석 중...")
        all_links = await page.query_selector_all('a')
        print(f"   총 링크 수: {len(all_links)}개")

        # p 파라미터 포함 링크 찾기
        p_links = []
        character_links = []

        for link in all_links:
            try:
                href = await link.get_attribute('href')
                text = await link.inner_text()
                text = text.strip().replace('\n', ' ')[:50]

                if href:
                    if '?p=' in href or '&p=' in href:
                        p_links.append({'href': href, 'text': text})
                    if 'Character' in href:
                        character_links.append({'href': href, 'text': text})
            except:
                pass

        print(f"\n   Character 관련 링크: {len(character_links)}개")
        for item in character_links[:20]:
            print(f"      [{item['text'][:30]}] {item['href'][:80]}")

        print(f"\n   p 파라미터 포함 링크: {len(p_links)}개")
        for item in p_links[:20]:
            print(f"      [{item['text'][:30]}] {item['href'][:80]}")

        # 테이블 영역 확인
        print("\n4. 랭킹 테이블 영역 분석...")
        table_selectors = [
            '.rank_table',
            '.ranking_table',
            'table',
            '.search_com',
            '.rank_list',
        ]

        for selector in table_selectors:
            try:
                el = await page.query_selector(selector)
                if el:
                    inner_html = await el.inner_html()
                    inner_links = await el.query_selector_all('a')
                    print(f"\n   '{selector}' 발견 - 내부 링크 {len(inner_links)}개")
                    for link in inner_links[:10]:
                        href = await link.get_attribute('href')
                        text = await link.inner_text()
                        text = text.strip()[:30]
                        if href:
                            print(f"      [{text}] {href[:80]}")
            except Exception as e:
                pass

        # 캐릭터명으로 직접 검색
        print(f"\n5. 캐릭터명 '{character_name}' 포함 요소 찾기...")
        try:
            # 텍스트로 검색
            char_elements = await page.query_selector_all(f'text="{character_name}"')
            print(f"   텍스트 매칭: {len(char_elements)}개")

            # 부모 링크 찾기
            for el in char_elements[:5]:
                try:
                    parent = await el.evaluate_handle('el => el.closest("a")')
                    if parent:
                        href = await parent.get_property('href')
                        href_val = await href.json_value()
                        print(f"      부모 링크: {href_val}")
                except:
                    pass
        except Exception as e:
            print(f"   에러: {e}")

        print("\n" + "="*70)
        print("브라우저에서 수동으로 확인하세요.")
        print("="*70)
        print("\n30초 대기 중...")
        await asyncio.sleep(30)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_ranking_page())
