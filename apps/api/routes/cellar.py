from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.database.dependencies import get_db, get_read_db, get_demo_user_id
from apps.api.database.models.cellar import BottleStatus, Cellar
from apps.api.database.models.transactions import Transaction, TransactionType
from apps.api.database.models.wines import Wine
from apps.api.database.repositories.wine_repository import WineRepository
from apps.api.database.repositories.cellar_repository import CellarRepository

router = APIRouter(prefix="/api", tags=["inventory"])


@router.get("/cellar")
async def cellar_wines(db: AsyncSession = Depends(get_read_db)):
    """Return cellar references including wines currently at zero stock.

    The previous implementation only listed wines with IN_CELLAR bottles.
    This version keeps wines that were historically in cellar (sold out refs),
    with `stock=0`, so users can decide to restock or remove the reference.
    """
    user_id = await get_demo_user_id(db)
    cellar_repo = CellarRepository(db, read_only=True)
    in_stock = await cellar_repo.get_user_cellar_in_stock(user_id, limit=5000)
    all_entries = await cellar_repo.get_user_cellar(user_id, limit=5000)

    wine_stock: dict[int, int] = {}
    for entry in in_stock:
        wine_stock[entry.wine_id] = wine_stock.get(entry.wine_id, 0) + 1

    wine_repo = WineRepository(db, read_only=True)
    result = []
    all_wine_ids = {entry.wine_id for entry in all_entries}
    for wid in all_wine_ids:
        cnt = wine_stock.get(wid, 0)
        wine = await wine_repo.get_by_id(wid)
        if wine:
            result.append(
                {
                    "id": wine.id,
                    "name": wine.name,
                    "producer": wine.producer,
                    "vintage": wine.vintage,
                    "region": wine.region,
                    "country": wine.country,
                    "appellation": wine.appellation,
                    "grape_variety": wine.grape_variety,
                    "color": wine.color,
                    "alcohol": wine.alcohol,
                    "drink_from": wine.drink_from,
                    "drink_to": wine.drink_to,
                    "market_price": wine.market_price,
                    "stock": cnt,
                }
            )
    result.sort(key=lambda w: w["name"])
    return {"wines": result, "total": len(result)}


@router.delete("/cellar/reference/{wine_id}")
async def delete_cellar_reference(wine_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a wine reference for the current user and return a deletion summary.

    The operation removes:
      - cellar entries (in-stock and sold markers) for the wine
      - purchase/sale transactions for the same wine and user

    It keeps the shared `wines` catalog untouched.
    """
    user_id = await get_demo_user_id(db)
    wine_repo = WineRepository(db, read_only=True)
    wine = await wine_repo.get_by_id(wine_id)
    if not wine:
        raise HTTPException(404, "Wine not found")

    stock_count = (
        await db.execute(
            select(func.count(Cellar.id)).where(
                and_(
                    Cellar.user_id == user_id,
                    Cellar.wine_id == wine_id,
                    Cellar.status == BottleStatus.IN_CELLAR,
                )
            )
        )
    ).scalar() or 0

    sold_count = (
        await db.execute(
            select(func.coalesce(func.sum(Transaction.quantity), 0)).where(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.wine_id == wine_id,
                    Transaction.type == TransactionType.SALE,
                )
            )
        )
    ).scalar() or 0

    purchase_count = (
        await db.execute(
            select(func.coalesce(func.sum(Transaction.quantity), 0)).where(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.wine_id == wine_id,
                    Transaction.type == TransactionType.PURCHASE,
                )
            )
        )
    ).scalar() or 0

    total_rows = (
        await db.execute(
            select(func.count(Cellar.id)).where(
                and_(Cellar.user_id == user_id, Cellar.wine_id == wine_id)
            )
        )
    ).scalar() or 0
    if total_rows == 0 and purchase_count == 0 and sold_count == 0:
        raise HTTPException(404, "Reference not found in your cellar history")

    replacements_query = (
        select(Wine)
        .where(
            Wine.id != wine_id,
            Wine.color == wine.color,
            Wine.region == wine.region,
        )
        .order_by(Wine.market_price.asc().nulls_last(), Wine.name.asc())
        .limit(3)
    )
    replacements = (await db.execute(replacements_query)).scalars().all()
    if not replacements:
        replacements_query = (
            select(Wine)
            .where(
                Wine.id != wine_id,
                Wine.color == wine.color,
            )
            .order_by(Wine.market_price.asc().nulls_last(), Wine.name.asc())
            .limit(3)
        )
        replacements = (await db.execute(replacements_query)).scalars().all()

    await db.execute(
        delete(Cellar).where(
            and_(Cellar.user_id == user_id, Cellar.wine_id == wine_id)
        )
    )
    await db.execute(
        delete(Transaction).where(
            and_(Transaction.user_id == user_id, Transaction.wine_id == wine_id)
        )
    )
    await db.commit()

    denominator = int(stock_count) + int(sold_count)
    sell_through_pct = round((int(sold_count) / denominator) * 100) if denominator > 0 else 0
    summary = (
        f"Removed reference: {wine.producer} — {wine.name} {wine.vintage or 'NV'}. "
        f"Purchased: {int(purchase_count)} bottles, sold: {int(sold_count)}, "
        f"remaining stock before deletion: {int(stock_count)}, sell-through: {sell_through_pct}%."
    )

    return {
        "status": "deleted",
        "wine_id": wine_id,
        "summary": summary,
        "replacement_suggestions": [
            {
                "wine_id": r.id,
                "name": r.name,
                "producer": r.producer,
                "vintage": r.vintage,
                "region": r.region,
                "color": r.color,
                "market_price": r.market_price,
            }
            for r in replacements
        ],
    }
