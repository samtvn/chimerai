from pydantic import BaseModel, Field


class UpdateProfileRequest(BaseModel):
    user_id: str = Field(..., examples=["u_123"])
    comment: str = Field(..., examples=["I dislike wines that dry my mouth."])
    rating: int = Field(..., ge=1, le=5)


class UpdateProfileResponse(BaseModel):
    message: str
    state_id: str
