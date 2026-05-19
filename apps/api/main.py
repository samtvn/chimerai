from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

# Import all models to register them with SQLModel
from database.models import User, Wine, Cellar, Transaction  # noqa: F401
from database.database import engine
from database.dependencies import get_read_db
from database.repositories import UserRepository
from routes.examples import router as examples_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting Chimerai API")
    print("📊 Verifying database connection...")
    async with engine.begin():
        print("✅ Database connection successful")

    yield  # App runs here

    # Shutdown
    print("🛑 Shutting down Chimerai API")
    await engine.dispose()
    print("✅ Database connection closed")


app = FastAPI(
    title="Chimerai API",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include route modules
app.include_router(examples_router)

@app.get("/")
async def root():
    return {"status": "ok", "message": "Chimerai API is running"}

@app.get("/test-db")
async def test_db(db: AsyncSession = Depends(get_read_db)):
    """Test database connection and retrieve users using repository pattern"""
    user_repo = UserRepository(db, read_only=True)
    users = await user_repo.get_all(limit=10)
    return {"users": users}

@app.get("/health")
async def health():
    test_soup()
    return{"data" : f"{test_soup()}"}

repo = WineRepository("MiniWineAgent/data/wines.json")
taste_service = TasteService()

# @app.post("/analyze-comment")
# def analyze_comment(
#     request: AnalyzeCommentRequest
# ):

#     result = taste_service.analyze_comment(
#         request.comment
#     )

#     return {"data": "OK"}
