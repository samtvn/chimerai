"""
Chimerai Orchestrator
=====================
Top-level ReAct agent that delegates to four specialized subagents:
  - inventory_audit   — cellar state, diversity, low-stock detection
  - sales_analysis    — sales history, top sellers, fast/slow movers
  - market_research   — find matching wines in catalog, save recommendations
  - menu_generator    — menu management, pricing, analysis

Decision logic (from PROJECT.md):
  Case A — Cellar balanced, no low stock → report "No action needed", stop.
  Case B — Imbalance or low stock, wine sells well → save recommendation + update menu.
  Case C — Low stock but slow seller → alert sommelier, skip purchase, stop.

The LLM decides which branch to follow via tool observations.
No hardcoded if/else logic.
"""

import logging
import os
from contextlib import asynccontextmanager

from langchain.agents import create_agent
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from apps.api.agents.subagents.inventory_audit import make_inventory_audit_tool
from apps.api.agents.subagents.menu_generator import make_menu_generator_tool
from apps.api.agents.subagents.market_research import make_market_research_tool
from apps.api.agents.subagents.sales_analysis import make_sales_analysis_tool
from apps.api.agents.tools.alert_tools import make_alert_tools
from apps.api.llm_models.gemini_flash_3_1_lite import gemini_flash_3_1_lite

logger = logging.getLogger(__name__)


ORCHESTRATOR_SYSTEM_PROMPT = """You are Chimerai, an autonomous sommelier assistant for a restaurant.

Your role is to monitor the wine cellar and proactively manage it when changes occur.
You delegate all work to four specialist subagents. Never try to answer from memory — always use your tools.

## Your five tools

- run_inventory_audit(query)      — analyzes cellar state, diversity, detects low-stock wines
- run_sales_analysis(query)       — checks how well a wine sells; identifies top sellers and movers
- run_market_research(query)      — finds matching wines in our catalog and saves recommendations
- run_menu_generator(query)       — manages menu (add/remove wines), generates tasting notes, analyzes balance
- create_alert(message, severity) — creates an alert (info/warning/error) for the sommelier

## Decision process

1. START: call run_inventory_audit to understand the current cellar state and diversity.

2. EVALUATE the result:
    - If the cellar is balanced and no wines are low in stock:
      → Report "Cellar is balanced. No action needed." and stop.
    - If there are low-stock wines:
      → Continue to step 3 for each one.

3. For each low-stock wine:
    a. Call run_sales_analysis to check if it sells well (use get_sales_movers to get sell-through rates).
    b. If it sells well (high sell-through rate):
       → Call run_market_research to find a matching wine in our catalog.
       → The market_research subagent will save a recommendation to the database.
       → Call run_menu_generator to activate the wine on the menu.
    c. If it is a slow seller (low sell-through rate):
       → Call create_alert(severity="warning") to notify the sommelier.
       → Do NOT save a recommendation. Skip purchase.

4. Optional: Review the overall menu balance:
    Call run_menu_generator with "analyze the menu" to get get_menu_analysis.
    If there are missing categories (e.g., no sparkling wines), call create_alert(severity="info").

5. END with a clear summary:
    - What you found in the cellar
    - Which wines had recommendations saved
    - Which wines were added to the menu
    - Any alerts for the sommelier

## Rules
- Never skip run_inventory_audit. It is always your first action.
- Always call run_sales_analysis before deciding to save a recommendation.
- Market research handles saving recommendations to the database — you don't need to track that separately.
- When a wine is a slow seller, create an alert instead of saving a recommendation.
- Be concise in your reasoning. Think step by step but write briefly.
- If a subagent returns an error, note it and continue with the remaining wines.
"""


@asynccontextmanager
async def get_checkpointer():
    """
    Creates an AsyncPostgresSaver checkpointer using the app's DATABASE_URL.
    Used as an async context manager so the connection is properly closed.
    """
    db_url = os.environ.get("DATABASE_URL", "")
    conn_string = db_url.replace("postgresql+psycopg://", "postgresql://")

    async with AsyncPostgresSaver.from_conn_string(conn_string) as checkpointer:
        await checkpointer.setup()
        yield checkpointer


def create_orchestrator(user_id: str, checkpointer=None):
    """
    Assembles the 4 subagent-tools + alert tool and returns a compiled ReAct agent.
    Pass a checkpointer to enable persistence across runs.
    
    Note: Tools open their own AsyncSession instances for DB operations
    to avoid session contention during concurrent tool calls.
    
    WARNING: If checkpointer is None, the agent will not persist state,
    and checkpoint-based resumability will not work.
    """
    if checkpointer is None:
        logger.warning(
            "Orchestrator created without a checkpointer. "
            "Checkpoint persistence and resumability are disabled. "
            "Pass a checkpointer to create_orchestrator() to enable crash recovery."
        )
    
    tools = [
        make_inventory_audit_tool(user_id),
        make_sales_analysis_tool(user_id),
        make_market_research_tool(user_id),
        make_menu_generator_tool(user_id),
    ]
    
    # Add alert tool (stateless, no user_id needed)
    alert_tools = make_alert_tools()
    tools.extend(alert_tools)

    return create_agent(
        model=gemini_flash_3_1_lite,
        tools=tools,
        system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
        checkpointer=checkpointer,
    )
