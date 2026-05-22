"""Test script for Wine Cellar Analysis Agent

This script can be run to test the agent locally:
    python -m WineCellarAgent.test

Or with pytest:
    pytest WineCellarAgent/test.py
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
        from WineCellarAgent.models import (
            CriticalityLevel,
            Recommendation,
            RecommendationPlan,
            WineBuyingAspect,
            WineBuyingParameter,
            WineCellarAnalysis,
        )
        from WineCellarAgent.state import WineCellarAgentState
        from WineCellarAgent.repository import WineCellarRepository
        from WineCellarAgent.agent import WineCellarAgent
        from WineCellarAgent.service import WineCellarAnalysisService
        from database.repositories.cellar_repository import CellarRepository

        print("✓ All modules imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False


async def test_structured_models():
    """Test the structured recommendation schema validates correctly"""
    try:
        from WineCellarAgent.models import (
            CriticalityLevel,
            Recommendation,
            RecommendationPlan,
            WineBuyingAspect,
            WineBuyingParameter,
        )

        plan = RecommendationPlan(
            recommendations=[
                Recommendation(
                    title="Add Northern Italian Reds",
                    description="Improve geographic balance with structured purchases from Italy.",
                    criticality=CriticalityLevel.HIGH,
                    price_range="25-45 EUR",
                    quantity_to_buy=6,
                    parameters=[
                        WineBuyingParameter(
                            aspect=WineBuyingAspect.COUNTRY,
                            target="Italy",
                            rationale="The cellar is underrepresented in Italian wines",
                        ),
                        WineBuyingParameter(
                            aspect=WineBuyingAspect.REGION,
                            target="Piedmont or Veneto",
                            rationale="These regions add strong stylistic diversity",
                        ),
                    ],
                    suggested_action="Buy six bottles from a balanced mix of Italian producers",
                    estimated_impact="Better regional diversity and more food-pairing options",
                )
            ]
        )

        recommendation = plan.recommendations[0]
        assert recommendation.quantity_to_buy == 6
        assert recommendation.price_range == "25-45 EUR"
        assert recommendation.parameters[0].aspect == WineBuyingAspect.COUNTRY
        assert recommendation.parameters[1].aspect == WineBuyingAspect.REGION
        assert recommendation.criticality == CriticalityLevel.HIGH

        print("✓ Structured recommendation models validated successfully")
        return True
    except Exception as e:
        print(f"✗ Structured model validation failed: {e}")
        return False


async def test_database_connection():
    """Test database connection"""
    try:
        from WineCellarAgent.repository import WineCellarRepository
        from database.database import AsyncReadSessionLocal
        from database.repositories.cellar_repository import CellarRepository

        async with AsyncReadSessionLocal() as session:
            cellar_repo = CellarRepository(session, read_only=True)
            repo = WineCellarRepository(cellar_repo)
            count = await repo.get_wine_count()
            print(f"✓ Database connection successful - Found {count} wines")
        return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False


async def test_full_analysis():
    """Run a full analysis (this requires valid database and API key)"""
    try:
        print("\nRunning full wine cellar analysis...")
        from WineCellarAgent.service import WineCellarAnalysisService
        from database.database import AsyncReadSessionLocal
        from database.repositories.cellar_repository import CellarRepository
        import json

        async with AsyncReadSessionLocal() as session:
            cellar_repo = CellarRepository(session, read_only=True)
            analysis = await WineCellarAnalysisService.analyze_cellar(cellar_repo)

        print(f"\n✓ Analysis completed successfully!")
        print("\n" + "=" * 60)
        print("FULL CELLAR ANALYSIS RESPONSE")
        print("=" * 60)

        print(f"\nTotal wines: {analysis.total_wines}")

        print(f"\n--- Diversity Metrics ---")
        for key, value in analysis.diversity_metrics.items():
            if isinstance(value, dict):
                print(f"{key}:")
                for k, v in list(value.items())[:10]:  # Show first 10 items
                    print(f"  {k}: {v}")
                if len(value) > 10:
                    print(f"  ... and {len(value) - 10} more")
            else:
                print(f"{key}: {value}")

        print(f"\n--- Strengths ({len(analysis.strengths)}) ---")
        for i, strength in enumerate(analysis.strengths, 1):
            print(f"{i}. {strength}")

        print(f"\n--- Weaknesses ({len(analysis.weaknesses)}) ---")
        for i, weakness in enumerate(analysis.weaknesses, 1):
            print(f"{i}. {weakness}")

        print(f"\n--- Recommendations ({len(analysis.recommendations)}) ---")
        for i, rec in enumerate(analysis.recommendations, 1):
            print(f"\n{i}. {rec.title}")
            print(f"   Criticality: {rec.criticality.value}")
            print(f"   Price range: {rec.price_range}")
            print(f"   Description: {rec.description}")
            print(f"   Suggested Action: {rec.suggested_action}")
            print(f"   Estimated Impact: {rec.estimated_impact}")

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
    print("Wine Cellar Analysis Agent - Test Suite")
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
