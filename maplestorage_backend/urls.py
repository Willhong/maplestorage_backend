from django.contrib import admin
from django.urls import path, include
# maplestory_app은 여러분의 앱 이름에 맞게 변경하세요
from test.views import sampleview
from accounts.views import APIKeyView, AccountListView
from rest_framework.authtoken.views import obtain_auth_token
from characters.views import CharacterBasicView
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api-key/', APIKeyView.as_view(), name='api-key'),
    path('test/', sampleview),
    path('api-token-auth/', obtain_auth_token, name='api_token_auth'),
    path('accounts/', AccountListView.as_view(), name='account-list'),
    path('characters/basic/', CharacterBasicView.as_view(), name='character-basic'),


]


# from django.urls import path
# from .views import APIKeyView, AccountListView

# urlpatterns = [
#     path('api-key/', APIKeyView.as_view(), name='api-key'),
# ]
