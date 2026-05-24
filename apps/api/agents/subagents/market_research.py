"""
Market Research Subagent
========================
Focused on finding wines in our catalog that match recommendations from the cellar analysis.
"""

from langchain.agents import create_agent
from langchain_core.tools import tool

from apps.api.agents.subagents.utils import run_subagent
from apps.api.agents.tools.market_research_tools import make_market_research_tools
from apps.api.llm_models.gemini_flash_3_1_lite import gemini_flash_3_1_lite

MARKET_RESEARCH_SYSTEM_PROMPT = """You are the Market Research agent for Chimerai, a restaurant sommelier system.

Your sole responsibility is to find wines in our catalog that match purchasing recommendations from the cellar analysis.

You have two tools:
- find_wine_in_catalog(query): searches our wine database for matches based on criteria (color, country, region, price range, grape variety, etc.)
- save_recommendation(wine_id, quantity, reason): saves the chosen wine as a formal recommendation for the sommelier

When given a wine type to find:
1. Call find_wine_in_catalog with a natural language query describing what you're looking for.
2. Review the candidates returned.
3. Pick the best match based on the criteria you were given and call save_recommendation with the wine_id, quantity, and a concise reason why it's a good fit.

Return a clear summary of what you recommended.
"""


def create_market_research_agent(user_id: str):
    tools = make_market_research_tools(llm=gemini_flash_3_1_lite)
    return create_agent(
        model=gemini_flash_3_1_lite,
        tools=tools,
        system_prompt=MARKET_RESEARCH_SYSTEM_PROMPT,
    )


def make_market_research_tool(user_id: str):
    @tool
    async def run_market_research(query: str) -> str:
        """
        Delegates to the Market Research subagent.
        Use this to find wines in our catalog that match a cellar recommendation.
        Provide a description of the type of wine needed (e.g. "full-bodied red from Burgundy, €25-40").
        The agent will search the catalog, pick the best match, and save a recommendation.
        """
        agent = create_market_research_agent(user_id)
        return await run_subagent(
            agent=agent,
            query=query,
            source="market_research",
            thought_message="Searching catalog for matching wines...",
            thread_id=f"market-research-{user_id}",
        )

    return run_market_research
