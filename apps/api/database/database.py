import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

load_dotenv()

def get_url(env_var: str):
    url = os.environ.get(env_var)
    if url and url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url

PRIMARY_URL = get_url("DATABASE_URL")
REPLICA_URL = get_url("DATABASE_RO_URL")

engine = create_async_engine(PRIMARY_URL, echo=True, pool_pre_ping=True)
replica_engine = create_async_engine(REPLICA_URL or PRIMARY_URL, pool_pre_ping=True)

AsyncSessionLocal = sessionmaker(
    bind=engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

AsyncReadSessionLocal = sessionmaker(
    bind=replica_engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

# Use this in your routes: def route(db: AsyncSession = Depends(get_db))
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

async def get_read_db():
    async with AsyncReadSessionLocal() as session:
        yield session