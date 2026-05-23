import asyncio

from apps.api.agents.tools.inventory_tools import make_inventory_tools
from apps.api.database.database import AsyncSessionLocal
from apps.api.database.dependencies import get_demo_user_id


async def main():
    async with AsyncSessionLocal() as db:
        user_id = await get_demo_user_id(db)
        tools = make_inventory_tools(db, str(user_id))

        # Each tool has a .ainvoke() method too — but for direct testing,
        # since we defined them as async functions, we can call them directly:
        get_cellar_summary = tools[0]
        result = await get_cellar_summary.ainvoke({})
        print(result)


asyncio.run(main())
