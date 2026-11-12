from django.urls import path
from django.views.generic import RedirectView

from .views import ProjectCreateView, ProjectDetailView, ProjectListView

app_name = 'projects'
urlpatterns = [
    path('', RedirectView.as_view(pattern_name='projects:list', permanent=False)),
    path('proyectos/', ProjectListView.as_view(), name='list'),
    path('proyectos/nuevo/', ProjectCreateView.as_view(), name='create'),
    path('proyectos/<int:pk>/', ProjectDetailView.as_view(), name='detail'),
]
