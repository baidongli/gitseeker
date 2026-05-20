import markdown as md
from collections import Counter
from datetime import datetime, timedelta, timezone as py_timezone
from django.db.models import Q
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils import timezone
from django.utils.safestring import mark_safe

from .models import Repository, Bookmark
from . import github_api


RECENT_VIEWS_MAX = 20


def _push_recent_view(request, repo_id):
    recent = request.session.get("recent_views", [])
    recent = [rid for rid in recent if rid != repo_id]
    recent.insert(0, repo_id)
    request.session["recent_views"] = recent[:RECENT_VIEWS_MAX]


def _get_recent_repos(request, limit=8):
    ids = request.session.get("recent_views", [])[:limit]
    if not ids:
        return []
    repos = {r.id: r for r in Repository.objects.filter(id__in=ids)}
    return [repos[i] for i in ids if i in repos]


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

    recent_repos = _get_recent_repos(request, limit=6)

    return render(request, "discovery/index.html", {
        "repos": repos,
        "languages": LANGUAGES,
        "selected_lang": language,
        "since": since,
        "bookmarked_ids": bookmarked_ids,
        "recent_repos": recent_repos,
        "error": error,
    })


LICENSES = [
    ("mit", "MIT"),
    ("apache-2.0", "Apache 2.0"),
    ("gpl-3.0", "GPL 3.0"),
    ("bsd-3-clause", "BSD 3-Clause"),
    ("bsd-2-clause", "BSD 2-Clause"),
    ("mpl-2.0", "MPL 2.0"),
    ("agpl-3.0", "AGPL 3.0"),
    ("unlicense", "Unlicense"),
]

PUSHED_WITHIN = [
    ("7", "最近 1 周"),
    ("30", "最近 1 个月"),
    ("90", "最近 3 个月"),
    ("365", "最近 1 年"),
]


def search(request):
    query = request.GET.get("q", "").strip()
    language = request.GET.get("lang", "")
    sort = request.GET.get("sort", "stars")
    page = int(request.GET.get("page", 1))

    min_stars = request.GET.get("min_stars", "").strip()
    license_key = request.GET.get("license", "").strip()
    pushed_within = request.GET.get("pushed_within", "").strip()
    exclude_archived = request.GET.get("exclude_archived") == "on"

    repos = []
    total = 0
    error = None

    if query:
        q = query
        if min_stars.isdigit():
            q += f" stars:>={min_stars}"
        if license_key:
            q += f" license:{license_key}"
        if pushed_within.isdigit():
            date_from = (datetime.now(tz=py_timezone.utc) - timedelta(days=int(pushed_within))).strftime("%Y-%m-%d")
            q += f" pushed:>{date_from}"
        if exclude_archived:
            q += " archived:false"

        result = github_api.search_repos(
            query=q,
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

    has_advanced = bool(min_stars or license_key or pushed_within or exclude_archived)

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
        "licenses": LICENSES,
        "pushed_within_options": PUSHED_WITHIN,
        "min_stars": min_stars,
        "license_key": license_key,
        "pushed_within": pushed_within,
        "exclude_archived": exclude_archived,
        "has_advanced": has_advanced,
    })


def gems(request):
    language = request.GET.get("lang", "")
    age = request.GET.get("age", "2")

    days_active = 30
    pushed_from = (datetime.now(tz=py_timezone.utc) - timedelta(days=days_active)).strftime("%Y-%m-%d")
    age_years = int(age) if age.isdigit() else 2
    created_from = (datetime.now(tz=py_timezone.utc) - timedelta(days=age_years * 365)).strftime("%Y-%m-%d")

    q = f"stars:200..3000 pushed:>{pushed_from} created:>{created_from} archived:false"

    result = github_api.search_repos(
        query=q,
        language=language or None,
        sort="stars",
        per_page=24,
    )
    repos = _upsert_repos(result.get("items", []))
    error = result.get("error")

    bookmarked_ids = set(
        Bookmark.objects.values_list("repository_id", flat=True)
    )

    return render(request, "discovery/gems.html", {
        "repos": repos,
        "languages": LANGUAGES,
        "selected_lang": language,
        "age": age,
        "bookmarked_ids": bookmarked_ids,
        "error": error,
    })


