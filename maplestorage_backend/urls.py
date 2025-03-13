from django.contrib import admin
from django.urls import path, include, re_path
# maplestory_app은 여러분의 앱 이름에 맞게 변경하세요
from test.views import sampleview
from accounts.views import APIKeyView, AccountListView, RegisterView, CustomTokenObtainPairView
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenVerifyView,
)
from characters.views import (
    CharacterBasicView, CharacterAbilityView, CharacterItemEquipmentView,
    CharacterCashItemEquipmentView, CharacterSymbolView, CharacterLinkSkillView,
    CharacterVMatrixView, CharacterHexaMatrixView, CharacterHexaStatView
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
    path('accounts/', AccountListView.as_view(), name='account-list'),
    path('characters/basic/', CharacterBasicView.as_view(), name='character-basic'),
    path('characters/ability/', CharacterAbilityView.as_view(),
         name='character-ability'),
    path('characters/item-equipment/', CharacterItemEquipmentView.as_view(),
         name='character-item-equipment'),
    path('characters/cashitem-equipment/', CharacterCashItemEquipmentView.as_view(),
         name='character-cashitem-equipment'),
    path('characters/symbol-equipment/',
         CharacterSymbolView.as_view(), name='character-symbol'),
    path('characters/link-skill/', CharacterLinkSkillView.as_view(),
         name='character-link-skill'),
    path('characters/skill/', CharacterVMatrixView.as_view(), name='character-skill'),
    path('characters/hexamatrix/', CharacterHexaMatrixView.as_view(),
         name='character-hexamatrix'),
    path('characters/hexamatrix-stat/', CharacterHexaStatView.as_view(),
         name='character-hexamatrix-stat'),

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
