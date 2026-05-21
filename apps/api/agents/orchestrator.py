from uuid import UUID
from typing import TypedDict, Optional

from langgraph.graph import StateGraph, START, END

from agents.event_bus import event_bus, AgentEvent
from database.database import AsyncSessionLocal
from database.repositories.wine_repository import WineRepository
from database.repositories.cellar_repository import CellarRepository
from database.repositories.transactions_repository import TransactionRepository
from database.repositories.alert_repository import AlertRepository
from database.repositories.user_repository import UserRepository


class OrchestratorState(TypedDict, total=False):
    trigger: str
    trigger_data: Optional[dict]
    inventory_audit_result: Optional[str]
    sales_analysis_result: Optional[str]
    purchase_result: Optional[str]
    menu_result: Optional[str]
    final_summary: Optional[str]
    should_analyze_sales: bool
    should_purchase: bool
    should_update_menu: bool
    alerts: list[dict]


async def _emit(source: str, event_type: str, message: str):
    await event_bus.publish(AgentEvent(source=source, type=event_type, message=message))


async def _get_demo_user_id() -> UUID:
    async with AsyncSessionLocal() as db:
        repo = UserRepository(db, read_only=True)
        user = await repo.get_by_username("chimerai_bistro")
        return user.id if user else None


async def inventory_audit_node(state: OrchestratorState) -> dict:
    source = "inventory_audit"
    await _emit(source, "thought", "Starting cellar audit. Checking current stock levels and diversity...")

    async with AsyncSessionLocal() as db:
        user_id = await _get_demo_user_id()
        if not user_id:
            await _emit(source, "observation", "No demo user found. Skipping audit.")
            return {"inventory_audit_result": "No user", "should_analyze_sales": False}

        cellar_repo = CellarRepository(db, read_only=True)
        in_stock = await cellar_repo.get_user_cellar_in_stock(user_id, limit=1000)
        await _emit(source, "action", f"Retrieved {len(in_stock)} bottles in stock from cellar")

        wine_ids = list(set(c.wine_id for c in in_stock))
        wine_repo = WineRepository(db, read_only=True)

        regions: dict[str, int] = {}
        colors: dict[str, int] = {}
        low_stock_wines = []
        total_market_value = 0.0
        wine_stock: dict[int, int] = {}

        for c in in_stock:
            wine_stock[c.wine_id] = wine_stock.get(c.wine_id, 0) + 1

        for wid, cnt in wine_stock.items():
            wine = await wine_repo.get_by_id(wid)
            if wine:
                regions[wine.region] = regions.get(wine.region, 0) + cnt
                colors[wine.color] = colors.get(wine.color, 0) + cnt
                if wine.market_price:
                    total_market_value += wine.market_price * cnt
                if cnt <= 2:
                    low_stock_wines.append(
                        {"name": wine.name, "vintage": wine.vintage, "stock": cnt, "region": wine.region}
                    )

        total = len(in_stock)
        total_wines = len(wine_ids)

        imbalance_regions = []
        for region, cnt in regions.items():
            pct = round(cnt / total * 100) if total else 0
            if pct < 10 and total_wines > 3:
                imbalance_regions.append(f"{region} at {pct}%")

        obs_parts = [
            f"Cellar has {total} bottles across {total_wines} wines.",
            f"Total market value: €{total_market_value:,.0f}.",
        ]
        if low_stock_wines:
            obs_parts.append(f"LOW STOCK: {len(low_stock_wines)} wines at ≤2 bottles:")
            for w in low_stock_wines:
                obs_parts.append(f"  - {w['name']} {w['vintage'] or ''}: {w['stock']} bottle(s) ({w['region']})")
        if imbalance_regions:
            obs_parts.append(f"REGIONAL IMBALANCE: {', '.join(imbalance_regions)}")

        observation = " ".join(obs_parts)
        await _emit(source, "observation", observation)

        should_analyze = len(low_stock_wines) > 0 or len(imbalance_regions) > 0
        if should_analyze:
            await _emit(source, "thought", "Issues detected. I should check sales data before making recommendations.")
        else:
            await _emit(source, "thought", "Cellar looks balanced. No action needed.")

        return {
            "inventory_audit_result": observation,
            "should_analyze_sales": should_analyze,
        }


