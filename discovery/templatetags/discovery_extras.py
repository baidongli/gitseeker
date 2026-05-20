from django import template

register = template.Library()

LANG_COLORS = {
    "Python": "#3572A5",
    "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6",
    "Go": "#00ADD8",
    "Rust": "#dea584",
    "Java": "#b07219",
    "C++": "#f34b7d",
    "C": "#555555",
    "Swift": "#FA7343",
    "Kotlin": "#A97BFF",
    "Ruby": "#701516",
    "PHP": "#4F5D95",
    "Shell": "#89e051",
    "HTML": "#e34c26",
    "CSS": "#563d7c",
    "Vue": "#41b883",
    "Dart": "#00B4AB",
    "Scala": "#c22d40",
    "Elixir": "#6e4a7e",
    "Haskell": "#5e5086",
}


@register.filter
def lang_color(language):
    return LANG_COLORS.get(language, "#8b949e")
