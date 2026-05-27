import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import apps.api.env  # noqa: F401
import apps.api.database.models  # noqa: F401

from apps.api.agents.cellarAudit.agent import run_inventory_audit
from apps.api.database.database import AsyncSessionLocal
from apps.api.database.dependencies import get_demo_user_id


async def main():
    async with AsyncSessionLocal() as db:
        user_id = str(await get_demo_user_id(db))

    query = "Analyze the current cellar state and flag any concerns."
    print(f"Query: {query!r}\n")

    result = await run_inventory_audit(user_id, query)

    print("=== WineCellarAnalysis ===\n")
    print(f"Total wine entries: {result.total_wines}")
    print(f"Quantity observation: {result.quantity_observation}\n")

    print(f"Overall assessment:\n  {result.overall_assessment}\n")
    print(f"Summary:\n  {result.summary}\n")

    print(f"Diversity metrics:")
    for k, v in result.diversity_metrics.items():
        if not isinstance(v, dict):
            print(f"  {k}: {v}")

    print(f"\nDistribution by color:")
    for color, count in sorted(
        result.diversity_metrics.get("distribution_by_color", {}).items(), key=lambda x: -x[1]
    ):
        print(f"  {color}: {count}")

    print(f"\nDistribution by country (top 5):")
    for country, count in sorted(
        result.diversity_metrics.get("distribution_by_country", {}).items(), key=lambda x: -x[1]
    )[:5]:
        print(f"  {country}: {count}")

    print(f"\nStrengths ({len(result.strengths)}):")
    for s in result.strengths[:5]:
        print(f"  - {s}")

    print(f"\nWeaknesses ({len(result.weaknesses)}):")
    for w in result.weaknesses[:5]:
        print(f"  - {w}")

    print(f"\nRecommendations ({len(result.recommendations)}):")
    for rec in result.recommendations:
        print(f"  [{rec.criticality.value.upper()}] {rec.title}")
        print(f"    {rec.description}")
        print(f"    Price range: {rec.price_range} | Qty: {rec.quantity_to_buy}")
        print(f"    Action: {rec.suggested_action}")
        print(f"    Impact: {rec.estimated_impact}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
