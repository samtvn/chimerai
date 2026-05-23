from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.database.models.wines import Wine


def make_purchase_tools(db: AsyncSession, llm) -> list:

    @tool
    async def find_best_price(wine_name: str) -> str:
        """
        Given a wine name, queries mock distributors to find the best available
        market price and alternatives. Provide the wine_name parameter to search
        for a specific wine. Use this when you need to evaluate restocking options
        and compare distributor prices before making a purchase recommendation.
        """

        # 1. Look up the wine in the database to get baseline info
        result = await db.execute(
            select(
                Wine.name, Wine.market_price, Wine.region, Wine.vintage, Wine.color, Wine.producer
            )
            .where(Wine.name.ilike(f"%{wine_name}%"))
            .limit(1)
        )
        wine = result.first()

        if not wine:
            return f"No wine matching '{wine_name}' found in the database."

        # 2. Build context string about the wine for the LLM
        wine_info = (
            f"Wine: {wine.name}\n"
            f"Producer: {wine.producer}\n"
            f"Region: {wine.region}\n"
            f"Vintage: {wine.vintage}\n"
            f"Color: {wine.color}\n"
            f"Current market price (reference): €{wine.market_price}"
        )

        # 3. Ask the LLM to roleplay as a distributor aggregator
        # This is how you call an LLM in LangChain:
        # - You build a list of messages (HumanMessage, SystemMessage, etc.)
        # - You call llm.ainvoke(messages) — the `a` prefix means async
        # - The response is an AIMessage object; .content gives you the string
        prompt = f"""You are a wine distributor aggregator with access to three distributors: 
Vinissimo, WineDirect, and GlobalWine.

A sommelier wants to restock the following wine:

{wine_info}

Generate realistic mock pricing from all three distributors. 
Prices should vary slightly around the reference market price (±10-15%).
For each distributor provide: price per bottle, minimum order quantity, and delivery time.
Then clearly state which distributor offers the best deal and why.
Keep the response concise and practical."""

        response = await llm.ainvoke([HumanMessage(content=prompt)])

        return response.content

    return [find_best_price]
