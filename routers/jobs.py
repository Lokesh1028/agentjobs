"""Job search API endpoints."""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from services.search import search_jobs, get_job_by_id
from config import settings

router = APIRouter(prefix="/api/v1", tags=["jobs"])


@router.get("/jobs")
async def list_jobs(
    q: Optional[str] = Query(None, description="Full-text search query"),
    title: Optional[str] = Query(None, description="Title filter"),
    location: Optional[str] = Query(None, description="Location filter"),
    location_type: Optional[str] = Query(None, description="onsite/remote/hybrid"),
    company: Optional[str] = Query(None, description="Company name filter"),
    skills: Optional[str] = Query(None, description="Comma-separated skills"),
    salary_min: Optional[int] = Query(None, description="Minimum salary (monthly INR)"),
    salary_max: Optional[int] = Query(None, description="Maximum salary (monthly INR)"),
    experience_min: Optional[int] = Query(None, description="Minimum experience (years)"),
    experience_max: Optional[int] = Query(None, description="Maximum experience (years)"),
    category: Optional[str] = Query(None, description="Job category"),
    employment_type: Optional[str] = Query(None, description="full-time/part-time/contract/internship"),
    posted_after: Optional[str] = Query(None, description="ISO date filter"),
    sort: str = Query("relevance", description="Sort by: relevance, posted_at, salary"),
    limit: int = Query(20, ge=1, le=100, description="Results per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
):
    """Search and filter jobs. Optimized for AI agent consumption."""
    skills_list = [s.strip() for s in skills.split(",")] if skills else None

    jobs, total, query_time = await search_jobs(
        q=q, title=title, location=location, location_type=location_type,
        company=company, skills=skills_list, salary_min=salary_min,
        salary_max=salary_max, experience_min=experience_min,
        experience_max=experience_max, category=category,
        employment_type=employment_type, posted_after=posted_after,
        sort=sort, limit=limit, offset=offset,
    )

    # Strip full description from list view
    for job in jobs:
        job.pop("description", None)
        job.pop("experience_min", None)
        job.pop("experience_max", None)
        job.pop("salary_text", None)
        job.pop("source_id", None)
        job.pop("scraped_at", None)
        job.pop("is_active", None)

    return {
        "count": len(jobs),
        "total": total,
        "query_time_ms": query_time,
        "jobs": jobs,
    }


@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    """Get full job details by ID."""
    job = await get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
