from django.urls import path

from .views import ItemCreateView, ItemDetailView, ItemListView

app_name = 'catalog'
urlpatterns = [
    path('', ItemListView.as_view(), name='list'),
    path('nuevo/', ItemCreateView.as_view(), name='create'),
    path('<int:pk>/', ItemDetailView.as_view(), name='detail'),
]
