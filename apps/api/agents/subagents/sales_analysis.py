"""
Sales Analysis Subagent
=======================
Focused on sales performance: history per wine, top sellers.
"""

from datetime import datetime, timezone

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.agents.event_bus import AgentEvent, event_bus
from apps.api.agents.subagents.utils import extract_tool_output
from apps.api.agents.tools.sales_tools import make_sales_tools
from apps.api.llm_models.gemini_flash_3_1_lite import gemini_flash_3_1_lite

SALES_ANALYSIS_SYSTEM_PROMPT = """You are the Sales Analysis agent for Chimerai, a restaurant sommelier system.

Your sole responsibility is to evaluate wine sales performance.

You have two tools:
- get_sales_history(wine_name): sales data for a specific wine
- get_top_wines: the top 20 best-selling wines overall

Use these tools to determine whether a wine sells well enough to justify restocking.
Return a clear verdict: which wines sell well, which are slow movers, and why.
"""


def create_sales_analysis_agent(db: AsyncSession, user_id: str):
    tools = make_sales_tools(db, user_id)
    return create_agent(
        model=gemini_flash_3_1_lite,
        tools=tools,
        system_prompt=SALES_ANALYSIS_SYSTEM_PROMPT,
    )


def make_sales_analysis_tool(db: AsyncSession, user_id: str):
    @tool
    async def run_sales_analysis(query: str) -> str:
        """
        Delegates to the Sales Analysis subagent.
        Use this to check how well a wine sells, view top-selling wines,
        or determine if a low-stock wine is worth restocking based on sales data.
        """
        agent = create_sales_analysis_agent(db, user_id)
        config = {"configurable": {"thread_id": f"sales-analysis-{user_id}"}}
        final_message = ""

        async for event in agent.astream_events(
            {"messages": [HumanMessage(content=query)]},
            config=config,
            version="v2",
        ):
            kind = event.get("event")
            timestamp = datetime.now(timezone.utc).isoformat()

            if kind == "on_chat_model_start":
                await event_bus.publish(
                    AgentEvent(
                        source="sales_analysis",
                        type="thought",
                        message="Analyzing sales data...",
                        timestamp=timestamp,
                    )
                )
            elif kind == "on_chat_model_end":
                output = event.get("data", {}).get("output")
                if isinstance(output, AIMessage) and output.content:
                    if not output.tool_calls:
                        final_message = output.content
            elif kind == "on_tool_start":
                tool_name = event.get("name", "unknown")
                tool_input = event.get("data", {}).get("input", {})
                await event_bus.publish(
                    AgentEvent(
                        source="sales_analysis",
                        type="action",
                        message=f"Calling {tool_name}({tool_input})",
                        timestamp=timestamp,
                    )
                )
            elif kind == "on_tool_end":
                output = extract_tool_output(event)
                if len(output) > 500:
                    output = output[:500] + "..."
                await event_bus.publish(
                    AgentEvent(
                        source="sales_analysis",
                        type="observation",
                        message=output,
                        timestamp=timestamp,
                    )
                )

        return final_message

    return run_sales_analysis
