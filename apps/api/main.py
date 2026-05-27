import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.database.database import engine
from apps.api.database.dependencies import get_read_db
from apps.api.database.repositories import UserRepository
from apps.api.events.handlers.orchestrator_trigger import run_event_listener
from routes.agents import router as agent_router
from routes.alerts import router as alerts_router
from routes.cellar import router as inventory_router
from routes.examples import router as examples_router
from routes.recommendations import router as recommendations_router
from routes.sse import router as sse_router
from routes.summary import router as summary_router
from routes.transactions import router as transactions_router
from routes.wines import router as wines_router
from WineCardAgent.routes import router as wine_card_router
from WineCardAgent.trigger_service import WineCardTriggerService

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
    listener_task = asyncio.create_task(run_event_listener())
    wine_card_listener_task = asyncio.create_task(WineCardTriggerService.run_event_listener())
    print("🚀 Starting Chimerai API")
    print("📊 Verifying database connection...")
    async with engine.begin():
        print("✅ Database connection successful")

    # _scheduler_task = asyncio.create_task(_periodic_analysis())
    # print("⏰ Weekly scheduler started")

    yield

    print("🛑 Shutting down Chimerai API")
    listener_task.cancel()
    wine_card_listener_task.cancel()
    with suppress(asyncio.CancelledError):
        await listener_task
    with suppress(asyncio.CancelledError):
        await wine_card_listener_task
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
app.include_router(recommendations_router)
app.include_router(wine_card_router)
app.include_router(agent_router)


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
