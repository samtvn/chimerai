from pydantic import BaseModel
from .UserTasteProfile import UserTasteProfile

class User(BaseModel):
    id: str
    name: str
    email: str
    taste_profile: UserTasteProfile