async def sales_analysis_node(state: OrchestratorState) -> dict:
    source = "sales_analysis"
    await _emit(source, "thought", "Analyzing sales history to understand which wines are commercially important...")

    async with AsyncSessionLocal() as db:
        user_id = await _get_demo_user_id()
        if not user_id:
            return {"sales_analysis_result": "No user", "should_purchase": False}

        txn_repo = TransactionRepository(db, read_only=True)
        sales = await txn_repo.get_user_sales(user_id, limit=200)
        purchases = await txn_repo.get_user_purchases(user_id, limit=200)
        await _emit(source, "action", f"Retrieved {len(sales)} sales and {len(purchases)} purchase records")

        wine_sales: dict[int, int] = {}
        wine_revenue: dict[int, float] = {}
        for s in sales:
            wine_sales[s.wine_id] = wine_sales.get(s.wine_id, 0) + s.quantity
            wine_revenue[s.wine_id] = wine_revenue.get(s.wine_id, 0) + (s.purchase_price or 0) * s.quantity

        wine_repo = WineRepository(db, read_only=True)
        top_sellers = sorted(wine_sales.items(), key=lambda x: -x[1])[:5]

        obs_parts = [f"Total sales transactions: {len(sales)}."]
        if top_sellers:
            obs_parts.append("Top selling wines:")
            for wid, qty in top_sellers:
                wine = await wine_repo.get_by_id(wid)
                if wine:
                    rev = wine_revenue.get(wid, 0)
                    obs_parts.append(f"  - {wine.name} {wine.vintage or ''}: {qty} bottles sold, €{rev:,.0f} revenue")

        cellar_repo = CellarRepository(db, read_only=True)
        in_stock = await cellar_repo.get_user_cellar_in_stock(user_id, limit=1000)
        stock_counts: dict[int, int] = {}
        for c in in_stock:
            stock_counts[c.wine_id] = stock_counts.get(c.wine_id, 0) + 1

        restock_candidates = []
        for wid, sold_qty in wine_sales.items():
            current_stock = stock_counts.get(wid, 0)
            if current_stock <= 2 and sold_qty >= 2:
                wine = await wine_repo.get_by_id(wid)
                if wine:
                    restock_candidates.append(
                        {"name": wine.name, "vintage": wine.vintage, "sold": sold_qty, "stock": current_stock}
                    )

        if restock_candidates:
            obs_parts.append("RESTOCK CANDIDATES (high sales + low stock):")
            for c in restock_candidates:
                obs_parts.append(f"  - {c['name']} {c['vintage'] or ''}: sold {c['sold']}, stock {c['stock']}")

        observation = " ".join(obs_parts)
        await _emit(source, "observation", observation)

        should_purchase = len(restock_candidates) > 0
        if should_purchase:
            await _emit(
                source, "thought",
                "Found wines that sell well but are running low. I should find the best restocking options.",
            )
        else:
            await _emit(source, "thought", "No strong restock candidates found from sales data.")

        return {
            "sales_analysis_result": observation,
            "should_purchase": should_purchase,
        }


MOCK_DISTRIBUTORS = [
    {"name": "Maison du Vin", "discount": 0.92},
    {"name": "EuroWine Direct", "discount": 0.95},
    {"name": "Chais & Domaines", "discount": 0.88},
]


