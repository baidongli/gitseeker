import re

BADGE_LINE_RE = re.compile(r"^\s*(\[\!\[.*?\]\(.*?\)\]\(.*?\)|\!\[.*?\]\(.*?\)|<img[^>]*>)\s*$")
HTML_TAG_RE = re.compile(r"<[^>]+>")
MD_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
EMPHASIS_RE = re.compile(r"\*\*?([^*]+)\*\*?|__([^_]+)__|`([^`]+)`")


def extract_tldr(readme, max_chars=180):
    """Return a short plain-text summary of a README's first paragraph."""
    if not readme:
        return ""

    lines = readme.split("\n")
    paragraph_lines = []
    in_html_block = False
    skip_block_lines = 0

    for raw in lines:
        line = raw.rstrip()
        stripped = line.strip()

        if skip_block_lines > 0:
            skip_block_lines -= 1
            continue

        if not stripped:
            if paragraph_lines:
                break
            continue

        if stripped.startswith("#"):
            continue
        if stripped.startswith("```") or stripped.startswith("~~~"):
            continue
        if stripped.startswith(">"):
            continue
        if stripped.startswith(("- ", "* ", "+ ", "|")):
            continue
        if BADGE_LINE_RE.match(stripped):
            continue
        if stripped.startswith("<") and not stripped.startswith("</"):
            tag_match = re.match(r"<(\w+)", stripped)
            if tag_match and tag_match.group(1).lower() in {"p", "div", "img", "br", "hr", "h1", "h2", "h3"}:
                continue
            in_html_block = True
            continue
        if in_html_block:
            if stripped.startswith("</"):
                in_html_block = False
            continue

        paragraph_lines.append(stripped)

    if not paragraph_lines:
        return ""

    text = " ".join(paragraph_lines)
    text = HTML_TAG_RE.sub("", text)
    text = MD_LINK_RE.sub(r"\1", text)
    text = EMPHASIS_RE.sub(lambda m: next(g for g in m.groups() if g), text)
    text = re.sub(r"\s+", " ", text).strip()

    if len(text) > max_chars:
        cut = text[:max_chars].rsplit(" ", 1)[0]
        text = cut + "…"
    return text
