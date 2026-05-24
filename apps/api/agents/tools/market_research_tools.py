from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_, select
from typing import Optional

from apps.api.database.database import AsyncSessionLocal
from apps.api.database.models.wines import Wine
from apps.api.database.models.recommendations import Recommendation
from apps.api.database.repositories.recommendations_repository import RecommendationRepository
from apps.api.database.dependencies import get_demo_user_id


class CatalogSearchCriteria(BaseModel):
    """Structured extraction of search criteria from natural language query."""
    colour: Optional[str] = Field(default=None, description="Wine colour (red, white, rosé, sparkling)")
    country: Optional[str] = Field(default=None, description="Target country")
    region: Optional[str] = Field(default=None, description="Target region")
    grape_variety: Optional[str] = Field(default=None, description="Target grape variety")
    min_price: Optional[float] = Field(default=None, description="Minimum price in euros")
    max_price: Optional[float] = Field(default=None, description="Maximum price in euros")


class CatalogWine(BaseModel):
    """A wine from the catalog to present to the user."""
    wine_id: int
    name: str
    producer: str
    region: str
    country: str
    color: str
    grape_variety: Optional[str]
    vintage: Optional[str]
    market_price: Optional[float]


def make_market_research_tools(llm) -> list:
    """Create market research tools for finding wines in our catalog and saving recommendations."""

    @tool
    async def find_wine_in_catalog(query: str) -> str:
        """
        Searches the wine catalog for matches based on a natural language query.
        
        Example queries:
        - "full-bodied red from France, €20-35"
        - "dry white from Burgundy under €40"
        - "sparkling wine, Italian"
        
        Returns a list of matching wines with their key details so you can pick the best one.
        """
        # Use LLM with structured output to extract search criteria
        prompt = f"""Extract wine search criteria from this query:

"{query}"

Return the structured criteria. If a criterion is not mentioned, leave it as null.
Price should be extracted as min and max in euros."""

        structured_llm = llm.with_structured_output(CatalogSearchCriteria)
        criteria = await structured_llm.ainvoke([HumanMessage(content=prompt)])

        # Build SQLAlchemy filters
        filters = []

        if criteria.colour:
            filters.append(Wine.color.ilike(f"%{criteria.colour}%"))

        if criteria.country:
            filters.append(Wine.country.ilike(f"%{criteria.country}%"))

        if criteria.region:
            filters.append(Wine.region.ilike(f"%{criteria.region}%"))

        if criteria.grape_variety:
            filters.append(Wine.grape_variety.ilike(f"%{criteria.grape_variety}%"))

        if criteria.min_price is not None:
            filters.append(Wine.market_price >= criteria.min_price)

        if criteria.max_price is not None:
            filters.append(Wine.market_price <= criteria.max_price)

        # Query the database
        try:
            async with AsyncSessionLocal() as db:
                query_obj = select(Wine)
                if filters:
                    query_obj = query_obj.where(and_(*filters))
                query_obj = query_obj.limit(8)

                result = await db.execute(query_obj)
                wines = result.scalars().all()

                if not wines:
                    return "No wines found matching your criteria. Try adjusting the search parameters."

                # Format results for the subagent LLM to choose from
                lines = ["Found matching wines in the catalog:"]
                lines.append("")
                for wine in wines:
                    price_str = f"€{wine.market_price:.2f}" if wine.market_price else "Price TBD"
                    lines.append(
                        f"ID {wine.id}: {wine.name} | {wine.producer} | "
                        f"{wine.region}, {wine.country} | {wine.color} | "
                        f"{wine.grape_variety or 'N/A'} | {wine.vintage or 'NV'} | {price_str}"
                    )

                return "\n".join(lines)

        except Exception as e:
            return f"Error searching catalog: {str(e)}"

    @tool
    async def save_recommendation(wine_id: int, quantity: int, reason: str) -> str:
        """
        Saves a wine recommendation to the database for the sommelier to review.
        
        Call this after you've chosen the best matching wine from find_wine_in_catalog.
        
        Args:
            wine_id: The wine ID from the catalog
            quantity: How many bottles to buy
            reason: Concise reason why this wine is recommended (e.g. "Matches cellar gap in French reds")
        
        Returns:
            Confirmation message
        """
        try:
            async with AsyncSessionLocal() as db:
                user_id = await get_demo_user_id(db)

                # Look up the wine to get market price
                wine_result = await db.execute(select(Wine).where(Wine.id == wine_id))
                wine = wine_result.scalars().first()

                if not wine:
                    return f"Error: Wine ID {wine_id} not found in catalog."

                market_price = wine.market_price or 0.0

                # Create recommendation
                repo = RecommendationRepository(db, read_only=False)
                await repo.create(
                    user_id=user_id,
                    wine_id=wine_id,
                    quantity=quantity,
                    market_price=market_price,
                    priority_score=0.85,  # Default high score; can be refined later
                    recommendation_reason=reason,
                )

                return (
                    f"✓ Recommendation saved: {wine.name} (qty: {quantity}) at €{market_price:.2f}/bottle. "
                    f"Reason: {reason}"
                )

        except Exception as e:
            return f"Error saving recommendation: {str(e)}"

    return [find_wine_in_catalog, save_recommendation]
