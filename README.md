# 메이플스토리지 백엔드

Django REST Framework 기반 메이플스토리 캐릭터 정보 API 서버입니다.

## 📋 목차

- [기술 스택](#기술-스택)
- [프로젝트 구조](#프로젝트-구조)
- [설치 및 실행](#설치-및-실행)
- [환경 설정](#환경-설정)
- [API 엔드포인트](#api-엔드포인트)
- [아키텍처](#아키텍처)
- [개발 가이드](#개발-가이드)
- [테스트](#테스트)
- [알려진 이슈](#알려진-이슈)

## 기술 스택

### 코어 프레임워크
- **Django**: 5.1.4
- **Django REST Framework**: 3.15.2
- **Python**: 3.11+

### 인증 및 보안
- **djangorestframework-simplejwt**: 5.5.0 (JWT 인증)
- **django-cors-headers**: 4.6.0 (CORS 처리)

### 데이터 검증 및 처리
- **Pydantic**: 2.10.4 (스키마 검증)
- **requests**: 2.32.3 (외부 API 호출)

### 캐싱 및 비동기
- **Redis**: 5.2.1 (캐싱)
- **Celery**: 5.4.0 (비동기 작업)
- **aiohttp**: 3.11.14 (비동기 HTTP)

### 문서화
- **drf-yasg**: 1.21.10 (Swagger/OpenAPI)

### 데이터베이스
- **SQLite**: 개발 환경
- **PostgreSQL**: 프로덕션 권장 (psycopg2-binary)

## 프로젝트 구조

```
maplestorage_backend/
├── accounts/                    # 사용자 계정 관리
│   ├── models.py               # User, UserProfile 모델
│   ├── views.py                # 인증 관련 뷰 (Google OAuth)
│   ├── serializers.py          # 사용자 시리얼라이저
│   ├── schemas.py              # Pydantic 스키마 (Google OAuth)
│   └── tests.py                # 인증 테스트 (7 tests)
│
├── characters/                  # 캐릭터 정보 API
│   ├── models.py               # 캐릭터 데이터 모델 (87KB, 20+ 모델)
│   ├── views.py                # API 뷰 (38KB, 20+ 엔드포인트)
│   ├── serializers.py          # DRF 시리얼라이저
│   ├── services.py             # 비즈니스 로직 (메이플 API 클라이언트)
│   ├── schemas.py              # Pydantic 스키마 검증
│   ├── mixins.py               # 재사용 가능한 믹스인
│   ├── exceptions.py           # 커스텀 예외 클래스
│   ├── utils.py                # 유틸리티 함수
│   ├── urls.py                 # URL 라우팅
│   └── tests/                  # 테스트 파일
│
├── define/                      # 상수 및 설정
│   └── define.py               # API URL, 상수 정의
│
├── util/                        # 공통 유틸리티
│   ├── redis_client.py         # Redis 클라이언트
│   ├── rate_limiter.py         # API Rate Limiting
│   └── util.py                 # 기타 유틸리티
│
├── maplestorage_backend/        # Django 프로젝트 설정
│   ├── settings.py             # 메인 설정 파일
│   ├── urls.py                 # 루트 URL 설정
│   ├── wsgi.py                 # WSGI 설정
│   ├── asgi.py                 # ASGI 설정
│   └── celery.py               # Celery 설정
│
├── logs/                        # 로그 파일
│   └── maple_api.log           # API 호출 로그
│
├── manage.py                    # Django 관리 명령
├── requirements.txt             # 의존성 목록
├── pyproject.toml              # 프로젝트 메타데이터
├── pytest.ini                  # pytest 설정
├── .env                        # 환경 변수 (git에서 제외)
├── todo.md                     # 개선 계획
├── possible_bug.md             # 알려진 버그
└── issue.md                    # 이슈 목록
```

## 설치 및 실행

> **⚠️ 중요**: 이 프로젝트는 **`uv`** 패키지 매니저를 사용합니다.
> `pip` 대신 `uv`를 사용하여 의존성 관리, 테스트 실행, 서버 구동을 수행하세요.

### 0. uv 설치 (최초 1회)

```bash
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

설치 확인:
```bash
uv --version
```

### 1. 의존성 설치

```bash
# uv를 사용한 의존성 자동 설치 (가상환경도 자동 생성)
uv sync
```

### 2. 데이터베이스 마이그레이션

```bash
# uv run을 사용하여 Django 명령 실행
uv run python manage.py migrate
```

### 3. 슈퍼유저 생성 (선택사항)

```bash
uv run python manage.py createsuperuser
```

### 4. 개발 서버 실행

```bash
uv run python manage.py runserver
```

서버가 `http://localhost:8000`에서 실행됩니다.

### 6. Redis 서버 실행 (캐싱용)

```bash
# 별도 터미널에서 실행
redis-server
```

### 7. Celery Worker 실행 (선택사항)

```bash
# 별도 터미널에서 실행
celery -A maplestorage_backend worker -l info
```

## 환경 설정

`.env` 파일을 프로젝트 루트에 생성하고 다음 변수를 설정하세요:

```env
# Django 설정
SECRET_KEY=your-django-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# 메이플스토리 API
MAPLESTORY_API_KEY=your-nexon-api-key-here

# 데이터베이스 (PostgreSQL 사용시)
DB_ENGINE=django.db.backends.postgresql
DB_NAME=maplestorage
DB_USER=postgres
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000

# JWT
ACCESS_TOKEN_LIFETIME_HOURS=1
REFRESH_TOKEN_LIFETIME_DAYS=7
```

### 넥슨 오픈 API 키 발급

1. [넥슨 오픈 API](https://openapi.nexon.com/) 사이트 접속
2. 회원가입 및 로그인
3. API 키 발급 신청
4. 발급받은 API 키를 `.env` 파일에 추가

## API 엔드포인트

### Swagger 문서

- **Swagger UI**: http://localhost:8000/swagger/
- **ReDoc**: http://localhost:8000/redoc/
- **JSON Schema**: http://localhost:8000/swagger.json

### 인증 (Authentication)

#### 사용자 등록
```http
POST /api/register/
Content-Type: application/json

{
  "username": "testuser",
  "password": "Test1234!",
  "password2": "Test1234!",
  "email": "test@example.com",
  "first_name": "Test",
  "last_name": "User"
}
```

#### JWT 토큰 발급
```http
POST /api/token/
Content-Type: application/json

{
  "username": "testuser",
  "password": "Test1234!"
}

# 응답
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

#### 토큰 갱신
```http
POST /api/token/refresh/
Content-Type: application/json

{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

#### 토큰 검증
```http
POST /api/token/verify/
Content-Type: application/json

{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

#### Google OAuth 로그인
```http
POST /api/auth/google/
Content-Type: application/json

{
  "access_token": "ya29.a0AfH6SMBx..."
}

# 응답
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": 1,
    "username": "user123",
    "email": "user@gmail.com",
    "display_name": "User Name",
    "notification_enabled": true
  }
}
```

**프로세스:**
1. Frontend에서 Google OAuth로 access_token 획득
2. access_token을 Backend에 전송
3. Backend에서 Google API로 토큰 검증
4. google_id 기반으로 User 조회 또는 생성
5. JWT 토큰 발급 및 반환

### 캐릭터 정보 (Characters)

모든 캐릭터 엔드포인트는 선택적으로 `date` 쿼리 파라미터를 지원합니다:
- 형식: `YYYY-MM-DD`
- 예시: `?date=2024-03-20`
- 미지정시 최신 데이터 조회

#### OCID 조회
```http
GET /characters/id/?character_name=캐릭터명
Authorization: Bearer {access_token}

# 응답
{
  "ocid": "abc123def456..."
}
```

#### 캐릭터 기본 정보
```http
GET /characters/{ocid}/basic/?date=2024-03-20
Authorization: Bearer {access_token}

# 응답
{
  "character_name": "캐릭터명",
  "world_name": "리부트",
  "character_gender": "남",
  "character_class": "히어로",
  "character_level": 250,
  "character_exp": 12345678,
  "character_guild_name": "길드명",
  ...
}
```

#### 전체 엔드포인트 목록

| 엔드포인트 | 설명 |
|-----------|------|
| `GET /characters/id/` | OCID 조회 |
| `GET /characters/{ocid}/basic/` | 기본 정보 |
| `GET /characters/{ocid}/popularity/` | 인기도 |
| `GET /characters/{ocid}/stat/` | 종합 스탯 |
| `GET /characters/{ocid}/ability/` | 어빌리티 |
| `GET /characters/{ocid}/item-equipment/` | 장착 장비 |
| `GET /characters/{ocid}/skill/` | 스킬 정보 |
| `GET /characters/{ocid}/hexamatrix/` | 헥사 매트릭스 |
| `GET /characters/all/` | 모든 정보 통합 조회 |

## 아키텍처

### 계층 구조 (Layered Architecture)

```
Client Request → Views → Serializers → Services → Models → Database
```

### 캐싱 전략

1. **1시간 캐싱**: 최신 데이터 1시간 동안 캐시
2. **Redis 사용**: 빠른 조회를 위한 캐시 스토어
3. **선택적 강제 새로고침**: `force_refresh` 파라미터

## 개발 가이드

### 개선 계획

자세한 개선 계획은 [todo.md](todo.md)를 참조하세요:

**완료된 항목**:
- [x] JWT 인증 구현
- [x] 비즈니스 로직 서비스 레이어 분리
- [x] 커스텀 예외 처리 시스템

**진행 예정**:
- [ ] SQLite → PostgreSQL 마이그레이션
- [ ] 비동기 API 호출
- [ ] 단위 테스트 확장

## 테스트

> **⚠️ 중요**: 모든 테스트는 **`uv run`**을 통해 실행해야 합니다.

```bash
# 전체 테스트 실행
uv run python manage.py test

# 특정 앱 테스트
uv run python manage.py test accounts
uv run python manage.py test characters

# 특정 테스트 클래스 실행
uv run python manage.py test accounts.tests.GoogleLoginViewTest

# 특정 테스트 메서드 실행
uv run python manage.py test accounts.tests.GoogleLoginViewTest.test_google_login_success

# 상세 출력 (verbosity 2)
uv run python manage.py test --verbosity=2

# pytest 사용 (선택사항)
uv run pytest

# 커버리지 확인
uv run pytest --cov=characters --cov=accounts
```

### 테스트 환경 설정

테스트 실행 시 자동으로 테스트 데이터베이스가 생성되고 마이그레이션이 적용됩니다. Celery 작업은 `CELERY_TASK_ALWAYS_EAGER=True` 설정으로 동기적으로 실행됩니다.

## 알려진 이슈

자세한 이슈 목록:
- [possible_bug.md](possible_bug.md) - 잠재적 버그
- [issue.md](issue.md) - 현재 이슈

## 문서

- **전체 프로젝트**: [../README.md](../README.md)
- **프론트엔드**: [../maplestorage_frontend/README.md](../maplestorage_frontend/README.md)

## 라이선스

MIT License
