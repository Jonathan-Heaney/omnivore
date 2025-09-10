from django.urls import path
from . import views

urlpatterns = [
    path('submission-guidelines', views.submission_guidelines,
         name='submission_guidelines'),
]
