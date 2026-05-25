import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))
import apps.api.agents.cellarAudit.tools as cellarAuditTools
import apps.api.database.models  # noqa: F401 — registers all models
import apps.api.env  # noqa: F401 — loads .env
from apps.api.database.database import AsyncSessionLocal
from apps.api.database.dependencies import get_demo_user_id


async def main():
    async with AsyncSessionLocal() as db:
        user_id = str(await get_demo_user_id(db))
    tools = cellarAuditTools.make_tools(user_id)
    # Find the tool by name
    tool_map = {t.name: t for t in tools}

    # Test get_wines_by_field with different fields and values
    get_wines_by_field = tool_map["get_wines_by_field"]
    test_cases = [
        ("color", "red"),
        ("country", "France"),
        ("region", "Bordeaux"),
        ("grape_variety", "Chardonnay"),
    ]
    for field, value in test_cases:
        result = await get_wines_by_field.ainvoke({"field": field, "value": value})
        print(f"\n--- by {field}={value} ---")
        lines = result.split("\n")
        for line in lines[:5]:
            print(line)
        if len(lines) > 6:
            print(f"... ({len(lines) - 6} more lines)")
        else:
            for line in lines[5:]:
                print(line)

    get_cellar_overview = tool_map["get_cellar_overview"]
    overview_result = await get_cellar_overview.ainvoke({})
    print("\n--- cellar overview (first 30 lines) ---")
    lines = overview_result.split("\n")
    for line in lines[:30]:
        print(line)

    get_wine_count = tool_map["get_wine_count"]
    count_result = await get_wine_count.ainvoke({})
    print("\n--- wine count ---")
    print(count_result)


asyncio.run(main())
