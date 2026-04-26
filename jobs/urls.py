from django.urls import path

from . import views

urlpatterns = [
    path("recommendations/", views.recommended_jobs, name="recommended_jobs"),
]
