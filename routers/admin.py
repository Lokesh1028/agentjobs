"""Admin analytics and dashboard endpoints."""

import json
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Request, Query
from typing import Optional
from routers.auth import require_admin, log_activity
from database import get_db

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get("/dashboard")
async def dashboard(request: Request):
    """Overview dashboard stats. Requires admin role."""
    await require_admin(request)
    db = await get_db()
    now = datetime.utcnow()
    today = now.strftime("%Y-%m-%d")
    week_ago = (now - timedelta(days=7)).isoformat()
    month_ago = (now - timedelta(days=30)).isoformat()

    # Total users
    cursor = await db.execute("SELECT COUNT(*) FROM users")
    total_users = (await cursor.fetchone())[0]

    # New users today
    cursor = await db.execute("SELECT COUNT(*) FROM users WHERE created_at >= ?", [today])
    new_today = (await cursor.fetchone())[0]

    # New users this week
    cursor = await db.execute("SELECT COUNT(*) FROM users WHERE created_at >= ?", [week_ago])
    new_week = (await cursor.fetchone())[0]

    # New users this month
    cursor = await db.execute("SELECT COUNT(*) FROM users WHERE created_at >= ?", [month_ago])
    new_month = (await cursor.fetchone())[0]

    # Total searches
    cursor = await db.execute("SELECT COUNT(*) FROM user_activity WHERE action = 'search'")
    total_searches = (await cursor.fetchone())[0]

    # Total agent matches
    cursor = await db.execute("SELECT COUNT(*) FROM user_activity WHERE action = 'agent_search'")
    total_agent = (await cursor.fetchone())[0]

    # Active users last 7 days
    cursor = await db.execute(
        "SELECT COUNT(DISTINCT user_id) FROM user_activity WHERE timestamp >= ? AND user_id IS NOT NULL",
        [week_ago]
    )
    active_7d = (await cursor.fetchone())[0]

    # Top searches (from details JSON)
    cursor = await db.execute(
        """SELECT details, COUNT(*) as cnt FROM user_activity
           WHERE action IN ('search', 'agent_search') AND details IS NOT NULL
           GROUP BY details ORDER BY cnt DESC LIMIT 10"""
    )
    rows = await cursor.fetchall()
    top_searches = []
    for row in rows:
        try:
            d = json.loads(row["details"])
            query = d.get("q") or d.get("skills") or str(d)
            if isinstance(query, list):
                query = ", ".join(query)
            top_searches.append({"query": query, "count": row["cnt"]})
        except Exception:
            pass

    # Popular skills from agent sessions
    cursor = await db.execute(
        """SELECT resume_skills FROM agent_sessions
           WHERE resume_skills IS NOT NULL
           ORDER BY created_at DESC LIMIT 200"""
    )
    rows = await cursor.fetchall()
    skill_counts = {}
    for row in rows:
        try:
            skills = json.loads(row["resume_skills"])
            for s in skills:
                s = s.lower().strip()
                skill_counts[s] = skill_counts.get(s, 0) + 1
        except Exception:
            pass
    popular_skills = sorted(
        [{"skill": k, "count": v} for k, v in skill_counts.items()],
        key=lambda x: x["count"], reverse=True
    )[:15]

    # User growth (daily signups last 30 days)
    cursor = await db.execute(
        """SELECT DATE(created_at) as day, COUNT(*) as cnt
           FROM users WHERE created_at >= ?
           GROUP BY DATE(created_at) ORDER BY day""",
        [month_ago]
    )
    rows = await cursor.fetchall()
    user_growth = [{"date": row["day"], "count": row["cnt"]} for row in rows]

    return {
        "total_users": total_users,
        "new_users_today": new_today,
        "new_users_week": new_week,
        "new_users_month": new_month,
        "total_searches": total_searches,
        "total_agent_matches": total_agent,
        "active_users_7d": active_7d,
        "top_searches": top_searches,
        "popular_skills": popular_skills,
        "user_growth": user_growth,
    }


