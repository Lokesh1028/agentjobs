"""Resume-job matching algorithm for AgentJobs."""

import json
import time
from datetime import datetime, timedelta
from typing import List, Optional
from database import get_db
from services.skills import normalize_skill, normalize_skills, extract_skills_from_text, skills_match_details


# Location groupings (city -> state)
LOCATION_STATES = {
    "hyderabad": "telangana",
    "bangalore": "karnataka",
    "bengaluru": "karnataka",
    "mumbai": "maharashtra",
    "pune": "maharashtra",
    "delhi": "delhi ncr",
    "delhi ncr": "delhi ncr",
    "new delhi": "delhi ncr",
    "gurgaon": "delhi ncr",
    "gurugram": "delhi ncr",
    "noida": "delhi ncr",
    "chennai": "tamil nadu",
    "kolkata": "west bengal",
    "ahmedabad": "gujarat",
    "remote": "remote",
}


def _get_state(location: str) -> Optional[str]:
    """Get state/region from a location string."""
    if not location:
        return None
    loc = location.lower().strip()
    for city, state in LOCATION_STATES.items():
        if city in loc:
            return state
    return None


def _score_skills(candidate_skills: List[str], job_skills: List[str]) -> tuple:
    """Score skills match (0-40 points). Returns (score, matched, missing)."""
    if not job_skills:
        return 20, [], []  # No skills required, give partial credit

    c_set = set(normalize_skill(s) for s in candidate_skills)
    j_set = set(normalize_skill(s) for s in job_skills)

    matched = c_set & j_set
    missing = j_set - c_set

    if not j_set:
        return 20, list(matched), list(missing)

    match_pct = len(matched) / len(j_set)
    score = int(match_pct * 40)

    return score, sorted(list(matched)), sorted(list(missing))


def _score_location(candidate_locations: List[str], job_location: Optional[str], job_location_type: Optional[str]) -> tuple:
    """Score location match (0-20 points). Returns (score, reason)."""
    if not job_location and not job_location_type:
        return 10, "Location: Not specified by employer"

    # Remote jobs match everyone
    if job_location_type and job_location_type.lower() == "remote":
        return 20, "Location: Remote position — available anywhere"

    if not candidate_locations:
        return 10, "Location: No preference specified"

    candidate_locs = [loc.lower().strip() for loc in candidate_locations]
    job_loc = (job_location or "").lower().strip()

    # Check exact city match
    for cloc in candidate_locs:
        if cloc in job_loc or job_loc in cloc:
            return 20, f"Location: Exact match — {job_location}"

    # Check same state/region
    job_state = _get_state(job_loc)
    for cloc in candidate_locs:
        candidate_state = _get_state(cloc)
        if candidate_state and job_state and candidate_state == job_state:
            return 15, f"Location: Same region — {job_location}"

    # Check if candidate wants remote
    if "remote" in candidate_locs:
        if job_location_type and job_location_type.lower() == "hybrid":
            return 12, f"Location: Hybrid role in {job_location}"

    return 5, f"Location: Different — {job_location}"


def _score_salary(candidate_min: Optional[int], job_min: Optional[int], job_max: Optional[int]) -> tuple:
    """Score salary match (0-15 points). Returns (score, reason)."""
    if candidate_min is None or (job_min is None and job_max is None):
        return 8, "Salary: Not enough data to compare"

    job_top = job_max or job_min or 0

    if job_top >= candidate_min:
        return 15, f"Salary: Meets minimum requirement (₹{job_top:,}/mo ≥ ₹{candidate_min:,}/mo)"

    if job_top >= candidate_min * 0.8:
        return 10, f"Salary: Close to minimum (₹{job_top:,}/mo vs ₹{candidate_min:,}/mo desired)"

    return 3, f"Salary: Below minimum (₹{job_top:,}/mo vs ₹{candidate_min:,}/mo desired)"


def _score_experience(candidate_years: Optional[int], job_min: Optional[int], job_max: Optional[int]) -> tuple:
    """Score experience match (0-15 points). Returns (score, reason)."""
    if candidate_years is None or (job_min is None and job_max is None):
        return 8, "Experience: Not enough data to compare"

    jmin = job_min or 0
    jmax = job_max or 99

    if jmin <= candidate_years <= jmax:
        return 15, f"Experience: {candidate_years} years matches {jmin}-{jmax} year requirement"

    # Close match (within 1 year)
    if candidate_years >= jmin - 1 and candidate_years <= jmax + 1:
        return 10, f"Experience: Close match — {candidate_years} years vs {jmin}-{jmax} required"

    if candidate_years > jmax:
        return 7, f"Experience: Overqualified — {candidate_years} years vs {jmin}-{jmax} required"

    return 3, f"Experience: Underqualified — {candidate_years} years vs {jmin}-{jmax} required"


