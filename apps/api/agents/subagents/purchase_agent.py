"""
Purchase Agent Subagent
=======================
Focused on distributor pricing: finds the best price and restocking options for a wine.
"""

from datetime import datetime, timezone

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.agents.event_bus import AgentEvent, event_bus
from apps.api.agents.subagents.utils import extract_tool_output
from apps.api.agents.tools.purchase_tools import make_purchase_tools
from apps.api.llm_models.gemini_flash_3_1_lite import gemini_flash_3_1_lite

PURCHASE_AGENT_SYSTEM_PROMPT = """You are the Purchase Agent for Chimerai, a restaurant sommelier system.

Your sole responsibility is to research restocking options from distributors.

You have one tool:
- find_best_price(wine_name): queries mock distributors (Vinissimo, WineDirect, GlobalWine)
  and returns pricing, minimum order quantity, and delivery time for each.

Call find_best_price for the wine you are asked about.
Return a clear recommendation: which distributor to use, the price per bottle, and any relevant notes.
"""


def create_purchase_agent(db: AsyncSession, user_id: str):
    tools = make_purchase_tools(db, llm=gemini_flash_3_1_lite)
    return create_agent(
        model=gemini_flash_3_1_lite,
        tools=tools,
        system_prompt=PURCHASE_AGENT_SYSTEM_PROMPT,
    )


def make_purchase_agent_tool(db: AsyncSession, user_id: str):
    @tool
    async def run_purchase_agent(query: str) -> str:
        """
        Delegates to the Purchase Agent subagent.
        Use this to find the best distributor price for a wine that needs restocking.
        Provide the wine name in the query.
        Only call this after confirming via sales analysis that the wine is worth restocking.
        """
        agent = create_purchase_agent(db, user_id)
        config = {"configurable": {"thread_id": f"purchase-agent-{user_id}"}}
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
                        source="purchase_agent",
                        type="thought",
                        message="Researching distributor prices...",
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
                        source="purchase_agent",
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
                        source="purchase_agent",
                        type="observation",
                        message=output,
                        timestamp=timestamp,
                    )
                )

        return final_message

    return run_purchase_agent
