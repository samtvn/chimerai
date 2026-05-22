# Sales Analysis Agent

A LangGraph-based agent that analyzes sales trends versus stock levels and produces structured, recommendation-only insights.

## Features

- **Sales vs Stock Trends**: Compares recent sales with current stock and computes sell-through
- **Focused Analysis**: Supports a specific wine, wine type, or price range focus
- **Structured Recommendations**: Provides advisory actions (increase stock, reduce stock, adjust price, monitor)
- **AI-Powered Insights**: Uses LangChain and Google Gemini 3.1 Flash Lite for analysis

## Architecture

### Core Components

1. **Agent** (`agent.py`): Main LangGraph workflow with states and nodes
2. **Models** (`models.py`): Pydantic models for structured output
3. **Repository** (`repository.py`): Database access layer for sales and stock data
4. **State** (`state.py`): LangGraph state definition
5. **Service** (`service.py`): High-level API for running analysis

### Workflow

```
parse_focus → fetch_data → analyze_trends → generate_recommendations → format_output
```

## Usage

### Basic Usage in FastAPI

```python
from fastapi import APIRouter, Depends
from SalesAnalysisAgent.service import SalesAnalysisService
from database.dependencies import get_read_db
from database.repositories.cellar_repository import CellarRepository

router = APIRouter()

@router.get("/sales/analysis")
async def analyze_sales(db=Depends(get_read_db)):
    cellar_repo = CellarRepository(db, read_only=True)
    analysis = await SalesAnalysisService.analyze_sales(cellar_repo)
    return analysis.model_dump()
```

### Direct Usage

```python
import asyncio
from SalesAnalysisAgent.service import SalesAnalysisService
from database.repositories.cellar_repository import CellarRepository
from api.database.database import AsyncReadSessionLocal

async def main():
    async with AsyncReadSessionLocal() as session:
        cellar_repo = CellarRepository(session, read_only=True)
        analysis = await SalesAnalysisService.analyze_sales(
            cellar_repo=cellar_repo,
            focus={"wine_type": "red"},
        )
        print(analysis.summary)

asyncio.run(main())
```

## Output Structure

```python
{
    "focus": {"label": str, "details": dict},
    "stock_metrics": {"current": int},
    "sales_metrics": {
        "total": int,
        "recent": int,
        "previous": int,
        "trend": "up|down|flat",
        "change_pct": float | None,
        "sell_through_rate": float,
        "lookback_days": int
    },
    "movers": {"fast_movers": [...], "slow_movers": [...]},
    "trend_observations": [str, ...],
    "recommendations": [...],
    "overall_assessment": str,
    "summary": str
}
```

## Environment Variables

- `DATABASE_RO_URL`: PostgreSQL read-only database URL (async format with psycopg driver)
- `GOOGLE_API_KEY`: API key for Google Gemini access

## Notes

- Recommendations are advisory only and do not perform stock or price changes.
- Use `focus.query` for free-form focus recognition (wine name, type, or price range).
