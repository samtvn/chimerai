# Wine Cellar Analysis Agent

A LangGraph-based agent that analyzes wine cellar diversity and provides structured recommendations using Google's Gemini API.

## Features

- **Diversity Analysis**: Analyzes the distribution of wines by country, region, type, and colour
- **Strengths & Weaknesses**: Identifies what's working well in your cellar and areas for improvement
- **Structured Recommendations**: Provides actionable recommendations with criticality levels (low, medium, high, critical)
- **AI-Powered Insights**: Uses LangChain and Google Gemini 3.1 Flash Lite for intelligent analysis

## Architecture

### Core Components

1. **Agent** (`agent.py`): Main LangGraph workflow with states and nodes
2. **Models** (`models.py`): Pydantic models for structured output
3. **Repository** (`repository.py`): Database access layer for fetching wine data
4. **State** (`state.py`): LangGraph state definition
5. **Service** (`service.py`): High-level API for running analysis

### Workflow

The agent follows this LangGraph workflow:

```
fetch_data → analyze_diversity → analyze_strengths → analyze_weaknesses → generate_recommendations → format_output
```

## Usage

### Basic Usage in FastAPI

```python
from fastapi import APIRouter
from WineCellarAgent.service import WineCellarAnalysisService

router = APIRouter()

@router.get("/cellar/analysis")
async def analyze_wine_cellar():
    """Analyze the wine cellar and return recommendations"""
    analysis = await WineCellarAnalysisService.analyze_cellar()
    return analysis.model_dump()
```

### Direct Usage

```python
import asyncio
from WineCellarAgent.service import WineCellarAnalysisService

async def main():
    analysis = await WineCellarAnalysisService.analyze_cellar()
    print(f"Total Wines: {analysis.total_wines}")
    print(f"Recommendations: {analysis.recommendations}")

asyncio.run(main())
```

## Environment Variables

- `DATABASE_RO_URL`: PostgreSQL read-only database URL (async format with psycopg driver)
- `GOOGLE_API_KEY`: API key for Google Gemini access (used by langchain-google-genai)
- `DATABASE_URL`: (Optional) Primary database URL for comparison

## Output Structure

### WineCellarAnalysis

```python
{
    "total_wines": int,
    "diversity_metrics": {
        "countries": int,
        "regions": int,
        "wine_types": int,
        "colours": int,
        "sub_types": int,
        "distribution_by_country": dict,
        "distribution_by_type": dict
    },
    "strengths": [str, ...],
    "weaknesses": [str, ...],
    "recommendations": [
        {
            "title": str,
            "description": str,
            "criticality": "low|medium|high|critical",
            "suggested_action": str,
            "estimated_impact": str
        }
    ],
    "overall_assessment": str,
    "summary": str
}
```

## Dependencies

The agent requires these packages (already in `pyproject.toml`):

- `langgraph>=1.1.10`
- `langchain>=1.2.18`
- `langchain-google-genai>=4.2.2`
- `sqlmodel>=0.0.38`
- `sqlalchemy` (async support)
- `psycopg[binary]>=3.3.4` (PostgreSQL driver)

## Implementation Details

### Database Access

- Uses **read-only replica** (`DATABASE_RO_URL`) for non-blocking analysis
- Async SQLAlchemy sessions for concurrent database access
- Fetches wine metrics: country, region, type, colour, sub-type distributions

### LLM Integration

- Uses **Google Gemini 3.1 Flash Lite** model via LangChain
- Temperature: 0.5 (balanced creativity and consistency)
- Max tokens: 1000 per response
- Streaming: Disabled for structured analysis

### Graph Nodes

1. **fetch_data**: Retrieves all wines and calculates diversity metrics
2. **analyze_diversity**: Evaluates overall cellar diversity
3. **analyze_strengths**: Identifies positive aspects of the collection
4. **analyze_weaknesses**: Identifies areas for improvement
5. **generate_recommendations**: Creates actionable recommendations
6. **format_output**: Structures output into WineCellarAnalysis model

## Error Handling

- Database connection errors are caught and reported
- LLM API errors are handled gracefully
- Invalid model data falls back to default recommendations
- All errors are tracked in the state

## Performance Considerations

- Read-only database connection minimizes lock contention
- Async operations prevent blocking
- LLM calls are sequential but could be parallelized with StateGraph branches
- Full wine data is fetched (consider pagination for very large cellars)

## Future Enhancements

- Add filtering for specific subsets of cellar
- Implement user preferences in analysis
- Add temporal analysis (aging trends)
- Create comparison with other cellars
- Add price/value metrics
- Parallel LLM analysis nodes for faster execution
