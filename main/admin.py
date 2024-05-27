from django.contrib import admin
from .models import ArtPiece, SentArtPiece


class ArtPieceAdmin(admin.ModelAdmin):
    list_filter = ("user", "approved_status")
    list_display = ("piece_name", "artist_name", "link",
                    "approved_status", "created_at")


admin.site.register(ArtPiece, ArtPieceAdmin)
admin.site.register(SentArtPiece)
