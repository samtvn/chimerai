from fastapi import FastAPI
from .schemas import UpdateProfileRequest, UpdateProfileResponse
from ..orchestrator.runner import run_workflow

app = FastAPI()


@app.post("/update-profile", response_model=UpdateProfileResponse)
def update_profile(payload: UpdateProfileRequest) -> UpdateProfileResponse:
    state = run_workflow(payload)
    return UpdateProfileResponse(message="profile updated", state_id=state.state_id)
