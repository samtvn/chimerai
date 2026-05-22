"""Test script for Orchestrator Agent"""

import asyncio
from dotenv import load_dotenv

load_dotenv()


async def test_orchestrator():
    """Test the orchestrator agent"""
    try:
        from Orchestrator.orchestrator import CellarOrchestrator
        from Orchestrator.event_manager import event_manager
        from Orchestrator.events import WineSoldEvent
        from database.database import AsyncReadSessionLocal
        from database.repositories.cellar_repository import CellarRepository

        print("=" * 70)
        print("Wine Cellar Orchestrator - Test")
        print("=" * 70)

        event_manager.add_event(WineSoldEvent(wine_ids=["test-wine"], quantity=1))

        async with AsyncReadSessionLocal() as session:
            cellar_repo = CellarRepository(session, read_only=True)
            orchestrator = CellarOrchestrator(cellar_repo)
            result = await orchestrator.run()

        print("\n" + "=" * 70)
        print("Orchestrator Result Summary")
        print("=" * 70)

        cellar_analysis = result.get("cellar_analysis")
        if cellar_analysis:
            total = getattr(cellar_analysis, "total_wines", 0)
            countries = (
                cellar_analysis.diversity_metrics.get("countries", 0)
                if hasattr(cellar_analysis, "diversity_metrics")
                else 0
            )
            print(f"\n✓ Cellar Analysis: {total} wines analyzed")
            print(f"  Diversity Level: {countries} countries")
        else:
            print("\n✗ Cellar analysis not available")

        missing_cats = result.get("missing_wine_categories", [])
        print(f"\n✓ Market Analysis Targets Identified: {len(missing_cats)}")
        for i, cat in enumerate(missing_cats, 1):
            print(f"  {i}. {cat}")

        should_market = result.get("should_call_market_analysis", False)
        print(f"\n✓ Market Analysis Needed: {should_market}")

        search_plan = result.get("search_plan")
        if search_plan:
            print(f"\n✓ Search Plan Recommendations: {len(search_plan.recommendations)}")
            top_item = search_plan.recommendations[0]
            print(f"  Top Priority: {top_item.title}")
            print(f"  Top Priority Price Range: {top_item.criteria.price_range}")
            print(f"  Top Priority Colour: {top_item.criteria.colour}")
            print("\nStructured Output for Market Analysis:")
            market_items = [
                item for item in search_plan.recommendations if item.should_call_market_analysis
            ]
            if market_items:
                for item in market_items:
                    print(f"  - {item.title} (priority {item.priority_rank})")
                    print(f"    quantity_to_buy: {item.quantity_to_buy}")
                    print(f"    criteria: {item.criteria.model_dump()}")
            else:
                print("  (none)")

        market_results = result.get("market_analysis_results", [])
        if market_results:
            print("\nMarket Analysis Results:")
            for item in market_results:
                print(f"  - {item.recommendation_title}")
                print(f"    wine_id: {item.wine_id}")
                print(f"    wine_name: {item.wine_name}")
                print(f"    producer: {item.producer}")
                print(f"    price_per_bottle: {item.price_per_bottle}")
                print(f"    quantity: {item.quantity}")
                print(f"    total_price: {item.total_price}")
                print(f"    fit_score: {item.fit_score}")
                print(f"    fit_notes: {item.fit_notes}")
                print(f"    criteria: {item.criteria.model_dump()}")

        if result.get("error"):
            print(f"\n✗ Error: {result['error']}")
            return False

        print("\n" + "=" * 70)
        return True

    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_orchestrator())
    exit(0 if success else 1)
