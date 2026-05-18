"""Test script for Orchestrator Agent"""
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()


async def test_orchestrator():
    """Test the orchestrator agent"""
    try:
        from api.Orchestrator.orchestrator import CellarOrchestrator
        
        print("=" * 70)
        print("Wine Cellar Orchestrator - Test")
        print("=" * 70)
        
        orchestrator = CellarOrchestrator()
        result = await orchestrator.run()
        
        print("\n" + "=" * 70)
        print("Orchestrator Result Summary")
        print("=" * 70)
        
        cellar_analysis = result.get("cellar_analysis")
        if cellar_analysis:
            total = getattr(cellar_analysis, "total_wines", 0)
            countries = cellar_analysis.diversity_metrics.get('countries', 0) if hasattr(cellar_analysis, 'diversity_metrics') else 0
            print(f"\n✓ Cellar Analysis: {total} wines analyzed")
            print(f"  Diversity Level: {countries} countries")
        else:
            print("\n✗ Cellar analysis not available")
        
        missing_cats = result.get("missing_wine_categories", [])
        print(f"\n✓ Missing Wine Categories Identified: {len(missing_cats)}")
        for i, cat in enumerate(missing_cats, 1):
            print(f"  {i}. {cat}")
        
        should_market = result.get("should_call_market_analysis", False)
        print(f"\n✓ Market Analysis Needed: {should_market}")
        
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
