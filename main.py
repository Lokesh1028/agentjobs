"""AgentJobs — API-first job platform optimized for AI agents."""

import os
import sys
import time
import json
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import init_db, close_db

# Import routers
from routers import jobs, companies, agent, auth, mcp, stats
from routers import admin as admin_router


async def seed_admin():
    """Create default admin user if not exists."""
    from database import get_db
    import bcrypt as _bcrypt
    import uuid
    from datetime import datetime

    db = await get_db()
    cursor = await db.execute("SELECT id FROM users WHERE email = ?", ["admin@agentjobs.dev"])
    if not await cursor.fetchone():
        admin_id = f"u_{uuid.uuid4().hex[:12]}"
        password_hash = _bcrypt.hashpw("AgentJobs2024!".encode(), _bcrypt.gensalt()).decode()
        now = datetime.utcnow().isoformat()
        await db.execute("""
            INSERT INTO users (id, email, name, password_hash, company, role, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (admin_id, "admin@agentjobs.dev", "Admin", password_hash, "AgentJobs", "admin", now))
        await db.commit()
        print("Admin user seeded: admin@agentjobs.dev")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    # Startup
    await init_db()

    # Seed admin
    await seed_admin()

    # Auto-seed if empty
    from database import get_db
    db = await get_db()
    cursor = await db.execute("SELECT COUNT(*) FROM jobs")
    count = (await cursor.fetchone())[0]
    if count == 0:
        print("Database is empty. Running seed...")
        from seed.seed_data import seed_database
        await seed_database()

    yield

    # Shutdown
    await close_db()


app = FastAPI(
    title="AgentJobs",
    description="API-first job platform optimized for AI agents. Search 600+ jobs across 90+ companies in India.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timing + activity tracking middleware
@app.middleware("http")
async def add_timing_and_tracking(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    elapsed = (time.time() - start) * 1000
    response.headers["X-Response-Time-Ms"] = f"{elapsed:.2f}"

    # Track activity for API endpoints (non-blocking)
    path = request.url.path
    if path.startswith("/api/v1/"):
        try:
            # Determine action type
            action = None
            details = None

            if path == "/api/v1/jobs" and request.method == "GET":
                action = "search"
                params = dict(request.query_params)
                if params:
                    details = json.dumps(params)
            elif path == "/api/v1/agent/search" and request.method == "POST":
                action = "agent_search"
            elif path.startswith("/api/v1/jobs/") and request.method == "GET" and path != "/api/v1/jobs":
                action = "view_job"
                details = json.dumps({"job_id": path.split("/")[-1]})

            if action:
                # Get user_id from auth header if present
                user_id = None
                auth_header = request.headers.get("Authorization", "")
                if auth_header.startswith("Bearer "):
                    from routers.auth import get_current_user
                    user = await get_current_user(request)
                    if user:
                        user_id = user["id"]

                ip = request.client.host if request.client else None
                ua = request.headers.get("user-agent")
                from routers.auth import log_activity
                await log_activity(user_id, action, details, ip, ua)
        except Exception:
            pass  # Never let tracking break the request

    return response


# Register routers
app.include_router(jobs.router)
app.include_router(companies.router)
app.include_router(agent.router)
app.include_router(auth.router)
app.include_router(stats.router)
app.include_router(mcp.router)
app.include_router(admin_router.router)

# Static files
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


# Frontend routes
@app.get("/", response_class=HTMLResponse)
async def index():
    return FileResponse(os.path.join(static_dir, "index.html"))


@app.get("/search", response_class=HTMLResponse)
async def search_page():
    return FileResponse(os.path.join(static_dir, "search.html"))


@app.get("/docs-page", response_class=HTMLResponse)
async def docs_page():
    return FileResponse(os.path.join(static_dir, "docs.html"))


@app.get("/agent", response_class=HTMLResponse)
async def agent_page():
    return FileResponse(os.path.join(static_dir, "agent.html"))


@app.get("/login", response_class=HTMLResponse)
async def login_page():
    return FileResponse(os.path.join(static_dir, "login.html"))


@app.get("/admin", response_class=HTMLResponse)
async def admin_page():
    return FileResponse(os.path.join(static_dir, "admin.html"))


# Health check
@app.get("/health")
async def health():
    return {"status": "ok", "service": "agentjobs", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
