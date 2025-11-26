"""
Crawler services for web scraping (Story 2.3-2.6)

이 모듈은 메이플스토리 공식 웹사이트에서 인벤토리, 창고, 메소 등의
데이터를 크롤링하는 서비스를 제공합니다.
"""
import logging
import asyncio
import random
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from bs4 import BeautifulSoup
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


class CrawlerService:
    """
    웹 크롤링 서비스 (Story 2.3)

    Playwright를 사용하여 메이플스토리 공식 웹사이트에서
    캐릭터 정보를 크롤링합니다.
    """

    def __init__(self):
        """Initialize crawler service"""
        self.user_agent = "MapleStorage/1.0 (Educational Purpose)"
        self.request_delay = 2  # 요청 간격 (초) for rate limiting

    async def fetch_character_info_url(self, character_name: str) -> str:
        """
        랭킹 페이지에서 캐릭터 정보 URL (p 파라미터 포함) 가져오기

        p 파라미터는 만료 시간이 있으므로 크롤링 전마다 새로 얻어와야 함.
        레거시 mapleApi.py의 extract_character_details 로직 기반.

        Args:
            character_name: 캐릭터 이름

        Returns:
            캐릭터 정보 URL (예: https://maplestory.nexon.com/Common/Character/Detail/{name}?p={token})

        Raises:
            CrawlingError: 크롤링 실패 시
        """
        from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
        import urllib.parse

        encoded_name = urllib.parse.quote(character_name)

        # 본섭 랭킹 URL (레거시: N23Ranking)
        ranking_urls = [
            # 본섭
            f"https://maplestory.nexon.com/N23Ranking/World/Total?c={encoded_name}&w=0",
            # 리부트
            f"https://maplestory.nexon.com/N23Ranking/World/Total?c={encoded_name}&w=254",
        ]

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-setuid-sandbox',
                          '--disable-dev-shm-usage']
                )

                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )

                page = await context.new_page()

                try:
                    for ranking_url in ranking_urls:
                        logger.info(
                            f'Fetching character_info_url from: {ranking_url}')

                        response = await page.goto(ranking_url, wait_until='domcontentloaded', timeout=30000)
                        # await asyncio.sleep(2)

                        html_content = await page.content()

                        # "랭킹정보가 없습니다" 체크 (레거시 로직)
                        if '랭킹정보가 없습니다' in html_content:
                            logger.info(
                                f'No ranking info found at {ranking_url}, trying next...')
                            continue

                        # 레거시 셀렉터: div.rank_table_wrap > table > tbody > tr > td.left > dl > dt > a
                        character_links = await page.query_selector_all(
                            'div.rank_table_wrap > table > tbody > tr > td.left > dl > dt > a'
                        )

                        # 캐릭터 이름으로 매칭 (대소문자 무시)
                        for link in character_links:
                            link_text = await link.inner_text()
                            if link_text.strip().lower() == character_name.lower():
                                href = await link.get_attribute('href')
                                if href:
                                    # 절대 URL로 변환
                                    if href.startswith('/'):
                                        character_info_url = f"https://maplestory.nexon.com{href}"
                                    else:
                                        character_info_url = href

                                    logger.info(
                                        f'Found character_info_url: {character_info_url}')
                                    return character_info_url

                    # 모든 URL에서 찾지 못함
                    raise CrawlingError(f'캐릭터 링크를 찾을 수 없습니다: {character_name}')

                except PlaywrightTimeoutError:
                    raise CrawlingError(f'랭킹 페이지 로드 타임아웃: {character_name}')

                finally:
                    await browser.close()

        except PlaywrightTimeoutError as e:
            raise CrawlingError(f'Playwright timeout: {str(e)}')
        except CrawlingError:
            raise
        except Exception as e:
            logger.error(
                f'Failed to fetch character_info_url: {e}', exc_info=True)
            raise CrawlingError(f'캐릭터 정보 URL 조회 실패: {str(e)}')

    async def crawl_inventory(self, character_info_url: str, character_name: str) -> Dict[str, Any]:
        """
        인벤토리 크롤링 (AC 2.3.1 - 2.3.7)

        Args:
            character_info_url: 캐릭터 정보 페이지 URL
            character_name: 캐릭터 이름

        Returns:
            Dict containing inventory items

        Raises:
            CrawlingError: 크롤링 실패 시
        """
        logger.info(f'Starting inventory crawl for {character_name}')

        try:
            # AC 2.3.1: Playwright로 메이플 공식 사이트 접속
            html_content = await self._fetch_inventory_page(character_info_url, character_name)

            # AC 2.3.2: 인벤토리 탭으로 이동 후 모든 슬롯 파싱
            items = InventoryParser.parse_inventory(html_content)

            logger.info(
                f'Successfully crawled {len(items)} items for {character_name}')
            return {
                'character_name': character_name,
                'items': items,
                'crawled_at': datetime.now().isoformat()
            }

        except Exception as e:
            # AC 2.3.7: 실패 시 구체적 에러 메시지 로깅
            logger.error(
                f'Inventory crawling failed for {character_name}: {str(e)}')
            raise CrawlingError(f'인벤토리 크롤링 실패: {str(e)}')

    async def _fetch_inventory_page(self, character_info_url: str, character_name: str) -> str:
        """
        인벤토리 페이지 HTML 가져오기 (Playwright 사용)

        Args:
            character_info_url: 캐릭터 정보 페이지 URL (예: https://maplestory.nexon.com/MyMaple/Character/Detail/{name}?p={id})
            character_name: 캐릭터 이름

        Returns:
            HTML content as string

        Raises:
            CrawlingError: 크롤링 실패 시
            TimeoutError: 페이지 로드 타임아웃 시
        """
        from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
        import asyncio
        import random

        # Rate limiting: 요청 간격 랜덤 딜레이 (2-5초)
        delay = self.request_delay + random.uniform(0, 3)
        logger.info(f'Applying rate limiting: {delay:.2f}s delay')
        await asyncio.sleep(delay)

        # 인벤토리 URL 생성 (SubPage 로직 기반)
        inventory_url = self._build_inventory_url(character_info_url)
        logger.info(f'Inventory URL: {inventory_url}')

        try:
            async with async_playwright() as p:
                # AC 2.3.1: Playwright 브라우저 초기화 (headless 모드)
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',  # Docker 환경 대응
                    ]
                )

                context = await browser.new_context(
                    user_agent=self.user_agent,
                    viewport={'width': 1920, 'height': 1080}
                )

                page = await context.new_page()

                # Timeout 설정: 페이지 로드 30초
                try:
                    logger.info(
                        f'Navigating to inventory page for {character_name}')
                    response = await page.goto(
                        inventory_url,
                        wait_until='domcontentloaded',  # DOM 로드 완료 대기
                        timeout=30000  # 30초
                    )

                    if not response or not response.ok:
                        raise CrawlingError(
                            f'페이지 로드 실패: HTTP {response.status if response else "N/A"}')

                    # 페이지 내용 로드 대기 (동적 콘텐츠 대응)
                    await page.wait_for_selector('.inven_list', timeout=10000)

                    # HTML 콘텐츠 가져오기
                    html = await page.content()

                    logger.info(
                        f'Successfully fetched inventory HTML for {character_name} ({len(html)} bytes)')

                except PlaywrightTimeoutError as e:
                    logger.error(
                        f'Timeout while loading inventory page for {character_name}: {e}')
                    raise CrawlingError(
                        f'페이지 로드 타임아웃 (30초 초과): {character_name}')

                finally:
                    await browser.close()

                return html

        except PlaywrightTimeoutError as e:
            raise CrawlingError(f'Playwright timeout: {str(e)}')
        except Exception as e:
            logger.error(
                f'Unexpected error fetching inventory page: {e}', exc_info=True)
            raise CrawlingError(f'인벤토리 페이지 로드 실패: {str(e)}')

    def _build_inventory_url(self, character_info_url: str) -> str:
        """
        캐릭터 정보 URL에서 인벤토리 URL 생성 (SubPage 로직 기반)

        Args:
            character_info_url: 캐릭터 정보 URL
                예: https://maplestory.nexon.com/MyMaple/Character/Detail/test123?p=1234

        Returns:
            인벤토리 URL
                예: https://maplestory.nexon.com/MyMaple/Character/Detail/test123/Inventory?p=1234
        """
        question_mark_index = character_info_url.find('?')

        if question_mark_index != -1:
            url_before = character_info_url[:question_mark_index]
            url_after = character_info_url[question_mark_index:]
            return f'{url_before}/Inventory{url_after}'
        else:
            return f'{character_info_url}/Inventory'

    async def crawl_storage(self, character_info_url: str, character_name: str) -> Dict[str, Any]:
        """
        창고 크롤링 (AC 2.4.1 - 2.4.7, AC 2.5.1 - 2.5.6 메소 포함)

        Args:
            character_info_url: 캐릭터 정보 페이지 URL (사용 안됨, 새로 가져옴)
            character_name: 캐릭터 이름

        Returns:
            Dict containing storage items and meso:
            {
                'character_name': str,
                'items': List[dict],
                'meso': int or None,
                'crawled_at': str
            }

        Raises:
            CrawlingError: 크롤링 실패 시
            StorageParsingError: 파싱 실패 시
        """
        logger.info(f'Starting storage crawl for {character_name}')

        try:
            # p 파라미터는 만료되므로 랭킹 페이지에서 새로 얻어옴
            # fresh_character_info_url = await self.fetch_character_info_url(character_name)
            logger.info(f'Fresh character_info_url: {character_info_url}')

            # AC 2.4.1: Playwright로 창고 페이지 접속
            storage_html = await self._fetch_storage_page(character_info_url, character_name)
            # AC 2.4.2 - 2.4.4: 창고 파싱 (공유/개인 구분 없음)
            items = StorageParser.parse_storage(storage_html, 'storage')

            # AC 2.5.1 - 2.5.2: 창고 메소 파싱
            storage_meso = MesoParser.parse_storage_meso(storage_html)
            if storage_meso is not None:
                logger.info(f'Parsed storage meso: {storage_meso:,}')
            else:
                logger.warning(f'Failed to parse storage meso for {character_name}')

            logger.info(
                f'Successfully crawled storage for {character_name}: {len(items)} items, meso={storage_meso}')

            return {
                'character_name': character_name,
                'items': items,
                'meso': storage_meso,
                'crawled_at': datetime.now().isoformat()
            }

        except StorageParsingError as e:
            # AC 2.4.10: 구체적 에러 메시지 로깅
            logger.error(
                f'Storage parsing failed for {character_name}: {str(e)}')
            raise
        except Exception as e:
            # AC 2.4.10: 구체적 에러 메시지 로깅
            logger.error(
                f'Storage crawling failed for {character_name}: {str(e)}')
            raise CrawlingError(f'창고 크롤링 실패: {str(e)}')

    async def _fetch_storage_page(self, character_info_url: str, character_name: str) -> str:
        """
        창고 페이지 HTML 가져오기 (Playwright 사용)

        Args:
            character_info_url: 캐릭터 정보 페이지 URL
            character_name: 캐릭터 이름

        Returns:
            창고 페이지 HTML 문자열

        Raises:
            CrawlingError: 크롤링 실패 시
        """
        from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

        # Rate limiting: 요청 간격 랜덤 딜레이 (2-5초)
        # delay = self.request_delay + random.uniform(0, 3)
        # logger.info(f'Applying rate limiting: {delay:.2f}s delay')
        # await asyncio.sleep(delay)

        # 창고 URL 생성 (SubPage 로직 기반)
        storage_url = self._build_storage_url(character_info_url)
        logger.info(f'Storage URL: {storage_url}')

        try:
            async with async_playwright() as p:
                # AC 2.4.1: Playwright 브라우저 초기화 (headless 모드)
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',  # Docker 환경 대응
                    ]
                )

                context = await browser.new_context(
                    user_agent=self.user_agent,
                    viewport={'width': 1920, 'height': 1080}
                )

                page = await context.new_page()

                try:
                    logger.info(
                        f'Navigating to storage page for {character_name}')
                    response = await page.goto(
                        storage_url,
                        wait_until='networkidle',  # 모든 네트워크 요청 완료 대기
                        timeout=30000  # 30초
                    )

                    if not response or not response.ok:
                        raise CrawlingError(
                            f'페이지 로드 실패: HTTP {response.status if response else "N/A"}')

                    # 창고 컨텐츠 로드 대기 - 레거시: inven_item_img 클래스 사용
                    # 여러 selector 시도
                    selectors_to_try = [
                        '.inven_item_img',
                        '.inven_list',
                        '.my_info',
                        'li',  # 최소한의 fallback
                    ]

                    selector_found = False
                    for selector in selectors_to_try:
                        try:
                            await page.wait_for_selector(selector, timeout=5000)
                            logger.info(f'Found selector: {selector}')
                            selector_found = True
                            break
                        except:
                            continue

                    if not selector_found:
                        logger.warning(
                            'No storage content selector found, proceeding with page content')

                    # 추가 대기 (동적 컨텐츠 로드)
                    # await asyncio.sleep(2)

                    # 창고 HTML 추출
                    storage_html = await page.content()
                    logger.info(
                        f'Fetched storage HTML ({len(storage_html)} bytes)')

                except PlaywrightTimeoutError as e:
                    logger.error(
                        f'Timeout while loading storage page for {character_name}: {e}')
                    raise CrawlingError(
                        f'페이지 로드 타임아웃 (30초 초과): {character_name}')

                finally:
                    await browser.close()

                return storage_html

        except PlaywrightTimeoutError as e:
            raise CrawlingError(f'Playwright timeout: {str(e)}')
        except Exception as e:
            logger.error(
                f'Unexpected error fetching storage page: {e}', exc_info=True)
            raise CrawlingError(f'창고 페이지 로드 실패: {str(e)}')

    def _build_storage_url(self, character_info_url: str) -> str:
        """
        캐릭터 정보 URL에서 창고 URL 생성

        Args:
            character_info_url: 캐릭터 정보 URL
                예: https://maplestory.nexon.com/MyMaple/Character/Detail/test123?p=1234

        Returns:
            창고 URL
                예: https://maplestory.nexon.com/MyMaple/Character/Detail/test123/Storage?p=1234
        """
        question_mark_index = character_info_url.find('?')

        if question_mark_index != -1:
            url_before = character_info_url[:question_mark_index]
            url_after = character_info_url[question_mark_index:]
            return f'{url_before}/Storage{url_after}'
        else:
            return f'{character_info_url}/Storage'

    async def crawl_character_meso(self, character_info_url: str, character_name: str) -> Dict[str, Any]:
        """
        캐릭터 보유 메소 크롤링 (AC 2.5.1 - 2.5.6)

        기본정보 페이지에서 캐릭터가 보유한 메소를 추출합니다.

        Args:
            character_info_url: 캐릭터 정보 페이지 URL
            character_name: 캐릭터 이름

        Returns:
            Dict containing character meso:
            {
                'character_name': str,
                'meso': int or None,
                'crawled_at': str
            }

        Raises:
            CrawlingError: 크롤링 실패 시
        """
        from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

        logger.info(f'Starting character meso crawl for {character_name}')

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                    ]
                )

                context = await browser.new_context(
                    user_agent=self.user_agent,
                    viewport={'width': 1920, 'height': 1080}
                )

                page = await context.new_page()

                try:
                    logger.info(f'Navigating to character info page: {character_info_url}')
                    response = await page.goto(
                        character_info_url,
                        wait_until='networkidle',
                        timeout=30000
                    )

                    if not response or not response.ok:
                        raise CrawlingError(
                            f'페이지 로드 실패: HTTP {response.status if response else "N/A"}')

                    # 기본정보 테이블 로드 대기
                    try:
                        await page.wait_for_selector('table', timeout=5000)
                    except:
                        logger.warning('Table selector not found, proceeding anyway')

                    html_content = await page.content()

                    # AC 2.5.1-2.5.2: 메소 파싱
                    character_meso = MesoParser.parse_character_meso(html_content)

                    if character_meso is not None:
                        logger.info(f'Parsed character meso: {character_meso:,}')
                    else:
                        # AC 2.5.6: 파싱 실패 시 로깅
                        logger.warning(f'Failed to parse character meso for {character_name}')

                    return {
                        'character_name': character_name,
                        'meso': character_meso,
                        'crawled_at': datetime.now().isoformat()
                    }

                except PlaywrightTimeoutError as e:
                    logger.error(f'Timeout while loading character info page: {e}')
                    raise CrawlingError(f'페이지 로드 타임아웃: {character_name}')

                finally:
                    await browser.close()

        except PlaywrightTimeoutError as e:
            raise CrawlingError(f'Playwright timeout: {str(e)}')
        except Exception as e:
            logger.error(f'Character meso crawling failed: {e}', exc_info=True)
            raise CrawlingError(f'캐릭터 메소 크롤링 실패: {str(e)}')


