"""App-focused discovery: categories, type classification, and download platform detection."""

GAME_TOPICS = {
    "game", "godot", "godot-game", "godot4", "unity", "unity3d", "unity-game",
    "bevy", "bevy-game", "roguelike", "rpg", "2d-game", "3d-game", "game-engine",
    "platformer", "pixel-art-game", "indie-game", "love2d", "raylib", "pygame",
    "puzzle-game", "rogue-like", "fps", "mmorpg", "rts", "card-game",
    "minecraft", "minecraft-mod", "minecraft-plugin",
}

APP_TOPICS = {
    "electron", "electron-app", "tauri", "tauri-app", "flutter-app", "flutter-desktop",
    "macos-app", "windows-app", "linux-app", "desktop-app", "gui-application",
    "selfhosted", "self-hosted", "self-hosting",
    "android-application", "android-app", "ios-app", "ios-application",
    "react-native", "react-native-app", "expo",
    "chrome-extension", "firefox-extension", "browser-extension", "webextension",
    "vscode-extension", "vscode-theme", "neovim-plugin", "vim-plugin",
    "cli-tool", "tui", "command-line-tool", "terminal", "terminal-emulator",
    "raycast-extension", "alfred-workflow",
    "saas-alternative", "no-code", "low-code",
}

LIB_TOPICS = {
    "library", "framework", "sdk", "api-client", "parser", "compiler", "transpiler",
    "package", "module", "toolkit", "binding", "bindings", "wrapper",
    "rust-library", "python-library", "javascript-library", "go-library",
    "react-component", "vue-component", "ui-library", "component-library",
    "ast", "tokenizer", "lexer",
}


def detect_kind(topics):
    """Return 'game' | 'app' | 'lib' | '' based on topics."""
    if not topics:
        return ""
    ts = {t.lower() for t in topics}
    if ts & GAME_TOPICS:
        return "game"
    if ts & APP_TOPICS:
        return "app"
    if ts & LIB_TOPICS:
        return "lib"
    return ""


KIND_LABELS = {
    "app": ("App", "bi-app-indicator", "#3fb950"),
    "game": ("Game", "bi-controller", "#bc8cff"),
    "lib": ("Lib", "bi-box", "#7d8590"),
}


