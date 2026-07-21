from django.urls import path
from . import views

urlpatterns = [
    path('', views.upload_resume, name='upload_resume'),
    path('update-prediction/', views.update_prediction, name='update_prediction'),
]