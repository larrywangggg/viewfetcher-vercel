"""Core utilities shared across the Vercel deployment."""

from .db import Result, get_session, init_db

__all__ = ["Result", "get_session", "init_db"]