async def purchase_agent_node(state: OrchestratorState) -> dict:
    source = "purchase_agent"
    await _emit(source, "thought", "Researching best purchase options from distributor catalogs...")

    async with AsyncSessionLocal() as db:
        user_id = await _get_demo_user_id()
        if not user_id:
            return {"purchase_result": "No user", "should_update_menu": False}

        cellar_repo = CellarRepository(db, read_only=True)
        in_stock = await cellar_repo.get_user_cellar_in_stock(user_id, limit=1000)
        stock_counts: dict[int, int] = {}
        for c in in_stock:
            stock_counts[c.wine_id] = stock_counts.get(c.wine_id, 0) + 1

        txn_repo = TransactionRepository(db, read_only=True)
        sales = await txn_repo.get_user_sales(user_id, limit=200)
        wine_sales: dict[int, int] = {}
        for s in sales:
            wine_sales[s.wine_id] = wine_sales.get(s.wine_id, 0) + s.quantity

        wine_repo = WineRepository(db, read_only=True)
        await _emit(source, "action", "Querying distributor APIs for current market prices...")

        recommendations = []
        low_stock_wines = [wid for wid, cnt in stock_counts.items() if cnt <= 2 and wine_sales.get(wid, 0) >= 2]

        for wid in low_stock_wines[:5]:
            wine = await wine_repo.get_by_id(wid)
            if not wine or not wine.market_price:
                continue

            best_dist = min(MOCK_DISTRIBUTORS, key=lambda d: d["discount"])
            best_price = round(wine.market_price * best_dist["discount"], 2)
            margin = round((wine.market_price - best_price) / best_price * 100, 1)

            recommendations.append(
                {
                    "wine": f"{wine.name} {wine.vintage or ''}",
                    "market_price": wine.market_price,
                    "best_distributor": best_dist["name"],
                    "best_price": best_price,
                    "margin_pct": margin,
                    "region": wine.region,
                }
            )

        obs_parts = []
        if recommendations:
            obs_parts.append(f"Found {len(recommendations)} restock recommendations:")
            for r in recommendations:
                obs_parts.append(
                    f"  - {r['wine']}: Market €{r['market_price']:.0f}, "
                    f"Best €{r['best_price']:.0f} from {r['best_distributor']} "
                    f"(margin {r['margin_pct']}%)"
                )
        else:
            obs_parts.append("No profitable restock options found at this time.")

        observation = " ".join(obs_parts)
        await _emit(source, "observation", observation)

        should_update = len(recommendations) > 0
        if should_update:
            await _emit(source, "thought", "Good purchase options found. I should update the wine menu to reflect current stock.")
        else:
            await _emit(source, "thought", "No purchase needed. I'll alert the sommelier about the situation instead.")

        return {
            "purchase_result": observation,
            "should_update_menu": should_update,
        }


async def menu_generator_node(state: OrchestratorState) -> dict:
    source = "menu_generator"
    await _emit(source, "thought", "Regenerating the wine menu based on current cellar status...")

    async with AsyncSessionLocal() as db:
        user_id = await _get_demo_user_id()
        if not user_id:
            return {"menu_result": "No user"}

        cellar_repo = CellarRepository(db, read_only=True)
        in_stock = await cellar_repo.get_user_cellar_in_stock(user_id, limit=1000)
        await _emit(source, "action", "Reading current wine list and generating updated descriptions...")

        wine_ids = list(set(c.wine_id for c in in_stock))
        wine_repo = WineRepository(db, read_only=True)

        menu_items = []
        for wid in wine_ids:
            wine = await wine_repo.get_by_id(wid)
            if wine:
                stock = sum(1 for c in in_stock if c.wine_id == wid)
                if stock > 0:
                    desc = f"{wine.name} {wine.vintage or ''} — {wine.region}, {wine.country}. "
                    if wine.grape_variety:
                        desc += f"{wine.grape_variety}. "
                    if wine.market_price:
                        desc += f"€{wine.market_price:.0f}/bottle. "
                    if wine.drink_from and wine.drink_to:
                        desc += f"Drink {wine.drink_from}–{wine.drink_to}."
                    menu_items.append(desc)

        await _emit(
            source, "observation",
            f"Wine menu regenerated with {len(menu_items)} active wines. Descriptions and pairings updated.",
        )
        await _emit(source, "thought", "Menu is now up to date with current inventory.")

        return {"menu_result": f"Menu updated with {len(menu_items)} wines"}


async def orchestrator_think_node(state: OrchestratorState) -> dict:
    source = "orchestrator"
    trigger = state.get("trigger", "unknown")
    await _emit(source, "thought", f"Orchestrator activated by trigger: {trigger}. I'll start with an inventory audit.")
    return {}


async def orchestrator_decide_after_audit_node(state: OrchestratorState) -> str:
    source = "orchestrator"
    should_analyze = state.get("should_analyze_sales", False)
    if should_analyze:
        await _emit(source, "thought", "Audit found issues. Routing to sales analysis for deeper investigation.")
        return "sales_analysis"
    await _emit(source, "thought", "Cellar is healthy. Ending orchestration — no further action needed.")
    return "finalize"


