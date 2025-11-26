"""
Test for inventory parsing fix (실제 HTML 구조 기반)
"""
import pytest
from django.test import TestCase
from characters.crawler_services import InventoryParser


class TestInventoryParsingFix(TestCase):
    """실제 메이플스토리 웹사이트 HTML 구조 기반 파싱 테스트"""

    def test_parse_real_html_structure(self):
        """실제 HTML 구조로 아이템 이름 파싱 테스트"""
        # 실제 메이플스토리 인벤토리 페이지 HTML 구조
        html = """
        <div class="inven_list">
            <div class="inven_item_img">
                <a href="/Common/Resource/Item?p=12345">
                    <img alt="" src="https://avatar.maplestory.nexon.com/ItemIcon/KEPCIGPD.png"/>
                </a>
            </div>
            <div class="inven_item_memo">
                <div class="inven_item_memo_title">
                    <h1>
                        <a href="/Common/Resource/Item?p=12345">
                            카오스 자쿰의 투구 (+4)
                        </a>
                    </h1>
                </div>
                <div class="item_memo_sel">
                    유니크아이템
                </div>
            </div>
        </div>
        <div class="inven_list">
            <div class="inven_item_img">
                <a href="/Common/Resource/Item?p=67890">
                    <img alt="" src="https://avatar.maplestory.nexon.com/ItemIcon/ABCDEFGH.png"/>
                </a>
            </div>
            <div class="inven_item_memo">
                <div class="inven_item_memo_title">
                    <h1>
                        <a href="/Common/Resource/Item?p=67890">
                            엘릭서 (100개)
                        </a>
                    </h1>
                </div>
                <div class="item_memo_sel">
                    일반아이템
                </div>
            </div>
        </div>
        """

        items = InventoryParser.parse_inventory(html)

        # 검증
        assert len(items) == 2

        # 첫 번째 아이템: 카오스 자쿰의 투구 (+4)
        assert items[0]['item_name'] == '카오스 자쿰의 투구 (+4)'
        assert items[0]['item_icon'] == 'https://avatar.maplestory.nexon.com/ItemIcon/KEPCIGPD.png'
        assert items[0]['item_options']['rarity'] == '유니크아이템'
        assert items[0]['item_options']['spell_trace'] == 4  # +4 파싱
        assert items[0]['quantity'] == 1

        # 두 번째 아이템: 엘릭서 (100개)
        assert items[1]['item_name'] == '엘릭서'
        assert items[1]['quantity'] == 100  # (100개) 파싱
        assert items[1]['item_icon'] == 'https://avatar.maplestory.nexon.com/ItemIcon/ABCDEFGH.png'
        assert items[1]['item_options']['rarity'] == '일반아이템'

    def test_parse_star_force_item(self):
        """스타포스 강화 아이템 파싱 테스트"""
        html = """
        <div class="inven_list">
            <div class="inven_item_img">
                <a href="/Common/Resource/Item?p=11111">
                    <img alt="" src="https://avatar.maplestory.nexon.com/ItemIcon/TEST1234.png"/>
                </a>
                <em>17성 강화</em>
            </div>
            <div class="inven_item_memo">
                <div class="inven_item_memo_title">
                    <h1>
                        <a href="/Common/Resource/Item?p=11111">
                            앱솔랩스 메이지 슈트
                        </a>
                    </h1>
                </div>
                <div class="item_memo_sel">
                    레전드리아이템
                </div>
            </div>
        </div>
        """

        items = InventoryParser.parse_inventory(html)

        assert len(items) == 1
        assert items[0]['item_name'] == '앱솔랩스 메이지 슈트'
        assert items[0]['item_options']['star_force'] == 17
        assert items[0]['item_options']['rarity'] == '레전드리아이템'

    def test_parse_item_without_options(self):
        """옵션 없는 아이템 파싱 테스트"""
        html = """
        <div class="inven_list">
            <div class="inven_item_img">
                <a href="/Common/Resource/Item?p=99999">
                    <img alt="" src="https://avatar.maplestory.nexon.com/ItemIcon/SIMPLE01.png"/>
                </a>
            </div>
            <div class="inven_item_memo">
                <div class="inven_item_memo_title">
                    <h1>
                        <a href="/Common/Resource/Item?p=99999">
                            주황버섯의 모자
                        </a>
                    </h1>
                </div>
            </div>
        </div>
        """

        items = InventoryParser.parse_inventory(html)

        assert len(items) == 1
        assert items[0]['item_name'] == '주황버섯의 모자'
        assert items[0]['quantity'] == 1
        assert items[0]['item_options'] is None  # 옵션 없음
