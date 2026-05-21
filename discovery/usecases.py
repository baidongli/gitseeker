"""场景化推荐: 把"我想做什么"映射到精调的 GitHub 搜索。"""

USE_CASES = [
    # 笔记与写作
    {"key": "notes", "group": "笔记 / 写作", "icon": "📝",
     "title": "笔记 / 知识库",
     "desc": "Notion / Evernote / Obsidian 类",
     "query": "topic:note-taking stars:>500 archived:false"},
    {"key": "wiki", "group": "笔记 / 写作", "icon": "📚",
     "title": "Wiki / 文档",
     "desc": "Confluence / GitBook 替代",
     "query": "topic:wiki stars:>500 archived:false"},
    {"key": "markdown-editor", "group": "笔记 / 写作", "icon": "✍️",
     "title": "Markdown 编辑器",
     "desc": "Typora / iA Writer 替代",
     "query": "topic:markdown-editor stars:>200 archived:false"},

    # 协作 / 办公
    {"key": "kanban", "group": "协作 / 办公", "icon": "📋",
     "title": "看板 / 任务管理",
     "desc": "Trello / Jira / Linear 替代",
     "query": "topic:kanban stars:>500 archived:false"},
    {"key": "team-chat", "group": "协作 / 办公", "icon": "💬",
     "title": "团队聊天 / IM",
     "desc": "Slack / Discord 替代",
     "query": "topic:chat stars:>2000 archived:false"},
    {"key": "video-conf", "group": "协作 / 办公", "icon": "🎥",
     "title": "视频会议",
     "desc": "Zoom / Meet 替代",
     "query": "topic:video-conferencing stars:>200 archived:false"},
    {"key": "calendar", "group": "协作 / 办公", "icon": "📅",
     "title": "日历 / 日程",
     "desc": "Google Calendar 替代",
     "query": "topic:calendar stars:>500 archived:false"},

    # 媒体
    {"key": "media-server", "group": "媒体 / 娱乐", "icon": "🎬",
     "title": "影视 / 媒体服务器",
     "desc": "Plex / Jellyfin 替代",
     "query": "topic:media-server stars:>300 archived:false"},
    {"key": "music", "group": "媒体 / 娱乐", "icon": "🎵",
     "title": "音乐 / 流媒体",
     "desc": "Spotify 替代 / 自建",
     "query": "topic:music-player stars:>500 archived:false"},
    {"key": "photos", "group": "媒体 / 娱乐", "icon": "🖼️",
     "title": "照片管理",
     "desc": "Google Photos / iCloud 替代",
     "query": "topic:photos stars:>1000 archived:false"},

    # 设计 / 创作
    {"key": "diagrams", "group": "设计 / 创作", "icon": "🎨",
     "title": "画图 / 流程图 / 白板",
     "desc": "Excalidraw / Drawio / tldraw",
     "query": "topic:diagrams stars:>500 archived:false"},
    {"key": "image-editor", "group": "设计 / 创作", "icon": "🖌️",
     "title": "图片编辑",
     "desc": "Photoshop / GIMP 替代",
     "query": "topic:image-editor stars:>200 archived:false"},
    {"key": "video-editor", "group": "设计 / 创作", "icon": "🎞️",
     "title": "视频剪辑",
     "desc": "Premiere / DaVinci 开源替代",
     "query": "topic:video-editor stars:>200 archived:false"},

    # 工具
    {"key": "rss", "group": "信息工具", "icon": "📰",
     "title": "RSS 阅读器",
     "desc": "Inoreader / Feedly 替代",
     "query": "topic:rss-reader stars:>300 archived:false"},
    {"key": "password", "group": "信息工具", "icon": "🔐",
     "title": "密码管理器",
     "desc": "1Password / LastPass 替代",
     "query": "topic:password-manager stars:>500 archived:false"},
    {"key": "bookmarks", "group": "信息工具", "icon": "🔖",
     "title": "书签 / 稍后读",
     "desc": "Pocket / Raindrop 替代",
     "query": "topic:bookmarks stars:>200 archived:false"},
    {"key": "translation", "group": "信息工具", "icon": "🌍",
     "title": "翻译 / 词典",
     "desc": "DeepL / Google 翻译 替代",
     "query": "topic:translation stars:>500 archived:false"},

    # 开发工具
    {"key": "git-gui", "group": "开发", "icon": "🔱",
     "title": "Git 图形客户端",
     "desc": "GitHub Desktop / SourceTree 替代",
     "query": "topic:git-client stars:>200 archived:false"},
    {"key": "terminal", "group": "开发", "icon": "⌨️",
     "title": "终端模拟器",
     "desc": "iTerm / Windows Terminal 替代",
     "query": "topic:terminal-emulator stars:>500 archived:false"},
    {"key": "api-client", "group": "开发", "icon": "🔌",
     "title": "API 测试工具",
     "desc": "Postman / Insomnia 替代",
     "query": "topic:api-client stars:>500 archived:false"},
    {"key": "database-gui", "group": "开发", "icon": "🗄️",
     "title": "数据库 GUI",
     "desc": "DBeaver / Navicat 替代",
     "query": "topic:database-gui stars:>200 archived:false"},

    # 生产力
    {"key": "launcher", "group": "生产力", "icon": "🚀",
     "title": "启动器 / 全局搜索",
     "desc": "Raycast / Alfred / Wox 替代",
     "query": "topic:launcher stars:>500 archived:false"},
    {"key": "screenshot", "group": "生产力", "icon": "📸",
     "title": "截图 / 标注",
     "desc": "Snipaste / Greenshot 类",
     "query": "topic:screenshot stars:>300 archived:false"},
    {"key": "clipboard", "group": "生产力", "icon": "📎",
     "title": "剪贴板管理",
     "desc": "剪切板历史 / 多机同步",
     "query": "topic:clipboard-manager stars:>200 archived:false"},
    {"key": "automation", "group": "生产力", "icon": "🤖",
     "title": "自动化 / 工作流",
     "desc": "n8n / Zapier 替代",
     "query": "topic:automation stars:>2000 archived:false"},

    # 网络
    {"key": "vpn", "group": "网络 / 安全", "icon": "🌐",
     "title": "VPN / 代理",
     "desc": "WireGuard / V2Ray / Outline",
     "query": "topic:vpn stars:>500 archived:false"},
    {"key": "dns", "group": "网络 / 安全", "icon": "🔍",
     "title": "DNS / 广告拦截",
     "desc": "Pi-hole / AdGuard Home",
     "query": "topic:dns stars:>500 archived:false"},
]


def grouped():
    groups = {}
    for uc in USE_CASES:
        groups.setdefault(uc["group"], []).append(uc)
    return groups


def get(key):
    return next((u for u in USE_CASES if u["key"] == key), None)
