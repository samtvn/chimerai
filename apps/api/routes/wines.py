from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.database.dependencies import get_read_db
from apps.api.database.models.wines import Wine
from apps.api.database.repositories.wine_repository import WineRepository

router = APIRouter(prefix="/api", tags=["inventory"])


@router.get("/wines")
async def list_wines(
    color: Optional[str] = None,
    region: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
    db: AsyncSession = Depends(get_read_db),
):
    query = select(Wine)
    if color:
        query = query.where(Wine.color == color)
    if region:
        query = query.where(Wine.region == region)
    if search:
        pattern = f"%{search}%"
        query = query.where(
            (Wine.name.ilike(pattern))
            | (Wine.producer.ilike(pattern))
            | (Wine.region.ilike(pattern))
            | (Wine.grape_variety.ilike(pattern))
        )
    query = query.order_by(Wine.name).limit(limit).offset(offset)
    result = await db.execute(query)
    wines = result.scalars().all()

    count_q = select(func.count(Wine.id))
    if color:
        count_q = count_q.where(Wine.color == color)
    if region:
        count_q = count_q.where(Wine.region == region)
    if search:
        pattern = f"%{search}%"
        count_q = count_q.where(
            (Wine.name.ilike(pattern))
            | (Wine.producer.ilike(pattern))
            | (Wine.region.ilike(pattern))
            | (Wine.grape_variety.ilike(pattern))
        )
    total = (await db.execute(count_q)).scalar() or 0

    return {"wines": wines, "total": total}


@router.get("/wines/{wine_id}")
async def get_wine(wine_id: int, db: AsyncSession = Depends(get_read_db)):
    repo = WineRepository(db, read_only=True)
    wine = await repo.get_by_id(wine_id)
    if not wine:
        raise HTTPException(404, "Wine not found")
    return wine


@router.get("/wines/filters/regions")
async def get_regions(db: AsyncSession = Depends(get_read_db)):
    result = await db.execute(select(distinct(Wine.region)).order_by(Wine.region))
    return {"regions": [r for r in result.scalars().all() if r]}


@router.get("/wines/filters/colors")
async def get_colors(db: AsyncSession = Depends(get_read_db)):
    result = await db.execute(select(distinct(Wine.color)).order_by(Wine.color))
    return {"colors": [c for c in result.scalars().all() if c]}


@router.get("/wines/filters/appellations")
async def get_appellations(db: AsyncSession = Depends(get_read_db)):
    result = await db.execute(select(distinct(Wine.appellation)).order_by(Wine.appellation))
    return {"appellations": [c for c in result.scalars().all() if c]}
