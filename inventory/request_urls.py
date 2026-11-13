from django.urls import path
from .request_views import RequestActionView, RequestCreateView, RequestDataView, RequestDetailView, RequestListView

from .selector import RequestItemSelectorView

app_name = 'requests'
urlpatterns = [
    path('', RequestListView.as_view(), name='list'),
    path('datos/', RequestDataView.as_view(), name='data'),
    path('nueva/elementos/', RequestItemSelectorView.as_view(), name='items'),
    path('nueva/', RequestCreateView.as_view(), name='create'),
    path('<int:request_pk>/', RequestDetailView.as_view(), name='detail'),
    path('<int:request_pk>/reservar/', RequestActionView.as_view(action='reserve'), name='reserve'),
    path('<int:request_pk>/entregar/', RequestActionView.as_view(action='deliver'), name='deliver'),
    path('<int:request_pk>/reducir/', RequestActionView.as_view(action='reduce'), name='reduce'),
]
