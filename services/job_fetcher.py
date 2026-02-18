"""
Real Job Aggregator — Fetches jobs from free public APIs.

Sources:
  1. Remotive  — remote tech jobs
  2. Jobicy    — remote jobs
  3. The Muse  — global jobs (484K+)
  4. Arbeitnow — EU/global jobs

Every apply_url is verified before insertion. Dead links are skipped.
"""

import asyncio
import hashlib
import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import aiohttp

logger = logging.getLogger("agentjobs.fetcher")

# ── Constants ────────────────────────────────────────────────────

USD_TO_INR = 83
EUR_TO_INR = 90
GBP_TO_INR = 105

CONCURRENCY_LIMIT = 15
API_TIMEOUT = aiohttp.ClientTimeout(total=15)
VERIFY_TIMEOUT = aiohttp.ClientTimeout(total=5)

CATEGORY_KEYWORDS = {
    "engineering": [
        "software", "engineer", "developer", "backend", "frontend", "fullstack",
        "full-stack", "full stack", "devops", "sre", "platform", "infrastructure",
        "mobile", "android", "ios", "web developer", "cloud", "qa", "quality",
        "embedded", "firmware", "security engineer", "architect", "programming",
        "golang", "java developer", "python developer", "ruby", "node.js", "react",
        "vue", "angular", "typescript", "javascript", "rust", "c++", "php",
    ],
    "data-science": [
        "data scientist", "data science", "machine learning", "ml engineer",
        "deep learning", "ai ", "artificial intelligence", "data analyst",
        "data engineer", "analytics engineer", "nlp", "computer vision",
        "bi developer", "business intelligence", "data warehouse", "mlops",
        "statistical", "quantitative", "data annotation",
    ],
    "product": [
        "product manager", "product owner", "product lead", "product director",
        "product management", "program manager", "technical program",
    ],
    "design": [
        "designer", "ux ", "ui ", "user experience", "user interface",
        "graphic design", "visual design", "interaction design", "design system",
        "brand design", "motion design", "creative director",
    ],
    "marketing": [
        "marketing", "seo", "sem", "content", "social media", "growth",
        "brand manager", "email marketing", "digital marketing", "copywriter",
        "communications",
    ],
    "sales": [
        "sales", "account executive", "account manager", "business development",
        "revenue", "customer acquisition",
    ],
    "hr": [
        "human resources", "hr ", "recruiter", "recruiting", "talent acquisition",
        "people operations", "compensation", "benefits", "l&d",
    ],
    "finance": [
        "finance", "financial", "accounting", "accountant", "auditor", "tax",
        "treasury", "fp&a", "controller", "cfo",
    ],
    "operations": [
        "operations", "supply chain", "logistics", "strategy & ops",
        "business operations", "procurement",
    ],
    "customer-support": [
        "customer support", "customer success", "customer service",
        "technical support", "help desk", "support engineer", "implementation",
        "customer experience",
    ],
    "legal": [
        "legal", "lawyer", "counsel", "compliance", "paralegal", "attorney",
        "data privacy", "regulatory",
    ],
}

KNOWN_SKILLS = [
    "python", "java", "javascript", "typescript", "go", "golang", "rust", "c++",
    "c#", "ruby", "php", "swift", "kotlin", "scala", "r", "dart", "flutter",
    "react", "vue", "angular", "nextjs", "next.js", "svelte", "nodejs", "node.js",
    "django", "flask", "fastapi", "spring", "spring-boot", "express", "rails",
    "ruby-on-rails", "laravel",
    "aws", "azure", "gcp", "google-cloud", "docker", "kubernetes", "terraform",
    "jenkins", "ci-cd", "github-actions", "linux", "nginx",
    "postgresql", "mysql", "mongodb", "redis", "elasticsearch", "dynamodb",
    "cassandra", "sqlite", "sql", "nosql", "graphql", "rest-api",
    "machine-learning", "deep-learning", "tensorflow", "pytorch", "nlp",
    "computer-vision", "pandas", "numpy", "scikit-learn", "spark", "hadoop",
    "airflow", "kafka", "rabbitmq",
    "figma", "sketch", "adobe-xd", "photoshop", "illustrator",
    "git", "agile", "scrum", "jira", "confluence",
    "salesforce", "hubspot", "sap", "power-bi", "tableau",
    "html", "css", "sass", "webpack", "vite",
    "microservices", "system-design", "data-structures", "algorithms",
    "communication", "leadership", "project-management", "product-management",
    "excel", "data-analysis", "statistics",
]