@router.get("/users")
async def list_users(
    request: Request,
    q: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List all users with pagination, search, filters."""
    await require_admin(request)
    db = await get_db()

    where_clauses = []
    params = []

    if q:
        where_clauses.append("(u.email LIKE ? OR u.name LIKE ? OR u.company LIKE ?)")
        params.extend([f"%{q}%", f"%{q}%", f"%{q}%"])
    if role:
        where_clauses.append("u.role = ?")
        params.append(role)

    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

    # Count
    cursor = await db.execute(f"SELECT COUNT(*) FROM users u WHERE {where_sql}", params)
    total = (await cursor.fetchone())[0]

    # Fetch with search counts
    cursor = await db.execute(f"""
        SELECT u.*,
            (SELECT COUNT(*) FROM user_activity WHERE user_id = u.id AND action IN ('search', 'agent_search')) as total_searches
        FROM users u
        WHERE {where_sql}
        ORDER BY u.created_at DESC
        LIMIT ? OFFSET ?
    """, params + [limit, offset])
    rows = await cursor.fetchall()

    users = []
    for row in rows:
        users.append({
            "id": row["id"],
            "email": row["email"],
            "name": row["name"],
            "company": row["company"],
            "role": row["role"],
            "is_active": bool(row["is_active"]),
            "last_login": row["last_login"],
            "login_count": row["login_count"] or 0,
            "total_searches": row["total_searches"],
            "created_at": row["created_at"],
        })

    return {"count": len(users), "total": total, "users": users}


@router.get("/users/{user_id}")
async def get_user_detail(user_id: str, request: Request):
    """Get user detail with full activity log."""
    await require_admin(request)
    db = await get_db()

    cursor = await db.execute("SELECT * FROM users WHERE id = ?", [user_id])
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    user = {
        "id": row["id"],
        "email": row["email"],
        "name": row["name"],
        "company": row["company"],
        "role": row["role"],
        "avatar_url": row["avatar_url"],
        "is_active": bool(row["is_active"]),
        "last_login": row["last_login"],
        "login_count": row["login_count"] or 0,
        "created_at": row["created_at"],
    }

    # Recent activity
    cursor = await db.execute(
        """SELECT * FROM user_activity WHERE user_id = ?
           ORDER BY timestamp DESC LIMIT 100""",
        [user_id]
    )
    rows = await cursor.fetchall()
    activities = [{
        "id": r["id"],
        "action": r["action"],
        "details": r["details"],
        "ip_address": r["ip_address"],
        "timestamp": r["timestamp"],
    } for r in rows]

    return {"user": user, "activities": activities}


@router.get("/activity")
async def activity_feed(
    request: Request,
    action: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    since: Optional[str] = Query(None),
    until: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Activity feed — latest actions across all users."""
    await require_admin(request)
    db = await get_db()

    where_clauses = []
    params = []

    if action:
        where_clauses.append("a.action = ?")
        params.append(action)
    if user_id:
        where_clauses.append("a.user_id = ?")
        params.append(user_id)
    if since:
        where_clauses.append("a.timestamp >= ?")
        params.append(since)
    if until:
        where_clauses.append("a.timestamp <= ?")
        params.append(until)

    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

    cursor = await db.execute(f"SELECT COUNT(*) FROM user_activity a WHERE {where_sql}", params)
    total = (await cursor.fetchone())[0]

    cursor = await db.execute(f"""
        SELECT a.*, u.email as user_email, u.name as user_name
        FROM user_activity a
        LEFT JOIN users u ON a.user_id = u.id
        WHERE {where_sql}
        ORDER BY a.timestamp DESC
        LIMIT ? OFFSET ?
    """, params + [limit, offset])
    rows = await cursor.fetchall()

    activities = [{
        "id": r["id"],
        "user_id": r["user_id"],
        "user_email": r["user_email"],
        "user_name": r["user_name"],
        "action": r["action"],
        "details": r["details"],
        "ip_address": r["ip_address"],
        "timestamp": r["timestamp"],
    } for r in rows]

    return {"count": len(activities), "total": total, "activities": activities}


@router.get("/metrics")
async def metrics(request: Request):
    """Investor-friendly metrics: DAU, WAU, MAU, retention, growth."""
    await require_admin(request)
    db = await get_db()
    now = datetime.utcnow()
    today = now.strftime("%Y-%m-%d")
    week_ago = (now - timedelta(days=7)).isoformat()
    month_ago = (now - timedelta(days=30)).isoformat()
    prev_month = (now - timedelta(days=60)).isoformat()

    # DAU
    cursor = await db.execute(
        "SELECT COUNT(DISTINCT user_id) FROM user_activity WHERE timestamp >= ? AND user_id IS NOT NULL",
        [today]
    )
    dau = (await cursor.fetchone())[0]

    # WAU
    cursor = await db.execute(
        "SELECT COUNT(DISTINCT user_id) FROM user_activity WHERE timestamp >= ? AND user_id IS NOT NULL",
        [week_ago]
    )
    wau = (await cursor.fetchone())[0]

    # MAU
    cursor = await db.execute(
        "SELECT COUNT(DISTINCT user_id) FROM user_activity WHERE timestamp >= ? AND user_id IS NOT NULL",
        [month_ago]
    )
    mau = (await cursor.fetchone())[0]

    # Retention (users who signed up last month AND were active this month)
    cursor = await db.execute(
        """SELECT COUNT(DISTINCT u.id) FROM users u
           WHERE u.created_at >= ? AND u.created_at < ?""",
        [prev_month, month_ago]
    )
    prev_signups = (await cursor.fetchone())[0]

    cursor = await db.execute(
        """SELECT COUNT(DISTINCT a.user_id) FROM user_activity a
           JOIN users u ON a.user_id = u.id
           WHERE u.created_at >= ? AND u.created_at < ?
           AND a.timestamp >= ?""",
        [prev_month, month_ago, month_ago]
    )
    retained = (await cursor.fetchone())[0]
    retention_rate = (retained / prev_signups * 100) if prev_signups > 0 else 0.0

    # Searches per user (this month)
    cursor = await db.execute(
        """SELECT COUNT(*) FROM user_activity
           WHERE action IN ('search', 'agent_search') AND timestamp >= ?""",
        [month_ago]
    )
    total_searches = (await cursor.fetchone())[0]
    searches_per_user = (total_searches / mau) if mau > 0 else 0.0

    # Most active hours
    cursor = await db.execute(
        """SELECT CAST(strftime('%H', timestamp) AS INTEGER) as hour, COUNT(*) as cnt
           FROM user_activity WHERE timestamp >= ?
           GROUP BY hour ORDER BY cnt DESC""",
        [month_ago]
    )
    rows = await cursor.fetchall()
    most_active_hours = [{"hour": r["hour"], "count": r["cnt"]} for r in rows]

    # Growth rate (this month vs previous month signups)
    cursor = await db.execute(
        "SELECT COUNT(*) FROM users WHERE created_at >= ?", [month_ago]
    )
    this_month_signups = (await cursor.fetchone())[0]
    growth_rate = ((this_month_signups - prev_signups) / prev_signups * 100) if prev_signups > 0 else 0.0

    return {
        "dau": dau,
        "wau": wau,
        "mau": mau,
        "retention_rate": round(retention_rate, 1),
        "searches_per_user": round(searches_per_user, 1),
        "most_active_hours": most_active_hours,
        "growth_rate": round(growth_rate, 1),
    }
