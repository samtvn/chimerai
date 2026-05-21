from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import engine
from database.dependencies import get_read_db
from database.repositories import UserRepository

# from routes.agent import router as agent_router
from routes.alerts import router as alerts_router
from routes.examples import router as examples_router
from routes.cellar import router as inventory_router
from routes.sse import router as sse_router
from routes.summary import router as summary_router
from routes.transactions import router as transactions_router
from routes.wines import router as wines_router

# _scheduler_task = None

# async def _periodic_analysis():
#     while True:
#         await asyncio.sleep(3600 * 24 * 7)  # weekly
#         try:
#             from agent.orchestrator import run_orchestrator
#             await run_orchestrator(trigger="scheduled_weekly")
#         except Exception as e:
#             print(f"Scheduler error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # global _scheduler_task
    print("🚀 Starting Chimerai API")
    print("📊 Verifying database connection...")
    async with engine.begin():
        print("✅ Database connection successful")

    # _scheduler_task = asyncio.create_task(_periodic_analysis())
    # print("⏰ Weekly scheduler started")

    yield

    print("🛑 Shutting down Chimerai API")
    # if _scheduler_task:
    #     _scheduler_task.cancel()
    await engine.dispose()
    print("✅ Database connection closed")


app = FastAPI(
    title="Chimerai API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# app.include_router(agent_router)
app.include_router(alerts_router)
app.include_router(examples_router)
app.include_router(inventory_router)
app.include_router(sse_router)
app.include_router(summary_router)
app.include_router(transactions_router)
app.include_router(wines_router)

@app.get("/")
async def root():
    return {"status": "ok", "message": "Chimerai API is running"}


@app.get("/test-db")
async def test_db(db: AsyncSession = Depends(get_read_db)):
    user_repo = UserRepository(db, read_only=True)
    users = await user_repo.get_all(limit=10)
    return {"users": users}


@app.get("/health")
async def health():
    return {"status": "healthy"}
