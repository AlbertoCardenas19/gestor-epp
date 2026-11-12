from django.urls import path

from .views import HomeView, ProjectCreateView, ProjectDetailView, ProjectListView

app_name = 'projects'
urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('proyectos/', ProjectListView.as_view(), name='list'),
    path('proyectos/nuevo/', ProjectCreateView.as_view(), name='create'),
    path('proyectos/<int:pk>/', ProjectDetailView.as_view(), name='detail'),
]
