from django.urls import path
from . import views

urlpatterns = [
    path('id/', views.CharacterIdView.as_view(), name='character-id'),
    path('<str:ocid>/basic/', views.CharacterBasicView.as_view(),
         name='character-basic'),
    path('<str:ocid>/popularity/', views.CharacterPopularityView.as_view(),
         name='character-popularity'),
    path('<str:ocid>/stat/', views.CharacterStatView.as_view(),
         name='character-stat'),
    path('<str:ocid>/ability/', views.CharacterAbilityView.as_view(),
         name='character-ability'),
    path('<str:ocid>/item-equipment/', views.CharacterItemEquipmentView.as_view(),
         name='character-item-equipment'),
    path('<str:ocid>/cashitem-equipment/', views.CharacterCashItemEquipmentView.as_view(),
         name='character-cashitem-equipment'),
    path('<str:ocid>/symbol/', views.CharacterSymbolView.as_view(),
         name='character-symbol'),
    path('<str:ocid>/link-skill/', views.CharacterLinkSkillView.as_view(),
         name='character-link-skill'),
    path('<str:ocid>/skill/', views.CharacterSkillView.as_view(),
         name='character-skill'),
    path('<str:ocid>/hexamatrix/', views.CharacterHexaMatrixView.as_view(),
         name='character-hexamatrix'),
    path('<str:ocid>/hexamatrix-stat/', views.CharacterHexaMatrixStatView.as_view(),
         name='character-hexamatrix-stat'),
    path('<str:ocid>/vmatrix/', views.CharacterVMatrixView.as_view(),
         name='character-vmatrix'),
    path('<str:ocid>/dojang/', views.CharacterDojangView.as_view(),
         name='character-dojang'),
    path('<str:ocid>/set-effect/', views.CharacterSetEffectView.as_view(),
         name='character-set-effect'),
    path('<str:ocid>/beauty-equipment/', views.CharacterBeautyEquipmentView.as_view(),
         name='character-beauty-equipment'),
    path('<str:ocid>/android-equipment/', views.CharacterAndroidEquipmentView.as_view(),
         name='character-android-equipment'),
    path('<str:ocid>/pet-equipment/', views.CharacterPetEquipmentView.as_view(),
         name='character-pet-equipment'),
    path('<str:ocid>/propensity/', views.CharacterPropensityView.as_view(),
         name='character-propensity'),
    path('<str:ocid>/hyper-stat/', views.CharacterHyperStatView.as_view(),
         name='character-hyper-stat'),
    path('all/', views.CharacterAllDataView.as_view(),
         name='character-all-data'),
    path('redis-health/', views.RedisHealthCheckView.as_view(), name='redis-health'),
    # Story 3.4: 인벤토리 목록 조회 API
    path('<str:ocid>/inventory/', views.InventoryListView.as_view(), name='inventory-list'),
    # Story 3.6: 창고 목록 조회 API (계정 공유)
    path('<str:ocid>/storage/', views.StorageListView.as_view(), name='storage-list'),
    # Story 3.5.3: 아이템 상세 정보 조회 API
    path('inventory/<int:item_id>/detail/', views.ItemDetailView.as_view(), name='item-detail'),
    # Story 4.1: 통합 아이템 검색 API
    path('search/items/', views.ItemSearchView.as_view(), name='item-search'),
    # Story 4.3: 메소 요약 API
    path('meso/summary/', views.MesoSummaryView.as_view(), name='meso-summary'),
    # Story 5.6: 대시보드 통계 API
    path('dashboard/stats/', views.DashboardStatsView.as_view(), name='dashboard-stats'),
    # Story 5.1/5.4: 만료 예정 아이템 목록 API
    path('dashboard/expiring-items/', views.ExpiringItemsView.as_view(), name='expiring-items'),
]
