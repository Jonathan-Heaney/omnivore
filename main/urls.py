from django.urls import path
from django.contrib.auth.views import LoginView
from .forms import CustomAuthenticationForm
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('home/', views.home, name='home'),
    path('sign-up/', views.sign_up, name='sign_up'),
    path('login/', LoginView.as_view(
        authentication_form=CustomAuthenticationForm,
        template_name='registration/login.html'  # or keep default
    ), name='login'),
    path("logout/", views.LogOut, name="logout"),
    path("share-art/", views.share_art, name="share_art"),
    path("my-shared-art/", views.my_shared_art, name="my_shared_art"),
    path("my-received-art/", views.my_received_art, name="my_received_art"),
    path('edit-art-piece/<int:pk>', views.edit_art_piece, name='edit_art_piece'),
    path('delete-art-piece/<int:pk>',
         views.delete_art_piece, name='delete_art_piece'),
    path('toggle_like/<int:art_piece_id>/',
         views.toggle_like, name='toggle_like'),
    path('notifications/', views.notifications_view, name='notifications'),
    path('notification/<int:notification_id>/',
         views.notification_redirect, name='notification_redirect'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read,
         name='mark_all_notifications_read'),
    path('password_reset/', views.CustomPasswordResetView.as_view(template_name="registration/password_reset.html"),
         name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='registration/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'),
         name="password_reset_confirm"),
    path('reset/done/',
         auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name="password_reset_complete"),
    path('settings/', views.account_info_settings,
         name='account_info_settings'),
    path("settings/art-delivery/", views.art_delivery_settings,
         name="art_delivery_settings"),
    path('settings/email/', views.email_pref_settings,
         name='email_pref_settings'),
    path('settings/password/',
         views.password_settings, name='password_settings'),
    path("u/<str:token>/", views.unsubscribe_email, name="email_unsubscribe"),
]
