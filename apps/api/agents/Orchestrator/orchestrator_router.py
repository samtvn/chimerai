from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

from apps.api.agents.Orchestrator.state import OrchestratorState
from apps.api.agents.event_bus import AgentEvent, event_bus
from apps.api.agents.events import Event
from apps.api.llm_models.gemini_flash_3_1_lite import gemini_flash_3_1_lite


class OrchestratorRouterDecision(BaseModel):
    next_node: Literal[
        "analyze_cellar",
        "sales_analysis",
        "run_market_analysis",
        "persist_recommendations",
    ] = Field(..., description="The next graph node to execute")
    analysis_query: str = Field(
        default="",
        description="Instruction for the selected node, or empty when persisting",
    )
    validated_analysis: str = Field(
        default="",
        description="Final validation summary when the router is satisfied",
    )
    reasoning: str = Field(..., description="Concise explanation for the routing decision")


def _event_type(event: Event | str | None) -> str | None:
    if event is None:
        return None
    if isinstance(event, str):
        return event
    return getattr(event, "event_type", None)


def _wine_ids(event: Event | str | None) -> list[str]:
    if event is None or isinstance(event, str):
        return []

    wine_ids = getattr(event, "wine_ids", None)
    if not wine_ids:
        return []
    return [str(wine_id) for wine_id in wine_ids]


