from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database.dependencies import get_read_db, get_demo_user_id
from database.repositories.wine_repository import WineRepository
from database.repositories.transactions_repository import TransactionRepository
from database.repositories.cellar_repository import CellarRepository

router = APIRouter(prefix="/api", tags=["inventory"])


@router.get("/summary")
async def cellar_summary(db: AsyncSession = Depends(get_read_db)):
    user_id = await get_demo_user_id(db)
    cellar_repo = CellarRepository(db, read_only=True)
    in_stock = await cellar_repo.get_user_cellar_in_stock(user_id, limit=1000)

    wine_ids = list(set(c.wine_id for c in in_stock))
    wine_repo = WineRepository(db, read_only=True)

    total_bottles = len(in_stock)
    purchase_value = 0.0
    market_value = 0.0
    regions: dict[str, int] = {}
    colors: dict[str, int] = {}
    wine_stock: dict[int, int] = {}

    for c in in_stock:
        wine_stock[c.wine_id] = wine_stock.get(c.wine_id, 0) + 1

    for wid in wine_ids:
        wine = await wine_repo.get_by_id(wid)
        if wine:
            cnt = wine_stock[wid]
            if wine.market_price:
                market_value += wine.market_price * cnt
            regions[wine.region] = regions.get(wine.region, 0) + cnt
            colors[wine.color] = colors.get(wine.color, 0) + cnt

    sold = await cellar_repo.get_user_sold_bottles(user_id, limit=1000)
    txn_repo = TransactionRepository(db, read_only=True)
    purchases = await txn_repo.get_user_purchases(user_id, limit=1000)
    for p in purchases:
        purchase_value += (p.purchase_price or 0) * p.quantity

    region_balance = [
        {"region": r, "pct": round(cnt / total_bottles * 100) if total_bottles else 0}
        for r, cnt in sorted(regions.items(), key=lambda x: -x[1])
    ]

    top_wines = []
    for wid in sorted(wine_stock, key=wine_stock.get, reverse=True)[:5]:
        wine = await wine_repo.get_by_id(wid)
        if wine:
            top_wines.append(
                {"name": f"{wine.name} {wine.vintage or ''}", "bottles": wine_stock[wid]}
            )

    return {
        "total_bottles": total_bottles,
        "total_wines": len(wine_ids),
        "purchase_value": round(purchase_value, 2),
        "market_value": round(market_value, 2),
        "sold_bottles": len(sold),
        "region_balance": region_balance,
        "color_distribution": colors,
        "top_wines": top_wines,
    }
