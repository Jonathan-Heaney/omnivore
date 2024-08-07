from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('home/', views.home, name='home'),
    path('redirect_fail/', views.redirect_fail, name='redirect_fail'),
    path('sign-up/', views.sign_up, name='sign_up'),
    path("logout/", views.LogOut, name="logout"),
    path("share-art/", views.share_art, name="share_art"),
    path("my-shared-art/", views.my_shared_art, name="my_shared_art"),
    path("my-received-art/", views.my_received_art, name="my_received_art"),
    path('edit-art-piece/<int:pk>', views.edit_art_piece, name='edit_art_piece'),
    path('delete-art-piece/<int:pk>',
         views.delete_art_piece, name='delete_art_piece'),
    path('password_reset/', views.CustomPasswordResetView.as_view(template_name="registration/password_reset.html"),
         name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='registration/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'),
         name="password_reset_confirm"),
    path('reset/done/',
         auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name="password_reset_complete"),
]