def _gen_id(prefix="j"):
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _dedup_key(title, company, location):
    raw = f"{title.lower().strip()}|{company.lower().strip()}|{(location or '').lower().strip()}"
    return hashlib.md5(raw.encode()).hexdigest()


def _classify_category(title, tags=None):
    text = (title + " " + " ".join(tags or [])).lower()
    scores = {}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            scores[cat] = score
    if scores:
        return max(scores, key=scores.get)
    return "engineering"


def _extract_skills(tags, description=""):
    found = set()
    text = " ".join(t if isinstance(t, str) else str(t) for t in tags).lower() + " " + (description or "").lower()
    text = text.replace("node.js", "nodejs").replace("next.js", "nextjs")
    text = text.replace("ruby on rails", "ruby-on-rails").replace("spring boot", "spring-boot")

    for skill in KNOWN_SKILLS:
        for tag in tags:
            tag_str = tag if isinstance(tag, str) else str(tag)
            if tag_str.lower().strip() == skill or tag_str.lower().strip().replace(" ", "-") == skill:
                found.add(skill)
                break
        if skill not in found:
            pattern = r'\b' + re.escape(skill).replace(r'\-', r'[\-\s]?') + r'\b'
            if re.search(pattern, text):
                found.add(skill)

    return sorted(found)[:10]


def _normalize_location(loc):
    if not loc:
        return "Remote"
    loc = loc.strip()
    low = loc.lower()
    if low in ("anywhere", "worldwide", "global", "earth", "world", "", "other"):
        return "Remote"
    if "remote" in low and len(low) < 15:
        return "Remote"
    return loc


def _parse_salary_to_monthly_inr(salary_str):
    if not salary_str:
        return None, None
    s = salary_str.replace(",", "").replace(" ", "").lower()
    nums = re.findall(r'[\d]+(?:\.[\d]+)?', s)
    if not nums:
        return None, None
    vals = [float(n) for n in nums]

    multiplier = 1
    if "$" in salary_str or "usd" in s:
        multiplier = USD_TO_INR
    elif "€" in salary_str or "eur" in s:
        multiplier = EUR_TO_INR
    elif "£" in salary_str or "gbp" in s:
        multiplier = GBP_TO_INR
    elif "₹" in salary_str or "inr" in s:
        multiplier = 1
    else:
        multiplier = USD_TO_INR

    is_yearly = "year" in s or "annual" in s or "pa" in s or "/yr" in s or "/y" in s
    is_monthly = "month" in s or "/mo" in s or "/m" in s
    is_hourly = "hour" in s or "/hr" in s or "/h" in s

    for i, v in enumerate(vals):
        vals[i] = v * multiplier
        if is_yearly:
            vals[i] = vals[i] / 12
        elif is_hourly:
            vals[i] = vals[i] * 160
        elif not is_monthly:
            if vals[i] > 500000:
                vals[i] = vals[i] / 12

    vals = [int(v) for v in vals]
    if len(vals) >= 2:
        return min(vals[0], vals[1]), max(vals[0], vals[1])
    if len(vals) == 1:
        return vals[0], int(vals[0] * 1.3)
    return None, None


def _get_experience_level_from_title(title):
    t = title.lower()
    if any(kw in t for kw in ["intern", "trainee", "entry"]):
        return 0, 1
    if any(kw in t for kw in ["junior", "associate", "jr "]):
        return 0, 2
    if any(kw in t for kw in ["senior", "sr ", "sr."]):
        return 5, 10
    if any(kw in t for kw in ["lead", "principal", "staff", "director", "vp", "head"]):
        return 8, 15
    return 2, 5


# ── API Fetchers ─────────────────────────────────────────────────

