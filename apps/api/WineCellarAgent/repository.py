"""Database service for Wine Cellar Agent to fetch cellar data"""
from typing import List, Optional
from uuid import UUID
from sqlalchemy import func, select

from ..database.models.cellar import BottleStatus, Cellar
from ..database.models.users import User
from ..database.models.wines import Wine
from ..database.repositories.cellar_repository import CellarRepository


class WineCellarRepository:
    """Repository for accessing wine cellar data"""

    def __init__(self, cellar_repo: CellarRepository, user_id: Optional[UUID] = None):
        """Initialize with an existing CellarRepository instance"""
        if cellar_repo is None:
            raise ValueError("cellar_repo is required")
        self.cellar_repo = cellar_repo
        self._user_id: Optional[UUID] = user_id

    @property
    def _session(self):
        return self.cellar_repo.session

    async def _get_only_user_id(self) -> Optional[UUID]:
        """Fetch and cache the only user id in the database."""
        if self._user_id is not None:
            return self._user_id

        result = await self._session.execute(select(User.id).limit(1))
        self._user_id = result.scalar()
        return self._user_id

    def _model_to_dict(self, model) -> dict:
        if model is None:
            return {}
        if hasattr(model, "model_dump"):
            return model.model_dump()
        return model.dict()

    async def get_all_wines(self) -> List[dict]:
        """Fetch all wines from the user's cellar as dict rows"""
        user_id = await self._get_only_user_id()
        if not user_id:
            return []

        result = await self._session.execute(
            select(Cellar, Wine)
            .join(Wine, Cellar.wine_id == Wine.id)
            .where(
                Cellar.user_id == user_id,
                Cellar.status == BottleStatus.IN_CELLAR,
            )
        )
        rows = result.all()

        wines = []
        for cellar, wine in rows:
            cellar_data = self._model_to_dict(cellar)
            wine_data = self._model_to_dict(wine)
            wines.append(
                {
                    "cellar_id": cellar_data.get("id"),
                    "user_id": cellar_data.get("user_id"),
                    "transaction_id": cellar_data.get("transaction_id"),
                    "cellar_status": cellar_data.get("status"),
                    "wine": wine_data,
                }
            )
        return wines

    async def get_wine_count(self) -> int:
        """Get total count of bottles in the user's cellar"""
        user_id = await self._get_only_user_id()
        if not user_id:
            return 0
        result = await self._session.execute(
            select(func.count(Cellar.id)).where(
                Cellar.user_id == user_id,
                Cellar.status == BottleStatus.IN_CELLAR,
            )
        )
        return int(result.scalar() or 0)

    async def get_total_quantity(self) -> int:
        """Get total quantity of bottles for the user"""
        return await self.get_wine_count()

    async def get_wines_by_country(self) -> dict[str, int]:
        """Get breakdown of wines by country"""
        user_id = await self._get_only_user_id()
        if not user_id:
            return {}
        result = await self._session.execute(
            select(Wine.country, func.count(Cellar.id))
            .join(Cellar, Cellar.wine_id == Wine.id)
            .where(
                Cellar.user_id == user_id,
                Cellar.status == BottleStatus.IN_CELLAR,
            )
            .group_by(Wine.country)
        )
        return {row[0]: row[1] for row in result.all()}

    async def get_wines_by_region(self) -> dict[str, int]:
        """Get breakdown of wines by region"""
        user_id = await self._get_only_user_id()
        if not user_id:
            return {}
        result = await self._session.execute(
            select(Wine.region, func.count(Cellar.id))
            .join(Cellar, Cellar.wine_id == Wine.id)
            .where(
                Cellar.user_id == user_id,
                Cellar.status == BottleStatus.IN_CELLAR,
            )
            .group_by(Wine.region)
        )
        return {row[0]: row[1] for row in result.all()}

    async def get_wines_by_color(self) -> dict[str, int]:
        """Get breakdown of wines by color"""
        user_id = await self._get_only_user_id()
        if not user_id:
            return {}
        result = await self._session.execute(
            select(Wine.color, func.count(Cellar.id))
            .join(Cellar, Cellar.wine_id == Wine.id)
            .where(
                Cellar.user_id == user_id,
                Cellar.status == BottleStatus.IN_CELLAR,
            )
            .group_by(Wine.color)
        )
        return {row[0]: row[1] for row in result.all()}

    async def get_wines_by_grape_variety(self) -> dict[str, int]:
        """Get breakdown of wines by grape variety"""
        user_id = await self._get_only_user_id()
        if not user_id:
            return {}
        result = await self._session.execute(
            select(Wine.grape_variety, func.count(Cellar.id))
            .join(Cellar, Cellar.wine_id == Wine.id)
            .where(
                Cellar.user_id == user_id,
                Cellar.status == BottleStatus.IN_CELLAR,
            )
            .group_by(Wine.grape_variety)
        )
        return {row[0]: row[1] for row in result.all()}
