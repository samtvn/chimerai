#!/usr/bin/env bash
# Test script for inventory tools
cd "$(dirname "$0")/../../.."
export PYTHONPATH="$(pwd)"
uv run --project apps/api python -c "
import asyncio
from apps.api.database.database import AsyncSessionLocal
from apps.api.database.dependencies import get_demo_user_id
from apps.api.agents.tools.inventory_tools import make_inventory_tools

async def main():
    async with AsyncSessionLocal() as db:
        user_id = await get_demo_user_id(db)
        tools = make_inventory_tools(db, str(user_id))
        
        get_cellar_summary = tools[0]
        result = await get_cellar_summary.ainvoke({})
        print(result)

asyncio.run(main())
"
