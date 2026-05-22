from typing import List


def analyze_comment(comment: str) -> List[str]:
    # Placeholder for structured LLM output.
    lowered = comment.lower()
    tags = []
    if "dry" in lowered or "drying" in lowered:
        tags.append("astringent")
    if "dislike" in lowered:
        tags.append("negative_sentiment")
    return tags
