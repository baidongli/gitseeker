import requests
from datetime import datetime, timedelta, timezone
from django.utils import timezone as dj_timezone


GITHUB_API = "https://api.github.com"
HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


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
        resp = requests.get(f"{GITHUB_API}/search/repositories", headers=HEADERS, params=params, timeout=10)
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


def get_repo_detail(owner, repo):
    try:
        resp = requests.get(f"{GITHUB_API}/repos/{owner}/{repo}", headers=HEADERS, timeout=10)
        resp.raise_for_status()
        return _repo_from_data(resp.json())
    except Exception as e:
        return None
