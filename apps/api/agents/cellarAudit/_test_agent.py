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

    print("=== InventoryAuditResult ===\n")
    print(f"Summary:\n  {result.summary}\n")
    print(f"Has low stock:  {result.has_low_stock}")
    print(f"Low-stock wines: {len(result.low_stock_wines)} wines")
    if result.low_stock_wines:
        for wine in result.low_stock_wines[:5]:
            print(f"  - {wine}")
        if len(result.low_stock_wines) > 5:
            print(f"  ... and {len(result.low_stock_wines) - 5} more")
    
    print(f"\nDiversity gaps: {result.diversity_gaps if result.diversity_gaps else 'none'}\n")
    
    print(f"By color ({len(result.wines_by_color)} categories):")
    for color, count in sorted(result.wines_by_color.items(), key=lambda x: -x[1])[:5]:
        print(f"  {color}: {count}")
    
    print(f"\nBy country ({len(result.wines_by_country)} countries):")
    for country, count in sorted(result.wines_by_country.items(), key=lambda x: -x[1])[:5]:
        print(f"  {country}: {count}")
    
    print(f"\nBy region ({len(result.wines_by_region)} regions):")
    for region, count in sorted(result.wines_by_region.items(), key=lambda x: -x[1])[:5]:
        print(f"  {region}: {count}")
    
    print(f"\nBy variety ({len(result.wines_by_variety)} varieties):")
    for variety, count in sorted(result.wines_by_variety.items(), key=lambda x: -x[1])[:5]:
        print(f"  {variety}: {count}")


if __name__ == "__main__":
    asyncio.run(main())
