"""Generate realistic synthetic seed data for AgentJobs."""

import json
import os
import sys
import random
import uuid
import asyncio
from datetime import datetime, timedelta

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db, init_db, rebuild_fts

# ── Job Templates per Category ───────────────────────────────────

JOB_TEMPLATES = {
    "engineering": {
        "titles": [
            "Software Engineer", "Senior Software Engineer", "Staff Software Engineer",
            "Principal Engineer", "Backend Engineer", "Frontend Engineer",
            "Full Stack Developer", "Senior Full Stack Developer",
            "Platform Engineer", "Infrastructure Engineer",
            "Site Reliability Engineer", "DevOps Engineer", "Senior DevOps Engineer",
            "Cloud Engineer", "Solutions Architect", "Technical Architect",
            "Engineering Manager", "Senior Engineering Manager",
            "Mobile Developer (Android)", "Mobile Developer (iOS)",
            "React Native Developer", "Flutter Developer",
            "Embedded Software Engineer", "Firmware Engineer",
            "QA Engineer", "Senior QA Engineer", "SDET",
            "Performance Engineer", "Security Engineer",
            "API Developer", "Microservices Developer",
            "Java Developer", "Python Developer", "Go Developer",
            "Node.js Developer", "Ruby on Rails Developer",
        ],
        "skills_pool": [
            ["python", "django", "postgresql", "redis", "docker"],
            ["java", "spring-boot", "microservices", "kafka", "kubernetes"],
            ["javascript", "react", "nodejs", "typescript", "mongodb"],
            ["python", "fastapi", "postgresql", "docker", "aws"],
            ["go", "kubernetes", "docker", "terraform", "aws"],
            ["java", "spring", "mysql", "redis", "docker"],
            ["python", "flask", "postgresql", "celery", "redis"],
            ["typescript", "react", "nextjs", "postgresql", "graphql"],
            ["javascript", "vue", "nodejs", "mongodb", "docker"],
            ["kotlin", "android", "firebase", "rest-api", "git"],
            ["swift", "ios", "firebase", "rest-api", "git"],
            ["flutter", "dart", "firebase", "rest-api", "git"],
            ["python", "aws", "terraform", "docker", "kubernetes", "linux"],
            ["java", "aws", "docker", "kubernetes", "jenkins", "linux"],
            ["python", "selenium", "pytest", "ci-cd", "docker"],
            ["rust", "system-design", "linux", "docker", "aws"],
            ["cpp", "linux", "embedded", "git", "python"],
            ["ruby", "ruby-on-rails", "postgresql", "redis", "docker"],
        ],
        "descriptions": [
            "Design and develop scalable backend services handling millions of requests per day. Work with cross-functional teams to deliver high-quality software solutions.",
            "Build and maintain frontend applications using modern web frameworks. Collaborate with UX designers to create intuitive user interfaces.",
            "Develop and optimize cloud infrastructure to ensure 99.99% uptime. Implement CI/CD pipelines and monitoring solutions.",
            "Lead technical design and architecture of distributed systems. Mentor junior engineers and drive engineering excellence.",
            "Build robust APIs and microservices that power our core platform. Ensure code quality through testing and code reviews.",
            "Design and implement mobile applications with focus on performance and user experience. Work closely with product and design teams.",
            "Develop automated testing frameworks and tools. Ensure product quality through comprehensive test coverage.",
            "Build and maintain infrastructure as code using modern DevOps practices. Automate deployment and monitoring workflows.",
        ],
    },
    "data-science": {
        "titles": [
            "Data Scientist", "Senior Data Scientist", "Lead Data Scientist",
            "ML Engineer", "Senior ML Engineer", "Machine Learning Engineer",
            "Data Analyst", "Senior Data Analyst", "Business Analyst",
            "Data Engineer", "Senior Data Engineer", "Analytics Engineer",
            "AI Research Engineer", "NLP Engineer", "Computer Vision Engineer",
            "ML Data Associate", "Data Annotation Specialist",
            "Deep Learning Engineer", "MLOps Engineer",
            "Quantitative Analyst", "Statistical Analyst",
            "BI Developer", "Data Warehouse Engineer",
        ],
        "skills_pool": [
            ["python", "machine-learning", "tensorflow", "pandas", "sql"],
            ["python", "pytorch", "deep-learning", "nlp", "aws"],
            ["python", "scikit-learn", "pandas", "sql", "tableau"],
            ["python", "apache-spark", "hadoop", "sql", "aws"],
            ["python", "sql", "data-analysis", "excel", "power-bi"],
            ["python", "computer-vision", "tensorflow", "opencv", "docker"],
            ["python", "nlp", "pytorch", "transformers", "docker"],
            ["python", "machine-learning", "sql", "data-annotation", "pandas"],
            ["python", "apache-spark", "apache-airflow", "sql", "aws"],
            ["python", "sql", "tableau", "data-analysis", "statistics"],
            ["r", "python", "sql", "statistics", "machine-learning"],
        ],
        "descriptions": [
            "Apply machine learning techniques to solve complex business problems. Build and deploy ML models at scale in production environments.",
            "Analyze large datasets to extract actionable insights. Create dashboards and reports for stakeholders.",
            "Design and build data pipelines to process terabytes of data daily. Ensure data quality and reliability across the platform.",
            "Develop NLP models for text classification, entity extraction, and sentiment analysis. Stay current with latest research.",
            "Support AI/ML initiatives by improving data quality and building training datasets for machine learning models.",
            "Build and maintain data warehouses and ETL pipelines. Optimize query performance for analytical workloads.",
            "Research and implement state-of-the-art deep learning architectures. Publish findings and contribute to open source.",
        ],
    },
    "design": {
        "titles": [
            "Product Designer", "Senior Product Designer", "Lead Designer",
            "UX Designer", "Senior UX Designer", "UX Researcher",
            "UI Designer", "Visual Designer", "Interaction Designer",
            "Design System Lead", "Brand Designer",
            "Motion Designer", "Graphic Designer",
        ],
        "skills_pool": [
            ["figma", "sketch", "ui-design", "ux-design", "prototyping"],
            ["figma", "adobe-xd", "user-research", "wireframing", "html"],
            ["figma", "photoshop", "illustrator", "ui-design", "css"],
            ["figma", "user-research", "usability-testing", "prototyping", "analytics"],
            ["figma", "sketch", "design-systems", "css", "html"],
            ["after-effects", "figma", "motion-design", "illustrator", "photoshop"],
        ],
        "descriptions": [
            "Design intuitive and delightful user experiences for our products. Conduct user research and usability testing to inform design decisions.",
            "Create visual designs and design systems that scale across multiple products. Collaborate closely with engineering and product teams.",
            "Lead UX research initiatives to understand user needs and behaviors. Translate insights into actionable design recommendations.",
            "Design and maintain our design system to ensure consistency and efficiency across all products.",
            "Create stunning visual assets and brand materials. Work with marketing team on campaigns and content.",
        ],
    },
    "product": {
        "titles": [
            "Product Manager", "Senior Product Manager", "Lead Product Manager",
            "Associate Product Manager", "Group Product Manager",
            "Technical Product Manager", "Product Owner",
            "Director of Product", "VP Product",
        ],
        "skills_pool": [
            ["product-management", "agile", "jira", "sql", "data-analysis"],
            ["product-management", "scrum", "analytics", "sql", "communication"],
            ["product-management", "agile", "data-analysis", "a/b-testing", "sql"],
            ["product-management", "technical-writing", "api-design", "sql", "python"],
        ],
        "descriptions": [
            "Define product strategy and roadmap. Work with engineering, design, and business teams to deliver impactful features.",
            "Own the product lifecycle from ideation to launch. Analyze metrics and user feedback to drive product improvements.",
            "Manage product backlog and prioritize features based on business impact. Coordinate with stakeholders across the organization.",
            "Lead cross-functional teams to build products that solve real customer problems. Define success metrics and track outcomes.",
        ],
    },
    "marketing": {
        "titles": [
            "Digital Marketing Manager", "Content Marketing Manager",
            "SEO Specialist", "SEM Specialist", "Performance Marketing Lead",
            "Social Media Manager", "Brand Manager",
            "Growth Marketing Manager", "Marketing Analyst",
            "Email Marketing Specialist", "Content Strategist",
        ],
        "skills_pool": [
            ["digital-marketing", "google-analytics", "seo", "sem", "content-marketing"],
            ["social-media-marketing", "content-marketing", "copywriting", "analytics", "seo"],
            ["seo", "sem", "google-analytics", "content-marketing", "html"],
            ["digital-marketing", "performance-marketing", "sql", "analytics", "a/b-testing"],
        ],
        "descriptions": [
            "Plan and execute digital marketing campaigns across multiple channels. Analyze performance and optimize for ROI.",
            "Create compelling content strategy and manage content production. Drive organic growth through SEO and content marketing.",
            "Manage social media presence and engagement. Create viral content and build brand community.",
            "Lead growth marketing initiatives including acquisition, activation, and retention campaigns.",
        ],
    },
    "sales": {
        "titles": [
            "Sales Executive", "Senior Sales Executive", "Account Manager",
            "Business Development Manager", "Enterprise Sales Lead",
            "Sales Development Representative", "Regional Sales Manager",
            "Key Account Manager", "Sales Engineer",
        ],
        "skills_pool": [
            ["salesforce-crm", "communication", "negotiation", "presentation", "excel"],
            ["sales", "crm", "communication", "leadership", "analytics"],
            ["business-development", "communication", "salesforce-crm", "excel", "presentation"],
        ],
        "descriptions": [
            "Drive revenue growth by building and maintaining client relationships. Meet and exceed quarterly sales targets.",
            "Identify and qualify new business opportunities. Develop strategic partnerships to expand market presence.",
            "Manage key enterprise accounts and ensure client satisfaction. Drive upselling and cross-selling opportunities.",
        ],
    },
    "operations": {
        "titles": [
            "Operations Manager", "Senior Operations Manager",
            "Business Operations Analyst", "Strategy & Operations Lead",
            "Supply Chain Manager", "Logistics Manager",
            "Program Manager", "Senior Program Manager",
        ],
        "skills_pool": [
            ["excel", "sql", "data-analysis", "project-management", "communication"],
            ["operations", "analytics", "sql", "excel", "process-improvement"],
            ["supply-chain", "logistics", "excel", "erp", "analytics"],
        ],
        "descriptions": [
            "Optimize business operations and processes. Drive efficiency improvements and cost reduction initiatives.",
            "Manage cross-functional programs and initiatives. Ensure timely delivery and stakeholder alignment.",
            "Oversee supply chain operations and logistics. Build scalable processes for growing business needs.",
        ],
    },
    "finance": {
        "titles": [
            "Financial Analyst", "Senior Financial Analyst",
            "Investment Analyst", "Risk Analyst",
            "Finance Manager", "FP&A Manager",
            "Chartered Accountant", "Tax Analyst",
            "Treasury Analyst", "Audit Associate",
        ],
        "skills_pool": [
            ["excel", "sql", "financial-modeling", "data-analysis", "communication"],
            ["excel", "financial-analysis", "accounting", "sap-erp", "sql"],
            ["excel", "risk-management", "python", "sql", "statistics"],
        ],
        "descriptions": [
            "Perform financial analysis and modeling to support business decisions. Prepare reports and forecasts.",
            "Manage financial planning, budgeting, and forecasting. Work with leadership on strategic financial initiatives.",
            "Conduct risk assessment and develop mitigation strategies. Ensure compliance with financial regulations.",
        ],
    },
    "hr": {
        "titles": [
            "HR Business Partner", "Senior HR Manager",
            "Talent Acquisition Specialist", "Technical Recruiter",
            "HR Generalist", "People Operations Manager",
            "Compensation & Benefits Manager", "L&D Manager",
        ],
        "skills_pool": [
            ["hr", "recruitment", "communication", "excel", "people-management"],
            ["recruitment", "sourcing", "communication", "hr-analytics", "ats"],
            ["hr", "employee-engagement", "analytics", "communication", "leadership"],
        ],
        "descriptions": [
            "Partner with business leaders to develop HR strategies. Drive talent management and organizational development initiatives.",
            "Lead end-to-end recruitment process for technical and non-technical roles. Build talent pipeline and employer brand.",
            "Design and implement people programs to improve employee engagement and retention.",
        ],
    },
    "legal": {
        "titles": [
            "Legal Counsel", "Senior Legal Counsel",
            "Corporate Lawyer", "Compliance Manager",
            "Legal Associate", "IP Counsel",
            "Contract Manager", "Data Privacy Officer",
        ],
        "skills_pool": [
            ["legal", "compliance", "contract-management", "communication", "research"],
            ["corporate-law", "ip-law", "compliance", "contract-drafting", "negotiation"],
            ["data-privacy", "gdpr", "compliance", "legal-research", "communication"],
        ],
        "descriptions": [
            "Provide legal counsel on corporate matters, contracts, and compliance. Support business teams with legal guidance.",
            "Manage corporate legal affairs and ensure regulatory compliance. Draft and review contracts and agreements.",
            "Lead data privacy and compliance initiatives. Ensure compliance with GDPR, DPDPA, and other regulations.",
        ],
    },
    "customer-support": {
        "titles": [
            "Customer Support Specialist", "Senior Support Engineer",
            "Technical Support Engineer", "Customer Success Manager",
            "Support Team Lead", "Customer Experience Manager",
            "Help Desk Analyst", "Implementation Specialist",
        ],
        "skills_pool": [
            ["communication", "problem-solving", "crm", "technical-support", "sql"],
            ["customer-support", "communication", "jira", "troubleshooting", "documentation"],
            ["customer-success", "communication", "analytics", "crm", "presentation"],
        ],
        "descriptions": [
            "Provide exceptional technical support to customers. Troubleshoot issues and ensure customer satisfaction.",
            "Build and maintain customer relationships. Drive product adoption and ensure customer success.",
            "Lead support team to deliver best-in-class customer experience. Implement processes to improve resolution times.",
        ],
    },
}