async def _fetch_remotive(session):
    jobs = []
    try:
        url = "https://remotive.com/api/remote-jobs?limit=100"
        async with session.get(url, timeout=API_TIMEOUT) as resp:
            if resp.status != 200:
                logger.warning(f"Remotive returned {resp.status}")
                return []
            data = await resp.json()

        for item in data.get("jobs", []):
            apply_url = item.get("url", "")
            if not apply_url:
                continue
            tags = item.get("tags", []) or []
            title = item.get("title", "")
            company = item.get("company_name", "Unknown")
            location = _normalize_location(item.get("candidate_required_location", ""))
            salary_str = item.get("salary", "")
            sal_min, sal_max = _parse_salary_to_monthly_inr(salary_str)
            category = _classify_category(title, tags + [item.get("category", "")])
            skills = _extract_skills(tags, item.get("description", ""))
            exp_min, exp_max = _get_experience_level_from_title(title)
            desc = item.get("description", "")
            short = re.sub(r'<[^>]+>', '', desc or "")[:200].strip()
            job_type = (item.get("job_type", "") or "").lower().replace("_", "-")
            if job_type not in ("full-time", "part-time", "contract", "internship"):
                job_type = "full-time"

            jobs.append({
                "title": title, "company_name": company, "location": location,
                "location_type": "remote", "salary_min": sal_min, "salary_max": sal_max,
                "salary_text": salary_str or None, "experience_min": exp_min,
                "experience_max": exp_max, "skills": skills, "category": category,
                "employment_type": job_type, "apply_url": apply_url, "source": "remotive",
                "source_id": str(item.get("id", "")), "posted_at": item.get("publication_date"),
                "description": short, "description_short": short,
            })
        logger.info(f"Remotive: fetched {len(jobs)} jobs")
    except Exception as e:
        logger.error(f"Remotive fetch error: {e}")
    return jobs


async def _fetch_jobicy(session):
    jobs = []
    try:
        url = "https://jobicy.com/api/v2/remote-jobs?count=50"
        async with session.get(url, timeout=API_TIMEOUT) as resp:
            if resp.status != 200:
                logger.warning(f"Jobicy returned {resp.status}")
                return []
            data = await resp.json()

        for item in data.get("jobs", []):
            apply_url = item.get("url", "")
            if not apply_url:
                continue
            title = item.get("jobTitle", "")
            company = item.get("companyName", "Unknown")
            location = _normalize_location(item.get("jobGeo", ""))
            industries = item.get("jobIndustry", []) or []
            tags = industries if isinstance(industries, list) else [str(industries)]
            job_types = item.get("jobType", []) or []
            emp_type_raw = job_types[0] if isinstance(job_types, list) and job_types else "full-time"
            emp_type = str(emp_type_raw).lower().replace(" ", "-")
            if emp_type not in ("full-time", "part-time", "contract", "internship"):
                emp_type = "full-time"

            salary_str = ""
            ann_min = item.get("annualSalaryMin")
            ann_max = item.get("annualSalaryMax")
            salary_currency = item.get("salaryCurrency", "USD")
            if ann_min and ann_max:
                salary_str = f"{salary_currency} {ann_min}-{ann_max}/year"
            elif ann_min:
                salary_str = f"{salary_currency} {ann_min}/year"
            sal_min, sal_max = _parse_salary_to_monthly_inr(salary_str)

            category = _classify_category(title, tags)
            desc_text = item.get("jobExcerpt") or item.get("jobDescription") or ""
            desc_text = re.sub(r'<[^>]+>', '', desc_text)[:200].strip()
            skills = _extract_skills(tags, desc_text)
            exp_min, exp_max = _get_experience_level_from_title(title)

            jobs.append({
                "title": title, "company_name": company, "location": location,
                "location_type": "remote", "salary_min": sal_min, "salary_max": sal_max,
                "salary_text": salary_str or None, "experience_min": exp_min,
                "experience_max": exp_max, "skills": skills, "category": category,
                "employment_type": emp_type, "apply_url": apply_url, "source": "jobicy",
                "source_id": str(item.get("id", "")), "posted_at": item.get("pubDate"),
                "description": desc_text, "description_short": desc_text,
            })
        logger.info(f"Jobicy: fetched {len(jobs)} jobs")
    except Exception as e:
        logger.error(f"Jobicy fetch error: {e}")
    return jobs


