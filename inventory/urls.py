from django.urls import path

from .models import StockRecord
from .views import CorrectionView, HistoryView, InventoryListView, RecordCreateView

app_name = 'inventory'
urlpatterns = [
    path('', InventoryListView.as_view(), name='list'),
    path('elementos/<int:item_pk>/', HistoryView.as_view(), name='history'),
    path('elementos/<int:item_pk>/apertura/', RecordCreateView.as_view(), name='open'),
    path('elementos/<int:item_pk>/entrada/', RecordCreateView.as_view(operation=StockRecord.Operation.RECEIPT), name='receive'),
    path('elementos/<int:item_pk>/registros/<int:record_pk>/corregir/', CorrectionView.as_view(), name='correct'),
]
