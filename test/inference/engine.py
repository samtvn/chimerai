from typing import Dict, List


class InferenceEngine:
    def score_preferences(
        self,
        comment: str,
        semantic_tags: List[str],
        history: Dict[str, str],
    ) -> Dict[str, float]:
        scores: Dict[str, float] = {}
        if "astringent" in semantic_tags:
            scores["dry_mouthfeel"] = 0.9
        if history.get("sweet_preference") == "high":
            scores["sweetness"] = 0.2
        return scores
