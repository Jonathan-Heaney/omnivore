from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('home', views.home, name='home'),
    path('sign-up', views.sign_up, name='sign_up'),
    path("logout/", views.LogOut, name="logout"),
    path("share-art", views.share_art, name="share_art"),
    path("my-shared-art", views.my_shared_art, name="my_shared_art"),
    path('send-test-email/', views.send_test_email, name='send_test_email'),
]
