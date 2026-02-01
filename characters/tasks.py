"""
Celery tasks for expirable item detection (Story 5.1)
"""
import json
from celery import shared_task
from django.utils import timezone
import logging
from typing import Dict, List
from util.redis_client import redis_client
from .models import Inventory, Storage

logger = logging.getLogger(__name__)

# Story 5.1: Checkpoint thresholds for notifications
NOTIFICATION_THRESHOLDS = [7, 3, 1]  # D-7, D-3, D-1


@shared_task
def check_expirable_items() -> Dict:
    """
    Check for time-limited items daily at midnight (Story 5.1)

    Scans all Inventory and Storage items with expiry_date and calculates
    days_until_expiry (D-day). Identifies checkpoint items and stores them
    in Redis for notification delivery (Story 5.2).

    Returns:
        dict: Summary statistics
            - total_items: Total items scanned
            - expirable_items: Items with expiry_date set
            - checkpoint_items: Items at D-7, D-3, D-1 thresholds
            - expired_items: Items already expired (D < 0)
            - redis_keys_stored: Number of Redis keys created
    """
    logger.info("Starting daily expirable items check...")

    now = timezone.now()
    today = now.date()

    # Statistics
    stats = {
        'total_items': 0,
        'expirable_items': 0,
        'checkpoint_items': 0,
        'expired_items': 0,
        'redis_keys_stored': 0,
        'by_threshold': {threshold: 0 for threshold in NOTIFICATION_THRESHOLDS},
        'expired': 0
    }

    # Query items with expiry_date from both Inventory and Storage
    inventory_items = Inventory.objects.filter(
        expiry_date__isnull=False
    ).select_related('character_basic')

    storage_items = Storage.objects.filter(
        expiry_date__isnull=False
    ).select_related('character_basic')

    stats['total_items'] = inventory_items.count() + storage_items.count()

    # Process Inventory items
    checkpoint_items = []
    for item in inventory_items:
        stats['expirable_items'] += 1
        result = _process_expirable_item(item, today, 'inventory')
        if result:
            checkpoint_items.append(result)
            stats['checkpoint_items'] += 1
            if result['d_day'] < 0:
                stats['expired_items'] += 1
                stats['by_threshold']['expired'] += 1
            else:
                stats['by_threshold'][result['d_day']] += 1

    # Process Storage items
    for item in storage_items:
        stats['expirable_items'] += 1
        result = _process_expirable_item(item, today, 'storage')
        if result:
            checkpoint_items.append(result)
            stats['checkpoint_items'] += 1
            if result['d_day'] < 0:
                stats['expired_items'] += 1
                stats['by_threshold']['expired'] += 1
            else:
                stats['by_threshold'][result['d_day']] += 1

    # Story 5.2: Send notifications for checkpoint items
    from accounts.notifications import UserNotificationService
    from accounts.models import Character
    from django.contrib.auth.models import User

    notifications_sent = 0
    notifications_failed = 0

    for item_data in checkpoint_items:
        try:
            # Get the user who owns this character
            character = Character.objects.filter(ocid=item_data['ocid']).first()
            if not character or not character.user:
                logger.warning(f"No user found for character {item_data['ocid']}")
                continue

            user = character.user

            # Skip if user has no email
            if not user.email:
                logger.warning(f"User {user.id} has no email address")
                continue

            # Send notification
            success = UserNotificationService.send_expiry_notification(
                user=user,
                item_data={
                    'item_id': item_data['item_id'],
                    'item_name': item_data['item_name'],
                    'item_source': item_data['item_source'],
                    'character_name': item_data['character_name'],
                    'character_ocid': item_data['ocid'],
                    'expiry_date': item_data['expiry_date'],
                },
                d_day=item_data['d_day']
            )

            if success:
                notifications_sent += 1
                stats['redis_keys_stored'] += 1  # Keep stat name for backwards compat
            else:
                notifications_failed += 1

        except Exception as e:
            logger.error(f"Error sending notification for item {item_data['item_id']}: {e}")
            notifications_failed += 1

    # Update stats
    stats['notifications_sent'] = notifications_sent
    stats['notifications_failed'] = notifications_failed

    logger.info(
        f"Daily expirable items check completed: "
        f"{stats['total_items']} total, "
        f"{stats['expirable_items']} expirable, "
        f"{stats['checkpoint_items']} at checkpoints, "
        f"{stats['expired_items']} expired, "
        f"{stats.get('notifications_sent', 0)} notifications sent, "
        f"{stats.get('notifications_failed', 0)} notifications failed"
    )

    return stats


def _process_expirable_item(item, today, item_source: str) -> Dict | None:
    """
    Process a single item and determine if it's at a checkpoint threshold.

    Args:
        item: Inventory or Storage model instance
        today: Current date (date object)
        item_source: 'inventory' or 'storage'

    Returns:
        dict or None: Item data if at checkpoint, None otherwise
    """
    expiry_date = item.expiry_date.date() if item.expiry_date else None
    if not expiry_date:
        return None

    # Calculate D-day
    days_until_expiry = (expiry_date - today).days

    # Check if at checkpoint threshold or expired
    if days_until_expiry in NOTIFICATION_THRESHOLDS or days_until_expiry < 0:
        return {
            'ocid': item.character_basic.ocid,
            'item_id': item.id,
            'item_name': item.item_name,
            'item_source': item_source,
            'd_day': days_until_expiry,
            'expiry_date': expiry_date.isoformat(),
            'character_name': item.character_basic.character_name,
        }

    return None
