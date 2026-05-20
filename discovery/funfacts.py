"""Fun data facts and time capsule for the home page."""
import random
from collections import Counter
from datetime import timedelta

from django.utils import timezone

from .models import Bookmark, Repository


def _avg_stars_persona(avg):
    if avg > 20000:
        return "重口味爆款党"
    if avg > 5000:
        return "主流热门爱好者"
    if avg < 300:
        return "深度挖宝党"
    return "中等热度爱好者"


def did_you_know():
    """Return one random fact dict, or None if not enough data."""
    bms = list(Bookmark.objects.select_related("repository"))
    facts = []
    now = timezone.now()

    if not bms:
        repos_count = Repository.objects.count()
        if repos_count > 5:
            facts.append({"emoji": "📦", "text": f"GitSeeker 已经为你索引了 {repos_count} 个项目，去收藏一些它们就属于你了"})
        facts.append({"emoji": "✨", "text": "试试主题雷达，发现本月新兴的技术潮流"})
        facts.append({"emoji": "🎲", "text": "首页的今日盲盒每天换一个项目，运气好能挖到宝藏"})
        return random.choice(facts) if facts else None

    repos = [bm.repository for bm in bms]
    n = len(bms)

    total_stars = sum(r.stars for r in repos)
    facts.append({"emoji": "⭐", "text": f"你收藏的 {n} 个项目，总 stars 加起来 <strong>{total_stars:,}</strong>"})

    langs = set(r.language for r in repos if r.language)
    if langs:
        facts.append({"emoji": "🌐", "text": f"你的收藏跨越 <strong>{len(langs)}</strong> 种编程语言"})

    all_topics = set()
    for r in repos:
        for t in r.topics or []:
            all_topics.add(t)
    if all_topics:
        facts.append({"emoji": "🏷️", "text": f"关联了 <strong>{len(all_topics)}</strong> 个不同的 topic 标签"})

    with_age = [r for r in repos if r.created_at_github]
    if with_age:
        oldest = min(with_age, key=lambda r: r.created_at_github)
        years = (now - oldest.created_at_github).days // 365
        if years >= 5:
            facts.append({"emoji": "🏛️", "text": f"你收藏过的最古老项目 <strong>{oldest.full_name}</strong> 已经 <strong>{years}</strong> 岁了"})

        newest = max(with_age, key=lambda r: r.created_at_github)
        days = (now - newest.created_at_github).days
        if days < 180:
            facts.append({"emoji": "🌱", "text": f"最年轻的收藏 <strong>{newest.full_name}</strong> 才创建 <strong>{days}</strong> 天"})

    most = max(repos, key=lambda r: r.stars)
    facts.append({"emoji": "🏆", "text": f"<strong>{most.full_name}</strong> 是你的 stars 之王，{most.stars:,} ⭐"})

    total_forks = sum(r.forks for r in repos)
    if total_forks > 1000:
        facts.append({"emoji": "🔀", "text": f"这些项目一共被 fork 了 <strong>{total_forks:,}</strong> 次"})

    total_issues = sum(r.open_issues for r in repos)
    if total_issues > 100:
        facts.append({"emoji": "🐛", "text": f"加起来还有 <strong>{total_issues:,}</strong> 个 open issues 等待解决"})

    month_counts = Counter(bm.created_at.strftime("%Y 年 %m 月") for bm in bms)
    if len(month_counts) > 1:
        most_month, count = month_counts.most_common(1)[0]
        if count >= 2:
            facts.append({"emoji": "📈", "text": f"你在 <strong>{most_month}</strong> 最积极，那个月收藏了 {count} 个项目"})

    first = min(bms, key=lambda b: b.created_at)
    days_first = (now - first.created_at).days
    if days_first > 7:
        facts.append({"emoji": "📅", "text": f"挖宝之旅已经走过 <strong>{days_first}</strong> 天，第一个收藏的是 {first.repository.full_name}"})

    if n >= 5:
        avg_stars = total_stars // n
        facts.append({"emoji": "📊", "text": f"平均 stars <strong>{avg_stars:,}</strong> · 你是 <strong>{_avg_stars_persona(avg_stars)}</strong>"})

    avatars = set(r.owner_login for r in repos)
    if len(avatars) > 5:
        facts.append({"emoji": "👥", "text": f"你的收藏来自 <strong>{len(avatars)}</strong> 个不同的 owner / 组织"})

    return random.choice(facts) if facts else None


def time_capsule():
    """Return list of historical highlights for today."""
    items = []
    now = timezone.now()
    today = now.date()
    bms = list(Bookmark.objects.select_related("repository"))

    bookmark_milestones = [
        (365, "1 年前的今天"),
        (730, "2 年前的今天"),
        (180, "半年前的今天"),
        (30, "1 个月前的今天"),
    ]
    for days_ago, label in bookmark_milestones:
        target_date = today - timedelta(days=days_ago)
        match = next((bm for bm in bms if bm.created_at.date() == target_date), None)
        if match:
            items.append({
                "kind": "anniversary",
                "label": label,
                "bookmark": match,
            })

    if bms:
        first = min(bms, key=lambda b: b.created_at)
        days_first = (now - first.created_at).days
        for milestone in (30, 100, 180, 365, 730, 1000):
            if days_first == milestone:
                items.append({
                    "kind": "milestone",
                    "text": f"挖宝 {milestone} 天纪念日 🎉 你的第一个收藏是 {first.repository.full_name}",
                })
                break

    for years_back in (10, 5, 3):
        target_year = today.year - years_back
        if target_year < 2008:
            continue
        repo = (
            Repository.objects
            .filter(
                created_at_github__year=target_year,
                created_at_github__month=today.month,
                created_at_github__day=today.day,
            )
            .order_by("-stars")
            .first()
        )
        if repo:
            items.append({
                "kind": "history",
                "years": years_back,
                "repo": repo,
            })
            break

    return items
