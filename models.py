"""Pydantic models for AgentJobs API."""

from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime


# ── Company Models ──────────────────────────────────────────────

class CompanyBase(BaseModel):
    name: str
    website: Optional[str] = None
    careers_url: Optional[str] = None
    industry: Optional[str] = None
    size: Optional[str] = None
    logo_url: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None


class CompanySummary(BaseModel):
    name: str
    industry: Optional[str] = None
    size: Optional[str] = None


class CompanyResponse(CompanyBase):
    id: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    active_job_count: Optional[int] = None


class CompanyListResponse(BaseModel):
    count: int
    total: int
    companies: List[CompanyResponse]


# ── Job Models ──────────────────────────────────────────────────

class JobSummary(BaseModel):
    id: str
    title: str
    company: CompanySummary
    location: Optional[str] = None
    location_type: Optional[str] = None
    salary_range: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    experience: Optional[str] = None
    skills: List[str] = []
    category: Optional[str] = None
    employment_type: Optional[str] = None
    description_short: Optional[str] = None
    posted_at: Optional[str] = None
    apply_url: Optional[str] = None
    source: Optional[str] = None


class JobDetail(JobSummary):
    description: Optional[str] = None
    experience_min: Optional[int] = None
    experience_max: Optional[int] = None
    salary_text: Optional[str] = None
    source_id: Optional[str] = None
    scraped_at: Optional[str] = None
    is_active: bool = True


class JobListResponse(BaseModel):
    count: int
    total: int
    query_time_ms: float
    jobs: List[JobSummary]


# ── Agent Search Models ─────────────────────────────────────────

class AgentSearchRequest(BaseModel):
    resume_text: Optional[str] = None
    skills: Optional[List[str]] = None
    experience_years: Optional[int] = None
    preferred_locations: Optional[List[str]] = None
    salary_min: Optional[int] = None
    job_preferences: Optional[str] = None
    limit: int = Field(default=20, le=100, ge=1)


class MatchedJob(BaseModel):
    id: str
    title: str
    company: str
    location: Optional[str] = None
    salary_range: Optional[str] = None
    match_score: int
    match_reasons: List[str]
    description_short: Optional[str] = None
    apply_url: Optional[str] = None
    skills_match: List[str] = []
    skills_missing: List[str] = []


class AgentSearchResponse(BaseModel):
    session_id: str
    query_time_ms: float
    match_count: int
    jobs: List[MatchedJob]


# ── Auth Models ─────────────────────────────────────────────────

class AuthRegisterRequest(BaseModel):
    email: str
    name: Optional[str] = None


class AuthRegisterResponse(BaseModel):
    api_key: str
    message: str


class UsageResponse(BaseModel):
    api_key_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    tier: str
    rate_limit: int
    total_requests: int
    requests_today: int
    requests_this_hour: int
    created_at: Optional[str] = None


# ── Stats Models ────────────────────────────────────────────────

class CategoryCount(BaseModel):
    category: str
    count: int


class StatsResponse(BaseModel):
    total_jobs: int
    total_companies: int
    total_active_jobs: int
    categories: List[CategoryCount]
    locations: List[dict]
    updated_at: str


class TrendingSkill(BaseModel):
    skill: str
    count: int
    percentage: float


class TrendingSkillsResponse(BaseModel):
    skills: List[TrendingSkill]
    total_jobs_analyzed: int


# ── User Auth Models ────────────────────────────────────────────

class SignupRequest(BaseModel):
    email: str
    password: str = Field(..., min_length=6)
    name: Optional[str] = None
    company: Optional[str] = None
    role: str = Field(default="user")


class LoginRequest(BaseModel):
    email: str
    password: str


class UserProfile(BaseModel):
    id: str
    email: str
    name: Optional[str] = None
    company: Optional[str] = None
    role: str = "user"
    avatar_url: Optional[str] = None
    is_active: bool = True
    last_login: Optional[str] = None
    login_count: int = 0
    created_at: Optional[str] = None


class AuthResponse(BaseModel):
    user: UserProfile
    token: str
    message: str


class MessageResponse(BaseModel):
    message: str


# ── Admin Dashboard Models ──────────────────────────────────────

class DashboardStats(BaseModel):
    total_users: int
    new_users_today: int
    new_users_week: int
    new_users_month: int
    total_searches: int
    total_agent_matches: int
    active_users_7d: int
    top_searches: List[dict] = []
    popular_skills: List[dict] = []
    user_growth: List[dict] = []


class AdminUserSummary(BaseModel):
    id: str
    email: str
    name: Optional[str] = None
    company: Optional[str] = None
    role: str
    is_active: bool
    last_login: Optional[str] = None
    login_count: int = 0
    total_searches: int = 0
    created_at: Optional[str] = None


class AdminUserList(BaseModel):
    count: int
    total: int
    users: List[AdminUserSummary]


class ActivityEntry(BaseModel):
    id: int
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    action: str
    details: Optional[str] = None
    ip_address: Optional[str] = None
    timestamp: Optional[str] = None


class ActivityFeed(BaseModel):
    count: int
    total: int
    activities: List[ActivityEntry]


class MetricsResponse(BaseModel):
    dau: int
    wau: int
    mau: int
    retention_rate: float
    searches_per_user: float
    most_active_hours: List[dict] = []
    growth_rate: float
