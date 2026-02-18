"""MCP (Model Context Protocol) manifest and endpoints."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(tags=["mcp"])


@router.get("/mcp/manifest.json")
async def mcp_manifest(request: Request):
    """Return MCP tool manifest for AI agent discovery."""
    base_url = str(request.base_url).rstrip("/")

    manifest = {
        "schema_version": "v1",
        "name": "agentjobs",
        "display_name": "AgentJobs — Job Search API",
        "description": "Search and discover job listings across 90+ companies in India. Optimized for AI agent consumption.",
        "auth": {
            "type": "api_key",
            "header": "X-API-Key",
            "instructions": "Register at POST /api/v1/auth/register with your email to get a free API key."
        },
        "tools": [
            {
                "name": "search_jobs",
                "description": "Search job listings with filters. Returns structured JSON with job details, salary info, and skill requirements.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Full-text search query (e.g., 'python backend developer')"
                        },
                        "location": {
                            "type": "string",
                            "description": "City/location filter (e.g., 'Hyderabad', 'Bangalore', 'Remote')"
                        },
                        "skills": {
                            "type": "string",
                            "description": "Comma-separated skills (e.g., 'python,sql,docker')"
                        },
                        "salary_min": {
                            "type": "integer",
                            "description": "Minimum monthly salary in INR"
                        },
                        "category": {
                            "type": "string",
                            "description": "Job category (engineering, data-science, design, product, etc.)"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Max results (default 20, max 100)"
                        }
                    }
                },
                "endpoint": {
                    "method": "GET",
                    "url": f"{base_url}/api/v1/jobs",
                    "params_mapping": {
                        "query": "q",
                        "location": "location",
                        "skills": "skills",
                        "salary_min": "salary_min",
                        "category": "category",
                        "limit": "limit"
                    }
                }
            },
            {
                "name": "match_resume",
                "description": "Match a candidate's resume/skills against all active jobs. Returns scored matches with detailed match reasons.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "resume_text": {
                            "type": "string",
                            "description": "Full resume text or summary"
                        },
                        "skills": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of candidate skills"
                        },
                        "experience_years": {
                            "type": "integer",
                            "description": "Years of experience"
                        },
                        "preferred_locations": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Preferred work locations"
                        },
                        "salary_min": {
                            "type": "integer",
                            "description": "Minimum acceptable monthly salary in INR"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Max results (default 20)"
                        }
                    }
                },
                "endpoint": {
                    "method": "POST",
                    "url": f"{base_url}/api/v1/agent/search"
                }
            },
            {
                "name": "get_job_details",
                "description": "Get full details for a specific job listing.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "job_id": {
                            "type": "string",
                            "description": "Job ID (e.g., 'j_abc123')"
                        }
                    },
                    "required": ["job_id"]
                },
                "endpoint": {
                    "method": "GET",
                    "url": f"{base_url}/api/v1/jobs/{{job_id}}"
                }
            },
            {
                "name": "list_companies",
                "description": "List companies with filters for industry, size, and location.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "industry": {
                            "type": "string",
                            "description": "Industry filter (Technology, Fintech, Banking, etc.)"
                        },
                        "location": {
                            "type": "string",
                            "description": "Location filter"
                        },
                        "size": {
                            "type": "string",
                            "description": "Company size (startup, small, medium, large, enterprise)"
                        }
                    }
                },
                "endpoint": {
                    "method": "GET",
                    "url": f"{base_url}/api/v1/companies",
                    "params_mapping": {
                        "industry": "industry",
                        "location": "location",
                        "size": "size"
                    }
                }
            }
        ],
        "examples": [
            {
                "tool": "search_jobs",
                "input": {"query": "python developer", "location": "Bangalore", "limit": 5},
                "description": "Find Python developer jobs in Bangalore"
            },
            {
                "tool": "match_resume",
                "input": {
                    "skills": ["python", "sql", "machine-learning"],
                    "experience_years": 3,
                    "preferred_locations": ["Hyderabad", "Remote"],
                    "salary_min": 80000
                },
                "description": "Match a data scientist profile against available jobs"
            }
        ]
    }

    return JSONResponse(content=manifest)
