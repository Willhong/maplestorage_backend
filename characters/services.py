import time
import requests
from django.utils import timezone
from datetime import timedelta
import logging

from define.define import (
    APIKEY,
    CHARACTER_ID_URL,
    CHARACTER_BASIC_URL,
    CHARACTER_ITEM_EQUIPMENT_URL,
    CHARACTER_CASHITEM_EQUIPMENT_URL,
    CHARACTER_SYMBOL_URL,
    CHARACTER_LINK_SKILL_URL,
    CHARACTER_SKILL_URL,
    CHARACTER_HEXAMATRIX_URL,
    CHARACTER_HEXAMATRIX_STAT_URL,
    CHARACTER_POPULARITY_URL,
    CHARACTER_STAT_URL,
    CHARACTER_ABILITY_URL
)
from accounts.models import Character
from .models import (
    CharacterBasic, CharacterItemEquipment, ItemEquipment,
    ItemTotalOption, ItemBaseOption, ItemEtcOption,
    ItemStarforceOption, ItemExceptionalOption, ItemAddOption, Title
)
from .schemas import (
    CharacterItemEquipmentSchema, CharacterBasicSchema,
    CharacterPopularitySchema, CharacterStatSchema,
    CharacterSymbolSchema
)
from .mixins import MapleAPIClientMixin, CharacterDataMixin
from .utils import handle_api_exception, log_api_call
from .exceptions import CharacterNotFoundError, DatabaseError, DataValidationError

logger = logging.getLogger(__name__)


