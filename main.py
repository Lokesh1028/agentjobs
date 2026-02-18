"""AgentJobs — API-first job platform optimized for AI agents."""

import os
import sys
import time
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    # Startup
    await init_db()

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


# Request timing middleware
@app.middleware("http")
async def add_timing(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    elapsed = (time.time() - start) * 1000
    response.headers["X-Response-Time-Ms"] = f"{elapsed:.2f}"
    return response


# Register routers
app.include_router(jobs.router)
app.include_router(companies.router)
app.include_router(agent.router)
app.include_router(auth.router)
app.include_router(stats.router)
app.include_router(mcp.router)

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