def _score_recency(posted_at: Optional[str]) -> tuple:
    """Score job recency (0-10 points). Returns (score, reason)."""
    if not posted_at:
        return 5, "Recency: Unknown posting date"

    try:
        posted = datetime.fromisoformat(posted_at.replace("Z", "+00:00")) if isinstance(posted_at, str) else posted_at
        now = datetime.now(posted.tzinfo) if posted.tzinfo else datetime.now()
        days_ago = (now - posted).days
    except Exception:
        return 5, "Recency: Unknown posting date"

    if days_ago <= 1:
        return 10, "Recency: Posted today"
    elif days_ago <= 7:
        return 8, f"Recency: Posted {days_ago} days ago"
    elif days_ago <= 30:
        return 5, f"Recency: Posted {days_ago} days ago"
    else:
        return 2, f"Recency: Posted {days_ago} days ago"


async def match_jobs(
    skills: Optional[List[str]] = None,
    experience_years: Optional[int] = None,
    preferred_locations: Optional[List[str]] = None,
    salary_min: Optional[int] = None,
    resume_text: Optional[str] = None,
    job_preferences: Optional[str] = None,
    limit: int = 20,
) -> dict:
    """Match candidate profile against all active jobs. Returns session data."""
    start = time.time()

    # Extract skills from resume if provided
    candidate_skills = list(skills or [])
    if resume_text:
        extracted = extract_skills_from_text(resume_text)
        candidate_skills = list(set(normalize_skills(candidate_skills + extracted)))
    else:
        candidate_skills = normalize_skills(candidate_skills)

    db = await get_db()

    # Fetch all active jobs (for matching we need them all)
    cursor = await db.execute("""
        SELECT j.*, c.name as company_name, c.industry as company_industry,
               c.size as company_size
        FROM jobs j
        LEFT JOIN companies c ON j.company_id = c.id
        WHERE j.is_active = 1
    """)
    rows = await cursor.fetchall()

    scored_jobs = []
    for row in rows:
        job_skills_raw = row["skills"] if row["skills"] else "[]"
        try:
            job_skills = json.loads(job_skills_raw)
        except (json.JSONDecodeError, TypeError):
            job_skills = []

        # Score components
        skill_score, matched_skills, missing_skills = _score_skills(candidate_skills, job_skills)
        loc_score, loc_reason = _score_location(preferred_locations or [], row["location"], row["location_type"])
        sal_score, sal_reason = _score_salary(salary_min, row["salary_min"], row["salary_max"])
        exp_score, exp_reason = _score_experience(experience_years, row["experience_min"], row["experience_max"])
        rec_score, rec_reason = _score_recency(row["posted_at"])

        total_score = skill_score + loc_score + sal_score + exp_score + rec_score

        reasons = []
        if candidate_skills and job_skills:
            reasons.append(f"Skills match: {', '.join(matched_skills[:5])} ({len(matched_skills)}/{len(job_skills)} required skills)")
        reasons.append(loc_reason)
        reasons.append(exp_reason)
        reasons.append(sal_reason)
        reasons.append(rec_reason)

        # Build salary range string
        salary_range = None
        if row["salary_min"] and row["salary_max"]:
            salary_range = f"₹{row['salary_min']//1000}K-{row['salary_max']//1000}K/mo"
        elif row["salary_min"]:
            salary_range = f"₹{row['salary_min']//1000}K+/mo"

        scored_jobs.append({
            "id": row["id"],
            "title": row["title"],
            "company": row["company_name"] or "Unknown",
            "location": row["location"],
            "salary_range": salary_range,
            "match_score": total_score,
            "match_reasons": reasons,
            "description_short": row["description_short"],
            "apply_url": row["apply_url"],
            "skills_match": matched_skills,
            "skills_missing": missing_skills[:5],
        })

    # Sort by score descending
    scored_jobs.sort(key=lambda x: x["match_score"], reverse=True)
    top_jobs = scored_jobs[:limit]
    elapsed = (time.time() - start) * 1000

    return {
        "query_time_ms": round(elapsed, 2),
        "match_count": len([j for j in scored_jobs if j["match_score"] >= 30]),
        "jobs": top_jobs,
        "extracted_skills": candidate_skills,
    }
