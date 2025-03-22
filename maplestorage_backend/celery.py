import os
from celery import Celery

# Django 설정 모듈을 Celery의 기본 설정으로 지정
os.environ.setdefault('DJANGO_SETTINGS_MODULE',
                      'maplestorage_backend.settings')

app = Celery('maplestorage_backend')

# namespace='CELERY'는 모든 Celery 관련 설정 키가 'CELERY_' 로 시작해야 함을 의미
app.config_from_object('django.conf:settings', namespace='CELERY')

# 등록된 Django 앱 설정에서 task를 자동으로 로드
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
