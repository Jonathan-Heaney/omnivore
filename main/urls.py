from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('home', views.home, name='home'),
    path('sign-up', views.sign_up, name='sign_up'),
    path("logout/", views.LogOut, name="logout"),
    path("share-art", views.share_art, name="share_art")
]
