"""
Sales Analysis Subagent
=======================
Focused on sales performance: history per wine, top sellers, fast/slow movers.
"""

import re

from apps.api.agents.subagents.utils import run_subagent
from apps.api.llm_models.gemini_flash_3_1_lite import gemini_flash_3_1_lite
from langchain.agents import create_agent
from pydantic import BaseModel

from .tools import make_tools

SALES_ANALYSIS_SYSTEM_PROMPT = """You are the Sales Analysis agent for Chimerai, a restaurant sommelier system.

Your sole responsibility is to evaluate wine sales performance.

You have three tools:
- get_sales_history(wine_name): sales data for a specific wine
- get_top_movers: fast movers vs slow movers with sell-through rates (last 90 days)
- get_top_sellers(field, value, limit): top-selling wines, optionally filtered by field/value

Use these tools to determine whether wines sell well enough to justify restocking.
Return a clear verdict: which wines sell well, which are slow movers, and why.
"""


class SalesAnalysisResult(BaseModel):
    summary: str
    best_sellers: list[str]
    fast_movers: list[str]
    slow_movers: list[str]
    has_slow_movers: bool


def create_sales_analysis_agent(user_id: str):
    tools = make_tools(user_id)
    return create_agent(
        model=gemini_flash_3_1_lite,
        tools=tools,
        system_prompt=SALES_ANALYSIS_SYSTEM_PROMPT,
    )


def _parse_top_movers_output(text: str) -> dict:
    """
    Parse the text output from get_top_movers into structured fast/slow mover lists.
    """
    result = {
        "fast_movers": [],
        "slow_movers": [],
    }

    current_section = None
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue

        if "Fast Movers" in stripped:
            current_section = "fast"
            continue
        elif "Slow Movers" in stripped:
            current_section = "slow"
            continue
        elif stripped.startswith("No ") or "Sales Movers Analysis" in stripped:
            continue

        if current_section in ("fast", "slow"):
            # Format: "  Producer Name Vintage (Region, color) — Sold: N, Stock: M, Sell-through: X%"
            match = re.match(r"\s+(.+?)\s+\(", line)
            if match:
                full_label = match.group(1).strip()
                if current_section == "fast":
                    result["fast_movers"].append(full_label)
                else:
                    result["slow_movers"].append(full_label)

    return result


def _parse_top_sellers_output(text: str) -> list[str]:
    """
    Parse the text output from get_top_sellers into a list of wine labels.
    Format: "  Producer Name Vintage (Region, color) — N bottle(s) sold"
    """
    sellers = []
    for line in text.split("\n"):
        match = re.match(r"\s+(.+?)\s+\(", line)
        if match:
            sellers.append(match.group(1).strip())
    return sellers


async def run_sales_analysis(user_id: str, query: str) -> SalesAnalysisResult:
    """
    Hybrid approach:
    1. Call get_top_movers directly for structured fast/slow mover data
    2. Run the agent for reasoning/summary prose
    3. Return a typed SalesAnalysisResult
    """
    tools = make_tools(user_id)
    tool_map = {t.name: t for t in tools}

    # Step 1: Get structured data directly from both tools
    movers_text = await tool_map["get_top_movers"].ainvoke({})
    sellers_text = await tool_map["get_top_sellers"].ainvoke({})
    parsed_movers = _parse_top_movers_output(movers_text)
    best_sellers = _parse_top_sellers_output(sellers_text)

    # Step 2: Run agent for reasoning/summary
    agent = create_sales_analysis_agent(user_id)
    enriched_query = f"{query}\n\nTop Sellers:\n{sellers_text}\n\nSales Movers Data:\n{movers_text}"

    summary = await run_subagent(
        agent=agent,
        query=enriched_query,
        source="sales_analysis",
        thought_message="Analyzing sales data...",
        thread_id=f"sales-analysis-{user_id}",
    )

    return SalesAnalysisResult(
        summary=summary.strip() if summary else "Sales analysis complete.",
        best_sellers=best_sellers,
        fast_movers=parsed_movers["fast_movers"],
        slow_movers=parsed_movers["slow_movers"],
        has_slow_movers=len(parsed_movers["slow_movers"]) > 0,
    )
