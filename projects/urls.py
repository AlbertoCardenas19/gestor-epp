from django.urls import path

from .views import DeliveryDataView, HomeView, ProjectCreateView, ProjectDetailView, ProjectInfoView, ProjectListView, ProjectUpdateView

app_name = 'projects'
urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('proyectos/', ProjectListView.as_view(), name='list'),
    path('proyectos/nuevo/', ProjectCreateView.as_view(), name='create'),
    path('proyectos/<int:pk>/editar/', ProjectUpdateView.as_view(), name='update'),
    path('proyectos/<int:pk>/entregas/datos/', DeliveryDataView.as_view(), name='delivery-data'),
    path('proyectos/<int:pk>/informacion/', ProjectInfoView.as_view(), name='info'),
    path('proyectos/<int:pk>/', ProjectDetailView.as_view(), name='detail'),
]
