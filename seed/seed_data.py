"""
EMERGENCY FALLBACK SEED DATA for AgentJobs.

This file is ONLY used when ALL public API fetches fail (Remotive, Jobicy,
The Muse, Arbeitnow). It provides ~50 minimal jobs so the platform isn't
completely empty. These jobs have apply_url = None since we can't verify
fake links.

In normal operation this file is never called — real jobs come from
services/job_fetcher.py.
"""

import json
import os
import sys
import uuid
import asyncio
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db, init_db, rebuild_fts


FALLBACK_COMPANIES = [
    {"id": "c_fallback_01", "name": "Example Tech Co", "industry": "Technology", "size": "large"},
    {"id": "c_fallback_02", "name": "DataWorks Inc", "industry": "Data & Analytics", "size": "medium"},
    {"id": "c_fallback_03", "name": "CloudFirst Systems", "industry": "Cloud Computing", "size": "large"},
    {"id": "c_fallback_04", "name": "DesignHub Studio", "industry": "Design", "size": "startup"},
    {"id": "c_fallback_05", "name": "GrowthPath Marketing", "industry": "Marketing", "size": "medium"},
    {"id": "c_fallback_06", "name": "FinEdge Solutions", "industry": "Fintech", "size": "medium"},
    {"id": "c_fallback_07", "name": "PeopleFirst HR", "industry": "HR Tech", "size": "startup"},
    {"id": "c_fallback_08", "name": "SupportHero", "industry": "Customer Service", "size": "medium"},
]

