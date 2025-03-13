# 메이플스토리 백엔드 개선 Todo 리스트

## 보안 개선
- [x] API 키를 하드코딩에서 환경 변수로 이동
  ```python
  # 현재 (define/define.py)
  APIKEY = "test_4468fa7dc351c4fc07584a17f0b664d4ef5267515c18bc96e3db4c225b7f8789cb6dfb7e3b98213ec2b17da60c255a43"
  
  # 개선 방향
  import os
  from dotenv import load_dotenv
  
  load_dotenv()
  APIKEY = os.getenv("MAPLESTORY_API_KEY")
  ```
- [x] `SECRET_KEY` 환경 변수로 이동
- [ ] HTTPS 적용 및 보안 헤더 설정
- [x] 인증 시스템 강화 (JWT 도입 고려)

## 데이터베이스 최적화
- [ ] SQLite에서 PostgreSQL로 마이그레이션
  ```python
  # settings.py 수정
  DATABASES = {
      'default': {
          'ENGINE': 'django.db.backends.postgresql',
          'NAME': os.getenv('DB_NAME'),
          'USER': os.getenv('DB_USER'),
          'PASSWORD': os.getenv('DB_PASSWORD'),
          'HOST': os.getenv('DB_HOST', 'localhost'),
          'PORT': os.getenv('DB_PORT', '5432'),
      }
  }
  ```
- [ ] 데이터베이스 인덱스 최적화
- [ ] 쿼리 성능 개선 (select_related, prefetch_related 활용)

## 코드 구조 개선
- [x] 긴 뷰 함수 리팩토링 (characters/views.py - 867줄)
- [x] 공통 로직 추출 및 믹스인 활용
  ```python
  class MapleAPIClientMixin:
      def get_api_data(self, url, params=None):
          headers = {"accept": "application/json", "x-nxopen-api-key": APIKEY}
          response = requests.get(url, headers=headers, params=params)
          response.raise_for_status()
          return response.json()
  ```
- [x] 비즈니스 로직을 서비스 레이어로 분리
- [x] 일관된 예외 처리 패턴 적용
  ```python
  # 커스텀 예외 클래스 정의
  class MapleAPIError(Exception):
      status_code = status.HTTP_503_SERVICE_UNAVAILABLE
      default_message = "메이플스토리 API 호출 중 오류가 발생했습니다."
      
      def __init__(self, message=None, status_code=None, detail=None):
          self.message = message or self.default_message
          self.status_code = status_code or self.status_code
          self.detail = detail
          super().__init__(self.message)
  
  # 데코레이터를 활용한 예외 처리
  @handle_api_exception
  def get_ocid(character_name):
      # API 호출 로직
      pass
  
  # 뷰에서의 예외 처리
  try:
      # 비즈니스 로직
      pass
  except (InvalidParameterError, CharacterNotFoundError) as e:
      return Response({"error": e.message}, status=e.status_code)
  ```

## 성능 최적화
- [ ] 비동기 API 호출 구현 (aiohttp 활용)
  ```python
  import aiohttp
  import asyncio
  
  async def fetch_character_data(session, url, headers):
      async with session.get(url, headers=headers) as response:
          return await response.json()
          
  async def get_all_character_data(ocid):
      headers = {"accept": "application/json", "x-nxopen-api-key": APIKEY}
      async with aiohttp.ClientSession() as session:
          tasks = [
              fetch_character_data(session, f"{CHARACTER_BASIC_URL}?ocid={ocid}", headers),
              fetch_character_data(session, f"{CHARACTER_STAT_URL}?ocid={ocid}", headers),
              # 기타 API 엔드포인트
          ]
          return await asyncio.gather(*tasks)
  ```
- [ ] 캐싱 전략 개선 (Redis 도입)
  ```python
  # settings.py
  CACHES = {
      "default": {
          "BACKEND": "django_redis.cache.RedisCache",
          "LOCATION": "redis://127.0.0.1:6379/1",
          "OPTIONS": {
              "CLIENT_CLASS": "django_redis.client.DefaultClient",
          }
      }
  }
  ```
- [ ] 페이지네이션 구현

## 테스트 강화
- [ ] 단위 테스트 확장
- [ ] 통합 테스트 추가
- [ ] API 엔드포인트 테스트 자동화
  ```python
  from rest_framework.test import APITestCase
  
  class CharacterAPITests(APITestCase):
      def setUp(self):
          # 테스트 데이터 설정
          
      def test_character_basic_view(self):
          url = reverse('character-basic')
          response = self.client.get(url)
          self.assertEqual(response.status_code, status.HTTP_200_OK)
  ```
- [ ] 모의 객체(Mock)를 활용한 외부 API 테스트

## 문서화
- [ ] API 문서 자동화 (drf-yasg 또는 drf-spectacular 활용)
  ```python
  # settings.py에 추가
  INSTALLED_APPS += ['drf_yasg']
  
  # urls.py에 추가
  from drf_yasg.views import get_schema_view
  from drf_yasg import openapi
  
  schema_view = get_schema_view(
     openapi.Info(
        title="메이플스토리 API",
        default_version='v1',
        description="메이플스토리 캐릭터 정보 API",
     ),
     public=True,
  )
  
  urlpatterns += [
     path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
  ]
  ```
- [ ] 코드 주석 개선
- [ ] README 업데이트

## 에러 처리 개선
- [x] 일관된 예외 처리 시스템 구축
- [ ] 사용자 친화적인 에러 메시지
- [x] 로깅 시스템 강화
  ```python
  # settings.py
  LOGGING = {
      'version': 1,
      'disable_existing_loggers': False,
      'formatters': {
          'verbose': {
              'format': '{levelname} {asctime} {module} {message}',
              'style': '{',
          },
      },
      'handlers': {
          'file': {
              'level': 'ERROR',
              'class': 'logging.FileHandler',
              'filename': 'debug.log',
              'formatter': 'verbose',
          },
      },
      'loggers': {
          'django': {
              'handlers': ['file'],
              'level': 'ERROR',
              'propagate': True,
          },
      },
  }
  ```

## 배포 및 운영
- [ ] Docker 컨테이너화
  ```dockerfile
  FROM python:3.11-slim
  
  WORKDIR /app
  
  COPY requirements.txt .
  RUN pip install --no-cache-dir -r requirements.txt
  
  COPY . .
  
  CMD ["gunicorn", "maplestorage_backend.wsgi:application", "--bind", "0.0.0.0:8000"]
  ```
- [ ] CI/CD 파이프라인 구축
- [ ] 모니터링 시스템 도입 (Prometheus, Grafana)
- [ ] 백업 전략 수립
