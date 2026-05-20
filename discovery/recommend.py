import hashlib
from collections import Counter
from datetime import date, timedelta

from django.db.models import Q
from django.utils import timezone

from .models import Repository, Bookmark


def daily_pick(seed_offset=0):
    """Pick one project deterministically by date (treasure-like: 100-5000 stars,
    not bookmarked). seed_offset lets the user request a fresh pick within the same day."""
    today = date.today()
    bookmarked_ids = set(Bookmark.objects.values_list("repository_id", flat=True))

    qs = (
        Repository.objects
        .filter(stars__gte=100, stars__lte=5000)
        .exclude(id__in=bookmarked_ids)
        .order_by("id")
    )
    n = qs.count()
    if n == 0:
        return None

    seed = f"{today.isoformat()}-{seed_offset}".encode()
    idx = int(hashlib.md5(seed).hexdigest(), 16) % n
    return qs[idx]


def recommendations(limit=12):
    """Score non-bookmarked repos by overlap with bookmarked topics/languages."""
    bms = Bookmark.objects.select_related("repository").all()
    if not bms.exists():
        return []

    my_topics = Counter()
    my_langs = Counter()
    bookmarked_ids = set()
    for bm in bms:
        bookmarked_ids.add(bm.repository_id)
        for t in bm.repository.topics or []:
            my_topics[t] += 1
        if bm.repository.language:
            my_langs[bm.repository.language] += 1

    if not my_topics and not my_langs:
        return []

    candidates = (
        Repository.objects
        .exclude(id__in=bookmarked_ids)
        .filter(stars__gte=50)
    )

    scored = []
    for repo in candidates.iterator(chunk_size=500):
        score = 0
        for t in repo.topics or []:
            score += my_topics.get(t, 0) * 2
        if repo.language and my_langs.get(repo.language):
            score += my_langs[repo.language]
        if score > 0:
            scored.append((score, repo))

    scored.sort(key=lambda x: (-x[0], -x[1].stars))
    return [r for _, r in scored[:limit]]


def taste_profile():
    """Aggregate the user's bookmark patterns into a profile dict."""
    bms = list(Bookmark.objects.select_related("repository").order_by("created_at"))
    if not bms:
        return None

    langs = Counter()
    topics = Counter()
    tag_counts = Counter()
    ages = []
    stars_list = []
    now = timezone.now()

    for bm in bms:
        r = bm.repository
        if r.language:
            langs[r.language] += 1
        for t in r.topics or []:
            topics[t] += 1
        for tag in bm.tags or []:
            tag_counts[tag] += 1
        if r.created_at_github:
            ages.append((now - r.created_at_github).total_seconds() / 86400)
        stars_list.append(r.stars)

    cutoff = now - timedelta(days=30)
    recent = [bm for bm in bms if bm.created_at >= cutoff]
    recent_langs = Counter()
    recent_topics = Counter()
    for bm in recent:
        if bm.repository.language:
            recent_langs[bm.repository.language] += 1
        for t in bm.repository.topics or []:
            recent_topics[t] += 1

    max_lang = max(langs.values()) if langs else 1
    top_langs = [(l, c, int(c * 100 / max_lang)) for l, c in langs.most_common(8)]

    stars_sorted = sorted(stars_list)
    median_stars = stars_sorted[len(stars_sorted) // 2] if stars_sorted else 0

    return {
        "total": len(bms),
        "top_langs": top_langs,
        "top_topics": topics.most_common(15),
        "top_tags": tag_counts.most_common(8),
        "avg_age_years": round(sum(ages) / len(ages) / 365, 1) if ages else 0,
        "avg_stars": int(sum(stars_list) / len(stars_list)) if stars_list else 0,
        "median_stars": median_stars,
        "min_stars": min(stars_list) if stars_list else 0,
        "max_stars": max(stars_list) if stars_list else 0,
        "recent_count": len(recent),
        "recent_top_langs": recent_langs.most_common(3),
        "recent_top_topics": recent_topics.most_common(5),
        "first_bookmark": bms[0].created_at if bms else None,
        "first_repo": bms[0].repository if bms else None,
    }
