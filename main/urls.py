from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('home', views.home, name='home'),
    path('sign-up', views.sign_up, name='sign_up'),
    path("logout/", views.LogOut, name="logout"),
    path("share-art", views.share_art, name="share_art"),
    path("my-shared-art", views.my_shared_art, name="my_shared_art"),
    path("my-received-art", views.my_received_art, name="my_received_art"),
    path('edit-art-piece/<int:pk>', views.edit_art_piece, name='edit_art_piece'),
    path('delete-art-piece/<int:pk>',
         views.delete_art_piece, name='delete_art_piece'),
]
