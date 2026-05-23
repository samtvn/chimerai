"""
Load environment variables from apps/api/.env before any other module is imported.

Import this module first in main.py to ensure all env vars are available
at import time (e.g. DATABASE_URL for SQLAlchemy engine creation).
"""

from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")
