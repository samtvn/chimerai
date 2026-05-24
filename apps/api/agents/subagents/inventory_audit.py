"""
Inventory Audit Subagent
========================
Focused on cellar state analysis: bottle counts, regional balance, low-stock warnings.
"""

from langchain.agents import create_agent
from langchain_core.tools import tool

from apps.api.agents.subagents.utils import run_subagent
from apps.api.agents.tools.inventory_tools import make_inventory_tools
from apps.api.llm_models.gemini_flash_3_1_lite import gemini_flash_3_1_lite

INVENTORY_AUDIT_SYSTEM_PROMPT = """You are the Inventory Audit agent for Chimerai, a restaurant sommelier system.

Your sole responsibility is to analyze the current state of the wine cellar.

You have three tools:
- get_cellar_summary: full breakdown of bottles by region, color, and low-stock warnings
- flag_low_stock: list of wines at 2 bottles or fewer
- get_cellar_analysis: diversity score, balance analysis, missing color categories

Always call get_cellar_summary first. Then call flag_low_stock if low-stock wines were found.
Optionally call get_cellar_analysis if you want to understand overall cellar balance and diversity gaps.
Return a clear, concise summary of the cellar state, which wines need attention, and any diversity concerns.
"""


def create_inventory_audit_agent(user_id: str):
    tools = make_inventory_tools(user_id)
    return create_agent(
        model=gemini_flash_3_1_lite,
        tools=tools,
        system_prompt=INVENTORY_AUDIT_SYSTEM_PROMPT,
    )


def make_inventory_audit_tool(user_id: str):
    @tool
    async def run_inventory_audit(query: str) -> str:
        """
        Delegates to the Inventory Audit subagent.
        Use this to analyze the current cellar state, check for low-stock wines,
        and get a breakdown of inventory by region and color.
        Always call this first before any other subagent.
        """
        agent = create_inventory_audit_agent(user_id)
        return await run_subagent(
            agent=agent,
            query=query,
            source="inventory_audit",
            thought_message="Reasoning about cellar state...",
            thread_id=f"inventory-audit-{user_id}",
        )

    return run_inventory_audit
