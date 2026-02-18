"""Search engine logic for AgentJobs."""

import json
import re
import time
from typing import Optional, List, Tuple
from database import get_db


async def search_jobs(
    q: Optional[str] = None,
    title: Optional[str] = None,
    location: Optional[str] = None,
    location_type: Optional[str] = None,
    company: Optional[str] = None,
    skills: Optional[List[str]] = None,
    salary_min: Optional[int] = None,
    salary_max: Optional[int] = None,
    experience_min: Optional[int] = None,
    experience_max: Optional[int] = None,
    category: Optional[str] = None,
    employment_type: Optional[str] = None,
    posted_after: Optional[str] = None,
    sort: str = "relevance",
    limit: int = 20,
    offset: int = 0,
) -> Tuple[List[dict], int, float]:
    """
    Search jobs with filters. Returns (jobs, total_count, query_time_ms).
    """
    start = time.time()
    db = await get_db()

    # If text search query, use FTS
    if q:
        return await _fts_search(
            db, q, title, location, location_type, company, skills,
            salary_min, salary_max, experience_min, experience_max,
            category, employment_type, posted_after, sort, limit, offset, start
        )

    # Otherwise use regular SQL filters
    return await _filter_search(
        db, title, location, location_type, company, skills,
        salary_min, salary_max, experience_min, experience_max,
        category, employment_type, posted_after, sort, limit, offset, start
    )


async def _fts_search(
    db, q, title, location, location_type, company, skills,
    salary_min, salary_max, experience_min, experience_max,
    category, employment_type, posted_after, sort, limit, offset, start
):
    """Full-text search using FTS5."""
    params = []
    where_clauses = ["j.is_active = 1"]

    # Clean FTS query — strip FTS5 special characters to prevent syntax errors
    fts_query = q.replace('"', '').replace("'", "").strip()
    fts_query = re.sub(r'[^\w\s\-]', ' ', fts_query).strip()
    if not fts_query:
        return await _filter_search(
            db, title, location, location_type, company, skills,
            salary_min, salary_max, experience_min, experience_max,
            category, employment_type, posted_after, sort, limit, offset, start
        )

    base_from = """
        FROM jobs j
        LEFT JOIN companies c ON j.company_id = c.id
        INNER JOIN jobs_fts fts ON fts.job_id = j.id
    """

    where_clauses.append("jobs_fts MATCH ?")
    params.append(fts_query)

    # Add additional filters
    _add_filters(where_clauses, params, title, location, location_type,
                 company, skills, salary_min, salary_max, experience_min,
                 experience_max, category, employment_type, posted_after)

    where_sql = " AND ".join(where_clauses)

    # Get total count
    count_sql = f"SELECT COUNT(*) as cnt {base_from} WHERE {where_sql}"
    cursor = await db.execute(count_sql, params)
    row = await cursor.fetchone()
    total = row[0] if row else 0

    # Sort
    order_by = _get_order_by(sort, has_fts=True)

    # Get results
    select_sql = f"""
        SELECT j.*, c.name as company_name, c.industry as company_industry,
               c.size as company_size, fts.rank as fts_rank
        {base_from}
        WHERE {where_sql}
        ORDER BY {order_by}
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])

    cursor = await db.execute(select_sql, params)
    rows = await cursor.fetchall()

    jobs = [_row_to_job(row) for row in rows]
    elapsed = (time.time() - start) * 1000

    return jobs, total, round(elapsed, 2)


async def _filter_search(
    db, title, location, location_type, company, skills,
    salary_min, salary_max, experience_min, experience_max,
    category, employment_type, posted_after, sort, limit, offset, start
):
    """Filter-based search without FTS."""
    params = []
    where_clauses = ["j.is_active = 1"]

    base_from = """
        FROM jobs j
        LEFT JOIN companies c ON j.company_id = c.id
    """

    _add_filters(where_clauses, params, title, location, location_type,
                 company, skills, salary_min, salary_max, experience_min,
                 experience_max, category, employment_type, posted_after)

    where_sql = " AND ".join(where_clauses)

    # Count
    count_sql = f"SELECT COUNT(*) as cnt {base_from} WHERE {where_sql}"
    cursor = await db.execute(count_sql, params)
    row = await cursor.fetchone()
    total = row[0] if row else 0

    order_by = _get_order_by(sort, has_fts=False)

    select_sql = f"""
        SELECT j.*, c.name as company_name, c.industry as company_industry,
               c.size as company_size
        {base_from}
        WHERE {where_sql}
        ORDER BY {order_by}
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])

    cursor = await db.execute(select_sql, params)
    rows = await cursor.fetchall()

    jobs = [_row_to_job(row) for row in rows]
    elapsed = (time.time() - start) * 1000

    return jobs, total, round(elapsed, 2)


