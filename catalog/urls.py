from django.urls import path

from .views import ItemDataView, ItemCreateView, ItemDetailView, ItemListView

app_name = 'catalog'
urlpatterns = [
    path('', ItemListView.as_view(), name='list'),
    path('datos/', ItemDataView.as_view(), name='data'),
    path('nuevo/', ItemCreateView.as_view(), name='create'),
    path('<int:pk>/', ItemDetailView.as_view(), name='detail'),
]
