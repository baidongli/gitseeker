import base64
import requests
from collections import Counter
from datetime import datetime, timedelta, timezone
from django.utils import timezone as dj_timezone

from .cache import cached


GITHUB_API = "https://api.github.com"
BASE_HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


def _headers():
    headers = dict(BASE_HEADERS)
    try:
        from .models import Setting
        token = Setting.get("github_token")
        if token:
            headers["Authorization"] = f"Bearer {token}"
    except Exception:
        pass
    return headers


HEADERS = BASE_HEADERS  # backwards-compat alias; existing call sites updated below


def _parse_dt(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def _repo_from_data(data):
    return {
        "github_id": data["id"],
        "full_name": data["full_name"],
        "name": data["name"],
        "owner_login": data["owner"]["login"],
        "owner_avatar": data["owner"].get("avatar_url", ""),
        "description": data.get("description") or "",
        "html_url": data["html_url"],
        "language": data.get("language") or "",
        "stars": data.get("stargazers_count", 0),
        "forks": data.get("forks_count", 0),
        "watchers": data.get("watchers_count", 0),
        "open_issues": data.get("open_issues_count", 0),
        "topics": data.get("topics", []),
        "homepage": data.get("homepage") or "",
        "pushed_at": _parse_dt(data.get("pushed_at")),
        "created_at_github": _parse_dt(data.get("created_at")),
    }


@cached("search", ttl=600)
def search_repos(query, language=None, sort="stars", order="desc", per_page=30, page=1):
    q = query
    if language:
        q += f" language:{language}"
    params = {
        "q": q,
        "sort": sort,
        "order": order,
        "per_page": per_page,
        "page": page,
    }
    try:
        resp = requests.get(f"{GITHUB_API}/search/repositories", headers=_headers(), params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return {
            "total_count": data.get("total_count", 0),
            "items": [_repo_from_data(item) for item in data.get("items", [])],
        }
    except Exception as e:
        return {"total_count": 0, "items": [], "error": str(e)}


def get_trending(language=None, since="weekly"):
    since_map = {"daily": 1, "weekly": 7, "monthly": 30}
    days = since_map.get(since, 7)
    date_from = (datetime.now(tz=timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    q = f"created:>{date_from}"
    if language:
        q += f" language:{language}"
    return search_repos(q, sort="stars", order="desc", per_page=20)


def get_rate_limit():
    try:
        resp = requests.get(f"{GITHUB_API}/rate_limit", headers=_headers(), timeout=5)
        resp.raise_for_status()
        core = resp.json()["resources"]["core"]
        return {
            "limit": core["limit"],
            "remaining": core["remaining"],
            "reset": datetime.fromtimestamp(core["reset"], tz=timezone.utc),
            "authenticated": core["limit"] > 100,
        }
    except Exception as e:
        return {"error": str(e)}


@cached("search_count", ttl=3600)
def search_count(query):
    """Return just the total_count for a search query (faster than fetching items)."""
    try:
        resp = requests.get(
            f"{GITHUB_API}/search/repositories",
            headers=_headers(),
            params={"q": query, "per_page": 1},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("total_count", 0)
    except Exception:
        return 0


def validate_token(token):
    """Return (ok: bool, login_or_error: str)."""
    try:
        resp = requests.get(
            f"{GITHUB_API}/user",
            headers={**BASE_HEADERS, "Authorization": f"Bearer {token}"},
            timeout=5,
        )
        if resp.status_code == 200:
            return True, resp.json().get("login", "(unknown)")
        return False, f"HTTP {resp.status_code}: {resp.json().get('message', '')}"
    except Exception as e:
        return False, str(e)


@cached("repo", ttl=1800)
def get_repo_detail(owner, repo):
    try:
        resp = requests.get(f"{GITHUB_API}/repos/{owner}/{repo}", headers=_headers(), timeout=10)
        resp.raise_for_status()
        return _repo_from_data(resp.json())
    except Exception as e:
        return None


@cached("readme", ttl=3600)
def get_readme(owner, repo):
    try:
        resp = requests.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/readme",
            headers=_headers(),
            timeout=10,
        )
        if resp.status_code == 404:
            return ""
        resp.raise_for_status()
        data = resp.json()
        content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
        return content
    except Exception:
        return ""


@cached("contrib", ttl=3600)
def get_contributors(owner, repo, limit=10):
    try:
        resp = requests.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/contributors",
            headers=_headers(),
            params={"per_page": limit},
            timeout=10,
        )
        resp.raise_for_status()
        return [
            {
                "login": c["login"],
                "avatar_url": c.get("avatar_url", ""),
                "html_url": c.get("html_url", ""),
                "contributions": c.get("contributions", 0),
            }
            for c in resp.json()
        ]
    except Exception:
        return []


@cached("commits", ttl=3600)
def get_recent_commits(owner, repo, days=30):
    """Return a list of daily commit counts for the last `days` days (oldest first)."""
    since = (datetime.now(tz=timezone.utc) - timedelta(days=days)).isoformat()
    try:
        resp = requests.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/commits",
            headers=_headers(),
            params={"since": since, "per_page": 100},
            timeout=10,
        )
        resp.raise_for_status()
        commits = resp.json()
    except Exception:
        return []

    counts = Counter()
    for c in commits:
        date_str = c.get("commit", {}).get("author", {}).get("date", "")
        if date_str:
            try:
                day = datetime.fromisoformat(date_str.replace("Z", "+00:00")).date()
                counts[day] += 1
            except Exception:
                continue

    today = datetime.now(tz=timezone.utc).date()
    series = []
    for i in range(days - 1, -1, -1):
        day = today - timedelta(days=i)
        series.append({"date": day.isoformat(), "count": counts.get(day, 0)})
    return series


@cached("releases", ttl=3600)
def get_releases(owner, repo, limit=5):
    try:
        resp = requests.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/releases",
            headers=_headers(),
            params={"per_page": limit},
            timeout=10,
        )
        resp.raise_for_status()
        return [
            {
                "tag_name": r.get("tag_name", ""),
                "name": r.get("name") or r.get("tag_name", ""),
                "html_url": r.get("html_url", ""),
                "published_at": _parse_dt(r.get("published_at")),
                "prerelease": r.get("prerelease", False),
                "body": (r.get("body") or "")[:500],
            }
            for r in resp.json()
            if not r.get("draft")
        ]
    except Exception:
        return []


@cached("activity_year", ttl=21600)
def get_commit_activity_year(owner, repo):
    """Return 52 weeks of daily commit counts via /stats/commit_activity.
    Returns [] if GitHub is still computing (202) or on error."""
    try:
        resp = requests.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/stats/commit_activity",
            headers=_headers(),
            timeout=15,
        )
        if resp.status_code == 202:
            return []
        resp.raise_for_status()
        data = resp.json()
        weeks = []
        for week in data:
            ts = week.get("week", 0)
            days = week.get("days", [0] * 7)
            week_start = datetime.fromtimestamp(ts, tz=timezone.utc).date()
            weeks.append({
                "start": week_start.isoformat(),
                "days": [
                    {"date": (week_start + timedelta(days=i)).isoformat(), "count": c}
                    for i, c in enumerate(days)
                ],
                "total": sum(days),
            })
        return weeks
    except Exception:
        return []


@cached("similar", ttl=3600)
def get_similar(repo, limit=6):
    """Find similar repos by topic and language. `repo` is a dict from _repo_from_data."""
    topics = repo.get("topics") or []
    language = repo.get("language") or ""

    if topics:
        q = " ".join(f"topic:{t}" for t in topics[:2])
    elif language:
        q = "stars:>100"
    else:
        return []

    params = {
        "q": q + (f" language:{language}" if language else ""),
        "sort": "stars",
        "order": "desc",
        "per_page": limit + 2,
    }
    try:
        resp = requests.get(f"{GITHUB_API}/search/repositories", headers=_headers(), params=params, timeout=10)
        resp.raise_for_status()
        items = [_repo_from_data(i) for i in resp.json().get("items", [])]
        return [i for i in items if i["github_id"] != repo.get("github_id")][:limit]
    except Exception:
        return []
