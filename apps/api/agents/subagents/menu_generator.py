"""
Menu Generator Subagent
=======================
Focused on menu management: viewing the current menu, adding/removing wines,
and generating sommelier-quality tasting notes.
"""

from datetime import datetime, timezone

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.agents.event_bus import AgentEvent, event_bus
from apps.api.agents.subagents.utils import extract_tool_output
from apps.api.agents.tools.menu_tools import make_menu_tools
from apps.api.llm_models.gemini_flash_3_1_lite import gemini_flash_3_1_lite

MENU_GENERATOR_SYSTEM_PROMPT = """You are the Menu Generator agent for Chimerai, a restaurant sommelier system.

Your sole responsibility is to manage the wine menu.

You have four tools:
- get_current_menu: see all active wines currently on the menu
- activate_wine_on_menu(wine_name): add a wine to the menu (generates a tasting note automatically)
- remove_wine_from_menu(wine_name): mark a wine as inactive on the menu
- generate_wine_description(wine_name): generate a fresh tasting note and food pairings for a wine

When asked to add a wine, call activate_wine_on_menu.
When asked to remove a wine, call remove_wine_from_menu.
When asked to refresh a description, call generate_wine_description.
Return a clear summary of what menu changes were made.
"""


def create_menu_generator_agent(db: AsyncSession, user_id: str):
    tools = make_menu_tools(db, user_id, llm=gemini_flash_3_1_lite)
    return create_agent(
        model=gemini_flash_3_1_lite,
        tools=tools,
        system_prompt=MENU_GENERATOR_SYSTEM_PROMPT,
    )


def make_menu_generator_tool(db: AsyncSession, user_id: str):
    @tool
    async def run_menu_generator(query: str) -> str:
        """
        Delegates to the Menu Generator subagent.
        Use this to add or remove wines from the active menu, view the current menu,
        or generate fresh tasting notes and food pairing suggestions.
        Call this after purchase_agent confirms a restock — to add the wine to the menu.
        """
        agent = create_menu_generator_agent(db, user_id)
        config = {"configurable": {"thread_id": f"menu-generator-{user_id}"}}
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
                        source="menu_generator",
                        type="thought",
                        message="Updating the wine menu...",
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
                        source="menu_generator",
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
                        source="menu_generator",
                        type="observation",
                        message=output,
                        timestamp=timestamp,
                    )
                )

        return final_message

    return run_menu_generator
