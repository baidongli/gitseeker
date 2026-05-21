import re

CURATED = [
    ("sindresorhus/awesome", "Awesome", "所有 awesome 列表的总入口"),
    ("vinta/awesome-python", "Python", "Python 生态精选"),
    ("avelino/awesome-go", "Go", "Go 语言精选"),
    ("rust-unofficial/awesome-rust", "Rust", "Rust 语言精选"),
    ("sindresorhus/awesome-nodejs", "Node.js", "Node.js 资源"),
    ("enaqx/awesome-react", "React", "React 生态"),
    ("vuejs/awesome-vue", "Vue", "Vue 生态"),
    ("agarrharr/awesome-cli-apps", "CLI Tools", "命令行工具"),
    ("ZuzooVn/machine-learning-for-software-engineers", "ML for Engineers", "ML 学习路径"),
    ("josephmisiti/awesome-machine-learning", "Machine Learning", "ML 框架与库"),
    ("Hack-with-Github/Awesome-Hacking", "Hacking", "安全/渗透资源"),
    ("kahun/awesome-sysadmin", "Sysadmin", "运维资源"),
    ("public-apis/public-apis", "Public APIs", "免费 API 集合"),
    ("EbookFoundation/free-programming-books", "Free Books", "免费编程书籍"),
    ("ripienaar/free-for-dev", "Free for Dev", "开发者免费服务"),
    # 应用/游戏专项
    ("awesome-selfhosted/awesome-selfhosted", "Self-Hosted", "替代付费 SaaS 的开源应用（金矿）"),
    ("jaywcjlove/awesome-mac", "macOS Apps", "macOS 应用大全（中文）"),
    ("Awesome-Windows/Awesome", "Windows Apps", "Windows 优秀应用"),
    ("viatsko/awesome-vscode", "VSCode Extensions", "VSCode 扩展精选"),
    ("tauri-apps/awesome-tauri", "Tauri Apps", "Tauri 跨平台桌面应用"),
    ("godotengine/awesome-godot", "Godot Games", "Godot 游戏与资源"),
]


HEADING_RE = re.compile(r"^(#{2,4})\s+(.+?)\s*$")
LINK_RE = re.compile(
    r"\[([^\]]+)\]\(https://github\.com/([\w.-]+)/([\w.-]+?)/?(?:[#?].*?)?\)"
    r"(?:\s*[-–—:]\s*(.+))?"
)
BADGE_RE = re.compile(r"\[!\[.*?\]\(.*?\)\]\(.*?\)")
INNER_LINK_RE = re.compile(r"\[(.+?)\]\([^)]+\)")


def _clean_heading(text):
    text = BADGE_RE.sub("", text)
    text = INNER_LINK_RE.sub(r"\1", text)
    return text.strip(" #*_")


def parse(readme):
    sections = []
    current = None
    seen = set()
    skip_until_blank = False

    for raw in readme.split("\n"):
        line = raw.strip()

        h = HEADING_RE.match(line)
        if h:
            title = _clean_heading(h.group(2))
            if not title or title.lower() in {"contents", "table of contents", "toc", "目录"}:
                current = None
                continue
            current = {"title": title, "items": []}
            sections.append(current)
            continue

        if current is None:
            continue

        if not line.startswith(("-", "*", "+")):
            continue

        m = LINK_RE.search(line)
        if not m:
            continue
        name, owner, repo, desc = m.groups()
        repo = repo.rstrip(".")
        full = f"{owner}/{repo}".lower()
        if full in seen:
            continue
        seen.add(full)
        current["items"].append({
            "name": name.strip(),
            "owner": owner,
            "repo": repo,
            "full_name": f"{owner}/{repo}",
            "desc": (desc or "").strip(),
        })

    return [s for s in sections if s["items"]]
