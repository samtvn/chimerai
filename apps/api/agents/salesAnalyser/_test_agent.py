import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import apps.api.database.models  # noqa: F401
import apps.api.env  # noqa: F401
from apps.api.agents.salesAnalyser.agent import run_sales_analysis
from apps.api.database.database import AsyncSessionLocal
from apps.api.database.dependencies import get_demo_user_id


async def main():
    async with AsyncSessionLocal() as db:
        user_id = str(await get_demo_user_id(db))

    query = "Analyze sales performance and identify which low-stock wines are worth restocking."
    print(f"Query: {query!r}\n")

    result = await run_sales_analysis(user_id, query)

    print("=== SalesAnalysisResult ===\n")
    print(f"Summary:\n{result.summary}\n")
    print(f"Best sellers: {', '.join(result.best_sellers) if result.best_sellers else 'none'}")
    print(f"Has slow movers: {result.has_slow_movers}")
    print(f"\nFast movers ({len(result.fast_movers)}):")
    for wine in result.fast_movers:
        print(f"  + {wine}")
    print(f"\nSlow movers ({len(result.slow_movers)}):")
    for wine in result.slow_movers:
        print(f"  - {wine}")


if __name__ == "__main__":
    asyncio.run(main())
