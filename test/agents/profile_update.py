from ..db.repository import update_user_profile
from ..orchestrator.state import WorkflowState


def update_profile(state: WorkflowState) -> None:
    update_user_profile(
        user_id=state.user_id,
        semantic_tags=state.semantic_tags,
        scores=state.scores,
    )