def _safe_dump(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return [_safe_dump(item) for item in value]
    if isinstance(value, dict):
        return {key: _safe_dump(item) for key, item in value.items()}
    if hasattr(value, "model_dump"):
        try:
            return _safe_dump(value.model_dump())
        except Exception:
            return str(value)
    if hasattr(value, "dict"):
        try:
            return _safe_dump(value.dict())
        except Exception:
            return str(value)
    return str(value)


def _state_snapshot(state: OrchestratorState) -> dict[str, Any]:
    event = state.get("trigger_event")
    snapshot = {
        "trigger_event_type": _event_type(event),
        "trigger_event_wine_ids": _wine_ids(event),
        "cellar_analysis": _safe_dump(state.get("cellar_analysis")),
        "sales_analysis": _safe_dump(state.get("sales_analysis")),
        "market_analysis": _safe_dump(state.get("market_analysis")),
        "validated_analysis": _safe_dump(state.get("validated_analysis")),
        "analysis_query": state.get("analysis_query"),
        "sales_query": state.get("sales_query"),
        "market_analysis_query": state.get("market_analysis_query"),
        "next_node": state.get("next_node"),
        "workflow_phase": state.get("workflow_phase"),
        "router_iterations": state.get("router_iterations", 0),
    }
    return snapshot


def _router_prompt(state: OrchestratorState) -> str:
    snapshot = json.dumps(_state_snapshot(state), indent=2, ensure_ascii=True, default=str)
    return f"""You are the Orchestrator router for Chimerai.

You must choose the next LangGraph node and the query that node should receive.
You are allowed to inspect only the provided state snapshot and you must use the available analysis evidence.

Workflow rules:
- If the state does not yet contain enough cellar evidence, choose analyze_cellar.
- If a wine_sold event contains specific wine IDs, you may choose sales_analysis with a focused query.
- If a wine_sold event contains specific wine IDs, you may also choose analyze_cellar with a focused query.
- If sales_analysis has been run and has produced evidence of a certain wine or wine type to be relevant, you may choose run_market_analysis to find matching catalog wines and market context.
- When you are satisfied, populate validated_analysis with a concise but complete validation summary.
- Only choose persist_recommendations when the analysis is validated and complete enough to save.
- Keep the analysis moving forward; do not repeat the same node unless the state clearly still lacks the needed evidence.
- Prefer progress over stalling. If the state is already sufficiently analyzed, finalize with persist_recommendations.

Return a single structured decision.

State snapshot:
{snapshot}
"""


def _fallback_decision(state: OrchestratorState) -> OrchestratorRouterDecision:
    event = state.get("trigger_event")
    event_type = _event_type(event)
    wine_ids = _wine_ids(event)

    if state.get("validated_analysis"):
        return OrchestratorRouterDecision(
            next_node="persist_recommendations",
            analysis_query="",
            validated_analysis=str(state.get("validated_analysis")),
            reasoning="Validated analysis already exists; persist the recommendations.",
        )

    # Auto-run a single sales_analysis when the trigger explicitly indicates a sale
    if event_type == "wine_sold" and wine_ids:
        if not state.get("sales_analysis"):
            return OrchestratorRouterDecision(
                next_node="sales_analysis",
                analysis_query=(
                    "Run a focused sales analysis for the recently sold wines: "
                    + ", ".join(wine_ids)
                ),
                reasoning="A wine_sold event with specific wine IDs needs targeted sales context.",
            )
        # If sales_analysis already exists, do not re-run it here; fall through to other checks

    if state.get("cellar_analysis") is None:
        return OrchestratorRouterDecision(
            next_node="analyze_cellar",
            analysis_query="Run a full cellar analysis to establish the current cellar state.",
            reasoning="No cellar analysis is available yet.",
        )

    if event_type == "analysis_run" and state.get("sales_analysis") is None and state.get("market_analysis") is None:
        return OrchestratorRouterDecision(
            next_node="sales_analysis",
            analysis_query="Analyze sales performance for the wines that matter most in the current cellar context.",
            reasoning="Cellar evidence exists, but the router still needs sales evidence before validating.",
        )

    if state.get("market_analysis") is None and state.get("sales_analysis") is not None:
        return OrchestratorRouterDecision(
            next_node="run_market_analysis",
            analysis_query="Find matching catalog wines for the strongest cellar recommendations and summarize the fit.",
            reasoning="Sales evidence exists, but market matching is still missing.",
        )

    return OrchestratorRouterDecision(
        next_node="persist_recommendations",
        analysis_query="",
        validated_analysis="Cellar, sales, and market evidence are sufficient to persist recommendations.",
        reasoning="The available evidence is enough to validate the analysis.",
    )


async def orchestrator_router(user_id: str, state: OrchestratorState) -> str:
    """Call Gemini to decide the next graph node and attach the query for that node."""
    del user_id

    timestamp = datetime.now(timezone.utc).isoformat()
    await event_bus.publish(
        AgentEvent(
            source="orchestrator",
            type="thought",
            message="Evaluating the next workflow step.",
            timestamp=timestamp,
        )
    )

    # Respect explicit triggers first
    event = state.get("trigger_event")
    event_type = _event_type(event)
    wine_ids = _wine_ids(event)

    # Auto-run full analysis when an analysis event is explicitly requested
    if event_type in ("analysis", "analysis_run"):
        state["analysis_query"] = "Run a full cellar analysis because an analysis event was triggered."
        state["workflow_phase"] = "auto_analysis"
        state["next_node"] = "analyze_cellar"
        state["router_iterations"] = int(state.get("router_iterations", 0)) + 1
        return "analyze_cellar"

    if event_type in ("analysis", "analysis_run") and state.get("sales_analysis") is None:
        state["analysis_query"] = "Run a full sales analysis over recent sales."
        state["workflow_phase"] = "auto_sales_analysis"
        state["next_node"] = "sales_analysis"
        state["router_iterations"] = int(state.get("router_iterations", 0)) + 1
        return "sales_analysis"

    # Auto-run sales_analysis once for an explicit wine_sold trigger (only if not already present)
    if event_type == "wine_sold" and wine_ids and not state.get("sales_analysis"):
        state["analysis_query"] = (
            "Run a focused sales analysis for the recently sold wines: " + ", ".join(wine_ids)
        )
        state["workflow_phase"] = "auto_sales_analysis"
        state["next_node"] = "sales_analysis"
        state["router_iterations"] = int(state.get("router_iterations", 0)) + 1
        return "sales_analysis"

    # Otherwise delegate to the LLM to make the decision
    decision = None
    if os.environ.get("GOOGLE_API_KEY"):
        try:
            router_llm = gemini_flash_3_1_lite.with_structured_output(OrchestratorRouterDecision)
            prompt = _router_prompt(state)
            decision = await router_llm.ainvoke(prompt)
        except Exception:
            decision = None

    if decision is None:
        decision = _fallback_decision(state)

    # Apply decision into state
    state["next_node"] = decision.next_node
    state["analysis_query"] = decision.analysis_query or None
    state["workflow_phase"] = (
        "validated" if decision.next_node == "persist_recommendations" else decision.next_node
    )
    state["router_iterations"] = int(state.get("router_iterations", 0)) + 1

    # Safety: force persist_recommendations after too many router iterations
    max_iters = int(os.environ.get("ORCHESTRATOR_MAX_ROUTER_ITERATIONS", "8"))
    if state["router_iterations"] >= max_iters and decision.next_node != "persist_recommendations":
        state["validated_analysis"] = (
            decision.validated_analysis.strip() or "No recommendations after max router iterations."
        )
        state["next_node"] = "persist_recommendations"
        state["analysis_query"] = ""
        state["workflow_phase"] = "validated"
        await event_bus.publish(
            AgentEvent(
                source="orchestrator",
                type="action",
                message="Routing forced to persist_recommendations after reaching the iteration cap.",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )
        return "persist_recommendations"

    if decision.next_node == "persist_recommendations":
        validated = decision.validated_analysis.strip() or decision.reasoning.strip()
        if validated:
            state["validated_analysis"] = validated

    await event_bus.publish(
        AgentEvent(
            source="orchestrator",
            type="action",
            message=f"Router selected {decision.next_node}: {decision.reasoning}",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    )

    return decision.next_node
