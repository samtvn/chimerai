import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))
import apps.api.agents.salesAnalyser.tools as salesAnalyserTools
import apps.api.database.models  # noqa: F401 — registers all models
import apps.api.env  # noqa: F401 — loads .env
from apps.api.database.database import AsyncSessionLocal
from apps.api.database.dependencies import get_demo_user_id


async def main():
    async with AsyncSessionLocal() as db:
        user_id = str(await get_demo_user_id(db))
    tools = salesAnalyserTools.make_tools(user_id)
    # Find the tool by name
    tool_map = {t.name: t for t in tools}

    # Test get_sales_history with different fields and values
    get_sales_history = tool_map["get_sales_history"]
    test_cases = [
        "Chateau Margaux 2015",
        "Domaine de la Romanee-Conti 2018",
        "Opus One 2016",
    ]
    for wine_name in test_cases:
        result = await get_sales_history.ainvoke({"wine_name": wine_name})
        print(f"\n--- sales history for {wine_name} ---")
        lines = result.split("\n")
        for line in lines[:5]:
            print(line)
        if len(lines) > 6:
            print(f"... ({len(lines) - 6} more lines)")
        else:
            for line in lines[5:]:
                print(line)

    get_top_movers = tool_map["get_top_movers"]
    top_movers_result = await get_top_movers.ainvoke({})
    print("\n--- top movers (first 30 lines) ---")
    lines = top_movers_result.split("\n")
    for line in lines[:30]:
        print(line)

    get_top_sellers = tool_map["get_top_sellers"]
    top_sellers_result = await get_top_sellers.ainvoke({})
    print("\n--- top sellers (first 30 lines) ---")
    lines = top_sellers_result.split("\n")
    for line in lines[:30]:
        print(line)


asyncio.run(main())
