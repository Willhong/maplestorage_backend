import os
from celery import Celery
from celery.schedules import crontab

# Django 설정 모듈을 Celery의 기본 설정으로 지정
os.environ.setdefault('DJANGO_SETTINGS_MODULE',
                      'maplestorage_backend.settings')

app = Celery('maplestorage_backend')

# namespace='CELERY'는 모든 Celery 관련 설정 키가 'CELERY_' 로 시작해야 함을 의미
app.config_from_object('django.conf:settings', namespace='CELERY')

# 등록된 Django 앱 설정에서 task를 자동으로 로드
app.autodiscover_tasks()

# Story 2.10: Celery Beat 스케줄 설정
app.conf.beat_schedule = {
    # 매시간 크롤링 성공률 체크 (AC-2.10.3, AC-2.10.4)
    'check-crawl-success-rate-every-hour': {
        'task': 'accounts.tasks.check_crawl_success_rate',
        'schedule': crontab(minute=0),  # 매시 정각에 실행
        'options': {'expires': 3600},  # 1시간 후 만료 (중복 실행 방지)
    },
    # Story 5.1: 매일 자정 기간제 아이템 체크
    'check-expirable-items-daily': {
        'task': 'characters.tasks.check_expirable_items',
        'schedule': crontab(hour=0, minute=0),  # 매일 자정 (KST)
        'options': {'expires': 7200},  # 2시간 후 만료
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
