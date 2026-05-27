import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.agents.Orchestrator.checkpointer import get_checkpointer
from apps.api.agents.Orchestrator.new_orchestrator import Orchestrator
from apps.api.database.database import AsyncSessionLocal
from apps.api.database.dependencies import get_demo_user_id
from apps.api.database.models.agent_run_session import AgentRunSession, RunSessionStatus
from apps.api.database.repositories.cellar_repository import CellarRepository
from apps.api.events.bus import AgentEvent, event_bus

logger = logging.getLogger(__name__)


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
    result = await db.execute(
        select(AgentRunSession)
        .where(AgentRunSession.user_id == user_id)
        .order_by(desc(AgentRunSession.created_at))
        .limit(1)
    )
    latest_session = result.scalars().first()

    if latest_session and latest_session.status in (
        RunSessionStatus.FAILED,
        RunSessionStatus.RUNNING,
    ):
        latest_session.status = RunSessionStatus.RUNNING
        latest_session.updated_at = datetime.now(timezone.utc)
        db.add(latest_session)
        await db.commit()
        return latest_session.thread_id, latest_session, True

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


def _build_graph_input(agent_event: AgentEvent):
    """Seed a new graph run with fresh routing state while keeping checkpointed analysis."""
    from apps.api.events.schemas import AnalysisRunEvent, WineSoldEvent

    if agent_event.type == "wine_sold":
        wine_ids: list[str] = []
        quantity = 1

        if agent_event.message:
            try:
                payload = json.loads(agent_event.message)
            except json.JSONDecodeError:
                payload = None

            if isinstance(payload, dict):
                raw_wine_id = payload.get("wine_id") or payload.get("wine_ids")
                if isinstance(raw_wine_id, list):
                    wine_ids = [str(wid) for wid in raw_wine_id if wid is not None]
                elif raw_wine_id is not None:
                    wine_ids = [str(raw_wine_id)]
                quantity = int(payload.get("quantity", quantity) or quantity)
            else:
                wine_ids = [agent_event.message]

        trigger_ev = WineSoldEvent(wine_ids=wine_ids, quantity=quantity)
    elif agent_event.type == "analysis_run":
        trigger_ev = AnalysisRunEvent(agent_name="orchestrator", analysis_id=uuid.uuid4().hex)
    else:
        # For unknown event types, default to an analysis_run
        trigger_ev = AnalysisRunEvent(agent_name="orchestrator", analysis_id=uuid.uuid4().hex)

    return {
        "trigger_event": trigger_ev,
        "router_iterations": 0,
        "next_node": None,
        "workflow_phase": None,
        "analysis_query": None,
        "sales_query": None,
        "market_analysis_query": None,
        "validated_analysis": None,
    }


async def run_once(agent_event: AgentEvent) -> str:
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
                message=f"Triggered: {agent_event.type}",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )

        try:
            thread_id, session, resuming = await _get_or_create_session(
                db, user_id, f"Triggered: {agent_event.type}"
            )

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
                cellar_repo = CellarRepository(db)
                from uuid import UUID

                agent = Orchestrator(
                    cellar_repo=cellar_repo, user_id=UUID(user_id), checkpointer=checkpointer
                ).graph
                config = {"configurable": {"thread_id": thread_id}}

                input_data = _build_graph_input(agent_event)

                async for event in agent.astream_events(input_data, config=config, version="v2"):
                    pass

                final_state = await agent.aget_state(config)
                final_message = final_state.values.get("validated_analysis", "Workflow completed.")

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


async def run_event_listener() -> None:
    """
    Background task. Subscribes to the event_bus and fires the orchestrator
    whenever a 'wine_sold' or 'analysis_run' event is published.

    Includes exponential backoff restart logic so one crash doesn't kill
    the listener permanently.
    """
    retry_delay = 1
    max_retry_delay = 60

    while True:
        try:
            queue = event_bus.subscribe()
            logger.info("Agent runner: listening for events")
            retry_delay = 1

            while True:
                agent_event = await queue.get()

                if agent_event.type in ("wine_sold", "analysis_run"):
                    logger.info(f"Agent runner: received {agent_event.type} event — {agent_event.message}")
                    await run_once(agent_event)

        except Exception as e:
            logger.error(f"Agent runner event listener error: {e}", exc_info=True)
            logger.info(f"Restarting listener in {retry_delay} seconds...")
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, max_retry_delay)

        finally:
            try:
                event_bus.unsubscribe(queue)
            except Exception as e:
                logger.warning(f"Error unsubscribing from event_bus: {e}")
