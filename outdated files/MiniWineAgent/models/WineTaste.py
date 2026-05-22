from pydantic import BaseModel,Field
from .Aromas import Aromas

class WineTaste(BaseModel):
    tannins: float = Field(ge=0.0, le=1.0)
    acidity: float = Field(ge=0.0, le=1.0)
    sweetness: float = Field(ge=0.0, le=1.0)
    body: float = Field(ge=0.0, le=1.0)
    alcohol: float  = Field(ge=0.0, le=1.0)
    aromas: list[Aromas]
    confidence: float = Field(ge=0.0, le=1.0)
