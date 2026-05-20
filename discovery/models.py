from django.db import models
from django.utils import timezone


class Repository(models.Model):
    github_id = models.BigIntegerField(unique=True)
    full_name = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    owner_login = models.CharField(max_length=255)
    owner_avatar = models.URLField(blank=True)
    description = models.TextField(blank=True)
    html_url = models.URLField()
    language = models.CharField(max_length=100, blank=True)
    stars = models.IntegerField(default=0)
    forks = models.IntegerField(default=0)
    watchers = models.IntegerField(default=0)
    open_issues = models.IntegerField(default=0)
    topics = models.JSONField(default=list, blank=True)
    homepage = models.URLField(blank=True)
    pushed_at = models.DateTimeField(null=True, blank=True)
    created_at_github = models.DateTimeField(null=True, blank=True)
    cached_at = models.DateTimeField(default=timezone.now)
    ai_summary = models.TextField(blank=True)
    ai_summary_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-stars"]
        indexes = [
            models.Index(fields=["language"]),
            models.Index(fields=["stars"]),
        ]

    def __str__(self):
        return self.full_name

    @property
    def stars_display(self):
        if self.stars >= 1000:
            return f"{self.stars / 1000:.1f}k"
        return str(self.stars)

    @property
    def is_stale(self):
        return (timezone.now() - self.cached_at).total_seconds() > 3600


class Bookmark(models.Model):
    repository = models.OneToOneField(
        Repository, on_delete=models.CASCADE, related_name="bookmark"
    )
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Bookmark: {self.repository.full_name}"
