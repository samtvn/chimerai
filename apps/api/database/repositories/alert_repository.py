from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from database.models.alerts import Alert
from .base import BaseRepository


class AlertRepository(BaseRepository[Alert]):
    model = Alert

    def __init__(self, session: AsyncSession, read_only: bool = False):
        super().__init__(session, read_only)

    async def get_user_alerts(self, user_id: UUID, limit: int = 50) -> List[Alert]:
        result = await self.session.execute(
            select(Alert)
            .where(Alert.user_id == user_id)
            .order_by(Alert.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def get_unread_count(self, user_id: UUID) -> int:
        from sqlalchemy import func

        result = await self.session.execute(
            select(func.count(Alert.id)).where(
                and_(Alert.user_id == user_id, Alert.read.is_(False))
            )
        )
        return result.scalar() or 0

    async def mark_read(self, alert_id: UUID) -> bool:
        alert = await self.get_by_id(alert_id)
        if not alert:
            return False
        alert.read = True
        await self.session.commit()
        return True

    async def mark_all_read(self, user_id: UUID) -> int:
        result = await self.session.execute(
            select(Alert).where(and_(Alert.user_id == user_id, Alert.read.is_(False)))
        )
        alerts = result.scalars().all()
        for alert in alerts:
            alert.read = True
        await self.session.commit()
        return len(alerts)