def compare(request):
    repo_inputs = [r.strip() for r in request.GET.getlist("repos") if r.strip()]
    repos_data = []
    errors = []

    for r in repo_inputs[:3]:
        if "/" not in r:
            errors.append(f"格式错误：{r}（应为 owner/name）")
            continue
        owner, name = r.split("/", 1)
        owner, name = owner.strip(), name.strip()
        detail = github_api.get_repo_detail(owner, name)
        if not detail:
            errors.append(f"未找到：{r}")
            continue
        repo_obj = _upsert_repos([detail])[0]
        commits = github_api.get_recent_commits(owner, name, days=30)
        total_commits = sum(d["count"] for d in commits)
        max_count = max((d["count"] for d in commits), default=1) or 1
        contributors = github_api.get_contributors(owner, name, limit=5)
        repos_data.append({
            "repo": repo_obj,
            "commits": commits,
            "total_commits": total_commits,
            "max_count": max_count,
            "contributors": contributors,
        })

    bookmarked_ids = set(Bookmark.objects.values_list("repository_id", flat=True))

    return render(request, "discovery/compare.html", {
        "repos_data": repos_data,
        "input_values": repo_inputs + [""] * (3 - len(repo_inputs)),
        "errors": errors,
        "bookmarked_ids": bookmarked_ids,
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
    query = request.GET.get("q", "").strip()
    tag_filter = request.GET.get("tag", "").strip()

    qs = Bookmark.objects.select_related("repository").all()

    if query:
        qs = qs.filter(
            Q(repository__full_name__icontains=query)
            | Q(repository__description__icontains=query)
            | Q(note__icontains=query)
        )

    if tag_filter:
        qs = qs.filter(tags__contains=[tag_filter])

    bms = list(qs)
    bookmarked_ids = set(bm.repository_id for bm in bms)

    all_bms = Bookmark.objects.select_related("repository").all()
    lang_counts = Counter()
    topic_counts = Counter()
    tag_counts = Counter()
    for bm in all_bms:
        if bm.repository.language:
            lang_counts[bm.repository.language] += 1
        for t in bm.repository.topics or []:
            topic_counts[t] += 1
        for tag in bm.tags or []:
            tag_counts[tag] += 1

    top_langs = lang_counts.most_common(6)
    max_lang = top_langs[0][1] if top_langs else 1
    top_langs = [(lang, count, int(count * 100 / max_lang)) for lang, count in top_langs]

    return render(request, "discovery/bookmarks.html", {
        "bookmarks": bms,
        "bookmarked_ids": bookmarked_ids,
        "query": query,
        "tag_filter": tag_filter,
        "total_count": all_bms.count(),
        "top_langs": top_langs,
        "top_topics": topic_counts.most_common(10),
        "all_tags": sorted(tag_counts.items(), key=lambda x: (-x[1], x[0])),
    })


@require_POST
def update_bookmark(request, repo_id):
    bm = get_object_or_404(Bookmark, repository_id=repo_id)
    tags_raw = request.POST.get("tags", "").strip()
    note = request.POST.get("note", "").strip()

    tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
    seen = set()
    tags = [t for t in tags if not (t in seen or seen.add(t))]

    bm.tags = tags
    bm.note = note
    bm.save(update_fields=["tags", "note"])
    return redirect(request.META.get("HTTP_REFERER", "bookmarks"))


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


def repo_detail(request, owner, name):
    full_name = f"{owner}/{name}"
    repo = Repository.objects.filter(full_name__iexact=full_name).first()

    data = github_api.get_repo_detail(owner, name)
    if data:
        repo, _ = Repository.objects.update_or_create(
            github_id=data["github_id"],
            defaults={**data, "cached_at": timezone.now()},
        )

    if not repo:
        return render(request, "discovery/repo_detail.html", {"error": "项目未找到"})

    _push_recent_view(request, repo.id)

    readme_raw = github_api.get_readme(owner, name)
    readme_html = ""
    if readme_raw:
        readme_html = mark_safe(
            md.markdown(
                readme_raw,
                extensions=["fenced_code", "tables", "nl2br", "toc"],
                output_format="html5",
            )
        )

    contributors = github_api.get_contributors(owner, name, limit=10)
    commit_series = github_api.get_recent_commits(owner, name, days=30)
    total_commits = sum(d["count"] for d in commit_series)
    max_count = max((d["count"] for d in commit_series), default=1) or 1

    similar_items = github_api.get_similar(
        {
            "github_id": repo.github_id,
            "topics": repo.topics,
            "language": repo.language,
        },
        limit=6,
    )
    similar_repos = _upsert_repos(similar_items)

    bookmarked_ids = set(Bookmark.objects.values_list("repository_id", flat=True))

    return render(request, "discovery/repo_detail.html", {
        "repo": repo,
        "readme_html": readme_html,
        "contributors": contributors,
        "commit_series": commit_series,
        "total_commits": total_commits,
        "max_count": max_count,
        "similar_repos": similar_repos,
        "bookmarked_ids": bookmarked_ids,
    })
