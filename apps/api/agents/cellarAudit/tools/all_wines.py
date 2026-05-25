from typing import List

from apps.api.database.database import AsyncSessionLocal
from apps.api.database.models.cellar import BottleStatus, Cellar
from apps.api.database.models.wines import Wine
from langchain_core.tools import tool
from sqlalchemy import func, select


def make_all_wines_tool(user_id: str):
    @tool
    async def get_all_wines() -> List[dict]:
        """Fetch all wines from the user's cellar grouped by wine with quantity"""

        def _model_to_dict(model) -> dict:
            if model is None:
                return {}
            if hasattr(model, "model_dump"):
                return model.model_dump()
            return model.dict()

        if not user_id:
            return []

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Wine, func.count(Cellar.id).label("quantity"))
                .join(Cellar, Cellar.wine_id == Wine.id)
                .where(
                    Cellar.user_id == user_id,
                    Cellar.status == BottleStatus.IN_CELLAR,
                )
                .group_by(Wine.id)
            )
            rows = result.all()

        wines = []
        for wine, quantity in rows:
            wine_data = _model_to_dict(wine)
            wines.append(
                {
                    "name": wine_data.get("name"),
                    "region": wine_data.get("region"),
                    "country": wine_data.get("country"),
                    "color": wine_data.get("color"),
                    "grape_variety": wine_data.get("grape_variety"),
                    "vintage": wine_data.get("vintage"),
                    "quantity": quantity,
                }
            )
        return wines

    return get_all_wines
