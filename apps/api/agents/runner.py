"""
Agent Runner
============
Bridges the FastAPI event system to the orchestrator.

Two entry points:
  1. run_once(trigger)     — called manually or by the API route
  2. run_event_listener()  — background task, fires on "wine_sold" events from event_bus
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from langchain_core.messages import AIMessage, HumanMessage
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.agents.event_bus import AgentEvent, event_bus
from apps.api.agents.orchestrator import create_orchestrator, get_checkpointer
from apps.api.database.database import AsyncSessionLocal
from apps.api.database.dependencies import get_demo_user_id
from apps.api.database.models.agent_run_session import AgentRunSession, RunSessionStatus

logger = logging.getLogger(__name__)

# The 4 subagent-tool names registered on the orchestrator.
# Used to filter stream events so only orchestrator-level delegation is shown here;
# each subagent publishes its own inner tool events directly.
_SUBAGENT_TOOLS = {
    "run_inventory_audit",
    "run_sales_analysis",
    "run_purchase_agent",
    "run_menu_generator",
}


async def _get_or_create_session(db: AsyncSession, user_id: str, trigger: str):
    """
    Get the latest session for a user, or create a new one.

    Logic:
    - If there's a failed session for this user, reuse its thread_id (auto-resume).
    - If there's a running session, reuse its thread_id (continue from checkpoint).
    - Otherwise, create a new session with a fresh thread_id.

    Returns:
        (thread_id, session, should_resume_from_checkpoint)
    """
    # Look up the latest session for this user
    result = await db.execute(
        select(AgentRunSession)
        .where(AgentRunSession.user_id == user_id)
        .order_by(desc(AgentRunSession.created_at))
        .limit(1)
    )
    latest_session = result.scalars().first()

    # If there's a failed or running session, reuse it
    if latest_session and latest_session.status in (
        RunSessionStatus.FAILED,
        RunSessionStatus.RUNNING,
    ):
        # Update the session status back to RUNNING and timestamp
        latest_session.status = RunSessionStatus.RUNNING
        latest_session.updated_at = datetime.now(timezone.utc)
        db.add(latest_session)
        await db.commit()

        # Return the existing thread_id; LangGraph will load from checkpoint
        return latest_session.thread_id, latest_session, True

    # Create a new session with a fresh thread_id
    new_thread_id = f"orchestrator-{user_id}-{uuid.uuid4().hex[:8]}"
    new_session = AgentRunSession(
        user_id=user_id,
        thread_id=new_thread_id,
        status=RunSessionStatus.RUNNING,
        trigger=trigger,
    )
    db.add(new_session)
    await db.commit()

    return new_thread_id, new_session, False


async def _update_session_status(
    db: AsyncSession, session: AgentRunSession, status: RunSessionStatus
):
    """Update the status of a session and commit."""
    session.status = status
    session.updated_at = datetime.now(timezone.utc)
    db.add(session)
    await db.commit()


async def run_once(trigger: str) -> str:
    """
    Opens a DB session, resolves the demo user, and runs the orchestrator.
    Publishes start/end events to the event_bus so the SSE stream shows activity.

    Checkpoint resumability:
    - Looks up the latest session for the user.
    - If it's failed or running, reuses the thread_id (LangGraph resumes from checkpoint).
    - Otherwise, creates a fresh session with a new thread_id.

    Returns the agent's final response string.
    """
    async with AsyncSessionLocal() as db:
        user_id = str(await get_demo_user_id(db))

        await event_bus.publish(
            AgentEvent(
                source="orchestrator",
                type="action",
                message=f"Triggered: {trigger}",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )

        try:
            # Get or create session (checkpoint recovery happens here)
            thread_id, session, resuming = await _get_or_create_session(db, user_id, trigger)

            if resuming:
                await event_bus.publish(
                    AgentEvent(
                        source="orchestrator",
                        type="thought",
                        message="Resuming from last checkpoint...",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    )
                )
                logger.info(f"Resuming orchestrator session {thread_id} for user {user_id}")

            async with get_checkpointer() as checkpointer:
                agent = create_orchestrator(user_id, checkpointer=checkpointer)
                config = {"configurable": {"thread_id": thread_id}}
                final_message = ""

                # If resuming, don't send a new message; LangGraph will resume from checkpoint
                input_data = None if resuming else {"messages": [HumanMessage(content=trigger)]}

                async for event in agent.astream_events(
                    input_data,
                    config=config,
                    version="v2",
                ):
                    await _handle_stream_event(event)

                    # Capture final orchestrator message — on_chat_model_end fires for
                    # every LLM generation; the last text response (no tool_calls) is the answer
                    if event.get("event") == "on_chat_model_end":
                        output = event.get("data", {}).get("output")
                        if (
                            isinstance(output, AIMessage)
                            and output.content
                            and not output.tool_calls
                        ):
                            content = output.content
                            # Gemini may return a list of content blocks; extract text
                            if isinstance(content, list):
                                content = " ".join(
                                    block.get("text", "") if isinstance(block, dict) else str(block)
                                    for block in content
                                )
                            final_message = content

                # Mark session as completed
                await _update_session_status(db, session, RunSessionStatus.COMPLETED)

                await event_bus.publish(
                    AgentEvent(
                        source="orchestrator",
                        type="final",
                        message=final_message,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    )
                )

                return final_message

        except Exception as e:
            error_msg = f"Orchestrator error: {str(e)}"
            logger.error(error_msg, exc_info=True)

            # Mark session as failed so it can be resumed next time
            try:
                async with AsyncSessionLocal() as db_retry:
                    user_id_retry = str(await get_demo_user_id(db_retry))
                    result = await db_retry.execute(
                        select(AgentRunSession)
                        .where(AgentRunSession.user_id == user_id_retry)
                        .order_by(desc(AgentRunSession.created_at))
                        .limit(1)
                    )
                    session_retry = result.scalars().first()
                    if session_retry:
                        await _update_session_status(
                            db_retry, session_retry, RunSessionStatus.FAILED
                        )
            except Exception as retry_error:
                logger.error(f"Failed to mark session as failed: {retry_error}", exc_info=True)

            await event_bus.publish(
                AgentEvent(
                    source="orchestrator",
                    type="alert",
                    message=error_msg,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
            )
            return error_msg


def _extract_output(output) -> str:
    """
    Safely extract a string from a tool output.
    At the orchestrator level, on_tool_end delivers a ToolMessage object
    (not a plain string) when subagent-tools return. Extract .content if needed.
    """
    if hasattr(output, "content"):
        return str(output.content)
    if isinstance(output, str):
        return output
    return str(output)


async def _handle_stream_event(event: dict) -> None:
    """
    Handles orchestrator-level stream events.

    The subagents publish their own tool-level events directly to event_bus.
    At the orchestrator level we only see on_tool_start/end for the 4 subagent-tools
    (run_inventory_audit, run_sales_analysis, run_purchase_agent, run_menu_generator),
    and on_chat_model_start when the orchestrator LLM is reasoning about delegation.
    """
    kind = event.get("event")
    timestamp = datetime.now(timezone.utc).isoformat()

    if kind == "on_chat_model_start":
        # Only emit thought when the orchestrator is deciding — identified by having
        # no active subagent tool in the chain (metadata langgraph_node == "agent"
        # and no tool name in tags). Simplest reliable check: metadata check.
        metadata = event.get("metadata", {})
        if metadata.get("langgraph_node") == "agent" and not metadata.get("langgraph_step", 0) == 0:
            await event_bus.publish(
                AgentEvent(
                    source="orchestrator",
                    type="thought",
                    message="Deciding which subagent to call...",
                    timestamp=timestamp,
                )
            )

    elif kind == "on_tool_start":
        tool_name = event.get("name", "unknown_tool")
        # Only emit for the 4 top-level subagent-tools; subagents publish their own events
        if tool_name not in _SUBAGENT_TOOLS:
            return
        tool_input = event.get("data", {}).get("input", {})
        if isinstance(tool_input, dict) and "query" in tool_input:
            tool_input = tool_input["query"]
        await event_bus.publish(
            AgentEvent(
                source="orchestrator",
                type="action",
                message=f"Delegating to {tool_name}: {tool_input}",
                timestamp=timestamp,
            )
        )

    elif kind == "on_tool_end":
        tool_name = event.get("name", "unknown_tool")
        # Only emit for the 4 top-level subagent-tools
        if tool_name not in _SUBAGENT_TOOLS:
            return
        raw_output = event.get("data", {}).get("output", "")
        output = _extract_output(raw_output)
        if len(output) > 300:
            output = output[:300] + "..."
        await event_bus.publish(
            AgentEvent(
                source="orchestrator",
                type="observation",
                message=f"{tool_name} completed: {output}",
                timestamp=timestamp,
            )
        )


async def run_event_listener() -> None:
    """
    Background task. Subscribes to the event_bus and fires the orchestrator
    whenever a 'wine_sold' event is published.

    Includes exponential backoff restart logic so one crash doesn't kill
    the listener permanently.

    Started in main.py lifespan alongside the existing listeners.
    """
    retry_delay = 1  # seconds
    max_retry_delay = 60  # seconds

    while True:
        try:
            queue = event_bus.subscribe()
            logger.info("Agent runner: listening for wine_sold events")
            retry_delay = 1  # Reset backoff on successful subscription

            while True:
                agent_event = await queue.get()

                if agent_event.type == "wine_sold":
                    logger.info(f"Agent runner: received wine_sold event — {agent_event.message}")
                    trigger = f"A wine was sold: {agent_event.message}. Analyze the cellar and take appropriate action."
                    await run_once(trigger)

        except Exception as e:
            logger.error(f"Agent runner event listener error: {e}", exc_info=True)
            logger.info(f"Restarting listener in {retry_delay} seconds...")

            # Exponential backoff: double the delay up to max_retry_delay
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, max_retry_delay)

        finally:
            try:
                event_bus.unsubscribe(queue)
            except Exception as e:
                logger.warning(f"Error unsubscribing from event_bus: {e}")
