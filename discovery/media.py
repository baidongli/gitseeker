"""Extract images/screenshots from README markdown."""
import re
from urllib.parse import urlparse

MD_IMG = re.compile(r'!\[([^\]]*)\]\(([^)\s]+)(?:\s+"[^"]*")?\)')
HTML_IMG = re.compile(r'<img[^>]*\bsrc=["\']?([^"\'\s>]+)["\']?[^>]*>', re.IGNORECASE)
REF_IMG = re.compile(r'!\[([^\]]*)\]\[([^\]]+)\]')
REF_DEF = re.compile(r'^\s*\[([^\]]+)\]:\s*(\S+)', re.MULTILINE)

BADGE_HOSTS = (
    "img.shields.io", "shields.io", "travis-ci.org", "travis-ci.com",
    "circleci.com", "codecov.io", "coveralls.io", "badge.fury.io",
    "github-readme-stats.vercel.app", "readme-typing-svg.herokuapp.com",
    "capsule-render.vercel.app", "anuraghazra.github.io",
    "githubusercontent.com/u/", "avatars.githubusercontent.com",
    "img.badgesize.io", "snyk.io", "depfu.com",
)
BADGE_PATH_HINTS = ("/badge", "shields/", "/status/", ".badge.", "ci-status", "/build/", "/coverage")


def _is_badge_or_avatar(url):
    try:
        p = urlparse(url)
        host = p.netloc.lower()
        path = p.path.lower()
        if any(b in host for b in BADGE_HOSTS):
            return True
        if any(h in path for h in BADGE_PATH_HINTS):
            return True
        if path.endswith(".svg") and (host or path).count("badge"):
            return True
        return False
    except Exception:
        return False


def _resolve_url(url, owner, repo):
    url = url.strip()
    if url.startswith(("http://", "https://")):
        if "github.com" in url and "/blob/" in url:
            return url.replace("//github.com", "//raw.githubusercontent.com").replace("/blob/", "/")
        if "github.com" in url and "/raw/" in url:
            return url.replace("//github.com", "//raw.githubusercontent.com").replace("/raw/", "/")
        return url
    if url.startswith("//"):
        return "https:" + url
    clean = url.lstrip("./").lstrip("/")
    return f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/{clean}"


def extract_screenshots(readme, owner, repo, limit=6):
    if not readme:
        return []
    refs = {m.group(1).lower(): m.group(2) for m in REF_DEF.finditer(readme)}

    images = []
    for m in MD_IMG.finditer(readme):
        images.append((m.start(), m.group(2)))
    for m in HTML_IMG.finditer(readme):
        images.append((m.start(), m.group(1)))
    for m in REF_IMG.finditer(readme):
        ref = m.group(2).lower()
        if ref in refs:
            images.append((m.start(), refs[ref]))
    images.sort()

    seen = set()
    out = []
    for _, raw_url in images:
        if not raw_url or raw_url.startswith("data:"):
            continue
        resolved = _resolve_url(raw_url, owner, repo)
        if resolved in seen:
            continue
        if _is_badge_or_avatar(resolved):
            continue
        seen.add(resolved)
        is_gif = resolved.lower().endswith(".gif")
        out.append({"url": resolved, "is_gif": is_gif})
        if len(out) >= limit:
            break
    return out