CATEGORIES = [
    {"key": "electron", "group": "桌面应用", "icon": "bi-laptop",
     "title": "Electron 应用", "desc": "用 web 技术构建的桌面应用",
     "query": "topic:electron-app archived:false stars:>300"},
    {"key": "tauri", "group": "桌面应用", "icon": "bi-laptop",
     "title": "Tauri 应用", "desc": "用 Rust + web 构建的轻量桌面应用",
     "query": "topic:tauri-app archived:false stars:>100"},
    {"key": "flutter-desktop", "group": "桌面应用", "icon": "bi-laptop",
     "title": "Flutter 跨平台", "desc": "一套代码跑桌面 + 移动",
     "query": "topic:flutter-app archived:false stars:>300"},
    {"key": "macos-native", "group": "桌面应用", "icon": "bi-apple",
     "title": "macOS 原生", "desc": "用 Swift / Cocoa 构建的 Mac 应用",
     "query": "topic:macos topic:swift archived:false stars:>200"},

    {"key": "selfhosted-all", "group": "自托管", "icon": "bi-server",
     "title": "全部自托管", "desc": "可以自己部署的开源服务",
     "query": "topic:selfhosted archived:false stars:>1000"},
    {"key": "selfhosted-notes", "group": "自托管", "icon": "bi-journal-text",
     "title": "笔记/知识管理", "desc": "Notion / Evernote 替代品",
     "query": "topic:selfhosted topic:notes archived:false"},
    {"key": "selfhosted-media", "group": "自托管", "icon": "bi-film",
     "title": "媒体服务", "desc": "Plex / Jellyfin / 网盘",
     "query": "topic:selfhosted topic:media archived:false"},
    {"key": "selfhosted-productivity", "group": "自托管", "icon": "bi-kanban",
     "title": "协作/办公", "desc": "Trello / Slack / Airtable 替代",
     "query": "topic:selfhosted topic:productivity archived:false"},

    {"key": "godot-games", "group": "游戏", "icon": "bi-controller",
     "title": "Godot 游戏", "desc": "开源游戏引擎 Godot 的作品",
     "query": "topic:godot-game archived:false stars:>30"},
    {"key": "unity-games", "group": "游戏", "icon": "bi-controller",
     "title": "Unity 游戏", "desc": "Unity 引擎的开源游戏",
     "query": "topic:unity-game archived:false stars:>50"},
    {"key": "bevy-games", "group": "游戏", "icon": "bi-controller",
     "title": "Bevy 游戏（Rust）", "desc": "Rust 游戏引擎 Bevy",
     "query": "topic:bevy archived:false stars:>50"},
    {"key": "roguelike", "group": "游戏", "icon": "bi-dice-5",
     "title": "Roguelike", "desc": "随机生成、永久死亡",
     "query": "topic:roguelike archived:false stars:>100"},

    {"key": "chrome-ext", "group": "扩展插件", "icon": "bi-browser-chrome",
     "title": "Chrome 扩展", "desc": "Chrome 浏览器插件",
     "query": "topic:chrome-extension archived:false stars:>500"},
    {"key": "firefox-ext", "group": "扩展插件", "icon": "bi-browser-firefox",
     "title": "Firefox 扩展", "desc": "Firefox 浏览器插件",
     "query": "topic:firefox-extension archived:false stars:>200"},
    {"key": "vscode-ext", "group": "扩展插件", "icon": "bi-code-slash",
     "title": "VSCode 扩展", "desc": "VSCode / Cursor 扩展",
     "query": "topic:vscode-extension archived:false stars:>500"},
    {"key": "neovim-plugin", "group": "扩展插件", "icon": "bi-code-slash",
     "title": "Neovim 插件", "desc": "现代 Vim 编辑器插件",
     "query": "topic:neovim-plugin archived:false stars:>200"},

    {"key": "cli-tools", "group": "命令行", "icon": "bi-terminal",
     "title": "CLI 工具", "desc": "终端里能跑的工具",
     "query": "topic:cli-tool archived:false stars:>1000"},
    {"key": "tui-apps", "group": "命令行", "icon": "bi-terminal",
     "title": "TUI 应用", "desc": "终端图形界面",
     "query": "topic:tui archived:false stars:>500"},

    {"key": "android-apps", "group": "移动应用", "icon": "bi-phone",
     "title": "Android 应用", "desc": "原生 Android 开源应用",
     "query": "topic:android-application archived:false stars:>500"},
    {"key": "ios-apps", "group": "移动应用", "icon": "bi-phone",
     "title": "iOS 应用", "desc": "iOS / iPadOS 开源应用",
     "query": "topic:ios-app archived:false stars:>300"},
]


def get_category(key):
    return next((c for c in CATEGORIES if c["key"] == key), None)


def grouped_categories():
    groups = {}
    for cat in CATEGORIES:
        groups.setdefault(cat["group"], []).append(cat)
    return groups


PLATFORM_LABELS = {
    "macos": ("macOS", "bi-apple"),
    "windows": ("Windows", "bi-windows"),
    "linux": ("Linux", "bi-ubuntu"),
    "android": ("Android", "bi-android2"),
    "ios": ("iOS", "bi-phone"),
}


def detect_platform(filename):
    n = filename.lower()
    if n.endswith((".dmg", ".pkg")) or "macos" in n or "darwin" in n or "osx" in n:
        return "macos"
    if n.endswith((".exe", ".msi")) or "windows" in n or "win32" in n or "win64" in n or "win_x" in n:
        return "windows"
    if (n.endswith((".appimage", ".deb", ".rpm", ".flatpak", ".snap"))
            or ("linux" in n and not n.endswith((".tar.gz",)))):
        return "linux"
    if n.endswith(".apk"):
        return "android"
    if n.endswith(".ipa"):
        return "ios"
    return None


def build_app_package(releases):
    """Pick latest non-prerelease and group its assets by platform."""
    if not releases:
        return None
    non_pre = [r for r in releases if not r.get("prerelease")]
    latest = non_pre[0] if non_pre else releases[0]

    platforms = {}
    for asset in latest.get("assets") or []:
        plat = detect_platform(asset.get("name", ""))
        if plat and plat not in platforms:
            platforms[plat] = {
                "label": PLATFORM_LABELS[plat][0],
                "icon": PLATFORM_LABELS[plat][1],
                "filename": asset["name"],
                "url": asset["url"],
                "size_mb": round((asset.get("size", 0) or 0) / 1024 / 1024, 1),
                "downloads": asset.get("downloads", 0),
            }

    if not platforms:
        return None

    return {
        "tag": latest.get("tag_name", ""),
        "name": latest.get("name", "") or latest.get("tag_name", ""),
        "published_at": latest.get("published_at"),
        "html_url": latest.get("html_url", ""),
        "platforms": platforms,
        "total_assets": len(latest.get("assets") or []),
    }
