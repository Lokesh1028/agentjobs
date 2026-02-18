"""Authentication, user management, and API key endpoints."""

import uuid
import hashlib
import secrets
import json
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Header, Request, Depends
from typing import Optional
import bcrypt as _bcrypt
from models import (
    AuthRegisterRequest, AuthRegisterResponse, UsageResponse,
    SignupRequest, LoginRequest, UserProfile, AuthResponse, MessageResponse,
)
from database import get_db

router = APIRouter(prefix="/api/v1", tags=["auth"])


# ── Helpers ──────────────────────────────────────────────────────

def _hash_key(key: str) -> str:
    """Hash an API key for storage."""
    return hashlib.sha256(key.encode()).hexdigest()


def _generate_api_key() -> str:
    """Generate a new API key."""
    return f"aj_{secrets.token_hex(24)}"


def _generate_session_token() -> str:
    """Generate a session token."""
    return secrets.token_hex(32)


def _row_to_user(row) -> UserProfile:
    """Convert a DB row to UserProfile."""
    return UserProfile(
        id=row["id"],
        email=row["email"],
        name=row["name"],
        company=row["company"],
        role=row["role"],
        avatar_url=row["avatar_url"],
        is_active=bool(row["is_active"]),
        last_login=row["last_login"],
        login_count=row["login_count"] or 0,
        created_at=row["created_at"],
    )


async def get_current_user(request: Request) -> Optional[dict]:
    """Extract current user from Authorization header (Bearer token)."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth[7:]
    db = await get_db()
    cursor = await db.execute(
        """SELECT s.*, u.id as uid, u.email, u.name, u.company, u.role, u.avatar_url,
                  u.is_active, u.last_login, u.login_count, u.created_at as user_created_at
           FROM sessions s
           JOIN users u ON s.user_id = u.id
           WHERE s.token = ? AND s.is_active = 1 AND s.expires_at > ?""",
        [token, datetime.utcnow().isoformat()]
    )
    row = await cursor.fetchone()
    if not row:
        return None
    return {
        "id": row["uid"],
        "email": row["email"],
        "name": row["name"],
        "company": row["company"],
        "role": row["role"],
        "avatar_url": row["avatar_url"],
        "is_active": row["is_active"],
        "last_login": row["last_login"],
        "login_count": row["login_count"],
        "created_at": row["user_created_at"],
        "session_token": token,
    }


async def require_user(request: Request) -> dict:
    """Require authenticated user."""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


async def require_admin(request: Request) -> dict:
    """Require authenticated admin user."""
    user = await require_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


async def log_activity(user_id: Optional[str], action: str, details: Optional[str],
                       ip_address: Optional[str] = None, user_agent: Optional[str] = None):
    """Log user activity (fire and forget style)."""
    try:
        db = await get_db()
        await db.execute(
            """INSERT INTO user_activity (user_id, action, details, ip_address, user_agent)
               VALUES (?, ?, ?, ?, ?)""",
            [user_id, action, details, ip_address, user_agent]
        )
        await db.commit()
    except Exception:
        pass  # Don't let logging failures break the app


# ── User Auth Endpoints ──────────────────────────────────────────

@router.post("/auth/signup", response_model=AuthResponse)
async def signup(request: SignupRequest, req: Request):
    """Register a new user account."""
    db = await get_db()

    # Check if email exists
    cursor = await db.execute("SELECT id FROM users WHERE email = ?", [request.email])
    if await cursor.fetchone():
        raise HTTPException(status_code=409, detail="Email already registered")

    # Validate role
    allowed_roles = ["user", "recruiter"]
    role = request.role if request.role in allowed_roles else "user"

    # Create user
    user_id = f"u_{uuid.uuid4().hex[:12]}"
    password_hash = _bcrypt.hashpw(request.password.encode(), _bcrypt.gensalt()).decode()
    now = datetime.utcnow().isoformat()

    await db.execute("""
        INSERT INTO users (id, email, name, password_hash, company, role, last_login, login_count, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
    """, (user_id, request.email, request.name, password_hash, request.company, role, now, now))

    # Create session
    token = _generate_session_token()
    expires = (datetime.utcnow() + timedelta(hours=24)).isoformat()
    await db.execute(
        "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
        [token, user_id, expires]
    )
    await db.commit()

    # Log activity
    ip = req.client.host if req.client else None
    ua = req.headers.get("user-agent")
    await log_activity(user_id, "register", json.dumps({"email": request.email}), ip, ua)

    user = UserProfile(
        id=user_id, email=request.email, name=request.name,
        company=request.company, role=role, last_login=now,
        login_count=1, created_at=now,
    )
    return AuthResponse(user=user, token=token, message="Account created successfully")


@router.post("/auth/login", response_model=AuthResponse)
async def login(request: LoginRequest, req: Request):
    """Log in with email and password."""
    db = await get_db()

    cursor = await db.execute("SELECT * FROM users WHERE email = ? AND is_active = 1", [request.email])
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not _bcrypt.checkpw(request.password.encode(), row["password_hash"].encode()):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Update login stats
    now = datetime.utcnow().isoformat()
    new_count = (row["login_count"] or 0) + 1
    await db.execute(
        "UPDATE users SET last_login = ?, login_count = ? WHERE id = ?",
        [now, new_count, row["id"]]
    )

    # Create session
    token = _generate_session_token()
    expires = (datetime.utcnow() + timedelta(hours=24)).isoformat()
    await db.execute(
        "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
        [token, row["id"], expires]
    )
    await db.commit()

    # Log activity
    ip = req.client.host if req.client else None
    ua = req.headers.get("user-agent")
    await log_activity(row["id"], "login", None, ip, ua)

    user = UserProfile(
        id=row["id"], email=row["email"], name=row["name"],
        company=row["company"], role=row["role"], avatar_url=row["avatar_url"],
        last_login=now, login_count=new_count, created_at=row["created_at"],
    )
    return AuthResponse(user=user, token=token, message="Login successful")


@router.get("/auth/me", response_model=UserProfile)
async def get_me(request: Request):
    """Get current user profile."""
    user = await require_user(request)
    return UserProfile(**{k: v for k, v in user.items() if k != "session_token"})


@router.post("/auth/logout", response_model=MessageResponse)
async def logout(request: Request):
    """Invalidate current session."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
        db = await get_db()
        await db.execute("UPDATE sessions SET is_active = 0 WHERE token = ?", [token])
        await db.commit()
    return MessageResponse(message="Logged out successfully")


# ── Legacy API Key Endpoints (backward compat) ──────────────────

async def get_api_key_from_header(x_api_key: Optional[str] = Header(None)):
    """Dependency to extract and validate API key from header."""
    if not x_api_key:
        return None
    db = await get_db()
    key_hash = _hash_key(x_api_key)
    cursor = await db.execute(
        "SELECT * FROM api_keys WHERE key_hash = ? AND is_active = 1",
        [key_hash]
    )
    row = await cursor.fetchone()
    if not row:
        return None
    return dict(row)


@router.post("/auth/register")
async def register(request: AuthRegisterRequest):
    """Register for an API key."""
    if not request.email:
        raise HTTPException(status_code=400, detail="Email is required")

    db = await get_db()

    cursor = await db.execute(
        "SELECT id FROM api_keys WHERE email = ? AND is_active = 1",
        [request.email]
    )
    existing = await cursor.fetchone()
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Email already registered. Contact support for key recovery."
        )

    api_key = _generate_api_key()
    key_hash = _hash_key(api_key)
    key_id = f"ak_{uuid.uuid4().hex[:12]}"

    await db.execute("""
        INSERT INTO api_keys (id, key_hash, name, email, tier, rate_limit)
        VALUES (?, ?, ?, ?, 'free', 100)
    """, (key_id, key_hash, request.name, request.email))
    await db.commit()

    return AuthRegisterResponse(
        api_key=api_key,
        message="API key created successfully. Store it securely — it won't be shown again."
    )


