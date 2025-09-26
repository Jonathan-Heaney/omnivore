from django.contrib import admin
from .models import BlogPost


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ("title", "published", "created_at")
    prepopulated_fields = {"slug": ("title",)}

    class Media:
        css = {
            "all": ("css/admin_overrides.css",)
        }
