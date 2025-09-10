from django.urls import path
from . import views

urlpatterns = [
    path('faq', views.faq, name='faq'),
    path('submission-guidelines', views.submission_guidelines,
         name='submission_guidelines'),
]
