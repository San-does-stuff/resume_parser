from django.urls import path
from . import views

urlpatterns = [
    path('api/parse-cv/', views.upload_resume, name='api_parse_cv'),
]