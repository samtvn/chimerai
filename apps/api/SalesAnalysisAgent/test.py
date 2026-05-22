"""Test script for Sales Analysis Agent

This script can be run to test the agent locally:
    python -m SalesAnalysisAgent.test

Or with pytest:
    pytest SalesAnalysisAgent/test.py
"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()


# Check environment variables
def check_env():
    """Verify required environment variables are set"""
    required_vars = ["DATABASE_RO_URL", "GOOGLE_API_KEY"]
    missing = []

    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)

    if missing:
        print(f"⚠️  Missing environment variables: {', '.join(missing)}")
        print("Please set these variables before running the agent:")
        for var in missing:
            print(f"  export {var}=<value>")
        return False

    print("✓ Environment variables are configured")
    return True


async def test_basic_import():
    """Test that all modules can be imported"""
    try:
        from SalesAnalysisAgent.models import (
            CriticalityLevel,
            RecommendationType,
            SalesAnalysisFocus,
            SalesAnalysisResult,
            SalesRecommendation,
            SalesRecommendationPlan,
        )
        from SalesAnalysisAgent.state import SalesAnalysisAgentState
        from SalesAnalysisAgent.repository import SalesAnalysisRepository
        from SalesAnalysisAgent.agent import SalesAnalysisAgent
        from SalesAnalysisAgent.service import SalesAnalysisService
        from database.repositories.cellar_repository import CellarRepository

        print("✓ All modules imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False


async def test_structured_models():
    """Test the structured recommendation schema validates correctly"""
    try:
        from SalesAnalysisAgent.models import (
            CriticalityLevel,
            RecommendationType,
            SalesRecommendation,
            SalesRecommendationPlan,
        )

        plan = SalesRecommendationPlan(
            recommendations=[
                SalesRecommendation(
                    title="Increase stock for fast movers",
                    description="Strong sellers should have sufficient stock to avoid missed sales.",
                    criticality=CriticalityLevel.HIGH,
                    recommendation_type=RecommendationType.INCREASE_STOCK,
                    target="Top 3 fast movers",
                    suggested_action="Consider increasing reorder quantities for top sellers.",
                    evidence="Fast movers show high sell-through with low remaining stock.",
                    expected_impact="Higher availability and fewer stockouts.",
                )
            ]
        )

        recommendation = plan.recommendations[0]
        assert recommendation.recommendation_type == RecommendationType.INCREASE_STOCK
        assert recommendation.criticality == CriticalityLevel.HIGH
        assert recommendation.target == "Top 3 fast movers"

        print("✓ Structured recommendation models validated successfully")
        return True
    except Exception as e:
        print(f"✗ Structured model validation failed: {e}")
        return False


async def test_database_connection():
    """Test database connection"""
    try:
        from SalesAnalysisAgent.repository import SalesAnalysisRepository
        from database.database import AsyncReadSessionLocal
        from database.repositories.cellar_repository import CellarRepository

        async with AsyncReadSessionLocal() as session:
            cellar_repo = CellarRepository(session, read_only=True)
            repo = SalesAnalysisRepository(cellar_repo)
            summary = await repo.get_sales_stock_summary(focus=None, lookback_days=30)
            print("✓ Database connection successful")
            print(f"  Stock current: {summary.get('stock', {}).get('current', 0)}")
            print(f"  Recent sales: {summary.get('sales', {}).get('recent', 0)}")
        return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False


async def test_full_analysis():
    """Run a full analysis (this requires valid database and API key)"""
    try:
        print("\nRunning full sales analysis...")
        from SalesAnalysisAgent.service import SalesAnalysisService
        from database.database import AsyncReadSessionLocal
        from database.repositories.cellar_repository import CellarRepository
        import json

        async with AsyncReadSessionLocal() as session:
            cellar_repo = CellarRepository(session, read_only=True)
            analysis = await SalesAnalysisService.analyze_sales(
                cellar_repo=cellar_repo,
                focus={"wine_type": "red"},
            )

        print("\n✓ Analysis completed successfully!")
        print("\n" + "=" * 60)
        print("FULL SALES ANALYSIS RESPONSE")
        print("=" * 60)

        print(f"\nFocus: {analysis.focus}")
        print(f"\nStock metrics: {analysis.stock_metrics}")
        print(f"\nSales metrics: {analysis.sales_metrics}")

        print(f"\n--- Trend Observations ({len(analysis.trend_observations)}) ---")
        for i, observation in enumerate(analysis.trend_observations, 1):
            print(f"{i}. {observation}")

        print(f"\n--- Recommendations ({len(analysis.recommendations)}) ---")
        for i, rec in enumerate(analysis.recommendations, 1):
            print(f"\n{i}. {rec.title}")
            print(f"   Criticality: {rec.criticality.value}")
            print(f"   Type: {rec.recommendation_type.value}")
            print(f"   Target: {rec.target}")
            print(f"   Suggested Action: {rec.suggested_action}")
            print(f"   Evidence: {rec.evidence}")
            print(f"   Expected Impact: {rec.expected_impact}")

        print(f"\n--- Overall Assessment ---")
        print(analysis.overall_assessment)

        print(f"\n--- Summary ---")
        print(analysis.summary)

        print("\n" + "=" * 60)
        print("JSON RESPONSE")
        print("=" * 60)
        print(json.dumps(analysis.model_dump(), indent=2, default=str))

        return True
    except Exception as e:
        print(f"✗ Analysis failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("=" * 60)
    print("Sales Analysis Agent - Test Suite")
    print("=" * 60)
    print()

    tests = [
        ("Environment Variables", check_env),
        ("Module Imports", test_basic_import),
        ("Structured Models", test_structured_models),
        ("Database Connection", test_database_connection),
        ("Full Analysis", test_full_analysis),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n[Test] {test_name}")
        print("-" * 40)
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
            import traceback

            traceback.print_exc()
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")

    passed = sum(1 for _, result in results if result)
    total = len(results)
    print(f"\nTotal: {passed}/{total} tests passed")

    return all(result for _, result in results)


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