async def _fetch_themuse(session):
    jobs = []
    pages_to_fetch = list(range(1, 26))

    async def fetch_page(page):
        page_jobs = []
        try:
            url = f"https://www.themuse.com/api/public/jobs?page={page}&per_page=20"
            async with session.get(url, timeout=API_TIMEOUT) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
            for item in data.get("results", []):
                apply_url = (item.get("refs") or {}).get("landing_page", "")
                if not apply_url:
                    continue
                title = item.get("name", "")
                company_data = item.get("company") or {}
                company = company_data.get("name", "Unknown")
                locations_list = item.get("locations", [])
                loc_name = locations_list[0].get("name", "Remote") if locations_list else "Remote"
                location = _normalize_location(loc_name)
                categories = [c.get("name", "") for c in (item.get("categories") or [])]
                levels = [l.get("name", "") for l in (item.get("levels") or [])]
                tags = categories + levels
                category = _classify_category(title, tags)
                contents = item.get("contents", "")
                desc_text = re.sub(r'<[^>]+>', '', contents or "")[:200].strip()
                skills = _extract_skills(tags, contents or "")
                exp_min, exp_max = _get_experience_level_from_title(title)
                loc_type = "onsite"
                if "flexible" in loc_name.lower() or "remote" in loc_name.lower():
                    loc_type = "remote"
                elif location == "Remote":
                    loc_type = "remote"

                page_jobs.append({
                    "title": title, "company_name": company, "location": location,
                    "location_type": loc_type, "salary_min": None, "salary_max": None,
                    "salary_text": None, "experience_min": exp_min, "experience_max": exp_max,
                    "skills": skills, "category": category, "employment_type": "full-time",
                    "apply_url": apply_url, "source": "themuse",
                    "source_id": str(item.get("id", "")),
                    "posted_at": item.get("publication_date"),
                    "description": desc_text, "description_short": desc_text,
                })
        except Exception as e:
            logger.error(f"The Muse page {page} error: {e}")
        return page_jobs

    sem = asyncio.Semaphore(5)
    async def fetch_with_sem(page):
        async with sem:
            return await fetch_page(page)

    results = await asyncio.gather(*[fetch_with_sem(p) for p in pages_to_fetch])
    for page_jobs in results:
        jobs.extend(page_jobs)
    logger.info(f"The Muse: fetched {len(jobs)} jobs")
    return jobs


async def _fetch_arbeitnow(session):
    jobs = []
    try:
        url = "https://www.arbeitnow.com/api/job-board-api"
        async with session.get(url, timeout=API_TIMEOUT) as resp:
            if resp.status != 200:
                logger.warning(f"Arbeitnow returned {resp.status}")
                return []
            data = await resp.json()

        for item in data.get("data", []):
            apply_url = item.get("url", "")
            if not apply_url:
                continue
            title = item.get("title", "")
            company = item.get("company_name", "Unknown")
            location = _normalize_location(item.get("location", ""))
            tags = item.get("tags", []) or []
            is_remote = item.get("remote", False)
            loc_type = "remote" if is_remote else "onsite"
            if is_remote and location != "Remote":
                loc_type = "hybrid"
            job_types = item.get("job_types", []) or []
            emp_type = "full-time"
            for jt in job_types:
                jt_lower = (jt or "").lower().replace(" ", "-")
                if jt_lower in ("full-time", "part-time", "contract", "internship"):
                    emp_type = jt_lower
                    break
            category = _classify_category(title, tags)
            desc_text = re.sub(r'<[^>]+>', '', item.get("description", "") or "")[:200].strip()
            skills = _extract_skills(tags, item.get("description", ""))
            exp_min, exp_max = _get_experience_level_from_title(title)

            jobs.append({
                "title": title, "company_name": company, "location": location,
                "location_type": loc_type, "salary_min": None, "salary_max": None,
                "salary_text": None, "experience_min": exp_min, "experience_max": exp_max,
                "skills": skills, "category": category, "employment_type": emp_type,
                "apply_url": apply_url, "source": "arbeitnow",
                "source_id": item.get("slug", ""), "posted_at": item.get("created_at"),
                "description": desc_text, "description_short": desc_text,
            })
        logger.info(f"Arbeitnow: fetched {len(jobs)} jobs")
    except Exception as e:
        logger.error(f"Arbeitnow fetch error: {e}")
    return jobs


# ── URL Verification ─────────────────────────────────────────────

async def _verify_urls(session, jobs):
    """Verify apply_url for each job. Returns only jobs with working URLs."""
    verified = []
    sem = asyncio.Semaphore(CONCURRENCY_LIMIT)
    now_iso = datetime.now(timezone.utc).isoformat()

    async def check_one(job):
        url = job.get("apply_url", "")
        if not url:
            return None
        async with sem:
            try:
                async with session.head(url, timeout=VERIFY_TIMEOUT,
                                        allow_redirects=True, ssl=False) as resp:
                    if resp.status < 400:
                        job["verified_at"] = now_iso
                        return job
            except Exception:
                pass
            try:
                async with session.get(url, timeout=VERIFY_TIMEOUT,
                                       allow_redirects=True, ssl=False) as resp:
                    if resp.status < 400:
                        job["verified_at"] = now_iso
                        return job
            except Exception:
                pass
        return None

    results = await asyncio.gather(*[check_one(j) for j in jobs], return_exceptions=True)
    for r in results:
        if isinstance(r, dict):
            verified.append(r)

    logger.info(f"URL verification: {len(verified)}/{len(jobs)} passed")
    return verified


