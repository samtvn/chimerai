from pydantic import BaseModel

class UserTasteProfile(BaseModel):
    sweetness: float = 0.5
    acidity: float = 0.5
    tannins: float = 0.5
    body: float = 0.5
