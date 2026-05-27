"""
Shared utilities for subagents.
"""

import logging
from datetime import datetime, timezone

from langchain_core.messages import AIMessage

from apps.api.events.bus import AgentEvent, event_bus

logger = logging.getLogger(__name__)


def extract_tool_output(event: dict) -> str:
    """
    Safely extract the string output from an on_tool_end event.
    In astream_events v2, the output may be a ToolMessage object or a plain string.
    """
    raw = event.get("data", {}).get("output", "")
    if hasattr(raw, "content"):
        return str(raw.content)
    return str(raw) if raw is not None else ""


async def run_subagent(
    agent,
    query: str,
    source: str,
    thought_message: str,
    thread_id: str,
) -> str:
    """
    Generic runner for all subagents.
    
    Handles the standard streaming loop:
    - Publishes thought events on LLM start
    - Publishes action/observation events for tool calls
    - Handles Gemini content extraction (list of blocks)
    - Catches exceptions and returns error strings
    
    Args:
        agent: The LangGraph agent instance to run
        query: The input query/instruction
        source: Event source name (e.g. "inventory_audit", "purchase_agent")
        thought_message: Message to publish on LLM start (e.g. "Reasoning about cellar state...")
        thread_id: LangGraph thread_id for checkpoint tracking
    
    Returns:
        Final text response from the subagent, or error message if an exception occurs
    """
    try:
        config = {"configurable": {"thread_id": thread_id}}
        final_message = ""

        async for event in agent.astream_events(
            {"messages": [{"type": "human", "content": query}]},
            config=config,
            version="v2",
        ):
            kind = event.get("event")
            timestamp = datetime.now(timezone.utc).isoformat()

            if kind == "on_chat_model_start":
                await event_bus.publish(
                    AgentEvent(
                        source=source,
                        type="thought",
                        message=thought_message,
                        timestamp=timestamp,
                    )
                )
            elif kind == "on_chat_model_end":
                output = event.get("data", {}).get("output")
                if isinstance(output, AIMessage) and output.content:
                    # Extract content if it's a list (Gemini may return list of blocks)
                    content = output.content
                    if isinstance(content, list):
                        content = " ".join(
                            block.get("text", "") if isinstance(block, dict) else str(block)
                            for block in content
                        )
                    # Only capture text responses (not tool-call-only responses)
                    if not output.tool_calls:
                        final_message = content
            elif kind == "on_tool_start":
                tool_name = event.get("name", "unknown")
                tool_input = event.get("data", {}).get("input", {})
                await event_bus.publish(
                    AgentEvent(
                        source=source,
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
                        source=source,
                        type="observation",
                        message=output,
                        timestamp=timestamp,
                    )
                )

        return final_message

    except Exception as e:
        error_msg = f"Error: {source} failed — {e}"
        logger.error(f"{source} subagent error: {e}", exc_info=True)
        return error_msg