# ── Main Entry Point ─────────────────────────────────────────────

async def fetch_real_jobs():
    """
    Fetch from all APIs, verify URLs, deduplicate, insert into database.
    Returns number of jobs inserted.
    """
    if os.environ.get("SKIP_FETCH", "").strip() == "1":
        logger.info("SKIP_FETCH=1, skipping job fetch")
        return 0

    from database import get_db, rebuild_fts

    logger.info("Starting real job fetch from public APIs...")

    headers = {
        "User-Agent": "AgentJobs/1.0 (job aggregator; contact@agentjobs.dev)",
    }

    all_jobs = []

    async with aiohttp.ClientSession(headers=headers) as session:
        results = await asyncio.gather(
            _fetch_remotive(session),
            _fetch_jobicy(session),
            _fetch_themuse(session),
            _fetch_arbeitnow(session),
            return_exceptions=True,
        )

        source_counts = {}
        for r in results:
            if isinstance(r, list):
                for j in r:
                    src = j.get("source", "unknown")
                    source_counts[src] = source_counts.get(src, 0) + 1
                all_jobs.extend(r)
            elif isinstance(r, Exception):
                logger.error(f"Fetch exception: {r}")

        logger.info(f"Total raw jobs fetched: {len(all_jobs)}")
        for src, cnt in source_counts.items():
            logger.info(f"  {src}: {cnt}")

        if not all_jobs:
            logger.warning("No jobs fetched from any API. Will use fallback seed.")
            return 0

        # Deduplicate
        seen = {}
        unique_jobs = []
        for job in all_jobs:
            key = _dedup_key(job["title"], job["company_name"], job.get("location", ""))
            if key not in seen:
                seen[key] = True
                unique_jobs.append(job)

        logger.info(f"After dedup: {len(unique_jobs)} unique jobs")

        # Verify URLs
        logger.info("Verifying apply URLs...")
        verified_jobs = await _verify_urls(session, unique_jobs)

    if not verified_jobs:
        logger.warning("No jobs passed URL verification. Will use fallback seed.")
        return 0

    # Insert into database
    db = await get_db()

    # Build company map
    company_map = {}
    for job in verified_jobs:
        cname = job["company_name"]
        cname_lower = cname.lower().strip()
        if cname_lower not in company_map:
            cid = f"c_{hashlib.md5(cname_lower.encode()).hexdigest()[:12]}"
            company_map[cname_lower] = {"id": cid, "name": cname}

    # Insert companies
    for cdata in company_map.values():
        await db.execute("""
            INSERT OR IGNORE INTO companies (id, name, created_at)
            VALUES (?, ?, ?)
        """, (cdata["id"], cdata["name"], datetime.now(timezone.utc).isoformat()))

    logger.info(f"Inserted {len(company_map)} companies")

    # Insert jobs
    inserted = 0
    for job in verified_jobs:
        cname_lower = job["company_name"].lower().strip()
        company_id = company_map[cname_lower]["id"]
        job_id = _gen_id("j")
        skills_json = json.dumps(job.get("skills", []))
        verified_at = job.get("verified_at")

        try:
            await db.execute("""
                INSERT OR IGNORE INTO jobs
                (id, company_id, title, description, description_short, location,
                 location_type, salary_min, salary_max, salary_text,
                 experience_min, experience_max, skills, category,
                 employment_type, apply_url, source, source_id,
                 posted_at, is_active, verified_at, raw_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job_id, company_id, job["title"], job.get("description"),
                job.get("description_short"), job.get("location"),
                job.get("location_type"), job.get("salary_min"),
                job.get("salary_max"), job.get("salary_text"),
                job.get("experience_min"), job.get("experience_max"),
                skills_json, job.get("category"), job.get("employment_type"),
                job["apply_url"], job.get("source"), job.get("source_id"),
                job.get("posted_at"), True, verified_at,
                json.dumps({"source": job.get("source")}),
            ))
            inserted += 1
        except Exception as e:
            logger.error(f"Insert error for '{job['title']}': {e}")

    await db.commit()
    logger.info(f"Inserted {inserted} verified jobs into database")

    # Rebuild FTS index
    logger.info("Rebuilding FTS index...")
    await rebuild_fts()

    logger.info("Job fetch complete!")
    return inserted
