import uuid
from ..backend.schemas import UpdateProfileRequest
from .state import WorkflowState
from ..agents.semantic_analysis import analyze_comment
from ..agents.history_retrieval import fetch_user_history
from ..inference.engine import InferenceEngine
from ..agents.profile_update import update_profile


def run_workflow(payload: UpdateProfileRequest) -> WorkflowState:
    state = WorkflowState(
        state_id=str(uuid.uuid4()),
        user_id=payload.user_id,
        comment=payload.comment,
        rating=payload.rating,
    )

    state.semantic_tags = analyze_comment(state.comment)
    state.history = fetch_user_history(state.user_id)

    engine = InferenceEngine()
    state.scores = engine.score_preferences(
        comment=state.comment,
        semantic_tags=state.semantic_tags,
        history=state.history,
    )

    update_profile(state)
    return state
