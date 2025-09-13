from django.contrib import admin
from .models import ArtPiece, SentArtPiece, CustomUser, Comment, Like, Notification
from django.http import HttpResponse
import csv


@admin.action(description="Export emails (CSV)")
def export_emails_csv(modeladmin, request, queryset):
    # de-dupe + ignore blanks
    emails = (
        queryset
        .exclude(email__isnull=True)
        .exclude(email__exact="")
        .values_list("email", flat=True)
        .distinct()
    )

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="emails.csv"'
    writer = csv.writer(response)
    writer.writerow(["email"])
    for e in emails:
        writer.writerow([e])
    return response


class ArtPieceAdmin(admin.ModelAdmin):
    list_filter = ("user", "approved_status", "welcome_eligible", "is_deleted")
    list_display = ("piece_name", "artist_name", "link", "user",
                    "approved_status", "welcome_eligible", "welcome_weight", "is_deleted", "created_at")
    search_fields = ("piece_name", "artist_name",
                     "user__first_name", "user__last_name")

    list_editable = (
        "approved_status",
        "welcome_eligible",
        "welcome_weight",
    )

    actions = ["mark_as_welcome_eligible",
               "unmark_as_welcome_eligible", "export_emails_csv"]

    def mark_as_welcome_eligible(self, request, queryset):
        updated = queryset.update(welcome_eligible=True)
        self.message_user(
            request, f"{updated} piece(s) marked as welcome-eligible.")
    mark_as_welcome_eligible.short_description = "Mark selected as welcome-eligible"

    def unmark_as_welcome_eligible(self, request, queryset):
        updated = queryset.update(welcome_eligible=False)
        self.message_user(
            request, f"{updated} piece(s) unmarked as welcome-eligible.")
    unmark_as_welcome_eligible.short_description = "Unmark selected as welcome-eligible"


class CustomUserAdmin(admin.ModelAdmin):
    list_filter = ("date_joined", "last_login", "is_active", "is_staff")

    list_display = ("first_name",
                    "last_name", "email", "username", "receive_art_paused", "email_on_art_shared", "email_on_comment", "email_on_like", "date_joined", "last_login", "is_active")

    list_display_links = ("email",)

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

    list_editable = (
        "email_on_art_shared",
        "email_on_comment",
        "email_on_like",
        "receive_art_paused",
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
                   "art_piece", "is_read", "timestamp", "message")
    list_display = ("sender", "recipient", "notification_type",
                    "art_piece", "is_read", "timestamp", "message")


admin.site.register(ArtPiece, ArtPieceAdmin)
admin.site.register(SentArtPiece, SentArtPieceAdmin)
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Comment, CommentAdmin)
admin.site.register(Like, LikeAdmin)
admin.site.register(Notification, NotificationAdmin)