# Salary ranges per category and experience level (monthly INR)
SALARY_RANGES = {
    "engineering": {
        "junior": (25000, 55000),
        "mid": (55000, 120000),
        "senior": (120000, 250000),
        "lead": (200000, 450000),
    },
    "data-science": {
        "junior": (30000, 60000),
        "mid": (60000, 130000),
        "senior": (130000, 280000),
        "lead": (250000, 500000),
    },
    "design": {
        "junior": (20000, 45000),
        "mid": (45000, 100000),
        "senior": (100000, 200000),
        "lead": (180000, 350000),
    },
    "product": {
        "junior": (35000, 70000),
        "mid": (70000, 150000),
        "senior": (150000, 300000),
        "lead": (280000, 550000),
    },
    "marketing": {
        "junior": (18000, 40000),
        "mid": (40000, 85000),
        "senior": (85000, 180000),
        "lead": (160000, 300000),
    },
    "sales": {
        "junior": (20000, 45000),
        "mid": (45000, 100000),
        "senior": (100000, 200000),
        "lead": (180000, 350000),
    },
    "operations": {
        "junior": (20000, 40000),
        "mid": (40000, 80000),
        "senior": (80000, 160000),
        "lead": (140000, 280000),
    },
    "finance": {
        "junior": (25000, 50000),
        "mid": (50000, 110000),
        "senior": (110000, 220000),
        "lead": (200000, 400000),
    },
    "hr": {
        "junior": (18000, 35000),
        "mid": (35000, 70000),
        "senior": (70000, 150000),
        "lead": (130000, 250000),
    },
    "legal": {
        "junior": (30000, 60000),
        "mid": (60000, 120000),
        "senior": (120000, 250000),
        "lead": (220000, 450000),
    },
    "customer-support": {
        "junior": (15000, 30000),
        "mid": (30000, 60000),
        "senior": (60000, 120000),
        "lead": (100000, 200000),
    },
}

