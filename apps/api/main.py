from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
load_dotenv()
from MiniWineAgent.AnalyzeCommentRequest import AnalyzeCommentRequest
from MiniWineAgent.models.WineRepository import WineRepository
from MiniWineAgent.services.TasteService import TasteService
import requests
from bs4 import BeautifulSoup



def test_soup():
    html = requests.get("https://www.idealwine.com/fr/prix-vin/133180------Bouteille-Charente-Cognac-Louis-XIII-Remy-Martin-ambre").text
    soup = BeautifulSoup(html, "html.parser")
    print(type(soup))
    return soup




app = FastAPI(title="Chimerai API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"status": "ok", "message": "Chimerai API is running"}

def create_user():
    return True

@app.get("/health")
async def health():
    test_soup()
    return{"data" : f"{test_soup()}"}

repo = WineRepository("MiniWineAgent/data/wines.json")
taste_service = TasteService()

@app.post("/analyze-comment")
def analyze_comment(
    request: AnalyzeCommentRequest
):

    result = taste_service.analyze_comment(
        request.comment
    )

    return {"data": "OK"}