class InventoryParser:
    """
    인벤토리 HTML 파싱 클래스 (AC 2.3.2 - 2.3.5)

    레거시 크롤링 로직 기반으로 실제 메이플스토리 웹사이트 HTML을 파싱합니다.
    """

    @staticmethod
    def parse_inventory(html_content: str) -> List[Dict[str, Any]]:
        """
        인벤토리 HTML 파싱 (레거시 parseItem 함수 기반)

        Args:
            html_content: HTML 문자열

        Returns:
            List of item dictionaries

        Raises:
            ParsingError: 파싱 실패 시
        """
        import re

        try:
            soup = BeautifulSoup(html_content, 'lxml')
            items = []

            # AC 2.3.2: 인벤토리 탭 찾기 (레거시: '<div class="inven_list">')
            inven_list_divs = html_content.split('<div class="inven_list">')

            if len(inven_list_divs) < 2:
                logger.warning('No inventory lists found in HTML')
                return []

            # 5개 아이템 타입 순회 (장비, 소비, 기타, 설치, 캐시)
            # 레거시: for itemType in range(1, 6)
            item_types = ['equips', 'consumables',
                          'miscs', 'installables', 'cashes']

            for item_type_idx in range(1, min(6, len(inven_list_divs))):
                tab_html = inven_list_divs[item_type_idx]
                item_type = item_types[item_type_idx - 1]

                # AC 2.3.3: 아이템 이미지 div로 분할
                item_divs = tab_html.split('<div class="inven_item_img">')

                for item_div in item_divs:
                    if len(item_div) < 200 or "없습니다." in item_div:
                        continue

                    try:
                        item_data = InventoryParser._parse_single_item(
                            item_div, item_type, len(items)
                        )
                        if item_data:
                            items.append(item_data)

                    except Exception as e:
                        logger.warning(
                            f'Failed to parse item in {item_type}: {e}')
                        continue

            logger.info(
                f'Successfully parsed {len(items)} items from inventory')
            return items

        except Exception as e:
            logger.error(f'Inventory parsing failed: {e}', exc_info=True)
            raise ParsingError(f'인벤토리 파싱 실패: {str(e)}')

    @staticmethod
    def _parse_single_item(item_html: str, item_type: str, slot_position: int) -> Optional[Dict[str, Any]]:
        """
        단일 아이템 HTML 파싱 (BeautifulSoup 사용)

        Args:
            item_html: 아이템 HTML 문자열
            item_type: 아이템 타입 (equips, consumables, etc.)
            slot_position: 슬롯 위치

        Returns:
            Item data dictionary or None
        """
        import re

        try:
            # BeautifulSoup으로 안전한 파싱
            soup = BeautifulSoup(item_html, 'lxml')

            # AC 2.3.3: 아이템 정보 추출

            # 아이템 아이콘 URL (inven_item_img 영역의 img 태그)
            img_tag = soup.select_one('.inven_item_img img')
            if not img_tag:
                img_tag = soup.find('img')  # fallback
            image_url = img_tag.get('src', '') if img_tag else ''

            # 아이템 이름 및 상세 URL (inven_item_memo_title 영역의 h1 > a 태그)
            memo_title_tag = soup.select_one('.inven_item_memo_title h1 a')
            if not memo_title_tag:
                memo_title_tag = soup.find('a')  # fallback

            detail_url = memo_title_tag.get(
                'href', '') if memo_title_tag else ''

            # 아이템 이름 및 수량 파싱
            text_content = memo_title_tag.get_text(
                strip=True) if memo_title_tag else ''

            # &nbsp; 및 일반 공백 정규화
            text_content = text_content.replace(
                '\xa0', ' ').replace('&nbsp;', ' ')

            # 수량 파싱: "아이템명 (100개)" 형식
            quantity = 1
            quantity_match = re.search(r'\((\d+)개\)', text_content)
            if quantity_match:
                quantity = int(quantity_match.group(1))
                # 아이템 이름에서 수량 부분 제거
                item_name = re.sub(r'\s*\(\d+개\)', '', text_content).strip()
            else:
                item_name = text_content.strip()

            # &#39; 처리 (작은따옴표)
            item_name = item_name.replace("&#39;", "'")

            # 스타포스 강화 수치
            star_force_count = None
            em_tag = soup.find('em')
            if em_tag and '성 강화' in em_tag.get_text():
                star_force_match = re.search(r'(\d+)성 강화', em_tag.get_text())
                if star_force_match:
                    star_force_count = int(star_force_match.group(1))

            # 주문서 강화 수치 (+7 등)
            spell_trace_count = None
            spell_trace_match = re.search(r'\+(\d+)', text_content)
            if spell_trace_match:
                spell_trace_count = int(spell_trace_match.group(1))

            # 희귀도 (rarity)
            rarity = None
            rarity_div = soup.find('div', class_='item_memo_sel')
            if rarity_div:
                rarity = rarity_div.get_text(strip=True)

            # item_options 구성
            item_options = {}
            if star_force_count:
                item_options['star_force'] = star_force_count
            if spell_trace_count:
                item_options['spell_trace'] = spell_trace_count
            if rarity:
                item_options['rarity'] = rarity

            # 아이콘 URL 정규화
            if image_url.startswith('//'):
                image_url = f'https:{image_url}'
            elif not image_url.startswith('http'):
                image_url = f'https://maplestory.nexon.com{image_url}' if image_url else ''

            # 상세 URL 정규화
            if detail_url and detail_url.startswith('/'):
                detail_url = f'https://maplestory.nexon.com{detail_url}'

            # AC 2.6.1: 만료 날짜 추출 (기간제 아이템)
            expiry_date = ExpiryDateParser.parse_expiry_date(item_html)

            return {
                'item_name': item_name,
                'item_icon': image_url,
                'quantity': quantity,
                'item_options': item_options if item_options else None,
                'slot_position': slot_position,
                'expiry_date': expiry_date,  # AC 2.6.1-2.6.3: 만료 날짜 (없으면 None)
                'item_type': item_type,
                'detail_url': detail_url
            }

        except Exception as e:
            logger.warning(f'Failed to parse single item: {e}', exc_info=True)
            return None


