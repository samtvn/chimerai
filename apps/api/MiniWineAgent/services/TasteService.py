import json
import os
import urllib.request

from llm_models import gemini_flash_3_1_lite
from langchain.agents import create_agent
from dotenv import load_dotenv

from ..models.Aromas import Aromas
from ..models.WineTaste import WineTaste


class TasteService:
    def analyze_comment(self, comment: str) -> WineTaste:

        prompt = f"""
        You are a wine semantic analysis expert.

        Analyze the following wine comment and return ONLY valid JSON.

        Required fields:
        - tannins
        - acidity
        - sweetness
        - body
        - alcohol
        - aromas
        - confidence

        Rules:
        - Numeric values must be floats between 0 and 1
        - aromas must be an array chosen only from:
          ["fruity", "floral", "spicy", "earthy", "oaky"]
        - Return JSON only
        - No markdown
        - No explanations

        Comment:
        {comment}
        """

        structured_llm = gemini_flash_3_1_lite.with_structured_output(WineTaste)

        result = structured_llm.invoke(prompt)

        print(result)
        print(type(result))

        return result
