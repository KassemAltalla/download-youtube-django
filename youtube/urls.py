from django.urls import path
from . import views

from youtube.views import download_video, get_download_status, download_file

urlpatterns = [
    path('download/', views.download_video, name='download_video'),
    path('download_video/', download_video, name='download_video'),
    path('download_status/<str:task_id>/', get_download_status, name='download_status'),
    path('download_file/<str:task_id>/', download_file, name='download_file'),
]