FALLBACK_JOBS = [
    # Engineering (15)
    {"title": "Software Engineer", "company_idx": 0, "category": "engineering", "skills": ["python", "django", "postgresql"], "location": "Remote", "sal": (55000, 120000)},
    {"title": "Senior Software Engineer", "company_idx": 0, "category": "engineering", "skills": ["java", "spring-boot", "kubernetes"], "location": "Remote", "sal": (120000, 250000)},
    {"title": "Frontend Developer", "company_idx": 0, "category": "engineering", "skills": ["react", "typescript", "css"], "location": "Remote", "sal": (50000, 100000)},
    {"title": "Backend Engineer", "company_idx": 2, "category": "engineering", "skills": ["go", "docker", "aws"], "location": "Remote", "sal": (80000, 160000)},
    {"title": "Full Stack Developer", "company_idx": 2, "category": "engineering", "skills": ["javascript", "nodejs", "mongodb"], "location": "Remote", "sal": (60000, 130000)},
    {"title": "DevOps Engineer", "company_idx": 2, "category": "engineering", "skills": ["docker", "kubernetes", "terraform", "aws"], "location": "Remote", "sal": (90000, 180000)},
    {"title": "Mobile Developer (Android)", "company_idx": 0, "category": "engineering", "skills": ["kotlin", "android", "firebase"], "location": "Remote", "sal": (60000, 130000)},
    {"title": "Mobile Developer (iOS)", "company_idx": 0, "category": "engineering", "skills": ["swift", "ios", "firebase"], "location": "Remote", "sal": (60000, 130000)},
    {"title": "QA Engineer", "company_idx": 2, "category": "engineering", "skills": ["python", "selenium", "ci-cd"], "location": "Remote", "sal": (45000, 90000)},
    {"title": "Site Reliability Engineer", "company_idx": 2, "category": "engineering", "skills": ["linux", "kubernetes", "python", "aws"], "location": "Remote", "sal": (100000, 200000)},
    {"title": "Platform Engineer", "company_idx": 2, "category": "engineering", "skills": ["aws", "terraform", "docker"], "location": "Remote", "sal": (90000, 180000)},
    {"title": "Security Engineer", "company_idx": 0, "category": "engineering", "skills": ["python", "linux", "aws"], "location": "Remote", "sal": (100000, 200000)},
    {"title": "Node.js Developer", "company_idx": 0, "category": "engineering", "skills": ["nodejs", "typescript", "postgresql"], "location": "Remote", "sal": (55000, 110000)},
    {"title": "Python Developer", "company_idx": 2, "category": "engineering", "skills": ["python", "fastapi", "docker"], "location": "Remote", "sal": (55000, 110000)},
    {"title": "React Developer", "company_idx": 0, "category": "engineering", "skills": ["react", "javascript", "html", "css"], "location": "Remote", "sal": (50000, 100000)},
    # Data Science (8)
    {"title": "Data Scientist", "company_idx": 1, "category": "data-science", "skills": ["python", "machine-learning", "sql"], "location": "Remote", "sal": (80000, 160000)},
    {"title": "ML Engineer", "company_idx": 1, "category": "data-science", "skills": ["python", "pytorch", "docker"], "location": "Remote", "sal": (100000, 200000)},
    {"title": "Data Analyst", "company_idx": 1, "category": "data-science", "skills": ["sql", "python", "tableau"], "location": "Remote", "sal": (45000, 90000)},
    {"title": "Data Engineer", "company_idx": 1, "category": "data-science", "skills": ["python", "spark", "sql", "aws"], "location": "Remote", "sal": (80000, 160000)},
    {"title": "NLP Engineer", "company_idx": 1, "category": "data-science", "skills": ["python", "nlp", "pytorch"], "location": "Remote", "sal": (100000, 200000)},
    {"title": "Analytics Engineer", "company_idx": 1, "category": "data-science", "skills": ["sql", "python", "data-analysis"], "location": "Remote", "sal": (70000, 140000)},
    {"title": "Deep Learning Engineer", "company_idx": 1, "category": "data-science", "skills": ["python", "tensorflow", "deep-learning"], "location": "Remote", "sal": (110000, 220000)},
    {"title": "BI Developer", "company_idx": 1, "category": "data-science", "skills": ["sql", "power-bi", "excel"], "location": "Remote", "sal": (50000, 100000)},
    # Design (5)
    {"title": "Product Designer", "company_idx": 3, "category": "design", "skills": ["figma", "ui-design", "ux-design"], "location": "Remote", "sal": (60000, 120000)},
    {"title": "UX Designer", "company_idx": 3, "category": "design", "skills": ["figma", "user-research", "prototyping"], "location": "Remote", "sal": (50000, 100000)},
    {"title": "UI Designer", "company_idx": 3, "category": "design", "skills": ["figma", "photoshop", "illustrator"], "location": "Remote", "sal": (40000, 80000)},
    {"title": "Visual Designer", "company_idx": 3, "category": "design", "skills": ["figma", "photoshop", "illustrator"], "location": "Remote", "sal": (40000, 80000)},
    {"title": "Design System Lead", "company_idx": 3, "category": "design", "skills": ["figma", "design-systems", "css"], "location": "Remote", "sal": (100000, 200000)},
    # Product (4)
    {"title": "Product Manager", "company_idx": 0, "category": "product", "skills": ["product-management", "agile", "sql"], "location": "Remote", "sal": (80000, 160000)},
    {"title": "Senior Product Manager", "company_idx": 2, "category": "product", "skills": ["product-management", "data-analysis", "agile"], "location": "Remote", "sal": (150000, 300000)},
    {"title": "Technical Product Manager", "company_idx": 0, "category": "product", "skills": ["product-management", "sql", "python"], "location": "Remote", "sal": (100000, 200000)},
    {"title": "Product Owner", "company_idx": 2, "category": "product", "skills": ["agile", "scrum", "jira"], "location": "Remote", "sal": (70000, 140000)},
    # Marketing (4)
    {"title": "Digital Marketing Manager", "company_idx": 4, "category": "marketing", "skills": ["digital-marketing", "seo", "google-analytics"], "location": "Remote", "sal": (50000, 100000)},
    {"title": "Content Marketing Manager", "company_idx": 4, "category": "marketing", "skills": ["content-marketing", "seo", "copywriting"], "location": "Remote", "sal": (45000, 90000)},
    {"title": "Growth Marketing Manager", "company_idx": 4, "category": "marketing", "skills": ["digital-marketing", "analytics", "a/b-testing"], "location": "Remote", "sal": (60000, 120000)},
    {"title": "SEO Specialist", "company_idx": 4, "category": "marketing", "skills": ["seo", "google-analytics", "html"], "location": "Remote", "sal": (35000, 70000)},
    # Sales (3)
    {"title": "Sales Executive", "company_idx": 5, "category": "sales", "skills": ["salesforce-crm", "communication", "negotiation"], "location": "Remote", "sal": (40000, 80000)},
    {"title": "Business Development Manager", "company_idx": 5, "category": "sales", "skills": ["business-development", "communication", "excel"], "location": "Remote", "sal": (60000, 120000)},
    {"title": "Account Manager", "company_idx": 5, "category": "sales", "skills": ["crm", "communication", "presentation"], "location": "Remote", "sal": (50000, 100000)},
    # Finance (3)
    {"title": "Financial Analyst", "company_idx": 5, "category": "finance", "skills": ["excel", "sql", "financial-modeling"], "location": "Remote", "sal": (50000, 100000)},
    {"title": "Finance Manager", "company_idx": 5, "category": "finance", "skills": ["excel", "financial-analysis", "accounting"], "location": "Remote", "sal": (80000, 160000)},
    {"title": "Risk Analyst", "company_idx": 5, "category": "finance", "skills": ["excel", "python", "risk-management"], "location": "Remote", "sal": (60000, 120000)},
    # HR (3)
    {"title": "HR Business Partner", "company_idx": 6, "category": "hr", "skills": ["hr", "communication", "people-management"], "location": "Remote", "sal": (50000, 100000)},
    {"title": "Technical Recruiter", "company_idx": 6, "category": "hr", "skills": ["recruitment", "sourcing", "communication"], "location": "Remote", "sal": (40000, 80000)},
    {"title": "People Operations Manager", "company_idx": 6, "category": "hr", "skills": ["hr", "analytics", "communication"], "location": "Remote", "sal": (60000, 120000)},
    # Operations (2)
    {"title": "Operations Manager", "company_idx": 0, "category": "operations", "skills": ["excel", "sql", "project-management"], "location": "Remote", "sal": (60000, 120000)},
    {"title": "Program Manager", "company_idx": 2, "category": "operations", "skills": ["project-management", "agile", "communication"], "location": "Remote", "sal": (80000, 160000)},
    # Customer Support (2)
    {"title": "Customer Support Specialist", "company_idx": 7, "category": "customer-support", "skills": ["communication", "problem-solving", "crm"], "location": "Remote", "sal": (25000, 50000)},
    {"title": "Customer Success Manager", "company_idx": 7, "category": "customer-support", "skills": ["customer-success", "communication", "analytics"], "location": "Remote", "sal": (50000, 100000)},
    # Legal (1)
    {"title": "Legal Counsel", "company_idx": 5, "category": "legal", "skills": ["legal", "compliance", "contract-management"], "location": "Remote", "sal": (80000, 160000)},
]


