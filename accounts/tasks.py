"""
Celery tasks for character crawling (Story 2.1, 2.2, 2.3)
"""
from celery import shared_task
from typing import List
import logging
import time
import asyncio
from .services import TaskStatusService
from .models import Character, CrawlTask
from characters.services import MapleAPIService
from characters.models import CharacterBasic, CharacterPopularity, CharacterStat, Inventory, Storage
from characters.crawler_services import CrawlerService, CrawlingError, ParsingError, StorageParsingError
from characters.schemas import InventoryItemSchema, StorageItemSchema
from pydantic import ValidationError

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def crawl_character_data(self, character_id: int, crawl_types: List[str]):
    """
    캐릭터 데이터 크롤링 메인 태스크 (Story 2.1, 2.2, 2.3)

    Args:
        character_id: Character의 primary key
        crawl_types: ['inventory', 'item_details', 'storage', 'meso', 'api_data']

    Returns:
        dict: {'status': 'SUCCESS', 'data': {...}}
    """
    task_id = self.request.id

    try:
        # 1. Task 상태 업데이트: STARTED (Story 2.7: AC #2)
        TaskStatusService.update_task_status(
            task_id,
            'STARTED',
            progress=0,
            message='크롤링 시작 중...'
        )
        logger.info(f'Crawl task {task_id} started for character {character_id}')

        # 2. Character 조회
        try:
            character = Character.objects.get(id=character_id)
        except Character.DoesNotExist:
            raise ValueError(f'Character with id {character_id} not found')

        # 3. 크롤링 실행
        results = {}
        total_types = len(crawl_types)

        for idx, crawl_type in enumerate(crawl_types):
            base_progress = int((idx / total_types) * 100)

            # Story 2.2: 공식 API 데이터 수집
            if crawl_type == 'api_data':
                try:
                    # Step 1: OCID 조회 (AC 2.2.1)
                    TaskStatusService.update_task_status(
                        task_id,
                        'STARTED',
                        progress=base_progress,
                        message='OCID 조회 중...'
                    )
                    ocid = MapleAPIService.get_ocid(character.character_name)
                    logger.info(f'OCID retrieved: {ocid}')

                    # Step 2: 캐릭터 기본 정보 (AC 2.2.2)
                    TaskStatusService.update_task_status(
                        task_id,
                        'STARTED',
                        progress=base_progress + int((1/4) * (100/total_types)),
                        message='캐릭터 기본 정보 수집 중...'
                    )
                    character_basic, date = MapleAPIService.get_character_basic(ocid)
                    logger.info(f'Character basic data saved: {character_basic.character_name}')

                    # Step 3: 인기도 (AC 2.2.3)
                    TaskStatusService.update_task_status(
                        task_id,
                        'STARTED',
                        progress=base_progress + int((2/4) * (100/total_types)),
                        message='인기도 정보 수집 중...'
                    )
                    popularity_data = MapleAPIService.get_character_popularity(ocid)
                    CharacterPopularity.create_from_data(character_basic, popularity_data)
                    logger.info(f'Popularity data saved')

                    # Step 4: 스탯 (AC 2.2.4)
                    TaskStatusService.update_task_status(
                        task_id,
                        'STARTED',
                        progress=base_progress + int((3/4) * (100/total_types)),
                        message='스탯 정보 수집 중...'
                    )
                    stat_data = MapleAPIService.get_character_stat(ocid)
                    CharacterStat.create_from_data(character_basic, stat_data)
                    logger.info(f'Stat data saved')

                    results['api_data'] = {
                        'status': 'success',
                        'ocid': ocid,
                        'character_name': character_basic.character_name
                    }

                except ValidationError as ve:
                    # AC 2.2.7: 검증 실패 로깅
                    logger.error(f'Pydantic validation error for character {character_id}: {ve}')
                    results['api_data'] = {
                        'status': 'validation_error',
                        'error': str(ve)
                    }
                except Exception as e:
                    logger.error(f'API data collection failed for character {character_id}: {e}')
                    results['api_data'] = {
                        'status': 'error',
                        'error': str(e)
                    }

            # Story 2.3: 인벤토리 크롤링
            elif crawl_type == 'inventory':
                try:
                    TaskStatusService.update_task_status(
                        task_id,
                        'STARTED',
                        progress=base_progress,
                        message=f'인벤토리 수집 중... ({base_progress}%)'  # Story 2.7: AC #2
                    )

                    # AC 2.3.1: Playwright로 크롤링 실행
                    # CharacterBasic 조회하여 character_info_url 얻기
                    character_basic = CharacterBasic.objects.filter(
                        character_name=character.character_name
                    ).first()

                    if not character_basic:
                        raise ValueError(f'CharacterBasic not found for {character.character_name}')

                    # character_info_url이 없으면 임시 URL 생성 (TODO: 실제 URL은 랭킹 페이지에서 크롤링)
                    character_info_url = character_basic.character_info_url
                    if not character_info_url:
                        # 임시 URL 생성 (실제로는 랭킹 페이지에서 검색 필요)
                        character_info_url = f'https://maplestory.nexon.com/MyMaple/Character/Detail/{character.character_name}'
                        logger.warning(f'character_info_url not found for {character.character_name}, using temporary URL')

                    crawler = CrawlerService()
                    crawled_data = asyncio.run(
                        crawler.crawl_inventory(character_info_url, character.character_name)
                    )

                    # AC 2.3.3 - 2.3.5: 데이터 검증 및 저장
                    character_basic = CharacterBasic.objects.filter(
                        character_name=character.character_name
                    ).first()

                    if not character_basic:
                        raise ValueError(f'CharacterBasic not found for {character.character_name}')

                    # AC 2.3.6: 이전 데이터는 히스토리로 보관 (덮어쓰지 않음)
                    saved_items = []
                    for item_data in crawled_data['items']:
                        try:
                            # Pydantic 검증
                            validated_item = InventoryItemSchema(**item_data)

                            # DB 저장 (AC 2.3.8: detail_url 포함)
                            inventory_item = Inventory.objects.create(
                                character_basic=character_basic,
                                item_name=validated_item.item_name,
                                item_icon=validated_item.item_icon,
                                quantity=validated_item.quantity,
                                item_options=validated_item.item_options,
                                slot_position=validated_item.slot_position,
                                expiry_date=validated_item.expiry_date,
                                detail_url=validated_item.detail_url,
                                has_detail=False  # 상세 정보는 아직 크롤링 안됨
                            )
                            saved_items.append(inventory_item.id)

                        except ValidationError as ve:
                            # AC 2.3.7: 검증 실패 로깅
                            logger.warning(f'Item validation failed for slot {item_data.get("slot_position")}: {ve}')
                            continue

                    logger.info(f'Inventory crawling completed: {len(saved_items)} items saved')
                    results['inventory'] = {
                        'status': 'success',
                        'items_saved': len(saved_items),
                        'crawled_at': crawled_data['crawled_at']
                    }

                except (CrawlingError, ParsingError) as e:
                    # AC 2.3.7: 구체적 에러 메시지 로깅
                    logger.error(f'Inventory crawling error: {e}')
                    results['inventory'] = {
                        'status': 'error',
                        'error': str(e)
                    }
                except Exception as e:
                    logger.error(f'Unexpected error during inventory crawling: {e}')
                    results['inventory'] = {
                        'status': 'error',
                        'error': str(e)
                    }

            # Story 2.3 확장: 아이템 상세 정보 크롤링
            elif crawl_type == 'item_details':
                try:
                    TaskStatusService.update_task_status(
                        task_id,
                        'STARTED',
                        progress=base_progress,
                        message='아이템 상세 정보 수집 중...'
                    )

                    # 캐릭터의 Inventory 아이템 조회 (detail_url이 있는 것만)
                    character_basic = CharacterBasic.objects.filter(
                        character_name=character.character_name
                    ).first()

                    if not character_basic:
                        raise ValueError(f'CharacterBasic not found for {character.character_name}')

                    inventory_items = Inventory.objects.filter(
                        character_basic=character_basic,
                        detail_url__isnull=False,
                        has_detail=False  # 아직 상세 정보가 없는 것만
                    ).order_by('id')

                    total_items = inventory_items.count()
                    logger.info(f'Found {total_items} items to crawl details')

                    if total_items == 0:
                        results['item_details'] = {
                            'status': 'success',
                            'message': 'No items to crawl',
                            'success_count': 0
                        }
                    else:
                        # Progress 콜백 함수
                        def update_progress(current, total):
                            progress = base_progress + int((current / total) * (100 / total_types))
                            TaskStatusService.update_task_status(
                                task_id,
                                'STARTED',
                                progress=progress,
                                message=f'아이템 상세 정보 수집 중... ({current}/{total})'
                            )

                        # ItemDetailCrawler로 크롤링
                        from characters.crawler_services import ItemDetailCrawler
                        crawler = ItemDetailCrawler()
                        crawl_result = asyncio.run(
                            crawler.crawl_item_details(
                                list(inventory_items),
                                progress_callback=update_progress
                            )
                        )

                        logger.info(f'Item details crawling completed: {crawl_result["success_count"]}/{total_items}')
                        results['item_details'] = {
                            'status': 'success',
                            'success_count': crawl_result['success_count'],
                            'failed_count': len(crawl_result['failed_items']),
                            'total_time': crawl_result['total_time']
                        }

                except Exception as e:
                    logger.error(f'Item details crawling error: {e}', exc_info=True)
                    results['item_details'] = {
                        'status': 'error',
                        'error': str(e)
                    }

            # Story 2.4: 창고 크롤링
            elif crawl_type == 'storage':
                try:
                    TaskStatusService.update_task_status(
                        task_id,
                        'STARTED',
                        progress=base_progress,
                        message=f'창고 수집 중... ({base_progress}%)'  # Story 2.7: AC #2
                    )

                    # CharacterBasic 조회
                    character_basic = CharacterBasic.objects.filter(
                        character_name=character.character_name
                    ).first()

                    if not character_basic:
                        raise ValueError(f'CharacterBasic not found for {character.character_name}')

                    # character_info_url 확인
                    character_info_url = character_basic.character_info_url
                    if not character_info_url:
                        character_info_url = f'https://maplestory.nexon.com/MyMaple/Character/Detail/{character.character_name}'
                        logger.warning(f'character_info_url not found for {character.character_name}, using temporary URL')

                    # AC 2.4.8: 공유 창고 중복 방지 체크
                    from django.core.cache import cache
                    user_id = character.user_id if hasattr(character, 'user_id') else character.id
                    shared_cache_key = f'shared_storage:{user_id}'
                    skip_shared = cache.get(shared_cache_key)

                    crawler = CrawlerService()
                    crawled_data = asyncio.run(
                        crawler.crawl_storage(character_info_url, character.character_name)
                    )

                    # AC 2.4.6, 2.4.7: Pydantic 검증 및 DB 저장
                    saved_shared = 0
                    saved_personal = 0

                    # 공유 창고 처리 (중복 방지 로직 적용)
                    if not skip_shared and crawled_data['shared_items']:
                        for item_data in crawled_data['shared_items']:
                            try:
                                validated_item = StorageItemSchema(**item_data)
                                Storage.objects.create(
                                    character_basic=character_basic,
                                    storage_type=validated_item.storage_type,
                                    item_name=validated_item.item_name,
                                    item_icon=validated_item.item_icon,
                                    quantity=validated_item.quantity,
                                    item_options=validated_item.item_options,
                                    slot_position=validated_item.slot_position,
                                    expiry_date=validated_item.expiry_date,
                                )
                                saved_shared += 1
                            except ValidationError as ve:
                                logger.warning(f'Storage item validation failed: {ve}')
                                continue

                        # AC 2.4.8: 공유 창고 캐시 설정 (1시간 TTL)
                        cache.set(shared_cache_key, True, timeout=3600)
                        logger.info(f'Shared storage cache set for user {user_id}')
                    elif skip_shared:
                        logger.info(f'Skipping shared storage crawl for user {user_id} (cached)')
                        saved_shared = -1  # 캐시 사용 표시

                    # 개인 창고 처리
                    for item_data in crawled_data['personal_items']:
                        try:
                            validated_item = StorageItemSchema(**item_data)
                            Storage.objects.create(
                                character_basic=character_basic,
                                storage_type=validated_item.storage_type,
                                item_name=validated_item.item_name,
                                item_icon=validated_item.item_icon,
                                quantity=validated_item.quantity,
                                item_options=validated_item.item_options,
                                slot_position=validated_item.slot_position,
                                expiry_date=validated_item.expiry_date,
                            )
                            saved_personal += 1
                        except ValidationError as ve:
                            logger.warning(f'Storage item validation failed: {ve}')
                            continue

                    logger.info(f'Storage crawling completed: {saved_shared} shared, {saved_personal} personal items')
                    results['storage'] = {
                        'status': 'success',
                        'shared_items_saved': saved_shared,
                        'personal_items_saved': saved_personal,
                        'shared_from_cache': skip_shared is not None,
                        'crawled_at': crawled_data['crawled_at']
                    }

                except (CrawlingError, StorageParsingError) as e:
                    # AC 2.4.10, 2.4.11: 구체적 에러 메시지 로깅
                    logger.error(f'Storage crawling error: {e}')
                    results['storage'] = {
                        'status': 'error',
                        'error': str(e)
                    }
                except Exception as e:
                    logger.error(f'Unexpected error during storage crawling: {e}', exc_info=True)
                    results['storage'] = {
                        'status': 'error',
                        'error': str(e)
                    }

            # Story 2.5: 메소 보유량 크롤링 (AC 2.5.1 - 2.5.6)
            elif crawl_type == 'meso':
                try:
                    TaskStatusService.update_task_status(
                        task_id,
                        'STARTED',
                        progress=base_progress,
                        message=f'메소 수집 중... ({base_progress}%)'  # Story 2.7: AC #2
                    )

                    # CharacterBasic 조회
                    character_basic = CharacterBasic.objects.filter(
                        character_name=character.character_name
                    ).first()

                    if not character_basic:
                        raise ValueError(f'CharacterBasic not found for {character.character_name}')

                    # character_info_url 확인 (없으면 랭킹 페이지에서 새로 얻어옴)
                    character_info_url = character_basic.character_info_url
                    crawler = CrawlerService()

                    if not character_info_url:
                        logger.info(f'Fetching character_info_url from ranking page for {character.character_name}')
                        character_info_url = asyncio.run(
                            crawler.fetch_character_info_url(character.character_name)
                        )
                        # 얻어온 URL 저장
                        character_basic.character_info_url = character_info_url
                        character_basic.save(update_fields=['character_info_url'])
                        logger.info(f'Saved character_info_url: {character_info_url}')

                    # AC 2.5.1: 캐릭터 메소 크롤링
                    crawled_data = asyncio.run(
                        crawler.crawl_character_meso(character_info_url, character.character_name)
                    )

                    meso_amount = crawled_data.get('meso')

                    # AC 2.5.3: 캐릭터와 연결하여 저장
                    # AC 2.5.5: 0 메소도 정상 저장
                    if meso_amount is not None:
                        # CharacterBasic.meso 업데이트
                        character_basic.meso = meso_amount
                        character_basic.save(update_fields=['meso'])
                        logger.info(f'Updated CharacterBasic.meso: {meso_amount:,}')

                        # AC 2.5.4: 히스토리 보관 - CharacterBasicHistory에 기록
                        from characters.models import CharacterBasicHistory
                        from django.utils import timezone
                        import pytz

                        kst = pytz.timezone('Asia/Seoul')
                        current_time = timezone.now().astimezone(kst)

                        # 오늘 날짜의 히스토리 찾기
                        existing_history = CharacterBasicHistory.objects.filter(
                            character=character_basic,
                            date__date=current_time.date()
                        ).first()

                        if existing_history:
                            # 기존 히스토리가 있으면 meso 필드만 업데이트
                            existing_history.meso = meso_amount
                            existing_history.save(update_fields=['meso'])
                            logger.info(f'Updated existing CharacterBasicHistory.meso: {meso_amount:,}')
                        else:
                            # 새 히스토리 생성 (메소 크롤링만 단독 실행된 경우)
                            logger.info(f'No existing history for today, meso will be saved on next api_data crawl')

                        results['meso'] = {
                            'status': 'success',
                            'meso': meso_amount,
                            'crawled_at': crawled_data['crawled_at']
                        }
                    else:
                        # AC 2.5.6: 파싱 실패 시 null 저장 및 에러 로깅
                        logger.warning(f'Meso parsing returned None for {character.character_name}')
                        results['meso'] = {
                            'status': 'success',
                            'meso': None,
                            'message': 'Meso parsing returned null',
                            'crawled_at': crawled_data['crawled_at']
                        }

                except CrawlingError as e:
                    # AC 2.5.6: 구체적 에러 메시지 로깅
                    logger.error(f'Meso crawling error: {e}')
                    results['meso'] = {
                        'status': 'error',
                        'error': str(e)
                    }
                except Exception as e:
                    logger.error(f'Unexpected error during meso crawling: {e}', exc_info=True)
                    results['meso'] = {
                        'status': 'error',
                        'error': str(e)
                    }

        # 3. Task 상태 업데이트: SUCCESS (Story 2.7: AC #2)
        TaskStatusService.update_task_status(
            task_id,
            'SUCCESS',
            progress=100,
            message='완료! (100%)'
        )
        logger.info(f'Crawl task {task_id} completed successfully')

        return results

    except Exception as exc:
        logger.error(f'Crawl task {task_id} failed: {exc}')

        # Retry logic with exponential backoff (AC #6, #7, #8)
        retry_count = self.request.retries
        countdown = 60 * (2 ** retry_count)  # 1분, 2분, 4분

        TaskStatusService.update_task_status(
            task_id,
            'RETRY',
            error=str(exc),
            message=f'재시도 {retry_count + 1}/3 ({countdown}초 후)'
        )

        if retry_count >= 2:
            # 최종 실패 (AC #8)
            TaskStatusService.update_task_status(
                task_id,
                'FAILURE',
                error=str(exc)
            )

            # CrawlTask 모델 업데이트 (AC #9)
            CrawlTask.objects.filter(task_id=task_id).update(
                status='FAILURE',
                error_message=str(exc),
                retry_count=3
            )

            raise  # 재시도 중단
        else:
            # 재시도 (AC #6, #7)
            raise self.retry(exc=exc, countdown=countdown)