class StorageParser:
    """
    창고 HTML 파싱 클래스 (AC 2.4.2 - 2.4.5)

    메이플스토리 웹사이트의 창고 페이지 HTML을 파싱합니다.
    """

    @staticmethod
    def parse_storage(html_content: str, storage_type: str) -> List[Dict[str, Any]]:
        """
        창고 HTML 파싱

        레거시 mapleApi.py get_storage_list 방식으로 파싱

        Args:
            html_content: HTML 문자열
            storage_type: 창고 유형 ('shared' 또는 'personal')

        Returns:
            List of storage item dictionaries

        Raises:
            StorageParsingError: 파싱 실패 시
        """
        try:
            # 레거시 방식으로 직접 파싱 (가장 신뢰성 있음)
            items = StorageParser._parse_storage_legacy(
                html_content, storage_type)
            return items

        except Exception as e:
            logger.error(
                f'Storage parsing failed for {storage_type}: {e}', exc_info=True)
            raise StorageParsingError(f'창고 파싱 실패 ({storage_type}): {str(e)}')

    @staticmethod
    def _parse_storage_legacy(html_content: str, storage_type: str) -> List[Dict[str, Any]]:
        """
        레거시 방식의 창고 HTML 파싱 (mapleApi.py get_storage_list 기반)

        레거시 코드 참조: references/msstorage_legacy/myapp/api/mapleApi.py

        Args:
            html_content: HTML 문자열
            storage_type: 창고 유형

        Returns:
            List of storage item dictionaries
        """
        import re

        items = []

        try:
            # 레거시 방식: <li> 태그를 regex로 찾아서 inven_item_img 포함 여부 확인
            pattern = r'<li>[\s\S]*?<\/li>'
            matches = re.findall(pattern, html_content)

            logger.info(f'Found {len(matches)} <li> elements in storage HTML')

            for match in matches:
                # inven_item_img 클래스가 없으면 스킵
                if 'inven_item_img' not in match:
                    continue

                try:
                    # 이미지 URL 추출
                    image_url = ''
                    if 'src="' in match:
                        image_url = match.split('src="')[1].split('"')[0]

                    # 상세 URL 추출
                    detail_url = ''
                    if 'href="' in match:
                        detail_url = match.split('href="')[1].split('"')[0]

                    # 아이템 이름 추출 (레거시 로직 개선)
                    name = None
                    if "font color" in match:
                        # regex로 font color 태그 내 텍스트 추출
                        font_match = re.search(
                            r'<font color[^>]*>([^<]+)</font>', match)
                        if font_match:
                            name = font_match.group(1).strip()

                    if not name:
                        if "&nbsp;" in match:
                            name = match.split("&nbsp;")[0].split(
                                ">")[-1].replace("\r\n", "").strip()
                        else:
                            name = match.split(
                                "</a></h1>")[0].split("<br>")[0].split(">")[-1].replace("\r\n", "").strip()

                    if name and "&#39;" in name:
                        name = name.replace("&#39;", "'")

                    if not name or name == ' ':
                        continue

                    # 수량 추출
                    count = 1
                    if '개)' in match:
                        try:
                            count_str = match.split('개)')[0].split(">(")[1]
                            if "일)" not in count_str and '유닛)' not in count_str and '분)' not in count_str and '왼쪽용)' not in count_str:
                                count = int(count_str)
                        except:
                            count = 1

                    # 스타포스 추출
                    star_force_count = None
                    if "성 강화]<br />" in match:
                        try:
                            star_force_count = int(
                                match.split("[")[1].split("성 강화]")[0])
                        except:
                            pass

                    # URL 정규화
                    if image_url.startswith('//'):
                        image_url = f'https:{image_url}'
                    elif image_url and not image_url.startswith('http'):
                        image_url = f'https://maplestory.nexon.com{image_url}'

                    if detail_url and detail_url.startswith('/'):
                        detail_url = f'https://maplestory.nexon.com{detail_url}'

                    # item_options 구성
                    item_options = {}
                    if star_force_count:
                        item_options['star_force'] = star_force_count

                    # 주문서 강화 추출
                    spell_trace_match = re.search(r'\+(\d+)', name)
                    if spell_trace_match:
                        item_options['spell_trace'] = int(
                            spell_trace_match.group(1))

                    # AC 2.6.1: 만료 날짜 추출 (기간제 아이템)
                    expiry_date = ExpiryDateParser.parse_expiry_date(match)

                    items.append({
                        'storage_type': storage_type,
                        'item_name': name,
                        'item_icon': image_url,
                        'quantity': count,
                        'slot_position': len(items),
                        'item_options': item_options if item_options else None,
                        'expiry_date': expiry_date,  # AC 2.6.1-2.6.3: 만료 날짜 (없으면 None)
                        'detail_url': detail_url
                    })

                except Exception as e:
                    logger.warning(
                        f'Failed to parse storage item from li: {e}')
                    continue

            logger.info(
                f'Parsed {len(items)} {storage_type} storage items using legacy method')
            return items

        except Exception as e:
            logger.error(f'Legacy storage parsing failed: {e}', exc_info=True)
            return []

    @staticmethod
    def _parse_single_storage_item(slot_element, storage_type: str, slot_position: int) -> Optional[Dict[str, Any]]:
        """
        단일 창고 슬롯 엘리먼트 파싱

        Args:
            slot_element: BeautifulSoup 엘리먼트
            storage_type: 창고 유형
            slot_position: 슬롯 위치

        Returns:
            Item data dictionary or None
        """
        import re

        try:
            # 아이템 이미지
            img_tag = slot_element.find('img')
            if not img_tag:
                return None  # 빈 슬롯

            image_url = img_tag.get('src', '')

            # 아이템 이름
            name_tag = slot_element.find('span', class_='item_name')
            if not name_tag:
                name_tag = slot_element.find('a')

            item_name = name_tag.get_text(strip=True) if name_tag else ''

            if not item_name:
                return None  # 빈 슬롯

            # 수량 파싱
            quantity = 1
            quantity_tag = slot_element.find('span', class_='item_count')
            if quantity_tag:
                quantity_text = quantity_tag.get_text(strip=True)
                quantity_match = re.search(r'(\d+)', quantity_text)
                if quantity_match:
                    quantity = int(quantity_match.group(1))
            else:
                # 아이템 이름에서 수량 파싱: "아이템명 (100개)"
                quantity_match = re.search(r'\((\d+)개\)', item_name)
                if quantity_match:
                    quantity = int(quantity_match.group(1))
                    item_name = re.sub(r'\s*\(\d+개\)', '', item_name).strip()

            # 아이콘 URL 정규화
            if image_url.startswith('//'):
                image_url = f'https:{image_url}'
            elif not image_url.startswith('http'):
                image_url = f'https://maplestory.nexon.com{image_url}' if image_url else ''

            # item_options 추출 (강화 수치 등)
            item_options = {}
            em_tag = slot_element.find('em')
            if em_tag and '성 강화' in em_tag.get_text():
                star_match = re.search(r'(\d+)성 강화', em_tag.get_text())
                if star_match:
                    item_options['star_force'] = int(star_match.group(1))

            # AC 2.6.1: 만료 날짜 추출
            expiry_date = ExpiryDateParser.parse_expiry_date(str(slot_element))

            return {
                'storage_type': storage_type,
                'item_name': item_name,
                'item_icon': image_url,
                'quantity': quantity,
                'slot_position': slot_position,
                'item_options': item_options if item_options else None,
                'expiry_date': expiry_date  # AC 2.6.1-2.6.3
            }

        except Exception as e:
            logger.warning(
                f'Failed to parse single storage item: {e}', exc_info=True)
            return None

    @staticmethod
    def _parse_single_item_from_html(item_html: str, storage_type: str, slot_position: int) -> Optional[Dict[str, Any]]:
        """
        단일 아이템 HTML 문자열 파싱 (레거시 방식)

        Args:
            item_html: 아이템 HTML 문자열
            storage_type: 창고 유형
            slot_position: 슬롯 위치

        Returns:
            Item data dictionary or None
        """
        import re

        try:
            soup = BeautifulSoup(item_html, 'lxml')

            # 아이템 이미지
            img_tag = soup.find('img')
            if not img_tag:
                return None

            image_url = img_tag.get('src', '')

            # 아이템 이름
            name_tag = soup.find('a')
            if not name_tag:
                name_tag = soup.find('span', class_='item_name')

            text_content = name_tag.get_text(strip=True) if name_tag else ''

            if not text_content:
                return None

            # &nbsp; 및 일반 공백 정규화
            text_content = text_content.replace(
                '\xa0', ' ').replace('&nbsp;', ' ')

            # 수량 파싱
            quantity = 1
            quantity_match = re.search(r'\((\d+)개\)', text_content)
            if quantity_match:
                quantity = int(quantity_match.group(1))
                item_name = re.sub(r'\s*\(\d+개\)', '', text_content).strip()
            else:
                item_name = text_content.strip()

            # &#39; 처리 (작은따옴표)
            item_name = item_name.replace("&#39;", "'")

            # 아이콘 URL 정규화
            if image_url.startswith('//'):
                image_url = f'https:{image_url}'
            elif not image_url.startswith('http'):
                image_url = f'https://maplestory.nexon.com{image_url}' if image_url else ''

            # item_options 추출
            item_options = {}
            em_tag = soup.find('em')
            if em_tag and '성 강화' in em_tag.get_text():
                star_match = re.search(r'(\d+)성 강화', em_tag.get_text())
                if star_match:
                    item_options['star_force'] = int(star_match.group(1))

            spell_trace_match = re.search(r'\+(\d+)', text_content)
            if spell_trace_match:
                item_options['spell_trace'] = int(spell_trace_match.group(1))

            # AC 2.6.1: 만료 날짜 추출
            expiry_date = ExpiryDateParser.parse_expiry_date(item_html)

            return {
                'storage_type': storage_type,
                'item_name': item_name,
                'item_icon': image_url,
                'quantity': quantity,
                'slot_position': slot_position,
                'item_options': item_options if item_options else None,
                'expiry_date': expiry_date  # AC 2.6.1-2.6.3
            }

        except Exception as e:
            logger.warning(
                f'Failed to parse item from HTML: {e}', exc_info=True)
            return None


