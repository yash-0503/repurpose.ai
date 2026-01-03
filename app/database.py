import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid

load_dotenv()

DATABASE_URL = os.getenv("NEON_DATABASE_URL")
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    connect_args={"ssl": "require"},
) if DATABASE_URL else None

async_session = async_sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
) if engine else None


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    google_id = Column(String(255), unique=True, nullable=False)
    email = Column(String(255), nullable=False)
    name = Column(String(255))
    avatar_url = Column(Text)
    default_style_id = Column(UUID(as_uuid=True), ForeignKey("styles.id", ondelete="SET NULL"), nullable=True)
    # API Keys stored as encrypted JSON: {"openai": "encrypted...", "anthropic": "encrypted..."}
    api_keys = Column(JSONB, default=dict)
    default_provider = Column(String(50), default="gemini")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Style(Base):
    __tablename__ = "styles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    style_guide = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Blog(Base):
    __tablename__ = "blogs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(500))
    youtube_url = Column(Text)
    content = Column(Text, nullable=False)
    style_id = Column(UUID(as_uuid=True), ForeignKey("styles.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


async def get_db():
    """Dependency for getting database session"""
    if async_session is None:
        raise Exception("Database not configured. Set NEON_DATABASE_URL in .env")
    async with async_session() as session:
        yield session


async def init_db():
    """Create all tables"""
    if engine:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