def _add_filters(where_clauses, params, title, location, location_type,
                 company, skills, salary_min, salary_max, experience_min,
                 experience_max, category, employment_type, posted_after):
    """Add SQL WHERE filters."""
    if title:
        where_clauses.append("LOWER(j.title) LIKE ?")
        params.append(f"%{title.lower()}%")

    if location:
        where_clauses.append("LOWER(j.location) LIKE ?")
        params.append(f"%{location.lower()}%")

    if location_type:
        where_clauses.append("LOWER(j.location_type) = ?")
        params.append(location_type.lower())

    if company:
        where_clauses.append("LOWER(c.name) LIKE ?")
        params.append(f"%{company.lower()}%")

    if skills:
        for skill in skills:
            where_clauses.append("LOWER(j.skills) LIKE ?")
            params.append(f"%{skill.lower()}%")

    if salary_min is not None:
        where_clauses.append("(j.salary_max >= ? OR j.salary_max IS NULL)")
        params.append(salary_min)

    if salary_max is not None:
        where_clauses.append("(j.salary_min <= ? OR j.salary_min IS NULL)")
        params.append(salary_max)

    if experience_min is not None:
        where_clauses.append("(j.experience_max >= ? OR j.experience_max IS NULL)")
        params.append(experience_min)

    if experience_max is not None:
        where_clauses.append("(j.experience_min <= ? OR j.experience_min IS NULL)")
        params.append(experience_max)

    if category:
        where_clauses.append("LOWER(j.category) = ?")
        params.append(category.lower())

    if employment_type:
        where_clauses.append("LOWER(j.employment_type) = ?")
        params.append(employment_type.lower())

    if posted_after:
        where_clauses.append("j.posted_at >= ?")
        params.append(posted_after)


def _get_order_by(sort: str, has_fts: bool = False) -> str:
    """Get ORDER BY clause."""
    if sort == "relevance" and has_fts:
        return "fts.rank"
    elif sort == "posted_at":
        return "j.posted_at DESC"
    elif sort == "salary":
        return "j.salary_max DESC"
    else:
        return "j.posted_at DESC"


def _row_to_job(row) -> dict:
    """Convert a database row to a job dict."""
    skills_raw = row["skills"] if row["skills"] else "[]"
    try:
        skills_list = json.loads(skills_raw)
    except (json.JSONDecodeError, TypeError):
        skills_list = []

    salary_range = None
    if row["salary_min"] and row["salary_max"]:
        salary_range = f"\u20b9{row['salary_min']:,} - \u20b9{row['salary_max']:,}/month"
    elif row["salary_min"]:
        salary_range = f"\u20b9{row['salary_min']:,}+/month"
    elif row["salary_max"]:
        salary_range = f"Up to \u20b9{row['salary_max']:,}/month"

    experience = None
    if row["experience_min"] is not None and row["experience_max"] is not None:
        experience = f"{row['experience_min']}-{row['experience_max']} years"
    elif row["experience_min"] is not None:
        experience = f"{row['experience_min']}+ years"
    elif row["experience_max"] is not None:
        experience = f"0-{row['experience_max']} years"

    return {
        "id": row["id"],
        "title": row["title"],
        "company": {
            "name": row["company_name"] or "Unknown",
            "industry": row["company_industry"],
            "size": row["company_size"],
        },
        "location": row["location"],
        "location_type": row["location_type"],
        "salary_range": salary_range,
        "salary_min": row["salary_min"],
        "salary_max": row["salary_max"],
        "experience": experience,
        "experience_min": row["experience_min"],
        "experience_max": row["experience_max"],
        "skills": skills_list,
        "category": row["category"],
        "employment_type": row["employment_type"],
        "description": row["description"],
        "description_short": row["description_short"],
        "posted_at": row["posted_at"],
        "apply_url": row["apply_url"],
        "source": row["source"],
        "salary_text": row["salary_text"],
        "source_id": row["source_id"],
        "scraped_at": row["scraped_at"],
        "is_active": bool(row["is_active"]),
    }


async def get_job_by_id(job_id: str) -> Optional[dict]:
    """Get a single job by ID."""
    db = await get_db()
    cursor = await db.execute("""
        SELECT j.*, c.name as company_name, c.industry as company_industry,
               c.size as company_size
        FROM jobs j
        LEFT JOIN companies c ON j.company_id = c.id
        WHERE j.id = ?
    """, [job_id])
    row = await cursor.fetchone()
    if not row:
        return None
    return _row_to_job(row)
