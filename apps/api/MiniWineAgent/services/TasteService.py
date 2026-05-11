import json
import os
import urllib.request

from models
from dotenv import load_dotenv

from ..models.Aromas import Aromas
from ..models.WineTaste import WineTaste

load_dotenv()

class TasteService:
    def analyze_comment(self, comment: str) -> WineTaste:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("GOOGLE_API_KEY is not set")

        prompt = (
            "You are a wine tasting assistant. Analyze the user comment and return a JSON object "
            "with these fields only: tannins, acidity, sweetness, body, alcohol, aromas, confidence. "
            "All numeric fields must be floats between 0 and 1. aromas must be an array of strings "
            "from [fruity, floral, spicy, earthy, oaky]. Return only JSON with no extra text.\n"
            f"Comment: {comment}"
        )

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2},
        }

        url = (
            "https://generativelanguage.googleapis.com/v1beta/"
            "models/gemini-1.5-flash:generateContent"
            f"?key={api_key}"
        )
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(request) as response:
            raw = response.read().decode("utf-8")

        response_json = json.loads(raw)
        text = (
            response_json.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
            .strip()
        )
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:].strip()

        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("Gemini response JSON is not an object")

        aromas_raw = data.get("aromas")
        if not isinstance(aromas_raw, list):
            raise ValueError("Gemini response missing aromas list")

        data["aromas"] = [Aromas(aroma) for aroma in aromas_raw]
        return WineTaste(**data)
