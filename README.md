# AgentJobs 🤖

**API-first job platform optimized for AI agents.**

600+ jobs from 90+ companies in India. Structured JSON responses in milliseconds. Built for agents, browsable by humans.

## Quick Start

```bash
cd agentjobs
pip install -r requirements.txt
python main.py
```

The server starts at `http://localhost:8000`. Database is auto-seeded on first run with 600+ jobs.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/jobs` | Search jobs with 15+ filters |
| GET | `/api/v1/jobs/{id}` | Get job details |
| POST | `/api/v1/agent/search` | AI-powered job matching |
| GET | `/api/v1/companies` | List companies |
| GET | `/api/v1/companies/{id}` | Company details |
| GET | `/api/v1/stats` | Platform statistics |
| GET | `/api/v1/categories` | Job categories |
| GET | `/api/v1/skills/trending` | Trending skills |
| POST | `/api/v1/auth/register` | Get API key |
| GET | `/api/v1/auth/usage` | Check usage |
| GET | `/mcp/manifest.json` | MCP tool manifest |
| GET | `/health` | Health check |

## Usage Examples

### Search Jobs
```bash
curl "http://localhost:8000/api/v1/jobs?q=python+developer&location=Bangalore&limit=5"
```

### Match Resume
```bash
curl -X POST "http://localhost:8000/api/v1/agent/search" \
  -H "Content-Type: application/json" \
  -d '{
    "skills": ["python", "sql", "machine-learning"],
    "experience_years": 3,
    "preferred_locations": ["Hyderabad"],
    "salary_min": 80000
  }'
```

### Python Client
```python
import requests

# Search
jobs = requests.get("http://localhost:8000/api/v1/jobs", params={
    "q": "data scientist",
    "salary_min": 100000,
}).json()

# Match
matches = requests.post("http://localhost:8000/api/v1/agent/search", json={
    "skills": ["python", "sql", "ml"],
    "experience_years": 3,
}).json()
```

## Frontend Pages

- `/` — Landing page
- `/search` — Job search with filters
- `/docs-page` — API documentation
- `/agent` — AI resume matching

## Matching Algorithm

Jobs are scored 0-100:
- **Skills match** (40 pts): % of required skills the candidate has
- **Location match** (20 pts): exact city = 20, same state = 15, remote = 20
- **Salary match** (15 pts): meets minimum = 15, close = 10
- **Experience match** (15 pts): within range = 15, close = 10
- **Recency** (10 pts): today = 10, this week = 8, this month = 5

## Tech Stack

- **Backend**: FastAPI + Python 3.11
- **Database**: SQLite (swap to PostgreSQL by changing DATABASE_URL)
- **Search**: SQLite FTS5 full-text search
- **Frontend**: Vanilla HTML/CSS/JS, dark theme

## Docker

```bash
docker-compose up --build
```

## License

MIT