LOCATIONS = [
    "Hyderabad, Telangana",
    "Bangalore, Karnataka",
    "Mumbai, Maharashtra",
    "Pune, Maharashtra",
    "Delhi NCR",
    "Chennai, Tamil Nadu",
    "Kolkata, West Bengal",
    "Ahmedabad, Gujarat",
    "Remote",
]

LOCATION_TYPES = ["onsite", "remote", "hybrid"]
EMPLOYMENT_TYPES = ["full-time", "part-time", "contract", "internship"]
SOURCES = ["linkedin", "company-website", "naukri", "indeed", "glassdoor"]

# Experience levels and their year ranges
EXPERIENCE_LEVELS = {
    "junior": (0, 2),
    "mid": (2, 5),
    "senior": (5, 10),
    "lead": (8, 15),
}


def _generate_id(prefix: str = "j") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _random_posted_date() -> str:
    days_ago = random.choices(
        range(0, 90),
        weights=[10] * 3 + [8] * 4 + [5] * 23 + [2] * 60,
        k=1,
    )[0]
    dt = datetime.now() - timedelta(days=days_ago)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _get_experience_level(title: str) -> str:
    title_lower = title.lower()
    if any(kw in title_lower for kw in ["senior", "lead", "principal", "staff", "director", "vp", "head"]):
        if any(kw in title_lower for kw in ["lead", "principal", "director", "vp", "head", "group"]):
            return "lead"
        return "senior"
    if any(kw in title_lower for kw in ["associate", "junior", "intern", "trainee", "entry"]):
        return "junior"
    return "mid"


