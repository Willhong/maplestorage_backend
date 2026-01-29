from django.contrib import admin
from django.urls import path, include, re_path
# maplestory_app은 여러분의 앱 이름에 맞게 변경하세요
from test.views import sampleview
from accounts.views import (
    APIKeyView, AccountListView, RegisterView, CustomTokenObtainPairView,
    GoogleLoginView, UserProfileView, CharacterCreateView, CharacterDetailView,
    CrawlStartView, CrawlStatusView, CrawlStatsAdminView,
    LinkedCharactersView, BatchCharacterRegistrationView,  # Story 3.10
    NotificationSettingsView, TestNotificationView,  # Story 5.3
    NotificationListView, NotificationReadView, NotificationMarkAllReadView, NotificationDeleteView  # Story 5.5
)
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenVerifyView,
)
# Swagger 관련 import 추가
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# Swagger 스키마 뷰 설정
schema_view = get_schema_view(
    openapi.Info(
        title="Maple Storage API",
        default_version='v1',
        description="메이플스토리지 API 문서",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@maplestorage.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api-key/', APIKeyView.as_view(), name='api-key'),
    path('test/', sampleview),
    path('api-token-auth/', obtain_auth_token, name='api_token_auth'),
    path('api/token/', CustomTokenObtainPairView.as_view(),
         name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('api/register/', RegisterView.as_view(), name='register'),
    path('api/auth/google/', GoogleLoginView.as_view(), name='google-login'),
    path('api/users/me/', UserProfileView.as_view(), name='user-profile'),
    path('api/characters/', CharacterCreateView.as_view(), name='character-create'),
    path('api/characters/<int:pk>/', CharacterDetailView.as_view(), name='character-detail'),  # Story 3.2: 캐릭터 연결 해제
    path('api/characters/linked/', LinkedCharactersView.as_view(), name='linked-characters'),  # Story 3.10: 연동 캐릭터 조회
    path('api/characters/batch/', BatchCharacterRegistrationView.as_view(), name='batch-registration'),  # Story 3.10: 일괄 등록
    path('api/characters/<str:ocid>/crawl/', CrawlStartView.as_view(), name='crawl-start'),
    path('api/crawl-tasks/<str:task_id>/', CrawlStatusView.as_view(), name='crawl-status'),
    path('api/admin/crawl-stats/', CrawlStatsAdminView.as_view(), name='crawl-stats-admin'),  # Story 2.10
    path('api/settings/notifications/', NotificationSettingsView.as_view(), name='notification-settings'),  # Story 5.3
    path('api/notifications/test/', TestNotificationView.as_view(), name='test-notification'),  # Story 5.3
    path('api/notifications/', NotificationListView.as_view(), name='notification-list'),  # Story 5.5
    path('api/notifications/<int:pk>/read/', NotificationReadView.as_view(), name='notification-read'),  # Story 5.5
    path('api/notifications/mark-all-read/', NotificationMarkAllReadView.as_view(), name='notification-mark-all-read'),  # Story 5.5
    path('api/notifications/<int:pk>/', NotificationDeleteView.as_view(), name='notification-delete'),  # Story 5.5
    path('accounts/', AccountListView.as_view(), name='account-list'),
    path('characters/', include('characters.urls')),
    # Swagger UI URL 추가
    re_path(r'^swagger(?P<format>\.json|\.yaml)$',
            schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger',
         cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc',
         cache_timeout=0), name='schema-redoc'),
]


# from django.urls import path
# from .views import APIKeyView, AccountListView

# urlpatterns = [
#     path('api-key/', APIKeyView.as_view(), name='api-key'),
# ]
