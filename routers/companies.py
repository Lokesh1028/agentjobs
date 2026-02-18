"""Company API endpoints."""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from database import get_db

router = APIRouter(prefix="/api/v1", tags=["companies"])


@router.get("/companies")
async def list_companies(
    industry: Optional[str] = Query(None, description="Industry filter"),
    size: Optional[str] = Query(None, description="Company size filter"),
    location: Optional[str] = Query(None, description="Location filter"),
    q: Optional[str] = Query(None, description="Search by name"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List companies with optional filters."""
    db = await get_db()
    params = []
    where = []

    if industry:
        where.append("LOWER(c.industry) = ?")
        params.append(industry.lower())
    if size:
        where.append("LOWER(c.size) = ?")
        params.append(size.lower())
    if location:
        where.append("LOWER(c.location) LIKE ?")
        params.append(f"%{location.lower()}%")
    if q:
        where.append("LOWER(c.name) LIKE ?")
        params.append(f"%{q.lower()}%")

    where_sql = " AND ".join(where) if where else "1=1"

    # Count
    cursor = await db.execute(f"SELECT COUNT(*) FROM companies c WHERE {where_sql}", params)
    total = (await cursor.fetchone())[0]

    # Results with job count
    cursor = await db.execute(f"""
        SELECT c.*, COUNT(j.id) as active_job_count
        FROM companies c
        LEFT JOIN jobs j ON j.company_id = c.id AND j.is_active = 1
        WHERE {where_sql}
        GROUP BY c.id
        ORDER BY active_job_count DESC
        LIMIT ? OFFSET ?
    """, params + [limit, offset])
    rows = await cursor.fetchall()

    companies = []
    for row in rows:
        companies.append({
            "id": row["id"],
            "name": row["name"],
            "website": row["website"],
            "careers_url": row["careers_url"],
            "industry": row["industry"],
            "size": row["size"],
            "location": row["location"],
            "description": row["description"],
            "active_job_count": row["active_job_count"],
        })

    return {
        "count": len(companies),
        "total": total,
        "companies": companies,
    }


@router.get("/companies/{company_id}")
async def get_company(company_id: str):
    """Get company details with active job count."""
    db = await get_db()
    cursor = await db.execute("""
        SELECT c.*, COUNT(j.id) as active_job_count
        FROM companies c
        LEFT JOIN jobs j ON j.company_id = c.id AND j.is_active = 1
        WHERE c.id = ?
        GROUP BY c.id
    """, [company_id])
    row = await cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Company not found")

    return {
        "id": row["id"],
        "name": row["name"],
        "website": row["website"],
        "careers_url": row["careers_url"],
        "industry": row["industry"],
        "size": row["size"],
        "location": row["location"],
        "description": row["description"],
        "active_job_count": row["active_job_count"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
