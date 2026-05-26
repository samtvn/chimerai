"""Market Analysis Agent for selecting wines based on criteria"""

from __future__ import annotations

import re
from typing import Optional, Tuple

from sqlalchemy import and_, select
from pydantic import BaseModel, Field

from .models import MarketAnalysisCriteria, MarketAnalysisResult
from apps.api.database.database import AsyncReadSessionLocal
from apps.api.database.models.wines import Wine
from apps.api.llm_models.gemini_flash_3_1_lite import gemini_flash_3_1_lite


class WineSelection(BaseModel):
    """LLM-selected wine choice from candidate list."""

    wine_id: int = Field(..., description="Wine ID chosen from the candidate list")
    detailed_explanation: str = Field(
        ..., description="Why this wine is a great fit for the criteria"
    )


class MarketAnalysisAgent:
    """Select a market wine that fits the requested criteria."""

    async def analyze_recommendation(
        self,
        criteria: MarketAnalysisCriteria,
        quantity: int,
        recommendation_title: str,
    ) -> MarketAnalysisResult:
        """Analyze market availability and select a wine from the database."""
        async with AsyncReadSessionLocal() as session:
            filters = self._build_filters(criteria)
            query = select(Wine)
            if filters:
                query = query.where(and_(*filters))

            result = await session.execute(query.limit(25))
            wines = result.scalars().all()

            if not wines:
                fallback = await session.execute(select(Wine).limit(25))
                wines = fallback.scalars().all()
                if not wines:
                    raise ValueError("No wines available in the database")

            candidates = []
            for wine in wines:
                fit_score, fit_notes = self._score_fit(criteria, wine)
                candidates.append(
                    {
                        "wine": wine,
                        "fit_score": fit_score,
                        "fit_notes": fit_notes,
                    }
                )

            selection = await self._choose_wine_with_llm(
                criteria,
                recommendation_title,
                candidates,
            )

            selected = next(
                (item for item in candidates if item["wine"].id == selection.wine_id),
                None,
            )
            if not selected:
                selected = max(candidates, key=lambda item: item["fit_score"])
                selection = WineSelection(
                    wine_id=selected["wine"].id,
                    detailed_explanation=(
                        "LLM selection was invalid; choosing the highest fit-score candidate instead."
                    ),
                )

            wine = selected["wine"]
            fit_score = selected["fit_score"]
            fit_notes = selected["fit_notes"]

            price_per_bottle = wine.market_price
            total_price = None
            if price_per_bottle is not None:
                total_price = round(price_per_bottle * quantity, 2)

            return MarketAnalysisResult(
                recommendation_title=recommendation_title,
                wine_id=wine.id,
                wine_name=wine.name,
                producer=wine.producer,
                country=wine.country,
                region=wine.region,
                sub_region=wine.appellation,
                vintage=wine.vintage,
                grape_variety=wine.grape_variety,
                colour=wine.color,
                price_per_bottle=price_per_bottle,
                quantity=quantity,
                total_price=total_price,
                fit_score=fit_score,
                fit_notes=fit_notes,
                detailed_explanation=selection.detailed_explanation,
                criteria=criteria,
            )

    async def _choose_wine_with_llm(
        self,
        criteria: MarketAnalysisCriteria,
        recommendation_title: str,
        candidates: list[dict],
    ) -> WineSelection:
        """Use the LLM to pick the best wine from candidates."""
        candidate_summary = []
        for item in candidates:
            wine = item["wine"]
            candidate_summary.append(
                {
                    "wine_id": wine.id,
                    "name": wine.name,
                    "producer": wine.producer,
                    "country": wine.country,
                    "region": wine.region,
                    "sub_region": wine.appellation,
                    "vintage": wine.vintage,
                    "grape_variety": wine.grape_variety,
                    "colour": wine.color,
                    "price_per_bottle": wine.market_price,
                    "fit_score": item["fit_score"],
                    "fit_notes": item["fit_notes"],
                }
            )

        prompt = (
            "You are selecting the best wine for a market recommendation. "
            "Choose exactly one wine_id from the candidate list and explain why it fits.\n\n"
            f"Recommendation title: {recommendation_title}\n"
            f"Criteria: {criteria.model_dump()}\n\n"
            "Candidates:\n"
            f"{candidate_summary}\n\n"
            "Return a short but detailed explanation focusing on how the selection aligns "
            "with the criteria and any tradeoffs."
        )

        structured_llm = gemini_flash_3_1_lite.with_structured_output(WineSelection)
        return await structured_llm.ainvoke(prompt)

    def _build_filters(self, criteria: MarketAnalysisCriteria) -> list:
        filters = []
        if criteria.colour:
            filters.append(Wine.color.ilike(criteria.colour))
        if criteria.country:
            filters.append(Wine.country.ilike(criteria.country))
        if criteria.region:
            filters.append(Wine.region.ilike(criteria.region))
        if criteria.sub_region:
            filters.append(Wine.appellation.ilike(criteria.sub_region))
        if criteria.grape_variety:
            filters.append(Wine.grape_variety.ilike(criteria.grape_variety))
        if criteria.vintage:
            filters.append(Wine.vintage == criteria.vintage)

        price_bounds = self._parse_numeric_range(criteria.price_range)
        if price_bounds:
            min_price, max_price = price_bounds
            filters.append(Wine.market_price.is_not(None))
            filters.append(Wine.market_price >= min_price)
            filters.append(Wine.market_price <= max_price)

        return filters

    def _score_fit(self, criteria: MarketAnalysisCriteria, wine: Wine) -> Tuple[float, list[str]]:
        checks = []
        notes = []

        checks.append(self._match_text(criteria.colour, wine.color, "colour", notes))
        checks.append(self._match_text(criteria.country, wine.country, "country", notes))
        checks.append(self._match_text(criteria.region, wine.region, "region", notes))
        checks.append(self._match_text(criteria.sub_region, wine.appellation, "sub_region", notes))
        checks.append(
            self._match_text(criteria.grape_variety, wine.grape_variety, "grape_variety", notes)
        )
        checks.append(self._match_text(criteria.vintage, wine.vintage, "vintage", notes))
        checks.append(self._match_price(criteria.price_range, wine.market_price, notes))

        relevant_checks = [check for check in checks if check is not None]
        if not relevant_checks:
            return 0.0, notes or ["No criteria provided to evaluate fit"]

        match_count = sum(1 for check in relevant_checks if check)
        fit_score = round(match_count / len(relevant_checks), 2)
        if not notes:
            notes.append("Criteria matched without conflicts")

        return fit_score, notes

    def _match_text(
        self,
        expected: Optional[str],
        actual: Optional[str],
        label: str,
        notes: list[str],
    ) -> Optional[bool]:
        if not expected:
            return None
        if not actual:
            notes.append(f"{label} missing on selected wine")
            return False
        if expected.strip().lower() == actual.strip().lower():
            return True
        notes.append(f"{label} differs (wanted {expected}, got {actual})")
        return False

    def _match_price(
        self,
        price_range: str,
        price: Optional[float],
        notes: list[str],
    ) -> Optional[bool]:
        if not price_range:
            return None
        if price is None:
            notes.append("price not available for selected wine")
            return False
        bounds = self._parse_numeric_range(price_range)
        if not bounds:
            notes.append("price range could not be parsed")
            return False
        min_price, max_price = bounds
        if min_price <= price <= max_price:
            return True
        notes.append(f"price {price} outside range {min_price}-{max_price}")
        return False

    def _parse_numeric_range(self, text: str) -> Optional[Tuple[float, float]]:
        if not text:
            return None
        numbers = [float(match) for match in re.findall(r"\d+(?:\.\d+)?", text)]
        if not numbers:
            return None
        if len(numbers) == 1:
            return numbers[0], numbers[0]
        return numbers[0], numbers[1]
