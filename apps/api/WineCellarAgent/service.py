"""Service module for Wine Cellar Analysis - provides high-level interface"""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from api.WineCellarAgent.agent import WineCellarAgent
from api.WineCellarAgent.models import WineCellarAnalysis
from api.database.database import AsyncReadSessionLocal


class WineCellarAnalysisService:
    """High-level service for wine cellar analysis"""

    @staticmethod
    async def analyze_cellar(db: AsyncSession) -> WineCellarAnalysis:
        """
        Analyze the wine cellar and return structured recommendations

        Args:
            db: Active database session

        Returns:
            WineCellarAnalysis: Structured analysis with recommendations and criticality levels
        """
        agent = WineCellarAgent(db)
        return await agent.analyze()


# Example usage for testing
async def example_usage():
    """Example of how to use the Wine Cellar Analysis Service"""
    print("Starting Wine Cellar Analysis...")

    try:
        async with AsyncReadSessionLocal() as session:
            analysis = await WineCellarAnalysisService.analyze_cellar(session)

        print(f"\n{'='*60}")
        print(f"Wine Cellar Analysis Report")
        print(f"{'='*60}\n")

        print(f"Total Wines: {analysis.total_wines}")
        print(f"\nDiversity Summary:")
        print(f"  - Countries: {analysis.diversity_metrics.get('countries', 0)}")
        print(f"  - Regions: {analysis.diversity_metrics.get('regions', 0)}")
        print(f"  - Wine Types: {analysis.diversity_metrics.get('wine_types', 0)}")
        print(f"  - Colours: {analysis.diversity_metrics.get('colours', 0)}")

        print(f"\n{'-'*60}")
        print("Strengths:")
        for i, strength in enumerate(analysis.strengths, 1):
            print(f"  {i}. {strength}")

        print(f"\n{'-'*60}")
        print("Areas for Improvement:")
        for i, weakness in enumerate(analysis.weaknesses, 1):
            print(f"  {i}. {weakness}")

        print(f"\n{'-'*60}")
        print("Recommendations:")
        for i, rec in enumerate(analysis.recommendations, 1):
            print(f"\n  {i}. {rec.title} [{rec.criticality.upper()}]")
            print(f"     Description: {rec.description}")
            print(f"     Action: {rec.suggested_action}")
            print(f"     Impact: {rec.estimated_impact}")

        print(f"\n{'-'*60}")
        print(f"Summary:\n{analysis.summary}")
        print(f"\nOverall Assessment:\n{analysis.overall_assessment}")

    except Exception as e:
        print(f"Error during analysis: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(example_usage())
