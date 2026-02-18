"""Configuration management for AgentJobs."""

import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./agentjobs.db"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    
    # API
    api_prefix: str = "/api/v1"
    default_page_size: int = 20
    max_page_size: int = 100
    
    # Rate Limiting
    free_rate_limit: int = 100
    pro_rate_limit: int = 1000
    enterprise_rate_limit: int = 10000
    
    # Scraping
    scrape_interval_hours: int = 6
    max_concurrent_scrapes: int = 5

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