class MapleAPIService(CharacterDataMixin):
    """메이플스토리 API 호출 서비스"""

    ENDPOINTS = {
        'basic': CHARACTER_BASIC_URL,
        'popularity': CHARACTER_POPULARITY_URL,
        'stat': CHARACTER_STAT_URL,
        'ability': CHARACTER_ABILITY_URL,
        'item_equipment': CHARACTER_ITEM_EQUIPMENT_URL,
        'cashitem_equipment': CHARACTER_CASHITEM_EQUIPMENT_URL,
        'skill': CHARACTER_SKILL_URL,
        'symbol': CHARACTER_SYMBOL_URL,
        'link_skill': CHARACTER_LINK_SKILL_URL,
        'hexamatrix': CHARACTER_HEXAMATRIX_URL,
        'hexamatrix_stat': CHARACTER_HEXAMATRIX_STAT_URL
    }

    @staticmethod
    def get_headers():
        """API 호출용 헤더 반환"""
        return {
            "accept": "application/json",
            "x-nxopen-api-key": APIKEY
        }

    @staticmethod
    @handle_api_exception
    def get_ocid(character_name):
        """
        캐릭터 OCID 조회

        Args:
            character_name (str): 캐릭터 이름

        Returns:
            str: 캐릭터 OCID

        Raises:
            CharacterNotFoundError: 캐릭터를 찾을 수 없는 경우
            MapleAPIError: API 호출 중 오류가 발생한 경우
        """
        log_api_call("get_ocid", {"character_name": character_name})

        # 로컬 DB에서 먼저 조회
        local_character = Character.objects.filter(
            character_name=character_name).first()
        if local_character:
            return local_character.ocid

        # API 호출
        headers = MapleAPIService.get_headers()
        response = requests.get(
            f"{CHARACTER_ID_URL}?character_name={character_name}",
            headers=headers
        )
        response.raise_for_status()
        data = response.json()

        ocid = data.get('ocid')
        if not ocid:
            raise CharacterNotFoundError(
                message=f"'{character_name}' 캐릭터를 찾을 수 없습니다."
            )

        return ocid

    @staticmethod
    @handle_api_exception
    def get_character_data(endpoint_key, ocid, date=None, **kwargs):
        """
        캐릭터 데이터 조회 공통 메서드

        Args:
            endpoint_key (str): 엔드포인트 키
            ocid (str): 캐릭터 OCID
            date (str, optional): 조회 기준일
            **kwargs: 추가 파라미터

        Returns:
            dict: API 응답 데이터

        Raises:
            MapleAPIError: API 호출 중 오류가 발생한 경우
        """
        log_api_call(f"get_character_{endpoint_key}", {
                     "ocid": ocid, "date": date, **kwargs})

        # API 호출
        headers = MapleAPIService.get_headers()
        base_url = MapleAPIService.ENDPOINTS[endpoint_key]

        # URL 파라미터 구성
        params = {'ocid': ocid}
        if date:
            params['date'] = date
        params.update(kwargs)

        # URL 생성
        param_str = '&'.join(f"{k}={v}" for k, v in params.items())
        url = f"{base_url}?{param_str}"

        response = requests.get(url, headers=headers)
        response.raise_for_status()

        return response.json()

    @staticmethod
    @handle_api_exception
    def get_character_basic(ocid, date=None):
        """캐릭터 기본 정보 조회"""
        basic_data = MapleAPIService.get_character_data('basic', ocid, date)
        service = MapleAPIService()
        current_time = service.convert_to_local_time(basic_data.get('date'))

        try:
            character_basic, created = CharacterBasic.objects.update_or_create(
                ocid=ocid,
                defaults={
                    'date': current_time,
                    'character_name': basic_data.get('character_name'),
                    'world_name': basic_data.get('world_name'),
                    'character_gender': basic_data.get('character_gender'),
                    'character_class': basic_data.get('character_class'),
                    'character_class_level': basic_data.get('character_class_level'),
                    'character_level': basic_data.get('character_level'),
                    'character_exp': basic_data.get('character_exp'),
                    'character_exp_rate': basic_data.get('character_exp_rate'),
                    'character_guild_name': basic_data.get('character_guild_name'),
                    'character_image': basic_data.get('character_image'),
                    'access_flag': True,
                    'liberation_quest_clear_flag': True
                }
            )
            return character_basic, current_time
        except Exception as e:
            raise DatabaseError(
                message="캐릭터 기본 정보 저장 중 오류가 발생했습니다.",
                detail=str(e)
            )

    @staticmethod
    @handle_api_exception
    def get_character_popularity(ocid, date=None):
        """캐릭터 인기도 정보 조회"""
        return MapleAPIService.get_character_data('popularity', ocid, date)

    @staticmethod
    @handle_api_exception
    def get_character_stat(ocid, date=None):
        """캐릭터 스탯 정보 조회"""
        return MapleAPIService.get_character_data('stat', ocid, date)

    @staticmethod
    @handle_api_exception
    def get_character_ability(ocid, date=None):
        """캐릭터 어빌리티 정보 조회"""
        return MapleAPIService.get_character_data('ability', ocid, date)

    @staticmethod
    @handle_api_exception
    def get_character_item_equipment(ocid, date=None):
        """캐릭터 장비 정보 조회"""
        return MapleAPIService.get_character_data('item_equipment', ocid, date)

    @staticmethod
    @handle_api_exception
    def get_character_cashitem_equipment(ocid, date=None):
        """캐릭터 캐시 장비 정보 조회"""
        return MapleAPIService.get_character_data('cashitem_equipment', ocid, date)

    @staticmethod
    @handle_api_exception
    def get_character_symbol(ocid, date=None):
        """캐릭터 심볼 정보 조회"""
        return MapleAPIService.get_character_data('symbol', ocid, date)

    @staticmethod
    @handle_api_exception
    def get_character_link_skill(ocid, date=None):
        """캐릭터 링크 스킬 정보 조회"""
        return MapleAPIService.get_character_data('link_skill', ocid, date)

    @staticmethod
    @handle_api_exception
    def get_character_skill(ocid, skill_grade, date=None):
        """캐릭터 스킬 정보 조회"""
        return MapleAPIService.get_character_data('skill', ocid, date, character_skill_grade=skill_grade)

    @staticmethod
    @handle_api_exception
    def get_character_hexamatrix(ocid, date=None):
        """캐릭터 HEXA 매트릭스 정보 조회"""
        return MapleAPIService.get_character_data('hexamatrix', ocid, date)

    @staticmethod
    @handle_api_exception
    def get_character_hexamatrix_stat(ocid, date=None):
        """캐릭터 HEXA 매트릭스 스탯 정보 조회"""
        return MapleAPIService.get_character_data('hexamatrix_stat', ocid, date)


