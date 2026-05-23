"""Repository utilities for wine-card read_inventory flow."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.cellar import BottleStatus, Cellar
from database.models.transactions import Transaction, TransactionType
from database.models.wines import Wine
from .models import InventoryItem


class WineCardRepository:
    """Read-only repository for inventory + pricing inputs."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def read_inventory(self, user_id: UUID, limit: int = 1000) -> list[InventoryItem]:
        unit_purchase_expr = case(
            (
                and_(
                    Transaction.type == TransactionType.PURCHASE,
                    Transaction.quantity.is_not(None),
                    Transaction.quantity > 0,
                    Transaction.price.is_not(None),
                ),
                Transaction.price / Transaction.quantity,
            ),
            else_=None,
        )

        stmt = (
            select(
                Wine.id.label("wine_id"),
                Wine.producer,
                Wine.name.label("wine_name"),
                Wine.region,
                Wine.country,
                Wine.appellation,
                Wine.color.label("wine_color"),
                Wine.vintage,
                Wine.grape_variety,
                Wine.drink_from,
                Wine.drink_to,
                Wine.market_price.label("avg_market_price"),
                func.count(Cellar.id).label("quantity"),
                func.avg(unit_purchase_expr).label("avg_purchase_price"),
            )
            .select_from(Cellar)
            .join(Wine, Cellar.wine_id == Wine.id)
            .outerjoin(Transaction, Cellar.transaction_id == Transaction.id)
            .where(
                Cellar.user_id == user_id,
                Cellar.status == BottleStatus.IN_CELLAR,
            )
            .group_by(
                Wine.id,
                Wine.producer,
                Wine.name,
                Wine.region,
                Wine.country,
                Wine.appellation,
                Wine.color,
                Wine.vintage,
                Wine.grape_variety,
                Wine.drink_from,
                Wine.drink_to,
                Wine.market_price,
            )
            .order_by(Wine.color, Wine.producer, Wine.name)
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        items: list[InventoryItem] = []
        for row in result:
            purchase_price = row.avg_purchase_price
            if purchase_price is None:
                purchase_price = row.avg_market_price or 0.0
            items.append(
                InventoryItem(
                    wine_id=row.wine_id,
                    producer=row.producer,
                    wine_name=row.wine_name,
                    region=row.region,
                    country=row.country,
                    appellation=row.appellation,
                    wine_color=row.wine_color,
                    vintage=row.vintage,
                    grape_variety=row.grape_variety,
                    drink_from=row.drink_from,
                    drink_to=row.drink_to,
                    quantity=int(row.quantity or 0),
                    purchase_price_ht=round(float(purchase_price or 0.0), 2),
                    avg_market_price=(
                        round(float(row.avg_market_price), 2)
                        if row.avg_market_price is not None
                        else None
                    ),
                )
            )
        return items

