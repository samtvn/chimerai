from pydantic import BaseModel

class Wine(BaseModel):
    id: int

    name: str
    region: str

    tannins: float
    acidity: float
    sweetness: float
    body: float
    alcohol: float
