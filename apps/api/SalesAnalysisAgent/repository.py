"""Repository utilities for sales analysis."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, func, or_, select

from ..database.models.cellar import BottleStatus, Cellar
from ..database.models.transactions import Transaction, TransactionType
from ..database.models.users import User
from ..database.models.wines import Wine
from ..database.repositories.cellar_repository import CellarRepository
from .models import SalesAnalysisFocus, SalesMover


class SalesAnalysisRepository:
    """Repository for sales and stock analysis."""

    def __init__(self, cellar_repo: CellarRepository, user_id: Optional[UUID] = None):
        if cellar_repo is None:
            raise ValueError("cellar_repo is required")
        self.cellar_repo = cellar_repo
        self._user_id: Optional[UUID] = user_id

    @property
    def _session(self):
        return self.cellar_repo.session

    async def _get_only_user_id(self) -> Optional[UUID]:
        if self._user_id is not None:
            return self._user_id

        result = await self._session.execute(select(User.id).limit(1))
        self._user_id = result.scalar()
        return self._user_id

    async def resolve_wine_by_name(self, wine_name: str) -> Optional[Wine]:
        if not wine_name:
            return None
        result = await self._session.execute(
            select(Wine).where(Wine.name.ilike(f"%{wine_name}%")).limit(1)
        )
        return result.scalars().first()

    def _parse_numeric_range(self, text: Optional[str]) -> Optional[tuple[float, float]]:
        if not text:
            return None
        numbers = []
        current = ""
        for ch in text:
            if ch.isdigit() or ch == ".":
                current += ch
            else:
                if current:
                    numbers.append(float(current))
                    current = ""
        if current:
            numbers.append(float(current))
        if not numbers:
            return None
        if len(numbers) == 1:
            return numbers[0], numbers[0]
        return numbers[0], numbers[1]

    def _build_focus_filters(self, focus: Optional[SalesAnalysisFocus]) -> list:
        filters = []
        if not focus:
            return filters

        if focus.wine_id:
            filters.append(Wine.id == focus.wine_id)
        elif focus.wine_name:
            filters.append(Wine.name.ilike(f"%{focus.wine_name}%"))

        if focus.wine_type:
            wine_type = focus.wine_type.strip()
            filters.append(
                or_(
                    Wine.color.ilike(wine_type),
                    Wine.grape_variety.ilike(wine_type),
                )
            )

        price_bounds = self._parse_numeric_range(focus.price_range)
        if price_bounds:
            min_price, max_price = price_bounds
            filters.append(Wine.market_price.is_not(None))
            filters.append(Wine.market_price >= min_price)
            filters.append(Wine.market_price <= max_price)

        return filters

    async def get_sales_stock_summary(
        self,
        focus: Optional[SalesAnalysisFocus],
        lookback_days: int = 30,
    ) -> dict:
        user_id = await self._get_only_user_id()
        if not user_id:
            return {
                "focus_label": "All wines",
                "lookback_days": lookback_days,
                "stock": {"current": 0},
                "sales": {"total": 0, "recent": 0, "previous": 0},
                "sales_trend": "flat",
                "sales_change_pct": None,
                "sell_through_rate": 0.0,
            }

        filters = self._build_focus_filters(focus)

        stock_query = (
            select(func.count(Cellar.id))
            .select_from(Cellar)
            .join(Wine, Cellar.wine_id == Wine.id)
            .where(
                Cellar.user_id == user_id,
                Cellar.status == BottleStatus.IN_CELLAR,
                *filters,
            )
        )
        stock_result = await self._session.execute(stock_query)
        stock_current = int(stock_result.scalar() or 0)

        sales_base = (
            select(func.coalesce(func.sum(Transaction.quantity), 0))
            .select_from(Transaction)
            .join(Wine, Transaction.wine_id == Wine.id)
            .where(
                Transaction.user_id == user_id,
                Transaction.type == TransactionType.SALE,
                *filters,
            )
        )
        sales_total_result = await self._session.execute(sales_base)
        sales_total = int(sales_total_result.scalar() or 0)

        now = datetime.now(timezone.utc)
        recent_start = now - timedelta(days=lookback_days)
        prev_start = recent_start - timedelta(days=lookback_days)

        sales_recent_query = sales_base.where(Transaction.transaction_date >= recent_start)
        sales_prev_query = sales_base.where(
            and_(
                Transaction.transaction_date >= prev_start,
                Transaction.transaction_date < recent_start,
            )
        )

        sales_recent_result = await self._session.execute(sales_recent_query)
        sales_prev_result = await self._session.execute(sales_prev_query)

        sales_recent = int(sales_recent_result.scalar() or 0)
        sales_previous = int(sales_prev_result.scalar() or 0)

        sales_change_pct = None
        if sales_previous > 0:
            sales_change_pct = round(((sales_recent - sales_previous) / sales_previous) * 100, 2)

        if sales_recent == sales_previous:
            sales_trend = "flat"
        elif sales_recent > sales_previous:
            sales_trend = "up"
        else:
            sales_trend = "down"

        denominator = max(stock_current + sales_recent, 1)
        sell_through_rate = round(sales_recent / denominator, 2)

        focus_label = "All wines"
        if focus:
            if focus.wine_id and focus.wine_name:
                focus_label = focus.wine_name
            elif focus.wine_name:
                focus_label = focus.wine_name
            elif focus.wine_type:
                focus_label = f"Type: {focus.wine_type}"
            elif focus.price_range:
                focus_label = f"Price range: {focus.price_range}"

        return {
            "focus_label": focus_label,
            "lookback_days": lookback_days,
            "stock": {"current": stock_current},
            "sales": {
                "total": sales_total,
                "recent": sales_recent,
                "previous": sales_previous,
            },
            "sales_trend": sales_trend,
            "sales_change_pct": sales_change_pct,
            "sell_through_rate": sell_through_rate,
        }

    async def get_sales_movers(
        self,
        lookback_days: int = 90,
        limit: int = 5,
    ) -> dict:
        user_id = await self._get_only_user_id()
        if not user_id:
            return {"fast_movers": [], "slow_movers": []}

        now = datetime.now(timezone.utc)
        recent_start = now - timedelta(days=lookback_days)

        sales_query = (
            select(
                Wine.id,
                Wine.name,
                func.coalesce(func.sum(Transaction.quantity), 0),
            )
            .select_from(Transaction)
            .join(Wine, Transaction.wine_id == Wine.id)
            .where(
                Transaction.user_id == user_id,
                Transaction.type == TransactionType.SALE,
                Transaction.transaction_date >= recent_start,
            )
            .group_by(Wine.id, Wine.name)
        )

        stock_query = (
            select(
                Wine.id,
                Wine.name,
                func.count(Cellar.id),
            )
            .select_from(Cellar)
            .join(Wine, Cellar.wine_id == Wine.id)
            .where(
                Cellar.user_id == user_id,
                Cellar.status == BottleStatus.IN_CELLAR,
            )
            .group_by(Wine.id, Wine.name)
        )

        sales_result = await self._session.execute(sales_query)
        stock_result = await self._session.execute(stock_query)

        sales_rows = {row[0]: {"wine_name": row[1], "sales_recent": int(row[2] or 0)} for row in sales_result}
        stock_rows = {row[0]: {"wine_name": row[1], "stock": int(row[2] or 0)} for row in stock_result}

        movers = []
        for wine_id, stock_data in stock_rows.items():
            sales_data = sales_rows.get(wine_id, {"sales_recent": 0})
            stock_qty = stock_data["stock"]
            sales_qty = sales_data["sales_recent"]
            denominator = max(stock_qty + sales_qty, 1)
            sell_through_rate = round(sales_qty / denominator, 2)
            movers.append(
                SalesMover(
                    wine_id=wine_id,
                    wine_name=stock_data["wine_name"],
                    stock_quantity=stock_qty,
                    sales_recent=sales_qty,
                    sell_through_rate=sell_through_rate,
                )
            )

        fast_movers = sorted(movers, key=lambda m: m.sales_recent, reverse=True)[:limit]
        slow_movers = [m for m in movers if m.stock_quantity > 0 and m.sales_recent == 0]
        slow_movers = slow_movers[:limit]

        return {
            "fast_movers": [m.model_dump() for m in fast_movers],
            "slow_movers": [m.model_dump() for m in slow_movers],
        }