class EquipmentService:
    """장비 정보 처리 서비스"""

    @staticmethod
    def save_equipment_data(validated_data, character_basic, current_time):
        """장비 데이터 저장"""
        save_start = time.time()

        # 서비스 인스턴스 생성 (convert_to_local_time 메서드 사용을 위해)
        service = MapleAPIService()

        # 날짜 확인 및 변환 (이미 변환된 경우 그대로 사용)
        if isinstance(current_time, str):
            # 문자열인 경우 변환 필요
            local_time = service.convert_to_local_time(current_time)
            logger.info(f"장비 데이터 저장 날짜 변환: {current_time} -> {local_time}")
        else:
            # 이미 datetime 객체인 경우 그대로 사용
            local_time = current_time
            logger.info(f"장비 데이터 저장 날짜 사용: {local_time}")

        # 기본 장비 정보 저장
        character_equipment = CharacterItemEquipment.objects.create(
            character=character_basic,
            date=local_time,
            character_gender=validated_data.character_gender,
            character_class=validated_data.character_class,
            preset_no=validated_data.preset_no,
        )
        print(f"기본 장비 정보 저장 소요시간: {time.time() - save_start:.2f}초")

        # 장비 아이템 저장
        equipment_list = EquipmentService.process_equipment_items(
            validated_data)

        # 장비 관계 설정
        EquipmentService.set_equipment_relations(
            character_equipment, equipment_list)

        print(f"전체 데이터 저장 소요시간: {time.time() - save_start:.2f}초")
        return character_equipment

    @staticmethod
    def process_equipment_items(validated_data):
        """장비 아이템 처리 및 저장"""
        option_start = time.time()
        equipment_list = {}

        for key, item_datas in validated_data.model_dump().items():
            if key.startswith('item_equipment') or key.startswith('dragon') or key.startswith('mechanic'):
                equipment_list[key] = EquipmentService.process_equipment_group(
                    item_datas)
            elif key == 'title':
                equipment_list[key] = EquipmentService.process_title(
                    item_datas)

        print(f"장비 옵션 데이터 생성 소요시간: {time.time() - option_start:.2f}초")
        return equipment_list

    @staticmethod
    def process_equipment_group(item_datas):
        """장비 그룹 처리"""
        item_list = []
        bulk_items = []
        bulk_total_options = []
        bulk_base_options = []
        bulk_etc_options = []
        bulk_starforce_options = []
        bulk_exceptional_options = []
        bulk_add_options = []

        for item_data in item_datas:
            # 옵션 객체 생성 (아직 저장하지 않음)
            total_option = ItemTotalOption(**item_data['item_total_option'])
            base_option = ItemBaseOption(**item_data['item_base_option'])
            etc_option = ItemEtcOption(**item_data['item_etc_option'])
            starforce_option = ItemStarforceOption(
                **item_data['item_starforce_option'])
            exceptional_option = ItemExceptionalOption(
                **item_data['item_exceptional_option']) if item_data['item_exceptional_option'] else None
            add_option = ItemAddOption(
                **item_data['item_add_option']) if item_data['item_add_option'] else None

            # 옵션 객체들을 각각의 리스트에 추가
            bulk_total_options.append(total_option)
            bulk_base_options.append(base_option)
            bulk_etc_options.append(etc_option)
            bulk_starforce_options.append(starforce_option)
            if exceptional_option:
                bulk_exceptional_options.append(exceptional_option)
            if add_option:
                bulk_add_options.append(add_option)

            # 장비 데이터 생성 준비
            equipment_data = {
                key: item_data[key] for key in item_data.keys() if key not in ['item_total_option', 'item_base_option', 'item_etc_option', 'item_starforce_option', 'item_exceptional_option', 'item_add_option']
            }

            # date_expire 필드가 있으면 형식 변환
            if 'date_expire' in equipment_data and equipment_data['date_expire']:
                try:
                    equipment_data['date_expire'] = timezone.datetime.fromisoformat(
                        equipment_data['date_expire'].replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    equipment_data['date_expire'] = None

            equipment = ItemEquipment.objects.filter(**equipment_data).first()
            if not equipment:
                bulk_items.append(
                    (equipment_data, len(bulk_total_options) - 1))
            else:
                item_list.append(equipment)

        # bulk_create로 옵션 데이터들을 한 번에 저장
        created_total_options = ItemTotalOption.objects.bulk_create(
            bulk_total_options)
        created_base_options = ItemBaseOption.objects.bulk_create(
            bulk_base_options)
        created_etc_options = ItemEtcOption.objects.bulk_create(
            bulk_etc_options)
        created_starforce_options = ItemStarforceOption.objects.bulk_create(
            bulk_starforce_options)
        created_exceptional_options = ItemExceptionalOption.objects.bulk_create(
            bulk_exceptional_options) if bulk_exceptional_options else []
        created_add_options = ItemAddOption.objects.bulk_create(
            bulk_add_options) if bulk_add_options else []

        # ItemEquipment 객체들 생성 및 옵션 연결
        new_items = []
        for equipment_data, idx in bulk_items:
            equipment_data.update({
                'item_total_option': created_total_options[idx],
                'item_base_option': created_base_options[idx],
                'item_etc_option': created_etc_options[idx],
                'item_starforce_option': created_starforce_options[idx],
            })
            if idx < len(created_exceptional_options):
                equipment_data['item_exceptional_option'] = created_exceptional_options[idx]
            if idx < len(created_add_options):
                equipment_data['item_add_option'] = created_add_options[idx]
            new_items.append(ItemEquipment(**equipment_data))

        # bulk_create로 ItemEquipment 객체들 생성
        if new_items:
            created_items = ItemEquipment.objects.bulk_create(new_items)
            item_list.extend(created_items)

        return item_list

    @staticmethod
    def process_title(item_datas):
        """타이틀 처리"""
        if not item_datas:
            return None

        title_data = item_datas.copy()
        # title의 date_expire와 date_option_expire 필드 형식 변환
        if 'date_expire' in title_data and title_data['date_expire']:
            try:
                title_data['date_expire'] = timezone.datetime.fromisoformat(
                    title_data['date_expire'].replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                title_data['date_expire'] = None
        if 'date_option_expire' in title_data and title_data['date_option_expire']:
            try:
                title_data['date_option_expire'] = timezone.datetime.fromisoformat(
                    title_data['date_option_expire'].replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                title_data['date_option_expire'] = None

        title = Title.objects.filter(**title_data).first()
        if not title:
            title = Title.objects.create(**title_data)
        return title

    @staticmethod
    def set_equipment_relations(character_equipment, equipment_list):
        """장비 관계 설정"""
        relation_start = time.time()

        character_equipment.item_equipment.set(
            equipment_list['item_equipment'])
        character_equipment.item_equipment_preset_1.set(
            equipment_list['item_equipment_preset_1'])
        character_equipment.item_equipment_preset_2.set(
            equipment_list['item_equipment_preset_2'])
        character_equipment.item_equipment_preset_3.set(
            equipment_list['item_equipment_preset_3'])
        character_equipment.title = equipment_list['title']
        character_equipment.dragon_equipment.set(
            equipment_list['dragon_equipment'])
        character_equipment.mechanic_equipment.set(
            equipment_list['mechanic_equipment'])

        character_equipment.save()
        print(f"장비 관계 설정 소요시간: {time.time() - relation_start:.2f}초")

    @staticmethod
    def log_equipment_data(character_name):
        """장비 데이터 로깅"""
        character_equipments = CharacterItemEquipment.objects.filter(
            character__character_name=character_name)

        equipment_fields = [
            'item_equipment',
            'item_equipment_preset_1',
            'item_equipment_preset_2',
            'item_equipment_preset_3',
            'dragon_equipment',
            'mechanic_equipment'
        ]

        # 각 장비 종류별 수 출력
        for equipment in character_equipments:
            print(f"캐릭터 장비 데이터 ID: {equipment.id}")
            print(f"데이터 일자: {equipment.date.strftime('%Y-%m-%d %H:%M')}")
            for field in equipment_fields:
                count = getattr(equipment, field).count()
                print(f"{field}: {count}개")
            if equipment.title:
                print("title: 1개")
            print("---")