def _salary_text(salary_min: int, salary_max: int) -> str:
    lpa_min = round(salary_min * 12 / 100000, 1)
    lpa_max = round(salary_max * 12 / 100000, 1)
    return f"{lpa_min}-{lpa_max} LPA"


def _generate_short_desc(title: str, company_name: str, skills: list) -> str:
    templates = [
        f"Join {company_name} as a {title}. Work with {', '.join(skills[:3])} in a fast-paced environment.",
        f"Exciting {title} opportunity at {company_name}. Looking for expertise in {', '.join(skills[:3])}.",
        f"{company_name} is hiring a {title} to build cutting-edge solutions using {', '.join(skills[:3])}.",
        f"Be part of {company_name}'s growing team as a {title}. Key skills: {', '.join(skills[:3])}.",
    ]
    return random.choice(templates)


def generate_jobs(companies: list) -> list:
    """Generate 600+ realistic synthetic jobs."""
    jobs = []
    categories = list(JOB_TEMPLATES.keys())

    # Distribute jobs across companies — bigger companies get more listings
    for company in companies:
        size = company.get("size", "medium")
        if size == "enterprise":
            num_jobs = random.randint(8, 15)
        elif size == "large":
            num_jobs = random.randint(5, 10)
        elif size == "medium":
            num_jobs = random.randint(3, 7)
        else:
            num_jobs = random.randint(1, 4)

        # Weight categories based on company industry
        industry = (company.get("industry") or "").lower()
        if "tech" in industry or "saas" in industry or "developer" in industry:
            cat_weights = {"engineering": 5, "data-science": 3, "design": 2, "product": 2,
                           "marketing": 1, "sales": 1, "operations": 1, "finance": 1,
                           "hr": 1, "legal": 0.5, "customer-support": 1}
        elif "banking" in industry or "fintech" in industry:
            cat_weights = {"engineering": 3, "data-science": 3, "design": 1, "product": 2,
                           "marketing": 1, "sales": 2, "operations": 2, "finance": 3,
                           "hr": 1, "legal": 1, "customer-support": 1}
        elif "consulting" in industry or "it services" in industry:
            cat_weights = {"engineering": 4, "data-science": 2, "design": 1, "product": 1,
                           "marketing": 1, "sales": 2, "operations": 2, "finance": 1,
                           "hr": 2, "legal": 1, "customer-support": 1}
        elif "ecommerce" in industry or "e-commerce" in industry:
            cat_weights = {"engineering": 4, "data-science": 2, "design": 2, "product": 2,
                           "marketing": 2, "sales": 1, "operations": 2, "finance": 1,
                           "hr": 1, "legal": 0.5, "customer-support": 2}
        else:
            cat_weights = {cat: 1 for cat in categories}

        weighted_cats = []
        for cat, weight in cat_weights.items():
            weighted_cats.extend([cat] * int(weight * 2))

        for _ in range(num_jobs):
            category = random.choice(weighted_cats)
            template = JOB_TEMPLATES[category]

            title = random.choice(template["titles"])
            skills = list(random.choice(template["skills_pool"]))
            description = random.choice(template["descriptions"])

            exp_level = _get_experience_level(title)
            exp_range = EXPERIENCE_LEVELS[exp_level]
            experience_min = exp_range[0]
            experience_max = exp_range[1]

            sal_range = SALARY_RANGES[category][exp_level]
            # Adjust salary for company size
            size_multiplier = {"enterprise": 1.3, "large": 1.1, "medium": 1.0, "startup": 0.85, "small": 0.8}.get(size, 1.0)
            salary_min = int(random.randint(sal_range[0], int((sal_range[0] + sal_range[1]) / 2)) * size_multiplier)
            salary_max = int(random.randint(int((sal_range[0] + sal_range[1]) / 2), sal_range[1]) * size_multiplier)

            # Round to nearest 1000
            salary_min = round(salary_min / 1000) * 1000
            salary_max = round(salary_max / 1000) * 1000
            if salary_max <= salary_min:
                salary_max = salary_min + 10000

            # Location — prefer company's HQ location but vary
            company_loc = company.get("location", "Bangalore, Karnataka")
            if random.random() < 0.6:
                location = company_loc
            else:
                location = random.choice(LOCATIONS)

            location_type = random.choices(
                LOCATION_TYPES,
                weights=[50, 25, 25],
                k=1,
            )[0]

            if location == "Remote":
                location_type = "remote"

            employment_type = random.choices(
                EMPLOYMENT_TYPES,
                weights=[70, 5, 15, 10],
                k=1,
            )[0]

            if exp_level == "junior" and random.random() < 0.2:
                employment_type = "internship"

            short_desc = _generate_short_desc(title, company["name"], skills)
            posted_at = _random_posted_date()
            source = random.choice(SOURCES)

            job = {
                "id": _generate_id("j"),
                "company_id": company["id"],
                "title": title,
                "description": description,
                "description_short": short_desc,
                "location": location,
                "location_type": location_type,
                "salary_min": salary_min,
                "salary_max": salary_max,
                "salary_text": _salary_text(salary_min, salary_max),
                "experience_min": experience_min,
                "experience_max": experience_max,
                "skills": json.dumps(skills),
                "category": category,
                "employment_type": employment_type,
                "apply_url": f"https://{company.get('website', 'example.com').replace('https://', '')}/careers/{_generate_id('apply')}",
                "source": source,
                "source_id": _generate_id("src"),
                "posted_at": posted_at,
                "is_active": True,
                "raw_data": json.dumps({"generated": True}),
            }
            jobs.append(job)

    return jobs


