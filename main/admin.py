from django.contrib import admin
from .models import ArtPiece, SentArtPiece, CustomUser


class ArtPieceAdmin(admin.ModelAdmin):
    list_filter = ("user", "approved_status")
    list_display = ("piece_name", "artist_name", "link",
                    "approved_status", "created_at")


class CustomUserAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "username", "email")


admin.site.register(ArtPiece, ArtPieceAdmin)
admin.site.register(SentArtPiece)
admin.site.register(CustomUser, CustomUserAdmin)
