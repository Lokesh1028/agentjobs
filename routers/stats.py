"""Stats and analytics endpoints."""

import json
from datetime import datetime
from fastapi import APIRouter
from database import get_db

router = APIRouter(prefix="/api/v1", tags=["stats"])


@router.get("/stats")
async def get_stats():
    """Get platform statistics."""
    db = await get_db()

    cursor = await db.execute("SELECT COUNT(*) FROM jobs WHERE is_active = 1")
    active_jobs = (await cursor.fetchone())[0]

    cursor = await db.execute("SELECT COUNT(*) FROM jobs")
    total_jobs = (await cursor.fetchone())[0]

    cursor = await db.execute("SELECT COUNT(*) FROM companies")
    total_companies = (await cursor.fetchone())[0]

    # Categories breakdown
    cursor = await db.execute("""
        SELECT category, COUNT(*) as count
        FROM jobs WHERE is_active = 1
        GROUP BY category
        ORDER BY count DESC
    """)
    categories = [{"category": row["category"] or "uncategorized", "count": row["count"]}
                  for row in await cursor.fetchall()]

    # Location breakdown
    cursor = await db.execute("""
        SELECT location, COUNT(*) as count
        FROM jobs WHERE is_active = 1
        GROUP BY location
        ORDER BY count DESC
        LIMIT 20
    """)
    locations = [{"location": row["location"] or "Unknown", "count": row["count"]}
                 for row in await cursor.fetchall()]

    return {
        "total_jobs": total_jobs,
        "total_companies": total_companies,
        "total_active_jobs": active_jobs,
        "categories": categories,
        "locations": locations,
        "updated_at": datetime.now().isoformat(),
    }


@router.get("/categories")
async def get_categories():
    """List all job categories with counts."""
    db = await get_db()
    cursor = await db.execute("""
        SELECT category, COUNT(*) as count
        FROM jobs WHERE is_active = 1
        GROUP BY category
        ORDER BY count DESC
    """)
    rows = await cursor.fetchall()
    return {
        "categories": [
            {"category": row["category"] or "uncategorized", "count": row["count"]}
            for row in rows
        ]
    }


@router.get("/skills/trending")
async def get_trending_skills():
    """Get top skills in demand based on active job listings."""
    db = await get_db()
    cursor = await db.execute("SELECT skills FROM jobs WHERE is_active = 1 AND skills IS NOT NULL")
    rows = await cursor.fetchall()

    skill_counts = {}
    total_jobs = 0
    for row in rows:
        try:
            skills = json.loads(row["skills"])
            total_jobs += 1
            for skill in skills:
                skill_lower = skill.lower().strip()
                if skill_lower:
                    skill_counts[skill_lower] = skill_counts.get(skill_lower, 0) + 1
        except (json.JSONDecodeError, TypeError):
            continue

    # Sort by count
    sorted_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:30]

    return {
        "skills": [
            {
                "skill": skill,
                "count": count,
                "percentage": round(count / total_jobs * 100, 1) if total_jobs else 0,
            }
            for skill, count in sorted_skills
        ],
        "total_jobs_analyzed": total_jobs,
    }
