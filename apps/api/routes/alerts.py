from fastapi import APIRouter, Depends, HTTPException, Query
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from database.dependencies import get_db, get_read_db, get_demo_user_id
from database.models.alerts import AlertSeverity
from database.repositories.alert_repository import AlertRepository
from agents.event_bus import event_bus, AgentEvent

router = APIRouter(prefix="/api", tags=["inventory"])

class AlertCreate(BaseModel):
    message: str
    severity: AlertSeverity = AlertSeverity.INFO
    source_agent: str | None = None

@router.get("/alerts")
async def list_alerts(
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_read_db),
):
    user_id = await get_demo_user_id(db)
    repo = AlertRepository(db, read_only=True)
    alerts = await repo.get_user_alerts(user_id, limit)
    return {
        "alerts": [
            {
                "id": str(a.id),
                "message": a.message,
                "severity": a.severity.value,
                "source_agent": a.source_agent,
                "read": a.read,
                "created_at": a.created_at.isoformat(),
            }
            for a in alerts
        ]
    }


@router.get("/alerts/unread-count")
async def unread_alert_count(db: AsyncSession = Depends(get_read_db)):
    user_id = await get_demo_user_id(db)
    repo = AlertRepository(db, read_only=True)
    count = await repo.get_unread_count(user_id)
    return {"count": count}


@router.put("/alerts/{alert_id}/read")
async def mark_alert_read(alert_id: UUID, db: AsyncSession = Depends(get_db)):
    repo = AlertRepository(db, read_only=False)
    ok = await repo.mark_read(alert_id)
    if not ok:
        raise HTTPException(404, "Alert not found")
    return {"status": "read"}


@router.put("/alerts/mark-all-read")
async def mark_all_alerts_read(db: AsyncSession = Depends(get_db)):
    user_id = await get_demo_user_id(db)
    repo = AlertRepository(db, read_only=False)
    count = await repo.mark_all_read(user_id)
    return {"marked_read": count}

@router.post("/alerts")
async def create_alert(body: AlertCreate, db: AsyncSession = Depends(get_db)):
    user_id = await get_demo_user_id(db)
    repo = AlertRepository(db, read_only=False)
    alert = await repo.create(
        user_id=user_id,
        message=body.message,
        severity=body.severity,
        source_agent=body.source_agent,
    )

    await event_bus.publish(
        AgentEvent(
            source=body.source_agent or "system",
            type="alert",
            message=body.message,
        )
    )

    return {
        "id": str(alert.id),
        "message": alert.message,
        "severity": alert.severity.value,
        "source_agent": alert.source_agent,
        "read": alert.read,
        "created_at": alert.created_at.isoformat(),
    }
