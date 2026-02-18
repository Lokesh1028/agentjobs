"""Skills extraction and normalization for AgentJobs."""

import re
from typing import List, Set

# Canonical skill mappings (variations -> canonical name)
SKILL_ALIASES = {
    "python": "python",
    "python3": "python",
    "py": "python",
    "javascript": "javascript",
    "js": "javascript",
    "node.js": "nodejs",
    "nodejs": "nodejs",
    "node": "nodejs",
    "typescript": "typescript",
    "ts": "typescript",
    "react": "react",
    "reactjs": "react",
    "react.js": "react",
    "angular": "angular",
    "angularjs": "angular",
    "vue": "vue",
    "vuejs": "vue",
    "vue.js": "vue",
    "java": "java",
    "c++": "cpp",
    "cpp": "cpp",
    "c#": "csharp",
    "csharp": "csharp",
    "c-sharp": "csharp",
    "golang": "go",
    "go": "go",
    "rust": "rust",
    "ruby": "ruby",
    "rails": "ruby-on-rails",
    "ruby on rails": "ruby-on-rails",
    "php": "php",
    "swift": "swift",
    "kotlin": "kotlin",
    "scala": "scala",
    "r": "r",
    "sql": "sql",
    "mysql": "mysql",
    "postgresql": "postgresql",
    "postgres": "postgresql",
    "mongodb": "mongodb",
    "mongo": "mongodb",
    "redis": "redis",
    "elasticsearch": "elasticsearch",
    "kafka": "kafka",
    "rabbitmq": "rabbitmq",
    "aws": "aws",
    "amazon web services": "aws",
    "gcp": "gcp",
    "google cloud": "gcp",
    "azure": "azure",
    "microsoft azure": "azure",
    "docker": "docker",
    "kubernetes": "kubernetes",
    "k8s": "kubernetes",
    "terraform": "terraform",
    "ansible": "ansible",
    "jenkins": "jenkins",
    "ci/cd": "ci-cd",
    "cicd": "ci-cd",
    "git": "git",
    "github": "github",
    "gitlab": "gitlab",
    "linux": "linux",
    "unix": "unix",
    "machine learning": "machine-learning",
    "ml": "machine-learning",
    "deep learning": "deep-learning",
    "dl": "deep-learning",
    "artificial intelligence": "ai",
    "ai": "ai",
    "nlp": "nlp",
    "natural language processing": "nlp",
    "computer vision": "computer-vision",
    "cv": "computer-vision",
    "tensorflow": "tensorflow",
    "tf": "tensorflow",
    "pytorch": "pytorch",
    "torch": "pytorch",
    "keras": "keras",
    "scikit-learn": "scikit-learn",
    "sklearn": "scikit-learn",
    "pandas": "pandas",
    "numpy": "numpy",
    "scipy": "scipy",
    "matplotlib": "matplotlib",
    "tableau": "tableau",
    "power bi": "power-bi",
    "powerbi": "power-bi",
    "data analysis": "data-analysis",
    "data engineering": "data-engineering",
    "data science": "data-science",
    "etl": "etl",
    "spark": "apache-spark",
    "apache spark": "apache-spark",
    "hadoop": "hadoop",
    "hive": "hive",
    "airflow": "apache-airflow",
    "apache airflow": "apache-airflow",
    "rest api": "rest-api",
    "restful": "rest-api",
    "graphql": "graphql",
    "microservices": "microservices",
    "system design": "system-design",
    "dsa": "data-structures",
    "data structures": "data-structures",
    "algorithms": "algorithms",
    "agile": "agile",
    "scrum": "scrum",
    "jira": "jira",
    "figma": "figma",
    "sketch": "sketch",
    "adobe xd": "adobe-xd",
    "photoshop": "photoshop",
    "illustrator": "illustrator",
    "html": "html",
    "css": "css",
    "sass": "sass",
    "tailwind": "tailwind-css",
    "tailwindcss": "tailwind-css",
    "bootstrap": "bootstrap",
    "django": "django",
    "flask": "flask",
    "fastapi": "fastapi",
    "spring": "spring",
    "spring boot": "spring-boot",
    "springboot": "spring-boot",
    ".net": "dotnet",
    "dotnet": "dotnet",
    "asp.net": "asp-dotnet",
    "express": "express",
    "expressjs": "express",
    "next.js": "nextjs",
    "nextjs": "nextjs",
    "nuxt": "nuxt",
    "nuxtjs": "nuxt",
    "flutter": "flutter",
    "react native": "react-native",
    "android": "android",
    "ios": "ios",
    "mobile development": "mobile-development",
    "devops": "devops",
    "sre": "sre",
    "site reliability": "sre",
    "cybersecurity": "cybersecurity",
    "security": "security",
    "penetration testing": "penetration-testing",
    "blockchain": "blockchain",
    "web3": "web3",
    "solidity": "solidity",
    "unity": "unity",
    "unreal": "unreal-engine",
    "game development": "game-development",
    "data annotation": "data-annotation",
    "data labeling": "data-annotation",
    "excel": "excel",
    "sap": "sap-erp",
    "salesforce": "salesforce-crm",
    "communication": "communication",
    "leadership": "leadership",
    "project management": "project-management",
    "product management": "product-management",
    "ux": "ux-design",
    "ui": "ui-design",
    "ux design": "ux-design",
    "ui design": "ui-design",
    "ui/ux": "ui-ux-design",
    "user research": "user-research",
    "seo": "seo",
    "sem": "sem",
    "google analytics": "google-analytics",
    "digital marketing": "digital-marketing",
    "content marketing": "content-marketing",
    "social media": "social-media-marketing",
    "copywriting": "copywriting",
}

