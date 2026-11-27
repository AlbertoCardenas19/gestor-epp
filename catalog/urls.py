from django.urls import path, reverse_lazy
from django.views.generic import RedirectView

from .views import (CategoryCreateView, CategoryDataView, CategoryListView, ItemCreateView,
                    ItemDetailView, ItemUpdateView)

app_name = 'catalog'
urlpatterns = [
    path('', RedirectView.as_view(url=reverse_lazy('stock:list'), permanent=False), name='list'),
    path('nuevo/', ItemCreateView.as_view(), name='create'),
    path('categorias/', CategoryListView.as_view(), name='categories'),
    path('categorias/datos/', CategoryDataView.as_view(), name='category-data'),
    path('categorias/nueva/', CategoryCreateView.as_view(), name='category-create'),
    path('<int:pk>/editar/', ItemUpdateView.as_view(), name='update'),
    path('<int:pk>/', ItemDetailView.as_view(), name='detail'),
]