class CrawlingError(Exception):
    """크롤링 중 발생하는 에러"""
    pass


class ParsingError(Exception):
    """HTML 파싱 중 발생하는 에러"""
    pass


class StorageParsingError(Exception):
    """창고 HTML 파싱 중 발생하는 에러 (Story 2.4)"""
    pass


class MesoParsingError(Exception):
    """메소 파싱 중 발생하는 에러 (Story 2.5)"""
    pass


class ExpiryDateParsingError(Exception):
    """만료 날짜 파싱 중 발생하는 에러 (Story 2.6)"""
    pass


class ExpiryDateParser:
    """
    기간제 아이템 만료 날짜 파싱 클래스 (AC 2.6.1 - 2.6.5)

    메이플스토리 웹사이트에서 기간제 아이템의 만료 날짜를 파싱합니다.
    """

    # 한국어 날짜 형식 패턴들
    # "2025년 12월 31일 23시 59분" 형식
    KOREAN_DATETIME_PATTERN = r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일\s*(\d{1,2})시\s*(\d{1,2})분'
    # "2025년 12월 31일" 형식 (시간 없음)
    KOREAN_DATE_PATTERN = r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일'
    # "2025.12.31" 또는 "2025-12-31" 형식
    NUMERIC_DATE_PATTERN = r'(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})'
    # "2025.12.31 23:59" 형식
    NUMERIC_DATETIME_PATTERN = r'(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})\s+(\d{1,2}):(\d{1,2})'

    @staticmethod
    def parse_expiry_date(item_html: str) -> Optional[datetime]:
        """
        아이템 HTML에서 만료 날짜 추출 (AC 2.6.1, 2.6.2)

        Args:
            item_html: 아이템 HTML 문자열

        Returns:
            datetime 객체 (ISO 8601 호환) 또는 None (만료일 없음)
        """
        import re
        from datetime import datetime
        import pytz

        if not item_html:
            return None

        # KST 타임존
        kst = pytz.timezone('Asia/Seoul')

        # 1. 한국어 날짜+시간 형식 시도: "2025년 12월 31일 23시 59분"
        match = re.search(ExpiryDateParser.KOREAN_DATETIME_PATTERN, item_html)
        if match:
            try:
                year, month, day, hour, minute = map(int, match.groups())
                dt = datetime(year, month, day, hour, minute, 0)
                # KST로 설정 후 반환
                return kst.localize(dt)
            except (ValueError, TypeError) as e:
                logger.warning(f'한국어 날짜+시간 파싱 실패: {match.group()} - {e}')

        # 2. 숫자 날짜+시간 형식 시도: "2025.12.31 23:59"
        match = re.search(ExpiryDateParser.NUMERIC_DATETIME_PATTERN, item_html)
        if match:
            try:
                year, month, day, hour, minute = map(int, match.groups())
                dt = datetime(year, month, day, hour, minute, 0)
                return kst.localize(dt)
            except (ValueError, TypeError) as e:
                logger.warning(f'숫자 날짜+시간 파싱 실패: {match.group()} - {e}')

        # 3. 한국어 날짜만 형식 시도: "2025년 12월 31일" (시간은 23:59:59로 설정)
        match = re.search(ExpiryDateParser.KOREAN_DATE_PATTERN, item_html)
        if match:
            try:
                year, month, day = map(int, match.groups())
                dt = datetime(year, month, day, 23, 59, 59)
                return kst.localize(dt)
            except (ValueError, TypeError) as e:
                logger.warning(f'한국어 날짜 파싱 실패: {match.group()} - {e}')

        # 4. 숫자 날짜만 형식 시도: "2025.12.31" (시간은 23:59:59로 설정)
        match = re.search(ExpiryDateParser.NUMERIC_DATE_PATTERN, item_html)
        if match:
            try:
                year, month, day = map(int, match.groups())
                dt = datetime(year, month, day, 23, 59, 59)
                return kst.localize(dt)
            except (ValueError, TypeError) as e:
                logger.warning(f'숫자 날짜 파싱 실패: {match.group()} - {e}')

        # 만료 날짜를 찾지 못함 (AC 2.6.3: null 반환)
        return None

    @staticmethod
    def get_alert_flags(expiry_date: Optional[datetime]) -> dict:
        """
        만료 날짜 기준 알림 플래그 반환 (AC 2.6.5)

        Args:
            expiry_date: 만료 날짜 (datetime)

        Returns:
            dict: {
                'needs_d7_alert': bool,  # D-7 (7일 이하 남음)
                'needs_d3_alert': bool,  # D-3 (3일 이하 남음)
                'needs_d1_alert': bool,  # D-1 (1일 이하 남음)
                'days_until_expiry': Optional[int]  # 남은 일수
            }
        """
        from datetime import datetime, timezone

        default_flags = {
            'needs_d7_alert': False,
            'needs_d3_alert': False,
            'needs_d1_alert': False,
            'days_until_expiry': None
        }

        if not expiry_date:
            return default_flags

        # 현재 시간 (UTC)
        now = datetime.now(timezone.utc)

        # expiry_date가 naive datetime이면 UTC로 가정
        if expiry_date.tzinfo is None:
            import pytz
            expiry_date = pytz.UTC.localize(expiry_date)

        # 남은 일수 계산
        delta = expiry_date - now
        days_remaining = delta.days

        return {
            'needs_d7_alert': 0 <= days_remaining <= 7,
            'needs_d3_alert': 0 <= days_remaining <= 3,
            'needs_d1_alert': 0 <= days_remaining <= 1,
            'days_until_expiry': days_remaining
        }

    @staticmethod
    def calculate_days_until_expiry(expiry_date: Optional[datetime]) -> Optional[int]:
        """
        만료까지 남은 일수 계산 (AC 2.6.4)

        Args:
            expiry_date: 만료 날짜 (datetime)

        Returns:
            남은 일수 (int) 또는 None
        """
        if not expiry_date:
            return None

        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)

        # expiry_date가 naive datetime이면 UTC로 가정
        if expiry_date.tzinfo is None:
            import pytz
            expiry_date = pytz.UTC.localize(expiry_date)

        delta = expiry_date - now
        return delta.days


