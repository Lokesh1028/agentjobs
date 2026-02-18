"""Agent hire / matching API endpoints."""

import uuid
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException
from models import AgentSearchRequest, AgentSearchResponse
from services.matcher import match_jobs
from services.skills import extract_skills_from_text
from database import get_db

router = APIRouter(prefix="/api/v1", tags=["agent"])


@router.post("/agent/search")
async def agent_search(request: AgentSearchRequest):
    """
    AI-powered job matching. Accepts resume text or structured skills/preferences.
    Returns scored and ranked job matches in <3 seconds.
    """
    # Extract skills from resume text if provided
    skills = list(request.skills or [])
    if request.resume_text:
        extracted = extract_skills_from_text(request.resume_text)
        skills = list(set(skills + extracted))

    if not skills and not request.resume_text and not request.job_preferences:
        raise HTTPException(
            status_code=400,
            detail="Provide at least one of: resume_text, skills, or job_preferences"
        )

    # Run matching
    match_jobs_result = await match_jobs(
        skills=skills if skills else None,
        experience_years=request.experience_years,
        preferred_locations=request.preferred_locations,
        salary_min=request.salary_min,
        resume_text=request.resume_text,
        job_preferences=request.job_preferences,
        limit=request.limit,
    )

    # Create session record
    session_id = f"sess_{uuid.uuid4().hex[:12]}"
    db = await get_db()
    await db.execute("""
        INSERT INTO agent_sessions
        (id, resume_text, resume_skills, resume_experience_years,
         resume_preferred_locations, resume_preferred_salary_min,
         status, results, completed_at)
        VALUES (?, ?, ?, ?, ?, ?, 'completed', ?, ?)
    """, (
        session_id,
        request.resume_text,
        json.dumps(match_jobs_result.get("extracted_skills", skills)),
        request.experience_years,
        json.dumps(request.preferred_locations) if request.preferred_locations else None,
        request.salary_min,
        json.dumps(match_jobs_result["jobs"]),
        datetime.now().isoformat(),
    ))
    await db.commit()

    return {
        "session_id": session_id,
        "query_time_ms": match_jobs_result["query_time_ms"],
        "match_count": match_jobs_result["match_count"],
        "jobs": match_jobs_result["jobs"],
    }


@router.get("/agent/session/{session_id}")
async def get_session(session_id: str):
    """Get results of a previous agent search session."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM agent_sessions WHERE id = ?", [session_id]
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")

    results = json.loads(row["results"]) if row["results"] else []
    return {
        "session_id": row["id"],
        "status": row["status"],
        "match_count": len(results),
        "jobs": results,
        "resume_skills": json.loads(row["resume_skills"]) if row["resume_skills"] else [],
        "created_at": row["created_at"],
        "completed_at": row["completed_at"],
    }
