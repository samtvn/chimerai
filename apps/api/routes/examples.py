"""
Example routes demonstrating read-only vs write access patterns.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database.dependencies import get_db, get_read_db
from database.repositories.user_repository import UserRepository
from database.repositories.wine_repository import WineRepository
from database.repositories.cellar_repository import CellarRepository

router = APIRouter(prefix="/api", tags=["examples"])


# ============================================================================
# READ-ONLY ROUTES (for AI agents, safe to call frequently)
# ============================================================================

@router.get("/users/{username}")
async def get_user(username: str, db: AsyncSession = Depends(get_read_db)):
    """AI agent route: Get user by username (read-only)"""
    repo = UserRepository(db, read_only=True)
    user = await repo.get_by_username(username)
    return user or {"error": "User not found"}


@router.get("/wines/color/{color}")
async def get_wines_by_color(color: str, db: AsyncSession = Depends(get_read_db)):
    """AI agent route: Get wines by color (read-only)"""
    repo = WineRepository(db, read_only=True)
    wines = await repo.get_by_color(color, limit=50)
    return {"color": color, "count": len(wines), "wines": wines}


@router.get("/cellar/{user_id}/inventory")
async def get_user_inventory(user_id: str, db: AsyncSession = Depends(get_read_db)):
    """AI agent route: Get user's current inventory (read-only)"""
    from uuid import UUID
    repo = CellarRepository(db, read_only=True)
    bottles = await repo.get_user_cellar_in_stock(UUID(user_id), limit=100)
    return {"user_id": user_id, "bottles_in_stock": len(bottles), "bottles": bottles}


# ============================================================================
# WRITE ROUTES (for admin, restricted to write-enabled sessions)
# ============================================================================

@router.post("/users")
async def create_user(username: str, email: str, db: AsyncSession = Depends(get_db)):
    """Admin route: Create new user (write-enabled)"""
    repo = UserRepository(db, read_only=False)
    try:
        user = await repo.create(username=username, email=email)
        return {"status": "created", "user": user}
    except PermissionError as e:
        return {"error": str(e)}


@router.put("/users/{user_id}")
async def update_user(user_id: str, username: str, db: AsyncSession = Depends(get_db)):
    """Admin route: Update user (write-enabled)"""
    from uuid import UUID
    repo = UserRepository(db, read_only=False)
    try:
        user = await repo.update(UUID(user_id), username=username)
        return {"status": "updated", "user": user}
    except PermissionError as e:
        return {"error": str(e)}


# ============================================================================
# MIXED ROUTES (read from read-only, write with write-enabled)
# ============================================================================

@router.get("/validate/user/{username}")
async def validate_user_exists(username: str, db: AsyncSession = Depends(get_read_db)):
    """Validation route: Check if user exists (read-only)"""
    repo = UserRepository(db, read_only=True)
    user = await repo.get_by_username(username)
    return {"exists": user is not None, "username": username}
