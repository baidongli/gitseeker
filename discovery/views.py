import markdown as md
from collections import Counter
from datetime import datetime, timedelta, timezone as py_timezone
from django.db.models import Q, F
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils import timezone
from django.utils.safestring import mark_safe

from .models import Repository, Bookmark, Setting, AwesomeList, StarSnapshot, TopicTrend, SharedList
from . import github_api, cache as cache_mod, awesome, tldr as tldr_mod, recommend, funfacts


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
    now = timezone.now()
    cutoff = now - timedelta(hours=12)
    for item in items:
        repo, _ = Repository.objects.update_or_create(
            github_id=item["github_id"],
            defaults={**item, "cached_at": now},
        )
        repos.append(repo)
        last = repo.snapshots.order_by("-captured_at").first()
        if not last or last.captured_at < cutoff:
            StarSnapshot.objects.create(repository=repo, stars=repo.stars)
    return repos


def index(request):
    language = request.GET.get("lang", "")
    since = request.GET.get("since", "weekly")
    skip_daily = int(request.GET.get("skip_daily", "0") or 0)

    result = github_api.get_trending(language=language or None, since=since)
    repos = _upsert_repos(result.get("items", []))
    error = result.get("error")

    bookmarked_ids = set(
        Bookmark.objects.values_list("repository_id", flat=True)
    )

    recent_repos = _get_recent_repos(request, limit=6)
    daily = recommend.daily_pick(seed_offset=skip_daily)
    recs = recommend.recommendations(limit=6)
    fact = funfacts.did_you_know()
    capsule = funfacts.time_capsule()

    return render(request, "discovery/index.html", {
        "repos": repos,
        "languages": LANGUAGES,
        "selected_lang": language,
        "since": since,
        "bookmarked_ids": bookmarked_ids,
        "recent_repos": recent_repos,
        "daily": daily,
        "skip_daily": skip_daily,
        "recommendations": recs,
        "fact": fact,
        "capsule": capsule,
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


def settings_page(request):
    test_result = None

    if request.method == "POST":
        action = request.POST.get("action", "save")
        if action == "clear":
            Setting.set("github_token", "")
            messages.success(request, "Token 已清除")
            return redirect("settings")
        if action == "clear_cache":
            cache_mod.clear_all()
            messages.success(request, "API 缓存已清空，下次请求会重新拉取")
            return redirect("settings")
        if action == "test":
            token = request.POST.get("token", "").strip()
            if not token:
                test_result = {"ok": False, "msg": "请先填入 token"}
            else:
                ok, info = github_api.validate_token(token)
                test_result = {
                    "ok": ok,
                    "msg": f"验证成功，账号：{info}" if ok else f"验证失败：{info}",
                }
        else:
            token = request.POST.get("token", "").strip()
            Setting.set("github_token", token)
            messages.success(request, "Token 已保存" if token else "Token 已清除")
            return redirect("settings")

    token_saved = bool(Setting.get("github_token"))
    rate = github_api.get_rate_limit()

    return render(request, "discovery/settings.html", {
        "token_saved": token_saved,
        "rate": rate,
        "test_result": test_result,
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
        summary = tldr_mod.extract_tldr(readme_raw)
        if summary and summary != repo.readme_summary:
            repo.readme_summary = summary
            repo.save(update_fields=["readme_summary"])

    star_chart = _build_star_chart(repo)

    heatmap = _build_heatmap(github_api.get_commit_activity_year(owner, name))

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
        "star_chart": star_chart,
        "heatmap": heatmap,
    })


def _build_heatmap(weeks):
    if not weeks:
        return None
    max_count = max((d["count"] for w in weeks for d in w["days"]), default=0)
    total = sum(w["total"] for w in weeks)
    return {
        "weeks": weeks,
        "max": max_count,
        "total": total,
    }


def _build_star_chart(repo):
    snaps = list(repo.snapshots.order_by("captured_at"))
    if len(snaps) < 2:
        return None
    min_s = min(s.stars for s in snaps)
    max_s = max(s.stars for s in snaps)
    span = max(max_s - min_s, 1)
    n = len(snaps)
    points = []
    for i, s in enumerate(snaps):
        x = round((i / (n - 1)) * 100, 2)
        y = round(40 - ((s.stars - min_s) / span) * 38 - 1, 2)
        points.append({"x": x, "y": y, "stars": s.stars, "at": s.captured_at})
    polyline = " ".join(f"{p['x']},{p['y']}" for p in points)
    return {
        "polyline": polyline,
        "points": points,
        "first": snaps[0],
        "last": snaps[-1],
        "delta": snaps[-1].stars - snaps[0].stars,
        "min": min_s,
        "max": max_s,
    }


def awesome_index(request):
    existing = {al.full_name: al for al in AwesomeList.objects.all()}
    lists = []
    for full_name, title, desc in awesome.CURATED:
        obj = existing.get(full_name)
        lists.append({
            "full_name": full_name,
            "owner": full_name.split("/")[0],
            "name": full_name.split("/")[1],
            "title": title,
            "desc": desc,
            "fetched": obj is not None,
            "items_count": obj.items_count if obj else 0,
            "last_fetched": obj.last_fetched if obj else None,
        })
    return render(request, "discovery/awesome.html", {"lists": lists})


@require_POST
def awesome_refresh(request, owner, name):
    full_name = f"{owner}/{name}"
    readme = github_api.get_readme(owner, name)
    if not readme:
        messages.error(request, f"无法获取 {full_name} 的 README")
        return redirect("awesome_index")

    sections = awesome.parse(readme)
    items_count = sum(len(s["items"]) for s in sections)

    title = full_name
    for t, label, _ in awesome.CURATED:
        if t == full_name:
            title = label
            break

    AwesomeList.objects.update_or_create(
        full_name=full_name,
        defaults={
            "title": title,
            "sections": sections,
            "items_count": items_count,
            "last_fetched": timezone.now(),
        },
    )
    messages.success(request, f"已抓取 {items_count} 个项目")
    return redirect("awesome_detail", owner=owner, name=name)


def awesome_detail(request, owner, name):
    full_name = f"{owner}/{name}"
    al = AwesomeList.objects.filter(full_name=full_name).first()
    if not al:
        messages.info(request, "该列表还未抓取，点击抓取按钮获取数据")
        return redirect("awesome_index")
    return render(request, "discovery/awesome_detail.html", {"al": al})


def rising(request):
    candidates = (
        Repository.objects
        .filter(snapshots__captured_at__lte=timezone.now() - timedelta(days=2))
        .distinct()
    )
    real_growth = []
    for repo in candidates[:500]:
        snaps = repo.snapshots.order_by("captured_at")
        first = snaps.first()
        last = snaps.last()
        if not first or not last or first.stars == 0:
            continue
        delta = last.stars - first.stars
        if delta <= 0:
            continue
        days = max((last.captured_at - first.captured_at).total_seconds() / 86400, 1)
        pct = (delta / first.stars) * 100
        real_growth.append({
            "repo": repo,
            "delta": delta,
            "days": round(days, 1),
            "pct": round(pct, 1),
            "rate": round(delta / days, 1),
        })
    real_growth.sort(key=lambda x: x["pct"], reverse=True)
    real_growth = real_growth[:30]

    year_ago = timezone.now() - timedelta(days=365)
    proxy = (
        Repository.objects
        .filter(created_at_github__gte=year_ago, stars__gte=100)
        .order_by("-stars")[:200]
    )
    proxy_items = []
    now = timezone.now()
    for repo in proxy:
        if not repo.created_at_github:
            continue
        days = max((now - repo.created_at_github).total_seconds() / 86400, 1)
        proxy_items.append({
            "repo": repo,
            "days": int(days),
            "rate": round(repo.stars / days, 1),
        })
    proxy_items.sort(key=lambda x: x["rate"], reverse=True)
    proxy_items = proxy_items[:30]

    bookmarked_ids = set(Bookmark.objects.values_list("repository_id", flat=True))

    return render(request, "discovery/rising.html", {
        "real_growth": real_growth,
        "proxy_items": proxy_items,
        "bookmarked_ids": bookmarked_ids,
    })


def trends(request):
    trends_list = TopicTrend.objects.order_by("-growth_pct")
    last_update = trends_list.first().updated_at if trends_list.exists() else None
    return render(request, "discovery/trends.html", {
        "trends": trends_list,
        "last_update": last_update,
    })


@require_POST
def trends_refresh(request):
    topic_counter = Counter()
    for repo in Repository.objects.exclude(topics=[]):
        for t in repo.topics or []:
            topic_counter[t] += 1

    candidates = [t for t, c in topic_counter.most_common(40) if c >= 3]
    if not candidates:
        candidates = ["machine-learning", "rust", "typescript", "ai", "llm",
                      "web", "cli", "database", "docker", "kubernetes",
                      "python", "javascript", "go", "agent", "rag",
                      "wasm", "blockchain", "security", "devops", "framework"]

    now = datetime.now(tz=py_timezone.utc)
    this_start = now.replace(day=1).strftime("%Y-%m-%d")
    last_month_end = (now.replace(day=1) - timedelta(days=1))
    last_start = last_month_end.replace(day=1).strftime("%Y-%m-%d")
    last_end = last_month_end.strftime("%Y-%m-%d")

    for topic in candidates[:30]:
        try:
            this_count = github_api.search_count(f"topic:{topic} created:>{this_start}")
            last_count = github_api.search_count(f"topic:{topic} created:{last_start}..{last_end}")
        except Exception:
            continue
        if last_count > 0:
            growth = (this_count - last_count) / last_count * 100
        elif this_count > 0:
            growth = 100.0
        else:
            growth = 0.0
        TopicTrend.objects.update_or_create(
            topic=topic,
            defaults={
                "this_month_count": this_count,
                "last_month_count": last_count,
                "growth_pct": round(growth, 1),
            },
        )

    messages.success(request, f"已刷新 {len(candidates[:30])} 个主题趋势")
    return redirect("trends")


import json
from collections import defaultdict


def _serialize_bookmark(bm):
    r = bm.repository
    return {
        "github_id": r.github_id,
        "full_name": r.full_name,
        "name": r.name,
        "owner_login": r.owner_login,
        "owner_avatar": r.owner_avatar,
        "description": r.description,
        "html_url": r.html_url,
        "language": r.language,
        "stars": r.stars,
        "forks": r.forks,
        "topics": r.topics,
        "homepage": r.homepage,
        "note": bm.note,
        "tags": bm.tags,
        "bookmarked_at": bm.created_at.isoformat(),
    }


def export_json(request):
    data = {
        "version": 1,
        "exported_at": timezone.now().isoformat(),
        "bookmarks": [_serialize_bookmark(bm) for bm in
                      Bookmark.objects.select_related("repository").all()],
    }
    body = json.dumps(data, ensure_ascii=False, indent=2)
    resp = HttpResponse(body, content_type="application/json; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="gitseeker-bookmarks-{timezone.now().date()}.json"'
    return resp


def export_markdown(request):
    bms = list(Bookmark.objects.select_related("repository").all())

    groups = defaultdict(list)
    for bm in bms:
        if not bm.tags:
            groups["未分组"].append(bm)
        else:
            for t in bm.tags:
                groups[t].append(bm)

    lines = [
        f"# GitSeeker 收藏导出",
        f"",
        f"导出时间：{timezone.now().strftime('%Y-%m-%d %H:%M')}  ·  共 {len(bms)} 个项目",
        f"",
        f"---",
        f"",
    ]
    for group_name in sorted(groups.keys(), key=lambda g: (g == "未分组", g)):
        items = groups[group_name]
        lines.append(f"## #{group_name} ({len(items)})")
        lines.append("")
        for bm in items:
            r = bm.repository
            line = f"- **[{r.full_name}]({r.html_url})**"
            badges = []
            if r.language:
                badges.append(r.language)
            badges.append(f"⭐ {r.stars_display}")
            line += f" · {' · '.join(badges)}"
            lines.append(line)
            if r.readme_summary or r.description:
                lines.append(f"  - {(r.readme_summary or r.description)[:200]}")
            if bm.note:
                lines.append(f"  - 📝 {bm.note}")
        lines.append("")

    body = "\n".join(lines)
    resp = HttpResponse(body, content_type="text/markdown; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="gitseeker-bookmarks-{timezone.now().date()}.md"'
    return resp


@require_POST
def import_bookmarks(request):
    upload = request.FILES.get("file")
    if not upload:
        messages.error(request, "请选择一个 JSON 文件")
        return redirect("import_export")

    try:
        raw = upload.read().decode("utf-8")
        data = json.loads(raw)
    except Exception as e:
        messages.error(request, f"文件解析失败：{e}")
        return redirect("import_export")

    bookmarks = data.get("bookmarks") or []
    imported = 0
    skipped = 0

    for item in bookmarks:
        try:
            github_id = item.get("github_id")
            full_name = item.get("full_name")
            if not github_id or not full_name:
                skipped += 1
                continue
            repo, _ = Repository.objects.update_or_create(
                github_id=github_id,
                defaults={
                    "full_name": full_name,
                    "name": item.get("name") or full_name.split("/")[-1],
                    "owner_login": item.get("owner_login") or full_name.split("/")[0],
                    "owner_avatar": item.get("owner_avatar", ""),
                    "description": item.get("description", ""),
                    "html_url": item.get("html_url", f"https://github.com/{full_name}"),
                    "language": item.get("language", ""),
                    "stars": item.get("stars", 0),
                    "forks": item.get("forks", 0),
                    "topics": item.get("topics", []),
                    "homepage": item.get("homepage", ""),
                    "cached_at": timezone.now(),
                },
            )
            Bookmark.objects.update_or_create(
                repository=repo,
                defaults={
                    "note": item.get("note", ""),
                    "tags": item.get("tags", []),
                },
            )
            imported += 1
        except Exception:
            skipped += 1

    messages.success(request, f"导入完成：成功 {imported} 个，跳过 {skipped} 个")
    return redirect("bookmarks")


def import_export(request):
    return render(request, "discovery/import_export.html", {
        "bookmark_count": Bookmark.objects.count(),
    })


def profile(request):
    data = recommend.taste_profile()
    return render(request, "discovery/profile.html", {"p": data})


import secrets


def feed(request):
    bms = list(
        Bookmark.objects
        .select_related("repository")
        .order_by("-created_at")[:25]
    )

    events = []
    for bm in bms:
        repo = bm.repository
        releases = github_api.get_releases(repo.owner_login, repo.name, limit=3)
        for rel in releases:
            if not rel.get("published_at"):
                continue
            events.append({
                "kind": "release",
                "at": rel["published_at"],
                "repo": repo,
                "title": rel["name"] or rel["tag_name"],
                "url": rel["html_url"],
                "prerelease": rel["prerelease"],
                "body": rel["body"],
            })

        commits = github_api.get_recent_commits(repo.owner_login, repo.name, days=14)
        total_2w = sum(d["count"] for d in commits)
        if total_2w > 0:
            last_active = None
            for day in reversed(commits):
                if day["count"] > 0:
                    last_active = day["date"]
                    break
            events.append({
                "kind": "activity",
                "at": timezone.now(),
                "repo": repo,
                "commits_2w": total_2w,
                "last_active": last_active,
            })

    events.sort(key=lambda e: e["at"], reverse=True)
    bookmarked_ids = set(bm.repository_id for bm in bms)

    return render(request, "discovery/feed.html", {
        "events": events[:50],
        "bookmark_count": len(bms),
        "bookmarked_ids": bookmarked_ids,
    })


def hot(request):
    from_date = (datetime.now(tz=py_timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    new_burst = github_api.search_repos(
        query=f"created:>{from_date} stars:>=50",
        sort="stars",
        per_page=20,
    )
    new_repos = _upsert_repos(new_burst.get("items", []))

    snap_cutoff = timezone.now() - timedelta(days=2)
    repos_with_snaps = (
        Repository.objects
        .filter(snapshots__captured_at__lte=snap_cutoff)
        .distinct()
    )
    surges = []
    for repo in repos_with_snaps[:300]:
        snaps = list(repo.snapshots.order_by("-captured_at"))
        if len(snaps) < 2:
            continue
        latest = snaps[0]
        baseline = None
        for s in snaps:
            if (latest.captured_at - s.captured_at).total_seconds() >= 18 * 3600:
                baseline = s
                break
        if not baseline:
            continue
        delta = latest.stars - baseline.stars
        hours = (latest.captured_at - baseline.captured_at).total_seconds() / 3600
        if delta < 5:
            continue
        surges.append({
            "repo": repo,
            "delta": delta,
            "hours": round(hours, 1),
            "rate": round(delta / max(hours, 1), 2),
        })
    surges.sort(key=lambda x: x["delta"], reverse=True)
    surges = surges[:20]

    bookmarked_ids = set(Bookmark.objects.values_list("repository_id", flat=True))
    return render(request, "discovery/hot.html", {
        "new_repos": new_repos,
        "surges": surges,
        "bookmarked_ids": bookmarked_ids,
        "error": new_burst.get("error"),
    })


def og_image(request, owner, name):
    from django.core.cache import cache
    from . import og as og_mod

    cache_key = f"og:{owner}/{name}"
    cached = cache.get(cache_key)
    if cached:
        return HttpResponse(cached, content_type="image/png")

    full_name = f"{owner}/{name}"
    repo = Repository.objects.filter(full_name__iexact=full_name).first()
    if not repo:
        data = github_api.get_repo_detail(owner, name)
        if not data:
            return HttpResponse(status=404)
        repo = _upsert_repos([data])[0]

    png = og_mod.render_card(repo)
    cache.set(cache_key, png, 86400)
    return HttpResponse(png, content_type="image/png")


@require_POST
def share_create(request):
    tag = request.POST.get("tag", "").strip()
    title = request.POST.get("title", "").strip()
    note = request.POST.get("note", "").strip()
    token = secrets.token_urlsafe(8).replace("-", "_").replace("=", "")
    sl = SharedList.objects.create(token=token, tag=tag, title=title or (tag or "我的收藏"), note=note)
    return redirect("shared_list", token=sl.token)


def shared_list(request, token):
    sl = get_object_or_404(SharedList, token=token)
    SharedList.objects.filter(pk=sl.pk).update(views=F("views") + 1)

    qs = Bookmark.objects.select_related("repository")
    if sl.tag:
        qs = qs.filter(tags__contains=[sl.tag])
    bms = list(qs)
    return render(request, "discovery/shared_list.html", {
        "sl": sl,
        "bookmarks": bms,
    })


def share_index(request):
    lists = SharedList.objects.all()
    return render(request, "discovery/share_index.html", {"lists": lists})


@require_POST
def share_delete(request, token):
    SharedList.objects.filter(token=token).delete()
    return redirect("share_index")