async def seed_database():
    """Seed the database with companies and jobs."""
    print("Initializing database...")
    await init_db()

    db = await get_db()

    # Check if already seeded
    cursor = await db.execute("SELECT COUNT(*) FROM jobs")
    row = await cursor.fetchone()
    if row[0] > 0:
        print(f"Database already has {row[0]} jobs. Skipping seed.")
        return

    # Load companies
    companies_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "companies.json")
    with open(companies_path, "r") as f:
        companies = json.load(f)

    print(f"Inserting {len(companies)} companies...")
    for company in companies:
        await db.execute("""
            INSERT OR IGNORE INTO companies (id, name, website, careers_url, industry, size, location, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            company["id"], company["name"], company.get("website"), company.get("careers_url"),
            company.get("industry"), company.get("size"), company.get("location"), company.get("description"),
        ))

    # Generate jobs
    print("Generating jobs...")
    jobs = generate_jobs(companies)
    print(f"Inserting {len(jobs)} jobs...")

    for job in jobs:
        await db.execute("""
            INSERT OR IGNORE INTO jobs
            (id, company_id, title, description, description_short, location, location_type,
             salary_min, salary_max, salary_text, experience_min, experience_max,
             skills, category, employment_type, apply_url, source, source_id,
             posted_at, is_active, raw_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            job["id"], job["company_id"], job["title"], job["description"],
            job["description_short"], job["location"], job["location_type"],
            job["salary_min"], job["salary_max"], job["salary_text"],
            job["experience_min"], job["experience_max"],
            job["skills"], job["category"], job["employment_type"],
            job["apply_url"], job["source"], job["source_id"],
            job["posted_at"], job["is_active"], job["raw_data"],
        ))

    await db.commit()

    # Rebuild FTS index
    print("Building search index...")
    await rebuild_fts()

    # Verify
    cursor = await db.execute("SELECT COUNT(*) FROM companies")
    c_count = (await cursor.fetchone())[0]
    cursor = await db.execute("SELECT COUNT(*) FROM jobs")
    j_count = (await cursor.fetchone())[0]
    print(f"Seeding complete: {c_count} companies, {j_count} jobs")


if __name__ == "__main__":
    asyncio.run(seed_database())
