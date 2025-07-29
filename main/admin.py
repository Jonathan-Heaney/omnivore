from django.contrib import admin
from .models import ArtPiece, SentArtPiece, CustomUser, Comment, Like, Notification


class ArtPieceAdmin(admin.ModelAdmin):
    list_filter = ("user", "approved_status")
    list_display = ("piece_name", "artist_name", "link", "user",
                    "approved_status", "created_at")


class CustomUserAdmin(admin.ModelAdmin):
    list_filter = ("date_joined", "last_login", "is_active", "is_staff")

    list_display = ("username", "first_name",
                    "last_name", "email", "date_joined", "last_login", "is_active")

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {'fields': ('is_active', 'is_staff',
         'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'email', 'first_name', 'last_name'),
        }),
    )


class SentArtPieceAdmin(admin.ModelAdmin):
    list_filter = ("user", "art_piece", "sent_time")
    list_display = ("user", "art_piece",
                    "art_piece_submitter", "sent_time")


class CommentAdmin(admin.ModelAdmin):
    list_filter = ("sender", "recipient", "art_piece",
                   "text", "parent_comment")
    list_display = ("sender", "recipient", "art_piece",
                    "text", "parent_comment", "created_at")


class LikeAdmin(admin.ModelAdmin):
    list_filter = ("user", "art_piece", "created_at")
    list_display = ("user", "art_piece", "created_at")


class NotificationAdmin(admin.ModelAdmin):
    list_filter = ("sender", "recipient", "notification_type",
                   "art_piece", "is_read", "timestamp")
    list_display = ("sender", "recipient", "notification_type",
                    "art_piece", "is_read", "timestamp")


admin.site.register(ArtPiece, ArtPieceAdmin)
admin.site.register(SentArtPiece, SentArtPieceAdmin)
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Comment, CommentAdmin)
admin.site.register(Like, LikeAdmin)
admin.site.register(Notification, NotificationAdmin)