@router.get("/auth/usage")
async def get_usage(x_api_key: str = Header(..., description="Your API key")):
    """Get usage statistics for your API key."""
    db = await get_db()
    key_hash = _hash_key(x_api_key)

    cursor = await db.execute(
        "SELECT * FROM api_keys WHERE key_hash = ? AND is_active = 1",
        [key_hash]
    )
    key_row = await cursor.fetchone()
    if not key_row:
        raise HTTPException(status_code=401, detail="Invalid API key")

    key_id = key_row["id"]

    cursor = await db.execute(
        "SELECT COUNT(*) FROM api_usage WHERE api_key_id = ?", [key_id]
    )
    total = (await cursor.fetchone())[0]

    today = datetime.now().strftime("%Y-%m-%d")
    cursor = await db.execute(
        "SELECT COUNT(*) FROM api_usage WHERE api_key_id = ? AND timestamp >= ?",
        [key_id, today]
    )
    today_count = (await cursor.fetchone())[0]

    hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
    cursor = await db.execute(
        "SELECT COUNT(*) FROM api_usage WHERE api_key_id = ? AND timestamp >= ?",
        [key_id, hour_ago]
    )
    hour_count = (await cursor.fetchone())[0]

    return UsageResponse(
        api_key_id=key_id,
        name=key_row["name"],
        email=key_row["email"],
        tier=key_row["tier"],
        rate_limit=key_row["rate_limit"],
        total_requests=total,
        requests_today=today_count,
        requests_this_hour=hour_count,
        created_at=key_row["created_at"],
    )
