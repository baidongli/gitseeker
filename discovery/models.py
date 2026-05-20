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
    readme_summary = models.TextField(blank=True)

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
    tags = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Bookmark: {self.repository.full_name}"


class Setting(models.Model):
    key = models.CharField(max_length=64, unique=True)
    value = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.key}"

    @classmethod
    def get(cls, key, default=""):
        try:
            return cls.objects.get(key=key).value
        except cls.DoesNotExist:
            return default

    @classmethod
    def set(cls, key, value):
        cls.objects.update_or_create(key=key, defaults={"value": value})


class AwesomeList(models.Model):
    full_name = models.CharField(max_length=255, unique=True)
    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    sections = models.JSONField(default=list, blank=True)
    items_count = models.IntegerField(default=0)
    last_fetched = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["full_name"]

    def __str__(self):
        return self.full_name

    @property
    def owner(self):
        return self.full_name.split("/")[0] if "/" in self.full_name else self.full_name

    @property
    def name(self):
        return self.full_name.split("/")[1] if "/" in self.full_name else ""


class StarSnapshot(models.Model):
    repository = models.ForeignKey(
        Repository, on_delete=models.CASCADE, related_name="snapshots"
    )
    stars = models.IntegerField()
    captured_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-captured_at"]
        indexes = [models.Index(fields=["repository", "captured_at"])]


class TopicTrend(models.Model):
    topic = models.CharField(max_length=100, unique=True)
    this_month_count = models.IntegerField(default=0)
    last_month_count = models.IntegerField(default=0)
    growth_pct = models.FloatField(default=0.0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-growth_pct"]
