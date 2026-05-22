import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from pydantic import BaseModel
from datetime import datetime

from database.dependencies import get_db, get_read_db, get_demo_user_id
from database.repositories.wine_repository import WineRepository
from database.repositories.transactions_repository import TransactionRepository
from database.repositories.cellar_repository import CellarRepository
from database.models.transactions import TransactionType
from database.models.cellar import BottleStatus
from agents.event_bus import event_bus, AgentEvent
import json

router = APIRouter(prefix="/api", tags=["inventory"])


class TransactionCreate(BaseModel):
    wine_id: int
    quantity: int
    purchase_price: float | None = None
    type: TransactionType
    date: datetime | None = None


class TransactionUpdate(BaseModel):
    quantity: int | None = None
    purchase_price: float | None = None
    type: TransactionType | None = None
    date: datetime | None = None


@router.get("/transactions")
async def list_transactions(
    type: Optional[TransactionType] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_read_db),
):
    user_id = await get_demo_user_id(db)
    if type:
        if type == TransactionType.PURCHASE:
            txns = await TransactionRepository(db, True).get_user_purchases(user_id, limit)
        else:
            txns = await TransactionRepository(db, True).get_user_sales(user_id, limit)
    else:
        txns = await TransactionRepository(db, True).get_by_user_id(user_id, limit)

    result = []
    for txn in txns:
        wine_repo = WineRepository(db, read_only=True)
        wine = await wine_repo.get_by_id(txn.wine_id)
        result.append(
            {
                "id": str(txn.id),
                "wine_id": txn.wine_id,
                "wine_name": wine.name if wine else "Unknown",
                "wine_producer": wine.producer if wine else "",
                "wine_vintage": wine.vintage if wine else "",
                "wine_region": wine.region if wine else "",
                "wine_color": wine.color if wine else "",
                "quantity": txn.quantity,
                "purchase_price": txn.purchase_price,
                "type": txn.type.value,
                "date": txn.transaction_date.isoformat() if txn.transaction_date else None,
            }
        )
    return {"transactions": result}


@router.post("/transactions")
async def create_transaction(body: TransactionCreate, db: AsyncSession = Depends(get_db)):
    user_id = await get_demo_user_id(db)
    wine_repo = WineRepository(db, read_only=True)
    wine = await wine_repo.get_by_id(body.wine_id)
    if not wine:
        raise HTTPException(404, "Wine not found")

    txn_data = {
        "wine_id": body.wine_id,
        "user_id": user_id,
        "quantity": body.quantity,
        "purchase_price": body.purchase_price,
        "type": body.type,
    }
    if body.date:
        txn_data["transaction_date"] = body.date

    txn_repo = TransactionRepository(db, read_only=False)
    txn = await txn_repo.create(**txn_data)

    cellar_repo = CellarRepository(db, read_only=False)
    if body.type == TransactionType.PURCHASE:
        for _ in range(body.quantity):
            await cellar_repo.create(
                user_id=user_id,
                wine_id=body.wine_id,
                transaction_id=txn.id,
                status=BottleStatus.IN_CELLAR,
            )
    elif body.type == TransactionType.SALE:
        in_stock = await cellar_repo.get_wine_in_cellar(user_id, body.wine_id)
        available = [c for c in in_stock if c.status == BottleStatus.IN_CELLAR]
        if len(available) < body.quantity:
            raise HTTPException(
                400,
                f"Only {len(available)} bottles in stock, cannot sell {body.quantity}",
            )
        for i in range(body.quantity):
            available[i].transaction_id = txn.id
            available[i].status = BottleStatus.SOLD
        await db.commit()

    await db.refresh(txn)

    if body.type == TransactionType.SALE:
        await event_bus.publish(
            AgentEvent(
                source="transactions",
                type="wine_sold",
                message=json.dumps(
                    {
                        "wine_id": body.wine_id,
                        "quantity": body.quantity,
                        "type": body.type.value,
                    }
                ),
            )
        )

    return {
        "id": str(txn.id),
        "wine_id": txn.wine_id,
        "wine_name": wine.name,
        "quantity": txn.quantity,
        "purchase_price": txn.purchase_price,
        "type": txn.type.value,
        "date": txn.transaction_date.isoformat() if txn.transaction_date else None,
    }


