import os
from datetime import datetime, timezone
from sqlalchemy import create_engine, String, Integer, Float, Boolean, DateTime, JSON, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

DATABASE_URL=os.getenv("DATABASE_URL", "sqlite:///./pikabora.db")
# Supabase/Render provide postgresql:// URLs; SQLAlchemy needs postgresql+psycopg://
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {"sslmode": "require"} if "supabase" in DATABASE_URL else {}
engine=create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal=sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase): pass

def now(): return datetime.now(timezone.utc)

class UserState(Base):
    __tablename__="user_states"
    id: Mapped[str]=mapped_column(String(128), primary_key=True)
    country: Mapped[str]=mapped_column(String(2), index=True)
    language: Mapped[str]=mapped_column(String(10), default="en")
    pregnancy_week: Mapped[int]=mapped_column(Integer)
    recent_food_groups: Mapped[list]=mapped_column(JSON, default=list)
    dietary_restrictions: Mapped[list]=mapped_column(JSON, default=list)
    allergies: Mapped[list]=mapped_column(JSON, default=list)
    supplement_status: Mapped[str|None]=mapped_column(Text, nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now, onupdate=now)

class RecommendationAudit(Base):
    __tablename__="recommendation_audits"
    id: Mapped[int]=mapped_column(Integer, primary_key=True, autoincrement=True)
    user_state_id: Mapped[str]=mapped_column(String(128), index=True)
    request_json: Mapped[dict]=mapped_column(JSON)
    response_json: Mapped[dict]=mapped_column(JSON)
    mode: Mapped[str]=mapped_column(String(32))
    data_confidence: Mapped[str]=mapped_column(String(64))
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now, index=True)

class Feedback(Base):
    __tablename__="feedback"
    id: Mapped[int]=mapped_column(Integer, primary_key=True, autoincrement=True)
    user_state_id: Mapped[str]=mapped_column(String(128), index=True)
    recommendation_id: Mapped[str]=mapped_column(String(128), index=True)
    prepared: Mapped[bool]=mapped_column(Boolean)
    barrier_reason: Mapped[str|None]=mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)

def init_db(): Base.metadata.create_all(bind=engine)
