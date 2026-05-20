import os
import logging

logger = logging.getLogger(__name__)

try:
    import anthropic
    _HAS_SDK = True
except ImportError:
    _HAS_SDK = False


def is_available():
    return _HAS_SDK and bool(os.environ.get("ANTHROPIC_API_KEY"))


SYSTEM_PROMPT = """你是一个开源项目分析专家。给定一个 GitHub 项目的名称、描述和 README 节选，用一句中文（30-60字）总结这个项目是做什么的、解决什么问题。

要求：
- 只输出一句话，不要任何前缀、解释或 Markdown
- 用通俗易懂的中文，避免直译英文
- 突出项目的核心价值或独特之处
"""


def summarize_repo(full_name, description, readme_excerpt):
    """Generate a one-sentence Chinese summary. Returns "" on failure."""
    if not is_available():
        return ""

    user_content = f"""项目名: {full_name}
描述: {description or "(无)"}

README 节选:
{readme_excerpt[:4000]}"""

    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=200,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )
        for block in response.content:
            if block.type == "text":
                return block.text.strip()
        return ""
    except Exception as e:
        logger.warning("AI summary failed for %s: %s", full_name, e)
        return ""
