from django.urls import path

from .views import CategoryCreateView, ItemDataView, ItemCreateView, ItemDetailView, ItemListView, ItemUpdateView

app_name = 'catalog'
urlpatterns = [
    path('', ItemListView.as_view(), name='list'),
    path('datos/', ItemDataView.as_view(), name='data'),
    path('nuevo/', ItemCreateView.as_view(), name='create'),
    path('categorias/nueva/', CategoryCreateView.as_view(), name='category-create'),
    path('<int:pk>/editar/', ItemUpdateView.as_view(), name='update'),
    path('<int:pk>/', ItemDetailView.as_view(), name='detail'),
]
