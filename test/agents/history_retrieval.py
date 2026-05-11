from typing import Dict
from ..db.repository import get_user_history


def fetch_user_history(user_id: str) -> Dict[str, str]:
    return get_user_history(user_id)
