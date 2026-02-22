"""
Vision-AI Authentication Routes
"""
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Body, HTTPException, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, User, ActivityLog

router = APIRouter(tags=["Authentication"])

# Simple JWT-like token store (in production use proper JWT)
_tokens: dict = {}


def _hash_password(password: str, salt: str = "") -> str:
    if not salt:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000).hex()
    return f"{salt}${hashed}"


def _verify_password(password: str, stored: str) -> bool:
    salt, hashed = stored.split("$", 1)
    return _hash_password(password, salt) == stored


def _generate_token(user_id: int, role: str) -> str:
    token = secrets.token_urlsafe(48)
    _tokens[token] = {
        "user_id": user_id, "role": role,
        "expires": datetime.utcnow() + timedelta(hours=24)
    }
    return token


async def get_current_user(authorization: Optional[str] = Header(None)):
    """Dependency to get current authenticated user."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.replace("Bearer ", "")
    info = _tokens.get(token)
    if not info:
        raise HTTPException(status_code=401, detail="Invalid token")
    if datetime.utcnow() > info["expires"]:
        del _tokens[token]
        raise HTTPException(status_code=401, detail="Token expired")
    return info


async def require_admin(user=Depends(get_current_user)):
    """Require admin role."""
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


@router.post("/auth/register")
async def register(data: dict = Body(...), db: AsyncSession = Depends(get_db)):
    """Register a new user."""
    username = data.get("username", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "")
    
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password required")
    
    # Check existing
    result = await db.execute(select(User).where(User.username == username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Username already exists")
    
    if email:
        result = await db.execute(select(User).where(User.email == email))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Email already in use")
    
    user = User(
        username=username,
        email=email or None,
        password_hash=_hash_password(password),
        role=data.get("role", "user"),
        is_active=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    # Log
    db.add(ActivityLog(user_id=user.id, action="register", details={"username": username}))
    await db.commit()
    
    return {"id": user.id, "username": user.username, "role": user.role}


@router.post("/auth/login")
async def login(data: dict = Body(...), db: AsyncSession = Depends(get_db)):
    """Login and get access token."""
    username = data.get("username", "")
    password = data.get("password", "")
    
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    
    if not user or not _verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")
    
    token = _generate_token(user.id, user.role)
    user.last_login = datetime.utcnow()
    
    db.add(ActivityLog(user_id=user.id, action="login", details={"ip": "n/a"}))
    await db.commit()
    
    return {
        "token": token,
        "user": {"id": user.id, "username": user.username, "role": user.role},
        "expires_in": 86400
    }


@router.post("/auth/logout")
async def logout(user=Depends(get_current_user)):
    """Logout / invalidate token."""
    to_remove = [k for k, v in _tokens.items() if v["user_id"] == user["user_id"]]
    for k in to_remove:
        del _tokens[k]
    return {"status": "logged out"}


@router.get("/auth/me")
async def get_me(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get current user profile."""
    result = await db.execute(select(User).where(User.id == user["user_id"]))
    u = result.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": u.id, "username": u.username, "email": u.email,
        "role": u.role, "is_active": u.is_active,
        "last_login": u.last_login.isoformat() if u.last_login else None,
        "created_at": u.created_at.isoformat() if u.created_at else None,
        "preferences": u.preferences
    }


@router.put("/auth/me")
async def update_profile(
    data: dict = Body(...),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user profile."""
    result = await db.execute(select(User).where(User.id == user["user_id"]))
    u = result.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    
    if "email" in data:
        u.email = data["email"]
    if "preferences" in data:
        u.preferences = data["preferences"]
    if "password" in data:
        u.password_hash = _hash_password(data["password"])
    
    await db.commit()
    return {"status": "updated"}


@router.put("/auth/me/password")
async def change_password(
    data: dict = Body(...),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Change password."""
    result = await db.execute(select(User).where(User.id == user["user_id"]))
    u = result.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404)
    
    if not _verify_password(data.get("current_password", ""), u.password_hash):
        raise HTTPException(status_code=400, detail="Current password incorrect")
    
    u.password_hash = _hash_password(data["new_password"])
    await db.commit()
    return {"status": "password changed"}


# ---- Admin ----

@router.get("/admin/users")
async def list_users(admin=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    """List all users (admin only)."""
    result = await db.execute(select(User))
    users = result.scalars().all()
    return [{
        "id": u.id, "username": u.username, "email": u.email,
        "role": u.role, "is_active": u.is_active,
        "last_login": u.last_login.isoformat() if u.last_login else None,
        "created_at": u.created_at.isoformat() if u.created_at else None
    } for u in users]


@router.put("/admin/users/{user_id}")
async def admin_update_user(
    user_id: int,
    data: dict = Body(...),
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Admin update user."""
    result = await db.execute(select(User).where(User.id == user_id))
    u = result.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404)
    
    for key in ["role", "is_active", "email"]:
        if key in data:
            setattr(u, key, data[key])
    await db.commit()
    return {"status": "updated"}


@router.delete("/admin/users/{user_id}")
async def admin_delete_user(
    user_id: int,
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Admin delete user."""
    result = await db.execute(select(User).where(User.id == user_id))
    u = result.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404)
    await db.delete(u)
    await db.commit()
    return {"status": "deleted"}


@router.get("/admin/activity")
async def get_activity_log(
    user_id: Optional[int] = None,
    limit: int = 100,
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get activity log (admin only)."""
    from sqlalchemy import desc
    query = select(ActivityLog).order_by(desc(ActivityLog.created_at)).limit(limit)
    if user_id:
        query = query.where(ActivityLog.user_id == user_id)
    result = await db.execute(query)
    logs = result.scalars().all()
    return [{
        "id": l.id, "user_id": l.user_id, "action": l.action,
        "details": l.details,
        "created_at": l.created_at.isoformat() if l.created_at else None
    } for l in logs]
