from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database.dependencies import get_read_db, get_demo_user_id
from database.repositories.wine_repository import WineRepository
from database.repositories.cellar_repository import CellarRepository

router = APIRouter(prefix="/api", tags=["inventory"])


@router.get("/cellar")
async def cellar_wines(db: AsyncSession = Depends(get_read_db)):
    user_id = await get_demo_user_id(db)
    cellar_repo = CellarRepository(db, read_only=True)
    in_stock = await cellar_repo.get_user_cellar_in_stock(user_id, limit=1000)

    wine_stock: dict[int, int] = {}
    for c in in_stock:
        wine_stock[c.wine_id] = wine_stock.get(c.wine_id, 0) + 1

    wine_repo = WineRepository(db, read_only=True)
    result = []
    for wid, cnt in wine_stock.items():
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
