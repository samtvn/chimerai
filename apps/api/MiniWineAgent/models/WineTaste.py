from pydantic import BaseModel,Field
from .Aromas import Aromas

class WineTaste(BaseModel):
    tannins: float
    acidity: float
    sweetness: float
    body: float
    alcohol: float
    aromas: list[Aromas]
    confidence: float = Field(ge=0.0, le=1.0)
