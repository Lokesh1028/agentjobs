"""Authentication and API key management endpoints."""

import uuid
import hashlib
import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Header, Depends
from typing import Optional
from models import AuthRegisterRequest, AuthRegisterResponse, UsageResponse
from database import get_db

router = APIRouter(prefix="/api/v1", tags=["auth"])


def _hash_key(key: str) -> str:
    """Hash an API key for storage."""
    return hashlib.sha256(key.encode()).hexdigest()


def _generate_api_key() -> str:
    """Generate a new API key."""
    return f"aj_{secrets.token_hex(24)}"


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

    # Check if email already registered
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

    # Generate key
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

    # Total requests
    cursor = await db.execute(
        "SELECT COUNT(*) FROM api_usage WHERE api_key_id = ?",
        [key_id]
    )
    total = (await cursor.fetchone())[0]

    # Today's requests
    today = datetime.now().strftime("%Y-%m-%d")
    cursor = await db.execute(
        "SELECT COUNT(*) FROM api_usage WHERE api_key_id = ? AND timestamp >= ?",
        [key_id, today]
    )
    today_count = (await cursor.fetchone())[0]

    # This hour's requests
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
