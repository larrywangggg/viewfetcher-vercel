"""Database helpers for the Vercel deployment.

Supports SQLite for local development and any SQLAlchemy compatible
connection string via the `DATABASE_URL` environment variable in production.
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import datetime
from typing import Iterator, Optional

from sqlalchemy import Column, DateTime, Float, Integer, String, UniqueConstraint, create_engine, select
from sqlalchemy.orm import Session, declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./kol_results.sqlite3")

# SQLite needs special arguments when used with SQLAlchemy in multithreaded envs.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    future=True,
    pool_pre_ping=True,
    connect_args=connect_args,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True, expire_on_commit=False)
Base = declarative_base()


class Result(Base):
    __tablename__ = "results"
    __table_args__ = (
        UniqueConstraint("url", name="uq_results_url"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    platform = Column(String(32), nullable=False)
    url = Column(String(512), nullable=False)
    creator = Column(String(255))
    campaign_id = Column(String(255))
    posted_at = Column(DateTime(timezone=True))
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    engagement_rate = Column(Float, default=0.0)
    notes = Column(String(512))
    fetched_at = Column(DateTime(timezone=True), default=datetime.utcnow)


def init_db() -> None:
    """Create database tables if they are missing."""
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_session() -> Iterator[Session]:
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def upsert_result(session: Session, payload: dict) -> Result:
    """Insert or update a result row keyed by URL."""
    stmt = select(Result).where(Result.url == payload["url"])
    existing: Optional[Result] = session.execute(stmt).scalar_one_or_none()

    now = datetime.utcnow()
    if existing:
        existing.platform = payload.get("platform", existing.platform)
        existing.views = payload.get("views", existing.views)
        existing.likes = payload.get("likes", existing.likes)
        existing.comments = payload.get("comments", existing.comments)
        existing.engagement_rate = payload.get("engagement_rate", existing.engagement_rate)
        existing.campaign_id = payload.get("campaign_id", existing.campaign_id)
        existing.notes = payload.get("notes", existing.notes)

        creator = payload.get("creator")
        if creator:
            existing.creator = creator

        posted_at = payload.get("posted_at")
        if posted_at:
            existing.posted_at = posted_at

        existing.fetched_at = now
        return existing

    record = Result(
        platform=payload.get("platform", ""),
        url=payload["url"],
        creator=payload.get("creator"),
        campaign_id=payload.get("campaign_id"),
        posted_at=payload.get("posted_at"),
        views=payload.get("views", 0),
        likes=payload.get("likes", 0),
        comments=payload.get("comments", 0),
        engagement_rate=payload.get("engagement_rate", 0.0),
        notes=payload.get("notes"),
        fetched_at=now,
    )
    session.add(record)
    return record

