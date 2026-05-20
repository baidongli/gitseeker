from django.contrib import admin
from .models import Repository, Bookmark


@admin.register(Repository)
class RepositoryAdmin(admin.ModelAdmin):
    list_display = ["full_name", "language", "stars", "forks", "cached_at"]
    search_fields = ["full_name", "description"]
    list_filter = ["language"]


@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ["repository", "created_at"]
