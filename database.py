"""Database setup and connection management for AgentJobs."""

import aiosqlite
import os
import json
from config import settings

DB_PATH = settings.database_url.replace("sqlite:///", "")
if DB_PATH.startswith("./"):
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), DB_PATH[2:])

_db = None


async def get_db() -> aiosqlite.Connection:
    """Get database connection (reuses single connection)."""
    global _db
    if _db is None:
        _db = await aiosqlite.connect(DB_PATH)
        _db.row_factory = aiosqlite.Row
        await _db.execute("PRAGMA journal_mode=WAL")
        await _db.execute("PRAGMA foreign_keys=ON")
    return _db


async def close_db():
    """Close database connection."""
    global _db
    if _db:
        await _db.close()
        _db = None


async def init_db():
    """Initialize database tables and indexes."""
    db = await get_db()

    await db.executescript("""
        CREATE TABLE IF NOT EXISTS companies (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            website TEXT,
            careers_url TEXT,
            industry TEXT,
            size TEXT,
            logo_url TEXT,
            location TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            company_id TEXT REFERENCES companies(id),
            title TEXT NOT NULL,
            description TEXT,
            description_short TEXT,
            location TEXT,
            location_type TEXT,
            salary_min INTEGER,
            salary_max INTEGER,
            salary_text TEXT,
            experience_min INTEGER,
            experience_max INTEGER,
            skills TEXT,
            category TEXT,
            employment_type TEXT,
            apply_url TEXT NOT NULL,
            source TEXT,
            source_id TEXT,
            posted_at TIMESTAMP,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            raw_data TEXT
        );

        CREATE TABLE IF NOT EXISTS api_keys (
            id TEXT PRIMARY KEY,
            key_hash TEXT NOT NULL UNIQUE,
            name TEXT,
            email TEXT,
            tier TEXT DEFAULT 'free',
            rate_limit INTEGER DEFAULT 100,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS api_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_key_id TEXT REFERENCES api_keys(id),
            endpoint TEXT,
            query_params TEXT,
            response_time_ms INTEGER,
            result_count INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS agent_sessions (
            id TEXT PRIMARY KEY,
            user_email TEXT,
            resume_text TEXT,
            resume_skills TEXT,
            resume_experience_years INTEGER,
            resume_preferred_locations TEXT,
            resume_preferred_salary_min INTEGER,
            status TEXT DEFAULT 'processing',
            results TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT NOT NULL UNIQUE,
            name TEXT,
            password_hash TEXT NOT NULL,
            company TEXT,
            role TEXT DEFAULT 'user',
            avatar_url TEXT,
            is_active BOOLEAN DEFAULT 1,
            last_login TIMESTAMP,
            login_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id TEXT REFERENCES users(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS user_activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT REFERENCES users(id),
            action TEXT NOT NULL,
            details TEXT,
            ip_address TEXT,
            user_agent TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Indexes for performance
        CREATE INDEX IF NOT EXISTS idx_jobs_company_id ON jobs(company_id);
        CREATE INDEX IF NOT EXISTS idx_jobs_category ON jobs(category);
        CREATE INDEX IF NOT EXISTS idx_jobs_location ON jobs(location);
        CREATE INDEX IF NOT EXISTS idx_jobs_location_type ON jobs(location_type);
        CREATE INDEX IF NOT EXISTS idx_jobs_employment_type ON jobs(employment_type);
        CREATE INDEX IF NOT EXISTS idx_jobs_salary_min ON jobs(salary_min);
        CREATE INDEX IF NOT EXISTS idx_jobs_salary_max ON jobs(salary_max);
        CREATE INDEX IF NOT EXISTS idx_jobs_experience_min ON jobs(experience_min);
        CREATE INDEX IF NOT EXISTS idx_jobs_experience_max ON jobs(experience_max);
        CREATE INDEX IF NOT EXISTS idx_jobs_posted_at ON jobs(posted_at);
        CREATE INDEX IF NOT EXISTS idx_jobs_is_active ON jobs(is_active);
        CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs(source);
        CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys(key_hash);
        CREATE INDEX IF NOT EXISTS idx_api_usage_api_key_id ON api_usage(api_key_id);
        CREATE INDEX IF NOT EXISTS idx_api_usage_timestamp ON api_usage(timestamp);
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        CREATE INDEX IF NOT EXISTS idx_user_activity_user_id ON user_activity(user_id);
        CREATE INDEX IF NOT EXISTS idx_user_activity_timestamp ON user_activity(timestamp);
        CREATE INDEX IF NOT EXISTS idx_user_activity_action ON user_activity(action);
        CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
    """)

    # Standalone FTS table (no content sync — we manage inserts ourselves)
    try:
        await db.execute("""
            CREATE VIRTUAL TABLE jobs_fts USING fts5(
                job_id,
                title,
                description,
                skills,
                location,
                company_name
            )
        """)
    except Exception:
        pass  # Already exists

    await db.commit()


async def rebuild_fts():
    """Rebuild the FTS index from jobs data."""
    db = await get_db()
    await db.execute("DELETE FROM jobs_fts")
    await db.execute("""
        INSERT INTO jobs_fts(job_id, title, description, skills, location, company_name)
        SELECT j.id, j.title, j.description, j.skills, j.location, c.name
        FROM jobs j
        LEFT JOIN companies c ON j.company_id = c.id
        WHERE j.is_active = 1
    """)
    await db.commit()