class MesoParser:
    """
    메소 HTML 파싱 클래스 (AC 2.5.1 - 2.5.6)

    메이플스토리 웹사이트에서 메소 보유량을 파싱합니다.
    - 캐릭터 보유 메소: 기본정보 페이지
    - 창고 메소: 창고 페이지
    """

    # 캐릭터 보유 메소 selector (기본정보 페이지)
    CHARACTER_MESO_SELECTOR = '#container > div.con_wrap > div.contents_wrap > div > div.tab01_con_wrap > table:nth-child(2) > tbody > tr:nth-child(3) > td:nth-child(2) > span'

    # 창고 메소 selector (창고 페이지)
    STORAGE_MESO_SELECTOR = '#container > div.con_wrap > div.contents_wrap > div > div > div > div'

    @staticmethod
    def parse_character_meso(html_content: str) -> Optional[int]:
        """
        캐릭터 보유 메소 파싱 (기본정보 페이지)

        Args:
            html_content: HTML 문자열

        Returns:
            메소 금액 (int) 또는 None (파싱 실패 시)
        """
        import re

        try:
            soup = BeautifulSoup(html_content, 'lxml')

            # CSS selector로 메소 영역 찾기
            meso_element = soup.select_one(MesoParser.CHARACTER_MESO_SELECTOR)

            if meso_element:
                meso_text = meso_element.get_text(strip=True)
                return MesoParser._extract_meso_amount(meso_text)

            # fallback: 테이블에서 '메소' 행 찾기
            tables = soup.select('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    for i, cell in enumerate(cells):
                        if '메소' in cell.get_text():
                            # 다음 셀에서 값 추출
                            if i + 1 < len(cells):
                                meso_text = cells[i + 1].get_text(strip=True)
                                return MesoParser._extract_meso_amount(meso_text)
                            # 같은 셀에서 숫자 추출
                            meso_text = cell.get_text(strip=True)
                            amount = MesoParser._extract_meso_amount(meso_text)
                            if amount is not None:
                                return amount

            logger.warning('메소 영역을 찾을 수 없습니다 (캐릭터 기본정보)')
            return None

        except Exception as e:
            logger.error(f'캐릭터 메소 파싱 실패: {e}', exc_info=True)
            return None

    @staticmethod
    def parse_storage_meso(html_content: str) -> Optional[int]:
        """
        창고 메소 파싱 (창고 페이지)

        Args:
            html_content: HTML 문자열

        Returns:
            메소 금액 (int) 또는 None (파싱 실패 시)
        """
        import re

        try:
            soup = BeautifulSoup(html_content, 'lxml')

            # CSS selector로 메소 영역 찾기
            meso_element = soup.select_one(MesoParser.STORAGE_MESO_SELECTOR)

            if meso_element:
                meso_text = meso_element.get_text(strip=True)
                amount = MesoParser._extract_meso_amount(meso_text)
                if amount is not None:
                    return amount

            # fallback: div에서 '메소' 텍스트 찾기
            divs = soup.find_all('div')
            for div in divs:
                text = div.get_text(strip=True)
                if '메소' in text or '골드' in text:
                    amount = MesoParser._extract_meso_amount(text)
                    if amount is not None:
                        return amount

            # fallback: span에서 숫자 패턴 찾기
            for span in soup.find_all('span'):
                text = span.get_text(strip=True)
                amount = MesoParser._extract_meso_amount(text)
                if amount is not None and amount > 0:
                    return amount

            logger.warning('메소 영역을 찾을 수 없습니다 (창고)')
            return None

        except Exception as e:
            logger.error(f'창고 메소 파싱 실패: {e}', exc_info=True)
            return None

    @staticmethod
    def _extract_meso_amount(text: str) -> Optional[int]:
        """
        텍스트에서 메소 금액 추출

        쉼표 제거 후 정수 변환 (AC 2.5.2)
        0 메소도 정상 처리 (AC 2.5.5)

        Args:
            text: 메소 텍스트 (예: "1,234,567,890 메소", "0")

        Returns:
            메소 금액 (int) 또는 None
        """
        import re

        if not text:
            return None

        try:
            # 쉼표 제거
            cleaned = text.replace(',', '').replace(' ', '')

            # 숫자만 추출
            match = re.search(r'(\d+)', cleaned)
            if match:
                amount = int(match.group(1))
                return amount  # 0도 유효한 값

            return None

        except (ValueError, TypeError) as e:
            logger.warning(f'메소 금액 변환 실패: {text} - {e}')
            return None


class ItemDetailParser:
    """
    아이템 상세 페이지 HTML 파싱 클래스

    레거시 parseDetail() 함수 로직 기반으로 구현
    """

    @staticmethod
    def parse_detail_page(html_content: str, item_name: str) -> Dict[str, Any]:
        """
        상세 페이지 HTML 파싱

        Args:
            html_content: HTML 문자열
            item_name: 아이템 이름 (검증용)

        Returns:
            파싱된 상세 정보 딕셔너리
        """
        try:
            html_content = html_content.replace('\r\n', '').strip()
            soup = BeautifulSoup(html_content, 'html.parser')

            # 모든 span 태그에서 데이터 추출
            all_spans = soup.find_all('span')
            span_data = {'name': item_name}

            for span in all_spans:
                key = span.text.strip()

                # 소울옵션 처리
                if '소울옵션' in key:
                    next_div = span.find_next('div')
                    if next_div:
                        span_data[key] = next_div.text
                    continue

                # 장비분류 처리
                if '장비분류' in key:
                    parts = key.split('|')
                    if len(parts) >= 2:
                        span_data['장비분류'] = parts[1].strip()
                    continue

                # 잠재능력 등급 처리
                if '아이템' in key:
                    if '에디셔널' in key:
                        # "에디셔널 아이템 (유니크)" -> "유니크"
                        grade = key.split('(')[1].split(
                            ')')[0] if '(' in key else None
                        span_data['에디셔널 잠재옵션 등급'] = grade
                    else:
                        # "아이템 (레전드리)" -> "레전드리"
                        grade = key.split('(')[1].split(
                            ')')[0] if '(' in key else None
                        span_data['잠재옵션 등급'] = grade

                    key = key.split('(')[0].strip()

                # 착용 가능한 직업 처리
                if '착용 가능한 직업' in key:
                    parts = key.split('|')
                    if len(parts) >= 2:
                        span_data['착용 가능한 직업'] = parts[1].strip()
                    continue

                # 일반 key-value 처리
                next_elem = span.find_next(
                    'div') if 'REQ' not in key else span.find_next('em')
                if next_elem:
                    value = [line.strip()
                             for line in next_elem.stripped_strings]
                    span_data[key] = value

            # 파싱된 데이터를 ItemDetail 필드에 매핑
            return ItemDetailParser._map_to_detail_fields(span_data)

        except Exception as e:
            logger.error(
                f'Failed to parse item detail for {item_name}: {e}', exc_info=True)
            raise ParsingError(f'Item detail parsing failed: {e}')

    @staticmethod
    def _map_to_detail_fields(span_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        파싱된 span_data를 ItemDetail 모델 필드에 매핑

        Args:
            span_data: 파싱된 원시 데이터

        Returns:
            ItemDetail 모델 필드에 맞춘 딕셔너리
        """
        detail = {}

        # 기본 정보
        detail['item_category'] = span_data.get('장비분류')

        # 착용 레벨 추출 (REQ LEV : 200 형식)
        req_lev = span_data.get('REQ LEV')
        if req_lev and isinstance(req_lev, list) and len(req_lev) > 0:
            try:
                detail['required_level'] = int(req_lev[0])
            except (ValueError, IndexError):
                detail['required_level'] = None

        detail['required_job'] = span_data.get('착용 가능한 직업')

        # 스탯 추출
        detail.update(ItemDetailParser._parse_base_stats(span_data))

        # 잠재능력
        detail.update(ItemDetailParser._parse_potential(span_data))

        # 에디셔널 잠재능력
        detail.update(ItemDetailParser._parse_additional_potential(span_data))

        # 소울 옵션
        detail.update(ItemDetailParser._parse_soul_option(span_data))

        return detail

    @staticmethod
    def _parse_base_stats(span_data: Dict[str, Any]) -> Dict[str, int]:
        """장비 기본 스탯 파싱"""
        stats = {}

        # 공격력/마력
        attack_power = span_data.get('공격력')
        if attack_power and isinstance(attack_power, list) and len(attack_power) > 0:
            try:
                stats['attack_power'] = int(attack_power[0].replace('+', ''))
            except (ValueError, IndexError):
                pass

        magic_power = span_data.get('마력')
        if magic_power and isinstance(magic_power, list) and len(magic_power) > 0:
            try:
                stats['magic_power'] = int(magic_power[0].replace('+', ''))
            except (ValueError, IndexError):
                pass

        # 기본 스탯 (STR, DEX, INT, LUK)
        for stat_name, field_name in [('STR', 'str_stat'), ('DEX', 'dex_stat'), ('INT', 'int_stat'), ('LUK', 'luk_stat')]:
            stat_value = span_data.get(stat_name)
            if stat_value and isinstance(stat_value, list) and len(stat_value) > 0:
                try:
                    stats[field_name] = int(stat_value[0].replace('+', ''))
                except (ValueError, IndexError):
                    pass

        # HP/MP
        for stat_name, field_name in [('MaxHP', 'hp_stat'), ('MaxMP', 'mp_stat')]:
            stat_value = span_data.get(stat_name)
            if stat_value and isinstance(stat_value, list) and len(stat_value) > 0:
                try:
                    stats[field_name] = int(stat_value[0].replace('+', ''))
                except (ValueError, IndexError):
                    pass

        # 방어력
        defense = span_data.get('방어력')
        if defense and isinstance(defense, list) and len(defense) > 0:
            try:
                stats['defense'] = int(defense[0].replace('+', ''))
            except (ValueError, IndexError):
                pass

        # 올스탯
        all_stat = span_data.get('올스탯')
        if all_stat and isinstance(all_stat, list) and len(all_stat) > 0:
            try:
                stats['all_stat'] = int(
                    all_stat[0].replace('+', '').replace('%', ''))
            except (ValueError, IndexError):
                pass

        # 보스 공격력 증가
        boss_damage = span_data.get('보스 몬스터 공격 시 데미지')
        if boss_damage and isinstance(boss_damage, list) and len(boss_damage) > 0:
            try:
                stats['boss_damage'] = int(
                    boss_damage[0].replace('+', '').replace('%', ''))
            except (ValueError, IndexError):
                pass

        # 방어율 무시
        ignore_defense = span_data.get('몬스터 방어율 무시')
        if ignore_defense and isinstance(ignore_defense, list) and len(ignore_defense) > 0:
            try:
                stats['ignore_defense'] = int(
                    ignore_defense[0].replace('+', '').replace('%', ''))
            except (ValueError, IndexError):
                pass

        return stats

    @staticmethod
    def _parse_potential(span_data: Dict[str, Any]) -> Dict[str, Any]:
        """잠재능력 파싱"""
        potential = {}

        potential['potential_grade'] = span_data.get('잠재옵션 등급')

        # 잠재능력 옵션 (3줄)
        potential_options = span_data.get('아이템', [])
        if isinstance(potential_options, list):
            for i in range(min(3, len(potential_options))):
                potential[f'potential_option_{i+1}'] = potential_options[i]

        return potential

    @staticmethod
    def _parse_additional_potential(span_data: Dict[str, Any]) -> Dict[str, Any]:
        """에디셔널 잠재능력 파싱"""
        additional = {}

        additional['additional_potential_grade'] = span_data.get(
            '에디셔널 잠재옵션 등급')

        # 에디셔널 잠재능력 옵션 (3줄)
        additional_options = span_data.get('에디셔널 아이템', [])
        if isinstance(additional_options, list):
            for i in range(min(3, len(additional_options))):
                additional[f'additional_potential_option_{i+1}'] = additional_options[i]

        return additional

    @staticmethod
    def _parse_soul_option(span_data: Dict[str, Any]) -> Dict[str, str]:
        """소울 옵션 파싱"""
        soul = {}

        soul_option_text = span_data.get('소울옵션')
        if soul_option_text:
            # "매그너스의 소울 : STR +7%, DEX +7%" 형식
            parts = soul_option_text.split(':')
            if len(parts) >= 2:
                soul['soul_name'] = parts[0].strip()
                soul['soul_option'] = parts[1].strip()
            else:
                soul['soul_option'] = soul_option_text

        return soul


class ItemDetailCrawler:
    """
    아이템 상세 정보 크롤링 클래스

    인벤토리 아이템의 detail_url을 사용하여
    상세 스탯과 옵션을 크롤링합니다.
    """

    def __init__(self):
        self.user_agent = "MapleStorage/1.0 (Educational Purpose)"
        self.request_delay_min = 2.0  # 최소 2초
        self.request_delay_max = 3.0  # 최대 3초
        self.batch_size = 50  # 배치 크기
        self.batch_rest_time = 30  # 배치 간 휴식 (초)

    async def crawl_item_details(
        self,
        inventory_items: list,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Dict[str, Any]:
        """
        여러 아이템의 상세 정보를 배치로 크롤링

        Args:
            inventory_items: Inventory 모델 객체 리스트
            progress_callback: 진행률 콜백 함수 (current, total)

        Returns:
            {
                'success_count': int,
                'failed_items': List[str],
                'total_time': float
            }
        """
        import time
        start_time = time.time()

        total = len(inventory_items)
        success_count = 0
        failed_items = []

        # 배치 단위로 처리
        for batch_idx in range(0, total, self.batch_size):
            batch = inventory_items[batch_idx:batch_idx + self.batch_size]

            for idx, item in enumerate(batch):
                current = batch_idx + idx + 1

                try:
                    # 상세 정보 크롤링
                    detail_data = await self._crawl_single_item(item)

                    if detail_data:
                        # Pydantic 검증
                        from characters.schemas import ItemDetailSchema
                        validated_data = ItemDetailSchema(**detail_data)

                        # DB 저장 (sync_to_async 래핑)
                        from characters.models import ItemDetail

                        @sync_to_async
                        def save_item_detail():
                            ItemDetail.objects.update_or_create(
                                inventory_item=item,
                                defaults=validated_data.model_dump(
                                    exclude_none=True)
                            )
                            # Inventory의 has_detail 플래그 업데이트
                            item.has_detail = True
                            item.save(update_fields=['has_detail'])

                        await save_item_detail()

                        success_count += 1
                        logger.info(
                            f'Item detail crawled: {item.item_name} ({current}/{total})')

                    else:
                        failed_items.append(item.item_name)
                        logger.warning(
                            f'Failed to crawl detail for: {item.item_name}')

                except Exception as e:
                    failed_items.append(item.item_name)
                    logger.error(
                        f'Error crawling {item.item_name}: {e}', exc_info=True)

                # Progress 콜백
                if progress_callback:
                    progress_callback(current, total)

                # Rate limiting (마지막 아이템은 딜레이 생략)
                if current < total:
                    await asyncio.sleep(random.uniform(self.request_delay_min, self.request_delay_max))

            # 배치 간 휴식 (마지막 배치는 생략)
            if batch_idx + self.batch_size < total:
                logger.info(
                    f'Batch rest for {self.batch_rest_time} seconds...')
                await asyncio.sleep(self.batch_rest_time)

        total_time = time.time() - start_time

        return {
            'success_count': success_count,
            'failed_items': failed_items,
            'total_time': total_time
        }

    async def _crawl_single_item(self, inventory_item) -> Optional[Dict[str, Any]]:
        """
        단일 아이템의 상세 정보 크롤링

        Args:
            inventory_item: Inventory 모델 객체

        Returns:
            파싱된 상세 정보 딕셔너리 또는 None (실패 시)
        """
        if not inventory_item.detail_url:
            logger.warning(
                f'No detail_url for item: {inventory_item.item_name}')
            return None

        try:
            # HTML 가져오기
            html_content = await self._fetch_detail_page(inventory_item.detail_url)

            # HTML 파싱
            detail_data = ItemDetailParser.parse_detail_page(
                html_content, inventory_item.item_name)

            return detail_data

        except Exception as e:
            logger.error(
                f'Failed to crawl item detail: {inventory_item.item_name}', exc_info=True)
            return None

    async def _fetch_detail_page(self, detail_url: str) -> str:
        """
        아이템 상세 페이지 HTML 가져오기

        Args:
            detail_url: 아이템 상세 페이지 URL

        Returns:
            HTML 문자열
        """
        from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=['--disable-dev-shm-usage']
                )

                context = await browser.new_context(
                    user_agent=self.user_agent,
                    extra_http_headers={
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                )

                page = await context.new_page()

                # 페이지 로드 (30초 timeout)
                await page.goto(detail_url, timeout=30000, wait_until='domcontentloaded')

                # HTML 가져오기
                html_content = await page.content()

                await browser.close()

                return html_content

        except PlaywrightTimeoutError:
            logger.error(f'Timeout fetching detail page: {detail_url}')
            raise CrawlingError(f'Timeout: {detail_url}')
        except Exception as e:
            logger.error(
                f'Failed to fetch detail page: {detail_url}', exc_info=True)
            raise CrawlingError(f'Failed to fetch: {e}')
