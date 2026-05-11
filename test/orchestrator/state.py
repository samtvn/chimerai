from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class WorkflowState:
    state_id: str
    user_id: str
    comment: str
    rating: int
    semantic_tags: List[str] = field(default_factory=list)
    history: Dict[str, str] = field(default_factory=dict)
    scores: Dict[str, float] = field(default_factory=dict)
