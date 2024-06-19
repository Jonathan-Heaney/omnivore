from django.contrib import admin
from .models import ArtPiece, SentArtPiece, CustomUser


class ArtPieceAdmin(admin.ModelAdmin):
    list_filter = ("user", "approved_status")
    list_display = ("piece_name", "artist_name", "link", "user",
                    "approved_status", "created_at")


class CustomUserAdmin(admin.ModelAdmin):
    list_display = ("username", "first_name", "last_name", "email")

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


admin.site.register(ArtPiece, ArtPieceAdmin)
admin.site.register(SentArtPiece)
admin.site.register(CustomUser, CustomUserAdmin)
