"""
Celery tasks for character crawling (Story 2.1, 2.2, 2.3, 2.9, 2.10)
"""
from celery import shared_task
from typing import List
import logging
import time
import asyncio
import pytz
from django.utils import timezone
from .services import TaskStatusService, MonitoringService
from .models import Character, CrawlTask
from .notifications import AlertService
from .exceptions import (
    CrawlError, CharacterNotFoundError, NetworkError, MaintenanceError,
    ErrorType, classify_exception
)
from characters.services import MapleAPIService
from characters.models import CharacterBasic, CharacterBasicHistory, CharacterPopularity, CharacterStat, Inventory, Storage
from characters.crawler_services import CrawlerService, CrawlingError, ParsingError, StorageParsingError, ItemDetailCrawler
from characters.schemas import InventoryItemSchema, StorageItemSchema
from pydantic import ValidationError

logger = logging.getLogger(__name__)

# Story 2.10: 성공률 임계치
SUCCESS_RATE_WARNING_THRESHOLD = 95.0  # AC-2.10.3: 이메일 알림
SUCCESS_RATE_CRITICAL_THRESHOLD = 80.0  # AC-2.10.4: 긴급 알림 (Slack)


@shared_task
def check_crawl_success_rate():
    """
    크롤링 성공률 체크 Periodic Task (Story 2.10: AC-2.10.3, AC-2.10.4)

    매시간 실행되어 성공률을 확인하고, 임계치 이하 시 알림 전송
    - 95% 미만: 이메일 알림 (WARNING)
    - 80% 미만: 이메일 + Slack 알림 (CRITICAL)

    알림 중복 방지: 동일 임계치 알림은 1시간 내 중복 발송 안 함
    """
    logger.info("Starting crawl success rate check...")

    # 최근 24시간 성공률 조회
    stats = MonitoringService.get_success_rate(hours=24)
    success_rate = stats['success_rate']
    total_tasks = stats['total_tasks']

    logger.info(f"Current success rate: {success_rate}% ({total_tasks} tasks)")

    # 데이터가 없으면 체크 스킵
    if total_tasks == 0:
        logger.info("No crawl tasks in the last 24 hours, skipping alert check")
        return {
            'status': 'skipped',
            'reason': 'no_data',
            'success_rate': success_rate,
            'total_tasks': total_tasks
        }

    # AC-2.10.4: 80% 미만 - 긴급 알림 (CRITICAL)
    if success_rate < SUCCESS_RATE_CRITICAL_THRESHOLD:
        if MonitoringService.can_send_alert('critical'):
            error_breakdown = MonitoringService.get_error_breakdown(hours=24)
            AlertService.send_critical_alert(success_rate, total_tasks, error_breakdown)
            MonitoringService.mark_alert_sent('critical')
            logger.warning(f"CRITICAL alert sent: success rate {success_rate}%")
            return {
                'status': 'alert_sent',
                'alert_type': 'critical',
                'success_rate': success_rate,
                'total_tasks': total_tasks
            }
        else:
            logger.info("Critical alert already sent within the last hour")
            return {
                'status': 'alert_skipped',
                'alert_type': 'critical',
                'reason': 'duplicate_prevention',
                'success_rate': success_rate,
                'total_tasks': total_tasks
            }

    # AC-2.10.3: 95% 미만 - 경고 알림 (WARNING)
    elif success_rate < SUCCESS_RATE_WARNING_THRESHOLD:
        if MonitoringService.can_send_alert('warning'):
            AlertService.send_warning_alert(success_rate, total_tasks)
            MonitoringService.mark_alert_sent('warning')
            logger.warning(f"WARNING alert sent: success rate {success_rate}%")
            return {
                'status': 'alert_sent',
                'alert_type': 'warning',
                'success_rate': success_rate,
                'total_tasks': total_tasks
            }
        else:
            logger.info("Warning alert already sent within the last hour")
            return {
                'status': 'alert_skipped',
                'alert_type': 'warning',
                'reason': 'duplicate_prevention',
                'success_rate': success_rate,
                'total_tasks': total_tasks
            }

    # 정상 상태 (95% 이상)
    logger.info(f"Success rate {success_rate}% is within normal range")
    return {
        'status': 'ok',
        'success_rate': success_rate,
        'total_tasks': total_tasks
    }


