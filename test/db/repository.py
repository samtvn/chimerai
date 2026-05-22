from typing import Dict, List


def get_user_history(user_id: str) -> Dict[str, str]:
    # Placeholder for SQLAlchemy query.
    return {"sweet_preference": "medium"}


def update_user_profile(user_id: str, semantic_tags: List[str], scores: Dict[str, float]) -> None:
    # Placeholder for SQLAlchemy upsert.
    _ = (user_id, semantic_tags, scores)
    return None
