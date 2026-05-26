# Orchestrator Agent

A LangGraph-based orchestrator that manages wine cellar analysis workflows and decides when to trigger market research.

## Features

- **Cellar Analysis Integration**: Orchestrates the Wine Cellar Analysis Agent
- **Gap Detection**: Identifies missing wine categories based on weaknesses and recommendations
- **Decision Making**: Automatically decides whether market analysis is needed
- **Workflow Coordination**: Uses LangGraph to pipeline analysis → evaluation → decision

## Architecture

### Workflow Pipeline

```
analyze_cellar → evaluate_gaps → decide_market_analysis → END
```

### Node Descriptions

1. **analyze_cellar**: Runs the WineCellarAnalysisService to get full cellar analysis
2. **evaluate_gaps**: Parses analysis results to identify missing wine categories
3. **decide_market_analysis**: Determines if market research is needed based on gaps

## State

The orchestrator maintains state with:
- `cellar_analysis`: Full WineCellarAnalysis object
- `needs_market_analysis`: Boolean flag for gap detection
- `missing_wine_categories`: List of identified wine categories to address
- `should_call_market_analysis`: Final decision flag
- `error`: Error tracking

## Usage

### Basic Usage

```python
import asyncio
from api.Orchestrator.service import OrchestratorService

async def main():
    result = await OrchestratorService.analyze_and_decide()
    
    if result.get("should_call_market_analysis"):
        print("Launch market analysis workflow")
        for category in result.get("missing_wine_categories", []):
            print(f"  - Research: {category}")

asyncio.run(main())
```

### Direct Usage

```python
import asyncio
from api.Orchestrator.orchestrator import CellarOrchestrator

async def main():
    orchestrator = CellarOrchestrator()
    result = await orchestrator.run()
    print(result)

asyncio.run(main())
```

## Output Example

```
[Orchestrator] Running cellar analysis...
[Orchestrator] Evaluating cellar gaps...
[Orchestrator] Found 4 wine categories to address:
  - New World wines
  - Diverse varietals
  - Expand Geographic Diversity
  - Balance Wine Types

[Orchestrator] Decision: Gaps detected in cellar
>>> Call the wine market analysis
```

## Gap Detection Logic

The orchestrator identifies gaps by:
1. Parsing cellar `weaknesses` for patterns (e.g., "New World", "fortified", "light reds")
2. Including all `recommendations` (high/medium/critical priority)
3. Deduplicating and presenting categorized list

## Next Steps (Future Enhancements)

1. **Market Analysis Agent**: Build agent to research wines for identified categories
2. **Recommendation Engine**: Generate specific wine recommendations based on gaps
3. **Purchase Integration**: Connect to wine APIs to find available wines
4. **Caching Layer**: Cache analysis results to avoid redundant LLM calls
5. **Reporting**: Generate purchase reports with priority rankings

## Testing

Run the test suite:

```bash
cd /home/gtomas/Projects/chimerai/apps
PYTHONPATH=$PWD:$PYTHONPATH uv run python api/Orchestrator/test.py
```

Expected output shows orchestrator detecting gaps and printing:
```
>>> Call the wine market analysis
```
