"""
Inventory Audit Subagent
========================
Focused on cellar state analysis: bottle counts, regional balance, low-stock warnings.
"""

import re
from apps.api.agents.subagents.utils import run_subagent
from apps.api.llm_models.gemini_flash_3_1_lite import gemini_flash_3_1_lite
from langchain.agents import create_agent
from pydantic import BaseModel

# from ..tools import make_inventory_tools

INVENTORY_AUDIT_SYSTEM_PROMPT = """You are the Inventory Audit agent for Chimerai, a restaurant sommelier system.

Your sole responsibility is to analyze the current state of the wine cellar and provide insights.

You have four tools:
- get_all_wines: list all wines in the cellar with quantity of each
- get_wines_by_field(field, value): filter wines by a specific field and value (e.g. color='red', country='France', region='Bordeaux', grape_variety='Chardonnay'). Returns detailed wine list.
- flag_low_stock: list of wines at 3 bottles or fewer
- get_wine_count: total bottle count in the cellar

Your task:
1. Examine the cellar data provided to you
2. Write a clear, concise summary of the cellar state and any issues
3. Identify diversity gaps (missing categories)
4. Flag any concerns about low-stock wines

Be analytical but concise. Focus on actionable insights.
"""


class InventoryAuditResult(BaseModel):
    summary: str
    wines_by_color: dict[str, int]
    wines_by_country: dict[str, int]
    wines_by_region: dict[str, int]
    wines_by_variety: dict[str, int]
    low_stock_wines: list[str]
    has_low_stock: bool
    diversity_gaps: list[str]


# def create_inventory_audit_agent(user_id: str):
#     tools = make_inventory_tools(user_id)
#     return create_agent(
#         model=gemini_flash_3_1_lite,
#         tools=tools,
#         system_prompt=INVENTORY_AUDIT_SYSTEM_PROMPT,
#     )


def _parse_cellar_overview_output(text: str) -> dict:
    """
    Parse the text output from get_cellar_overview into structured data.
    Extracts counts by color, country, region, and variety.
    """
    result = {
        "wines_by_color": {},
        "wines_by_country": {},
        "wines_by_region": {},
        "wines_by_variety": {},
        "low_stock_wines": [],
        "diversity_gaps": [],
    }

    lines = text.split("\n")

    current_section = None
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue

        # Detect sections (match on stripped line)
        if line_stripped.startswith("By Color:"):
            current_section = "color"
            continue
        elif line_stripped.startswith("By Country:"):
            current_section = "country"
            continue
        elif line_stripped.startswith("By Region:"):
            current_section = "region"
            continue
        elif line_stripped.startswith("By Grape Variety:"):
            current_section = "variety"
            continue
        elif line_stripped.startswith("Missing categories:"):
            current_section = "missing"
            # Parse missing categories: "Missing categories: red, white, ..."
            match = re.search(r"Missing categories: (.+)", line_stripped)
            if match:
                categories = [c.strip() for c in match.group(1).split(",")]
                result["diversity_gaps"] = categories
            continue
        elif line_stripped.startswith("Low stock"):
            current_section = "low_stock"
            continue
        elif line_stripped == "✓ All major color categories represented":
            current_section = None
            continue
        elif line_stripped.startswith("No low stock"):
            current_section = None
            continue

        # Parse data lines based on current section (use original line with spaces)
        if current_section in ["color", "country", "region", "variety"]:
            # Format: "  name: count bottles (pct%)"
            match = re.match(r"  (.+?): (\d+) bottles", line)
            if match:
                name, count = match.groups()
                count = int(count)
                if current_section == "color":
                    result["wines_by_color"][name] = count
                elif current_section == "country":
                    result["wines_by_country"][name] = count
                elif current_section == "region":
                    result["wines_by_region"][name] = count
                elif current_section == "variety":
                    result["wines_by_variety"][name] = count

        elif current_section == "low_stock":
            # Format: "  wine_name: count bottle(s)"
            match = re.match(r"  (.+?): (\d+) bottle", line)
            if match:
                wine_name = match.group(1)
                result["low_stock_wines"].append(wine_name)

    return result


async def run_inventory_audit(user_id: str, query: str) -> InventoryAuditResult:
    """
    Delegates to the Inventory Audit subagent.

    This is a hybrid approach:
    1. Call get_cellar_overview directly to get accurate structured data
    2. Run the agent for reasoning/analysis on that data
    3. Combine both into a complete InventoryAuditResult
    """
    from .tools import make_inventory_tools

    # Step 1: Get the raw cellar data directly from the tool
    tools = make_inventory_tools(user_id)
    tool_map = {t.name: t for t in tools}
    get_cellar_overview_tool = tool_map["get_cellar_overview"]

    overview_text = await get_cellar_overview_tool.ainvoke({})

    # Parse the overview into structured counts
    parsed_data = _parse_cellar_overview_output(overview_text)

    # Step 2: Run the agent for reasoning/summary (optional, for insights)
    agent = create_inventory_audit_agent(user_id)

    # Provide the overview data to the agent for analysis
    enriched_query = f"{query}\n\nCellar Overview:\n{overview_text}"

    summary_text = await run_subagent(
        agent=agent,
        query=enriched_query,
        source="inventory_audit",
        thought_message="Analyzing cellar state...",
        thread_id=f"inventory-audit-{user_id}",
    )

    # Extract summary from agent response
    summary = summary_text.strip() if summary_text else "Cellar analysis complete."

    # Build the final structured result
    result = InventoryAuditResult(
        summary=summary,
        wines_by_color=parsed_data["wines_by_color"],
        wines_by_country=parsed_data["wines_by_country"],
        wines_by_region=parsed_data["wines_by_region"],
        wines_by_variety=parsed_data["wines_by_variety"],
        low_stock_wines=parsed_data["low_stock_wines"],
        has_low_stock=len(parsed_data["low_stock_wines"]) > 0,
        diversity_gaps=parsed_data["diversity_gaps"],
    )

    return result
