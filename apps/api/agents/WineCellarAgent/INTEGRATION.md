"""Integration guide for adding Wine Cellar Agent to main FastAPI app"""

# ============================================================================
# STEP 1: Update main.py to include the Wine Cellar Agent routes
# ============================================================================

# Add this import at the top of your main.py:
from WineCellarAgent.routes import router as cellar_router

# Then add this to your FastAPI app setup (after initializing CORS):
app.include_router(cellar_router)

# Complete example section from main.py:
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from WineCellarAgent.routes import router as cellar_router  # <- Add this

load_dotenv()

app = FastAPI(title="Chimerai API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add cellar routes
app.include_router(cellar_router)  # <- Add this

@app.get("/")
async def root():
    return {"status": "ok", "message": "Chimerai API is running"}
"""

# ============================================================================
# STEP 2: Ensure environment variables are set
# ============================================================================

# Add to your .env file:
"""
DATABASE_URL=postgresql://user:password@localhost/chimerai
DATABASE_RO_URL=postgresql://user:password@localhost-read-replica/chimerai
GOOGLE_API_KEY=your_google_api_key_here
"""

# ============================================================================
# STEP 3: Available endpoints
# ============================================================================

# After integration, these endpoints will be available:

# GET /cellar/analysis
# - Full detailed analysis with all metrics, strengths, weaknesses, recommendations
# - Response: WineCellarAnalysis object
# - Example:
#   curl http://localhost:8000/cellar/analysis

# GET /cellar/analysis/summary
# - Quick summary with key metrics and top recommendations
# - Response: Simplified dict with priority items
# - Example:
#   curl http://localhost:8000/cellar/analysis/summary

# ============================================================================
# STEP 4: Example usage in other parts of the app
# ============================================================================

# In other route handlers:
from WineCellarAgent.service import WineCellarAnalysisService

@app.post("/api/report/generate")
async def generate_report():
    \"\"\"Generate a wine cellar report\"\"\"
    analysis = await WineCellarAnalysisService.analyze_cellar()
    
    return {
        "report": {
            "timestamp": datetime.now().isoformat(),
            "total_wines": analysis.total_wines,
            "recommendations": [
                {
                    "title": rec.title,
                    "criticality": rec.criticality,
                    "action": rec.suggested_action,
                }
                for rec in analysis.recommendations
            ]
        }
    }

# ============================================================================
# STEP 5: Testing the integration
# ============================================================================

# Run the test suite:
# cd apps/api
# python -m WineCellarAgent.test

# Test individual endpoints:
# python -c "
# import asyncio
# from WineCellarAgent.service import WineCellarAnalysisService
# 
# async def test():
#     analysis = await WineCellarAnalysisService.analyze_cellar()
#     print(f'Total wines: {analysis.total_wines}')
#     print(f'Recommendations: {len(analysis.recommendations)}')
# 
# asyncio.run(test())
# "

# ============================================================================
# STEP 6: Docker considerations
# ============================================================================

# If using Docker, ensure:
# 1. GOOGLE_API_KEY is passed as environment variable
# 2. DATABASE_RO_URL points to the correct replica
# 3. The service has network access to the database

# Example docker-compose.yml entry:
"""
services:
  api:
    build: ./apps/api
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://user:password@db:5432/chimerai
      DATABASE_RO_URL: postgresql://user:password@db-replica:5432/chimerai
      GOOGLE_API_KEY: ${GOOGLE_API_KEY}
    depends_on:
      - db
      - db-replica
"""

# ============================================================================
# STEP 7: Performance notes
# ============================================================================

# - The analysis takes several seconds due to sequential LLM calls
# - Consider caching results for frequently requested analyses
# - Database queries use read-only replica to avoid blocking writes
# - The service is async and non-blocking

# For caching strategy:
"""
from functools import lru_cache
from datetime import datetime, timedelta

_cache = {}
_cache_time = None

async def get_cached_analysis(ttl_seconds=3600):
    global _cache, _cache_time
    
    now = datetime.now()
    if _cache_time and (now - _cache_time).total_seconds() < ttl_seconds:
        return _cache
    
    _cache = await WineCellarAnalysisService.analyze_cellar()
    _cache_time = now
    return _cache
"""