@shared_task(bind=True, max_retries=3)
def crawl_character_data(self, ocid: str, crawl_types: List[str]):
    """
    캐릭터 데이터 크롤링 메인 태스크 (Story 2.1, 2.2, 2.3)
    Story 1.8: ocid 기반으로 변경하여 게스트 모드 지원

    Args:
        ocid: 캐릭터 OCID (CharacterBasic 식별자)
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
        logger.info(f'Crawl task {task_id} started for ocid {ocid}')

        # 2. CharacterBasic 조회 (Story 1.8: 게스트 모드 지원)
        try:
            character_basic = CharacterBasic.objects.get(ocid=ocid)
        except CharacterBasic.DoesNotExist:
            raise ValueError(f'CharacterBasic with ocid {ocid} not found')

        # 3. character_info_url 새로 가져오기 (만료시간이 있으므로 항상 갱신)
        character_info_url = None
        crawl_types_needing_url = {'inventory', 'storage', 'meso'}
        if crawl_types_needing_url.intersection(crawl_types):
            TaskStatusService.update_task_status(
                task_id,
                'STARTED',
                progress=0,
                message='캐릭터 URL 조회 중...'
            )
            crawler = CrawlerService()
            character_info_url = asyncio.run(
                crawler.fetch_character_info_url(character_basic.character_name)
            )
            # URL 저장
            character_basic.character_info_url = character_info_url
            character_basic.save(update_fields=['character_info_url'])
            logger.info(f'Fetched and saved character_info_url: {character_info_url}')

        # 4. 크롤링 실행
        results = {}
        total_types = len(crawl_types)

        for idx, crawl_type in enumerate(crawl_types):
            base_progress = int((idx / total_types) * 100)

            # Story 2.2: 공식 API 데이터 수집
            if crawl_type == 'api_data':
                try:
                    # Step 1: OCID는 이미 있음 (Story 1.8: ocid 기반으로 변경)
                    TaskStatusService.update_task_status(
                        task_id,
                        'STARTED',
                        progress=base_progress,
                        message='캐릭터 정보 수집 중...'
                    )
                    logger.info(f'Using existing OCID: {ocid}')

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
                    logger.error(f'Pydantic validation error for ocid {ocid}: {ve}')
                    results['api_data'] = {
                        'status': 'validation_error',
                        'error': str(ve)
                    }
                except Exception as e:
                    logger.error(f'API data collection failed for ocid {ocid}: {e}')
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
                    # character_info_url은 task 시작 시 미리 가져옴 (재사용)
                    crawler = CrawlerService()
                    crawled_data = asyncio.run(
                        crawler.crawl_inventory(character_info_url, character_basic.character_name)
                    )

                    # AC 2.3.3 - 2.3.5: 데이터 검증 및 저장
                    # AC 2.3.6: 이전 데이터는 히스토리로 보관 (덮어쓰지 않음)
                    saved_items = []
                    # 모든 아이템에 동일한 crawled_at 적용
                    crawl_timestamp = timezone.now()
                    for item_data in crawled_data['items']:
                        try:
                            # Pydantic 검증
                            validated_item = InventoryItemSchema(**item_data)

                            # DB 저장 (AC 2.3.8: detail_url 포함)
                            inventory_item = Inventory.objects.create(
                                character_basic=character_basic,
                                item_type=validated_item.item_type,
                                item_name=validated_item.item_name,
                                item_icon=validated_item.item_icon,
                                quantity=validated_item.quantity,
                                item_options=validated_item.item_options,
                                slot_position=validated_item.slot_position,
                                expiry_date=validated_item.expiry_date,
                                detail_url=validated_item.detail_url,
                                has_detail=False,  # 상세 정보는 아직 크롤링 안됨
                                crawled_at=crawl_timestamp  # 동일한 타임스탬프
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
                    # Story 1.8: character_basic은 이미 조회됨
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

                    # character_info_url은 task 시작 시 미리 가져옴 (재사용)
                    crawler = CrawlerService()
                    crawled_data = asyncio.run(
                        crawler.crawl_storage(character_info_url, character_basic.character_name)
                    )

                    # AC 2.4.6, 2.4.7: Pydantic 검증 및 DB 저장
                    saved_count = 0

                    # 크롤링 데이터 안전하게 가져오기 (storage는 shared/personal 구분 없음)
                    storage_items = crawled_data.get('items', [])

                    # 모든 아이템에 동일한 crawled_at 적용
                    crawl_timestamp = timezone.now()

                    for item_data in storage_items:
                        try:
                            validated_item = StorageItemSchema(**item_data)
                            Storage.objects.create(
                                character_basic=character_basic,
                                storage_type='storage',  # 단일 창고 타입
                                item_name=validated_item.item_name,
                                item_icon=validated_item.item_icon,
                                quantity=validated_item.quantity,
                                item_options=validated_item.item_options,
                                slot_position=validated_item.slot_position,
                                expiry_date=validated_item.expiry_date,
                                crawled_at=crawl_timestamp,  # 동일한 타임스탬프
                            )
                            saved_count += 1
                        except ValidationError as ve:
                            logger.warning(f'Storage item validation failed: {ve}')
                            continue

                    logger.info(f'Storage crawling completed: {saved_count} items saved')
                    results['storage'] = {
                        'status': 'success',
                        'items_saved': saved_count,
                        'crawled_at': crawled_data.get('crawled_at')
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

                    # character_info_url은 task 시작 시 미리 가져옴 (재사용)
                    # AC 2.5.1: 캐릭터 메소 크롤링
                    crawler = CrawlerService()
                    crawled_data = asyncio.run(
                        crawler.crawl_character_meso(character_info_url, character_basic.character_name)
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
                        logger.warning(f'Meso parsing returned None for {character_basic.character_name}')
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

        # 4. 크롤링 완료 후 all_data 캐시 무효화
        # 새로고침 시 크롤링 데이터가 포함된 최신 데이터 반환
        try:
            from util.redis_client import redis_client
            cache_key = f"character_data:{ocid}:all_data"
            redis_client.delete(cache_key)
            logger.info(f'Cache invalidated after crawl - Key: {cache_key}')
        except Exception as cache_error:
            logger.warning(f'Cache invalidation failed: {cache_error}')

        # Story 2.10: 성공 기록 (AC-2.10.1)
        MonitoringService.record_crawl_result(task_id, 'SUCCESS')

        logger.info(f'Crawl task {task_id} completed successfully')

        return results

    except Exception as exc:
        logger.error(f'Crawl task {task_id} failed: {exc}')

        # Story 2.9: 예외를 적절한 CrawlError로 분류 (AC-2.9.1, AC-2.9.2)
        crawl_error = classify_exception(exc)

        # Retry logic with exponential backoff (AC #6, #7, #8)
        retry_count = self.request.retries
        countdown = 60 * (2 ** retry_count)  # 1분, 2분, 4분

        TaskStatusService.update_task_status(
            task_id,
            'RETRY',
            error=crawl_error.user_message,
            message=f'재시도 {retry_count + 1}/3 ({countdown}초 후)',
            error_type=crawl_error.error_type.value,
            technical_error=crawl_error.technical_error
        )

        if retry_count >= 2:
            # 최종 실패 (AC #8, Story 2.9: AC-2.9.1, AC-2.9.2, AC-2.9.3)
            TaskStatusService.update_task_status(
                task_id,
                'FAILURE',
                error=crawl_error.user_message,
                error_type=crawl_error.error_type.value,
                technical_error=crawl_error.technical_error
            )

            # Story 2.10: 실패 기록 (AC-2.10.1)
            MonitoringService.record_crawl_result(
                task_id,
                'FAILURE',
                error_type=crawl_error.error_type.value
            )

            # CrawlTask 모델 업데이트 (AC #9, Story 2.9: AC-2.9.2, AC-2.9.3)
            CrawlTask.objects.filter(task_id=task_id).update(
                status='FAILURE',
                error_message=crawl_error.user_message,
                error_type=crawl_error.error_type.value,
                technical_error=crawl_error.technical_error,
                retry_count=3
            )

            raise  # 재시도 중단
        else:
            # 재시도 (AC #6, #7)
            raise self.retry(exc=exc, countdown=countdown)
