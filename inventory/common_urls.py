from django.urls import path

from .common_views import (CommonCorrectionView, CommonHistoryDataView, CommonHistoryView,
                           CommonInventoryDataView, CommonInventoryView, CommonReceiptView, CommonRecordView, ItemProjectsDataView)

from catalog.views import ItemCreateView, ItemDetailView

app_name = 'stock'
urlpatterns = [
    path('', CommonInventoryView.as_view(), name='list'),
    path('nuevo/', ItemCreateView.as_view(), name='create'),
    path('elementos/<int:pk>/ficha/', ItemDetailView.as_view(), name='item'),
    path('elementos/<int:item_pk>/proyectos/datos/', ItemProjectsDataView.as_view(), name='item-projects-data'),
    path('datos/', CommonInventoryDataView.as_view(), name='data'),
    path('elementos/<int:item_pk>/', CommonHistoryView.as_view(), name='history'),
    path('elementos/<int:item_pk>/datos/', CommonHistoryDataView.as_view(), name='history-data'),
    path('elementos/<int:item_pk>/entrada/', CommonReceiptView.as_view(), name='receive'),
    path('elementos/<int:item_pk>/registros/<int:record_pk>/', CommonRecordView.as_view(), name='record'),
    path('elementos/<int:item_pk>/registros/<int:record_pk>/corregir/', CommonCorrectionView.as_view(), name='correct'),
]
