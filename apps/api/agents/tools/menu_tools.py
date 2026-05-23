from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.database.models.menu import MenuItem
from apps.api.database.models.wines import Wine


def make_menu_tools(db: AsyncSession, user_id: str, llm) -> list:
    """
    Create menu management tools for the orchestrator.
    These tools manage the wine menu by adding/removing wines and generating descriptions.
    """

    @tool
    async def get_current_menu() -> str:
        """
        Retrieves the current active wine menu for the user.
        Returns all wines that are marked as active, sorted by position on the card.
        Use this to see what wines are currently on the menu.
        """
        result = await db.execute(
            select(
                Wine.name,
                Wine.region,
                Wine.color,
                Wine.producer,
                Wine.vintage,
                MenuItem.description,
                MenuItem.pairing_notes,
                MenuItem.position,
            )
            .join(MenuItem, MenuItem.wine_id == Wine.id)
            .where(
                and_(
                    MenuItem.user_id == user_id,
                    MenuItem.is_active,
                )
            )
            .order_by(MenuItem.position)
        )
        rows = result.all()

        if not rows:
            return "The menu is currently empty. No active wines on the menu."

        lines = ["Current Wine Menu:", ""]
        for i, row in enumerate(rows, 1):
            vintage = f" {row.vintage}" if row.vintage else ""
            lines.append(f"{i}. {row.name}{vintage} ({row.producer}, {row.region})")
            lines.append(f"   Color: {row.color}")
            if row.description:
                lines.append(f"   Tasting note: {row.description}")
            if row.pairing_notes:
                lines.append(f"   Pairings: {row.pairing_notes}")
            lines.append("")

        return "\n".join(lines)

    @tool
    async def activate_wine_on_menu(wine_name: str) -> str:
        """
        Adds a wine to the active menu. Provide the wine_name parameter.
        If the wine is already on the menu, updates it.
        If description is empty, generates one using LLM.
        Use this when restocking a wine and you want to add it to the menu.
        """
        # Find the wine
        wine_result = await db.execute(
            select(Wine).where(Wine.name.ilike(f"%{wine_name}%")).limit(1)
        )
        wine = wine_result.scalars().first()

        if not wine:
            return f"Wine '{wine_name}' not found in the database."

        # Check if already on menu
        existing_result = await db.execute(
            select(MenuItem).where(
                and_(
                    MenuItem.user_id == user_id,
                    MenuItem.wine_id == wine.id,
                )
            )
        )
        existing = existing_result.scalars().first()

        if existing:
            # Update existing menu item to active
            existing.is_active = True
            db.add(existing)
            await db.commit()
            return f"{wine.name} is now active on the menu."

        # Generate description if needed
        description = await _generate_description_internal(wine)

        # Create new menu item
        # Get max position
        max_pos_result = await db.execute(
            select(func.max(MenuItem.position)).where(
                MenuItem.user_id == user_id,
                MenuItem.is_active,
            )
        )
        max_position = (max_pos_result.scalar() or 0) + 1

        new_item = MenuItem(
            user_id=user_id,
            wine_id=wine.id,
            description=description["tasting_note"],
            pairing_notes=description["pairings"],
            position=max_position,
            is_active=True,
        )
        db.add(new_item)
        await db.commit()

        return f"{wine.name} has been added to the menu at position {max_position}."

    @tool
    async def remove_wine_from_menu(wine_name: str) -> str:
        """
        Removes a wine from the active menu (soft delete - marks as inactive).
        Provide the wine_name parameter.
        Use this when a wine runs out of stock or should no longer be offered.
        """
        # Find the wine
        wine_result = await db.execute(
            select(Wine).where(Wine.name.ilike(f"%{wine_name}%")).limit(1)
        )
        wine = wine_result.scalars().first()

        if not wine:
            return f"Wine '{wine_name}' not found in the database."

        # Find menu item
        item_result = await db.execute(
            select(MenuItem).where(
                and_(
                    MenuItem.user_id == user_id,
                    MenuItem.wine_id == wine.id,
                )
            )
        )
        item = item_result.scalars().first()

        if not item:
            return f"{wine.name} is not currently on the menu."

        if not item.is_active:
            return f"{wine.name} is already inactive on the menu."

        item.is_active = False
        db.add(item)
        await db.commit()

        return f"{wine.name} has been removed from the menu."

    @tool
    async def generate_wine_description(wine_name: str) -> str:
        """
        Generates a sommelier-quality tasting note and food pairing suggestions for a wine.
        Provide the wine_name parameter.
        Uses LLM to create compelling descriptions.
        Returns the generated tasting note and pairing suggestions.
        """
        # Find the wine
        wine_result = await db.execute(
            select(Wine).where(Wine.name.ilike(f"%{wine_name}%")).limit(1)
        )
        wine = wine_result.scalars().first()

        if not wine:
            return f"Wine '{wine_name}' not found in the database."

        description = await _generate_description_internal(wine)

        return f"""Tasting Note:
{description["tasting_note"]}

Food Pairings:
{description["pairings"]}"""

    async def _generate_description_internal(wine: Wine) -> dict:
        """
        Internal helper to generate tasting note and pairings via LLM.
        Returns dict with 'tasting_note' and 'pairings' keys.
        """
        prompt = f"""You are a professional sommelier. Generate a compelling and concise wine menu description.

Wine Details:
- Name: {wine.name}
- Producer: {wine.producer}
- Region: {wine.region}
- Vintage: {wine.vintage or "N/A"}
- Color: {wine.color}
- Alcohol: {wine.alcohol}%
- Appellation: {wine.appellation or "N/A"}
- Grape Variety: {wine.grape_variety or "N/A"}

Generate:
1. A 2-3 sentence tasting note (aroma, flavor profile, structure)
2. Three food pairings as a comma-separated list

Format your response as:
TASTING NOTE: [your tasting note]
PAIRINGS: [food1, food2, food3]"""

        response = await llm.ainvoke([HumanMessage(content=prompt)])
        content = response.content

        # Parse response
        tasting_note = ""
        pairings = ""

        lines = content.split("\n")
        for line in lines:
            if line.startswith("TASTING NOTE:"):
                tasting_note = line.replace("TASTING NOTE:", "").strip()
            elif line.startswith("PAIRINGS:"):
                pairings = line.replace("PAIRINGS:", "").strip()

        return {"tasting_note": tasting_note, "pairings": pairings}

    return [
        get_current_menu,
        activate_wine_on_menu,
        remove_wine_from_menu,
        generate_wine_description,
    ]
