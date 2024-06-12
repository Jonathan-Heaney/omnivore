from django.urls import path
from . import views

urlpatterns = [
    path('how-it-works', views.how_it_works, name='how_it_works'),
    path('faq', views.faq, name='faq'),
    path('submission-guidelines', views.submission_guidelines,
         name='submission_guidelines'),
]
