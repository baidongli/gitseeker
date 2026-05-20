from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils import timezone

from .models import Repository, Bookmark
from . import github_api


LANGUAGES = [
    "Python", "JavaScript", "TypeScript", "Go", "Rust",
    "Java", "C++", "C", "Swift", "Kotlin", "Ruby", "PHP",
]

TOPICS = [
    ("machine-learning", "机器学习"),
    ("web", "Web 开发"),
    ("cli", "命令行工具"),
    ("game", "游戏"),
    ("security", "安全"),
    ("database", "数据库"),
    ("devops", "DevOps"),
    ("mobile", "移动开发"),
]


def _upsert_repos(items):
    repos = []
    for item in items:
        repo, _ = Repository.objects.update_or_create(
            github_id=item["github_id"],
            defaults={**item, "cached_at": timezone.now()},
        )
        repos.append(repo)
    return repos


def index(request):
    language = request.GET.get("lang", "")
    since = request.GET.get("since", "weekly")

    result = github_api.get_trending(language=language or None, since=since)
    repos = _upsert_repos(result.get("items", []))
    error = result.get("error")

    bookmarked_ids = set(
        Bookmark.objects.values_list("repository_id", flat=True)
    )

    return render(request, "discovery/index.html", {
        "repos": repos,
        "languages": LANGUAGES,
        "selected_lang": language,
        "since": since,
        "bookmarked_ids": bookmarked_ids,
        "error": error,
    })


def search(request):
    query = request.GET.get("q", "").strip()
    language = request.GET.get("lang", "")
    sort = request.GET.get("sort", "stars")
    page = int(request.GET.get("page", 1))

    repos = []
    total = 0
    error = None

    if query:
        result = github_api.search_repos(
            query=query,
            language=language or None,
            sort=sort,
            per_page=20,
            page=page,
        )
        repos = _upsert_repos(result.get("items", []))
        total = result.get("total_count", 0)
        error = result.get("error")

    bookmarked_ids = set(
        Bookmark.objects.values_list("repository_id", flat=True)
    )

    has_next = total > page * 20
    has_prev = page > 1

    return render(request, "discovery/search.html", {
        "repos": repos,
        "query": query,
        "languages": LANGUAGES,
        "selected_lang": language,
        "sort": sort,
        "total": total,
        "page": page,
        "has_next": has_next,
        "has_prev": has_prev,
        "bookmarked_ids": bookmarked_ids,
        "error": error,
    })


def explore(request):
    topic_key = request.GET.get("topic", "")
    language = request.GET.get("lang", "")

    query = topic_key if topic_key else "stars:>1000"
    result = github_api.search_repos(
        query=query,
        language=language or None,
        sort="stars",
        per_page=24,
    )
    repos = _upsert_repos(result.get("items", []))
    error = result.get("error")

    bookmarked_ids = set(
        Bookmark.objects.values_list("repository_id", flat=True)
    )

    return render(request, "discovery/explore.html", {
        "repos": repos,
        "topics": TOPICS,
        "selected_topic": topic_key,
        "languages": LANGUAGES,
        "selected_lang": language,
        "bookmarked_ids": bookmarked_ids,
        "error": error,
    })


def bookmarks(request):
    bms = Bookmark.objects.select_related("repository").all()
    bookmarked_ids = set(bm.repository_id for bm in bms)
    return render(request, "discovery/bookmarks.html", {
        "bookmarks": bms,
        "bookmarked_ids": bookmarked_ids,
    })


@require_POST
def toggle_bookmark(request, repo_id):
    repo = get_object_or_404(Repository, id=repo_id)
    bm, created = Bookmark.objects.get_or_create(repository=repo)
    if not created:
        bm.delete()
        bookmarked = False
    else:
        bookmarked = True

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"bookmarked": bookmarked})

    return redirect(request.META.get("HTTP_REFERER", "/"))


@require_POST
def delete_bookmark(request, repo_id):
    repo = get_object_or_404(Repository, id=repo_id)
    Bookmark.objects.filter(repository=repo).delete()
    return redirect("bookmarks")