@router.put("/transactions/{txn_id}")
async def update_transaction(
    txn_id: UUID, body: TransactionUpdate, db: AsyncSession = Depends(get_db)
):
    user_id = await get_demo_user_id(db)

    txn_repo = TransactionRepository(db, read_only=False)
    cellar_repo = CellarRepository(db, read_only=False)

    txn = await txn_repo.get_by_id(txn_id)
    if not txn:
        raise HTTPException(404, "Transaction not found")

    old_type = txn.type
    old_qty = txn.quantity
    new_type = body.type or old_type
    new_qty = body.quantity if body.quantity is not None else old_qty

    update_data = {}
    if body.quantity is not None:
        update_data["quantity"] = body.quantity
    if body.purchase_price is not None:
        update_data["purchase_price"] = body.purchase_price
    if body.type is not None:
        update_data["type"] = body.type
    if body.date is not None:
        update_data["transaction_date"] = body.date

    cellar_entries = await cellar_repo.get_by_transaction(txn_id)

    # Reverse old cellar effects
    if old_type == TransactionType.PURCHASE:
        for entry in cellar_entries:
            await db.delete(entry)

    elif old_type == TransactionType.SALE:
        for entry in cellar_entries:
            if entry.status == BottleStatus.SOLD:
                entry.status = BottleStatus.IN_CELLAR
                entry.transaction_id = None

    # Apply new cellar effects
    if new_type == TransactionType.PURCHASE:
        for _ in range(new_qty):
            await cellar_repo.create(
                user_id=user_id,
                wine_id=txn.wine_id,
                transaction_id=txn.id,
                status=BottleStatus.IN_CELLAR,
            )

    elif new_type == TransactionType.SALE:
        fresh_stock = await cellar_repo.get_wine_in_cellar(user_id, txn.wine_id)
        available = [c for c in fresh_stock if c.status == BottleStatus.IN_CELLAR]

        if len(available) < new_qty:
            raise HTTPException(
                400,
                f"Only {len(available)} bottles in stock, cannot sell {new_qty}",
            )

        for i in range(new_qty):
            available[i].transaction_id = txn.id
            available[i].status = BottleStatus.SOLD

    await db.commit()
    txn = await txn_repo.update(txn_id, **update_data)

    wine_repo = WineRepository(db, read_only=True)
    wine = await wine_repo.get_by_id(txn.wine_id)

    return {
        "id": str(txn.id),
        "wine_id": txn.wine_id,
        "wine_name": wine.name if wine else "Unknown",
        "quantity": txn.quantity,
        "purchase_price": txn.purchase_price,
        "type": txn.type.value,
        "date": txn.transaction_date.isoformat() if txn.transaction_date else None,
    }


@router.delete("/transactions/{txn_id}")
async def delete_transaction(txn_id: UUID, db: AsyncSession = Depends(get_db)):
    txn_repo = TransactionRepository(db, read_only=False)
    cellar_repo = CellarRepository(db, read_only=False)

    txn = await txn_repo.get_by_id(txn_id)
    if not txn:
        raise HTTPException(404, "Transaction not found")

    cellar_entries = await cellar_repo.get_by_transaction(txn_id)

    if txn.type == TransactionType.PURCHASE:
        for entry in cellar_entries:
            if entry.status == BottleStatus.IN_CELLAR:
                await db.delete(entry)

    elif txn.type == TransactionType.SALE:
        for entry in cellar_entries:
            if entry.status == BottleStatus.SOLD:
                entry.status = BottleStatus.IN_CELLAR
                entry.transaction_id = None

    await db.commit()
    deleted = await txn_repo.delete(txn_id)
    if not deleted:
        raise HTTPException(404, "Transaction not found")
    return {"status": "deleted"}