# All known skills for extraction
ALL_SKILLS = set(SKILL_ALIASES.keys()) | set(SKILL_ALIASES.values())


def normalize_skill(skill: str) -> str:
    """Normalize a skill name to its canonical form."""
    s = skill.strip().lower()
    return SKILL_ALIASES.get(s, s)


def normalize_skills(skills: List[str]) -> List[str]:
    """Normalize a list of skills, removing duplicates."""
    seen = set()
    result = []
    for skill in skills:
        normalized = normalize_skill(skill)
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def extract_skills_from_text(text: str) -> List[str]:
    """Extract skills from free-form text (resume, job description, etc.)."""
    if not text:
        return []

    text_lower = text.lower()
    found: Set[str] = set()

    # Multi-word skills first (longer matches take priority)
    multi_word = sorted(
        [k for k in SKILL_ALIASES.keys() if " " in k or "/" in k or "." in k],
        key=len,
        reverse=True,
    )
    for skill_key in multi_word:
        if skill_key in text_lower:
            found.add(SKILL_ALIASES[skill_key])

    # Single-word skills (use word boundary matching)
    single_word = [k for k in SKILL_ALIASES.keys() if " " not in k and "/" not in k and "." not in k]
    for skill_key in single_word:
        # Skip very short keys to avoid false positives
        if len(skill_key) <= 1 and skill_key not in ("r", "c"):
            continue
        pattern = r'\b' + re.escape(skill_key) + r'\b'
        if re.search(pattern, text_lower):
            found.add(SKILL_ALIASES[skill_key])

    return sorted(list(found))


def skills_similarity(skills_a: List[str], skills_b: List[str]) -> float:
    """Calculate similarity between two skill sets (0-1)."""
    if not skills_a or not skills_b:
        return 0.0
    set_a = set(normalize_skill(s) for s in skills_a)
    set_b = set(normalize_skill(s) for s in skills_b)
    intersection = set_a & set_b
    union = set_a | set_b
    if not union:
        return 0.0
    return len(intersection) / len(union)


def skills_match_details(candidate_skills: List[str], job_skills: List[str]) -> dict:
    """Get detailed match info between candidate and job skills."""
    c_set = set(normalize_skill(s) for s in candidate_skills)
    j_set = set(normalize_skill(s) for s in job_skills)
    matched = c_set & j_set
    missing = j_set - c_set
    extra = c_set - j_set
    match_pct = len(matched) / len(j_set) * 100 if j_set else 0
    return {
        "matched": sorted(list(matched)),
        "missing": sorted(list(missing)),
        "extra": sorted(list(extra)),
        "match_percentage": round(match_pct, 1),
    }