async def orchestrator_decide_after_sales_node(state: OrchestratorState) -> str:
    source = "orchestrator"
    should_purchase = state.get("should_purchase", False)
    if should_purchase:
        await _emit(source, "thought", "Sales analysis confirms restock opportunity. Routing to purchase agent.")
        return "purchase_agent"
    await _emit(source, "thought", "Sales don't justify restocking. I'll alert the sommelier instead.")
    return "finalize"


async def orchestrator_decide_after_purchase_node(state: OrchestratorState) -> str:
    source = "orchestrator"
    should_update = state.get("should_update_menu", False)
    if should_update:
        await _emit(source, "thought", "Purchase recommendations ready. I should update the wine menu to reflect changes.")
        return "menu_generator"
    return "finalize"


async def finalize_node(state: OrchestratorState) -> dict:
    source = "orchestrator"

    audit = state.get("inventory_audit_result", "")
    sales = state.get("sales_analysis_result", "")
    purchase = state.get("purchase_result", "")
    menu = state.get("menu_result", "")

    summary_parts = []
    if audit:
        summary_parts.append("Inventory audit: completed.")
    if sales:
        summary_parts.append("Sales analysis: completed.")
    if purchase:
        summary_parts.append("Purchase recommendations: generated.")
    if menu:
        summary_parts.append("Menu update: completed.")

    summary = " | ".join(summary_parts) if summary_parts else "No actions taken."

    alerts_created = []
    async with AsyncSessionLocal() as db:
        alert_repo = AlertRepository(db, read_only=False)
        user_id = await _get_demo_user_id()

        if state.get("should_analyze_sales") and not state.get("should_purchase"):
            alert = await alert_repo.create(
                user_id=user_id,
                message="Cellar has low stock items but sales don't justify restocking. Consider manual review.",
                severity="warning",
                source_agent="orchestrator",
            )
            alerts_created.append(str(alert.id))

    await _emit(source, "final", f"Orchestration complete. {summary}")
    return {"final_summary": summary, "alerts": alerts_created}


def build_orchestrator_graph() -> StateGraph:
    graph = StateGraph(OrchestratorState)

    graph.add_node("orchestrator_think", orchestrator_think_node)
    graph.add_node("inventory_audit", inventory_audit_node)
    graph.add_node("sales_analysis", sales_analysis_node)
    graph.add_node("purchase_agent", purchase_agent_node)
    graph.add_node("menu_generator", menu_generator_node)
    graph.add_node("finalize", finalize_node)

    graph.add_edge(START, "orchestrator_think")
    graph.add_edge("orchestrator_think", "inventory_audit")
    graph.add_conditional_edges("inventory_audit", orchestrator_decide_after_audit_node, {
        "sales_analysis": "sales_analysis",
        "finalize": "finalize",
    })
    graph.add_conditional_edges("sales_analysis", orchestrator_decide_after_sales_node, {
        "purchase_agent": "purchase_agent",
        "finalize": "finalize",
    })
    graph.add_conditional_edges("purchase_agent", orchestrator_decide_after_purchase_node, {
        "menu_generator": "menu_generator",
        "finalize": "finalize",
    })
    graph.add_edge("menu_generator", "finalize")
    graph.add_edge("finalize", END)

    return graph.compile()


_orchestrator_running = False


async def run_orchestrator(trigger: str = "manual", data: dict = None):
    global _orchestrator_running
    if _orchestrator_running:
        await event_bus.publish(
            AgentEvent(source="orchestrator", type="thought", message="Orchestrator already running. Skipping.")
        )
        return

    _orchestrator_running = True
    try:
        graph = build_orchestrator_graph()
        initial_state: OrchestratorState = {
            "trigger": trigger,
            "trigger_data": data,
            "should_analyze_sales": False,
            "should_purchase": False,
            "should_update_menu": False,
        }
        result = await graph.ainvoke(initial_state)
        return result
    except Exception as e:
        await event_bus.publish(
            AgentEvent(source="orchestrator", type="alert", message=f"Orchestrator error: {str(e)}")
        )
    finally:
        _orchestrator_running = False