def _gen_id(prefix="j"):
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


async def seed_database():
    """Seed the database with MINIMAL fallback data (used only when APIs are down)."""
    print("*** FALLBACK SEED: Loading minimal offline data (APIs were unavailable) ***")
    await init_db()
    db = await get_db()

    # Check if already seeded
    cursor = await db.execute("SELECT COUNT(*) FROM jobs")
    row = await cursor.fetchone()
    if row[0] > 0:
        print(f"Database already has {row[0]} jobs. Skipping fallback seed.")
        return

    # Insert fallback companies
    for c in FALLBACK_COMPANIES:
        await db.execute("""
            INSERT OR IGNORE INTO companies (id, name, industry, size, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (c["id"], c["name"], c.get("industry"), c.get("size"), datetime.utcnow().isoformat()))

    print(f"Inserted {len(FALLBACK_COMPANIES)} fallback companies")

    # Insert fallback jobs — apply_url is None because we can't verify offline
    count = 0
    for j in FALLBACK_JOBS:
        company = FALLBACK_COMPANIES[j["company_idx"]]
        job_id = _gen_id("j")
        sal_min, sal_max = j["sal"]
        sal_text = f"₹{sal_min:,} - ₹{sal_max:,}/month"
        posted_at = (datetime.utcnow() - timedelta(days=count % 30)).isoformat()
        short_desc = f"{j['title']} at {company['name']}. Skills: {', '.join(j['skills'][:3])}"

        await db.execute("""
            INSERT OR IGNORE INTO jobs
            (id, company_id, title, description, description_short, location,
             location_type, salary_min, salary_max, salary_text,
             experience_min, experience_max, skills, category,
             employment_type, apply_url, source, source_id,
             posted_at, is_active, raw_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            job_id, company["id"], j["title"], short_desc,
            short_desc, j["location"], "remote",
            sal_min, sal_max, sal_text,
            2, 5,
            json.dumps(j["skills"]), j["category"], "full-time",
            None,  # apply_url is NULL — no fake URLs!
            "seed", None,
            posted_at, True,
            json.dumps({"fallback": True}),
        ))
        count += 1

    await db.commit()

    print("Building search index...")
    await rebuild_fts()

    cursor = await db.execute("SELECT COUNT(*) FROM jobs")
    j_count = (await cursor.fetchone())[0]
    print(f"Fallback seed complete: {len(FALLBACK_COMPANIES)} companies, {j_count} jobs (apply_url=NULL)")


if __name__ == "__main__":
    asyncio.run(seed_database())
