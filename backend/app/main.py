import os
import logging
import asyncio
from contextlib import asynccontextmanager
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.audio_downloader import fetch_transcript as fetch_transcript_service, TranscriptFetchError
from app.services.style_analyzer import analyze_style, StyleAnalysisError
from app.services.generate_blog_from_style import generate_blog_from_transcript
from app.database import get_db, User, Style, Blog, init_db
from app.rate_limit import check_rate_limit
from app.auth import (
    get_current_user, 
    get_current_user_required,
    get_google_oauth_url,
    get_google_tokens,
    get_google_user_info,
    get_or_create_user,
    create_access_token,
    GOOGLE_CLIENT_ID
)

logger = logging.getLogger(__name__)

# ============ Pydantic Models ============

class TranscriptRequest(BaseModel):
    url: str

class TranscriptResponse(BaseModel):
    status: str
    text: str
    title: str
    language: str

class StyleAnalyzeRequest(BaseModel):
    reference_text: str

class StyleAnalyzeResponse(BaseModel):
    status: str
    style_guide: str

class GenerateBlogRequest(BaseModel):
    transcript: str
    style_guide: Optional[str] = None
    youtube_url: Optional[str] = None
    title: Optional[str] = None
    style_id: Optional[str] = None
    output_format: Optional[str] = "blog"  # blog, linkedin, twitter
    output_option: Optional[str] = None    # linkedin: short/medium/long, twitter: single/thread

class GenerateBlogResponse(BaseModel):
    status: str
    blog_content: str
    blog_id: Optional[str] = None


# Style models
class StyleCreate(BaseModel):
    name: str
    style_guide: str

class StyleResponse(BaseModel):
    id: str
    name: str
    style_guide: str
    created_at: datetime
    
    class Config:
        from_attributes = True

# User models
class UserResponse(BaseModel):
    id: str
    email: str
    name: Optional[str]
    avatar_url: Optional[str]
    styles: List[StyleResponse] = []
    default_style_id: Optional[str] = None
    
    class Config:
        from_attributes = True


# Blog models
class BlogResponse(BaseModel):
    id: str
    title: Optional[str]
    youtube_url: Optional[str]
    content: str
    style_id: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

# ============ Lifespan ============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events"""
    required_vars = ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "JWT_SECRET", "NEON_DATABASE_URL", "FRONTEND_URL"]
    missing = [v for v in required_vars if not os.getenv(v)]
    if missing:
        logger.warning(f"Missing environment variables: {', '.join(missing)}")
    
    try:
        await init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.warning(f"Database initialization skipped: {e}")
    
    yield
    
    logger.info("Shutting down...")

# ============ FastAPI App ============

app = FastAPI(
    title="Repurpose.ai API",
    description="Convert YouTube videos into blog posts with optional style matching",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware for React frontend
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ Health Check ============

@app.get("/api/health")
async def health_check():
    """Health check endpoint for frontend connectivity"""
    return {"status": "healthy", "service": "repurpose.ai"}

# ============ Auth Endpoints ============

@app.get("/auth/google")
async def google_auth(request: Request):
    """Initiate Google OAuth flow"""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=500,
            detail="Google OAuth not configured. Add GOOGLE_CLIENT_ID to .env file"
        )
    
    redirect_uri = str(request.url_for("google_callback"))
    oauth_url = get_google_oauth_url(redirect_uri)
    return {"auth_url": oauth_url}

@app.get("/auth/callback")
async def google_callback(
    code: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Handle Google OAuth callback"""
    try:
        redirect_uri = str(request.url_for("google_callback"))
        logger.info(f"OAuth callback - redirect_uri: {redirect_uri}")
        
        tokens = await get_google_tokens(code, redirect_uri)
        
        google_user = await get_google_user_info(tokens["access_token"])
        logger.info(f"OAuth callback - user: {google_user.get('email')}")
        
        user = await get_or_create_user(db, google_user)
        
        access_token = create_access_token({"sub": str(user.id)})
        
        FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
        frontend_url = f"{FRONTEND_URL}/?token={access_token}"
        return RedirectResponse(url=frontend_url)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("OAuth callback failed")
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")

async def _get_user_styles(db: AsyncSession, user: User) -> List[Style]:
    result = await db.execute(
        select(Style).where(Style.user_id == user.id).order_by(Style.created_at.desc())
    )
    return list(result.scalars().all())


def _style_to_response(style: Style) -> StyleResponse:
    return StyleResponse(
        id=str(style.id),
        name=style.name,
        style_guide=style.style_guide,
        created_at=style.created_at,
    )


async def _save_user_style(
    db: AsyncSession,
    user: User,
    name: str,
    style_guide: str,
) -> Style:
    style = Style(user_id=user.id, name=name, style_guide=style_guide)
    db.add(style)
    await db.flush()
    user.default_style_id = style.id
    await db.commit()
    await db.refresh(style)
    return style


@app.get("/auth/me", response_model=UserResponse)
async def get_me(
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
):
    """Get current authenticated user with saved styles"""
    styles = await _get_user_styles(db, user)
    return UserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
        styles=[_style_to_response(s) for s in styles],
        default_style_id=str(user.default_style_id) if user.default_style_id else None,
    )

@app.post("/auth/logout")
async def logout():
    """Logout (client-side token removal)"""
    return {"status": "success", "message": "Logged out"}

# ============ Styles Endpoints ============

@app.get("/api/styles", response_model=List[StyleResponse])
async def list_styles(
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """List all styles for the current user"""
    result = await db.execute(
        select(Style).where(Style.user_id == user.id).order_by(Style.created_at.desc())
    )
    styles = result.scalars().all()
    return [
        StyleResponse(
            id=str(s.id),
            name=s.name,
            style_guide=s.style_guide,
            created_at=s.created_at
        ) for s in styles
    ]

@app.post("/api/styles", response_model=StyleResponse)
async def create_style(
    style_data: StyleCreate,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """Save a writing style (raw sample text, no analysis)."""
    check_rate_limit(
        key=f"style_save:{user.id}",
        max_calls=5,
        window_sec=600,
        label="style saves",
    )

    name = style_data.name.strip()
    style_guide = style_data.style_guide.strip()

    if not name:
        raise HTTPException(status_code=400, detail="Style name is required")
    if len(name) > 100:
        raise HTTPException(status_code=400, detail="Style name must be 100 characters or less")
    if len(style_guide) < 50:
        raise HTTPException(
            status_code=400,
            detail="Style sample must be at least 50 characters",
        )

    try:
        saved = await _save_user_style(db, user, name, style_guide)
        logger.info(f"Style saved: {saved.name} ({saved.id}) for user {user.email}")
        return _style_to_response(saved)
    except Exception as e:
        logger.exception("Style save failed")
        raise HTTPException(status_code=500, detail=f"Style save failed: {str(e)}")

@app.delete("/api/styles/{style_id}")
async def delete_style(
    style_id: str,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """Delete a style"""
    result = await db.execute(
        select(Style).where(Style.id == style_id, Style.user_id == user.id)
    )
    style = result.scalar_one_or_none()
    
    if not style:
        raise HTTPException(status_code=404, detail="Style not found")
    
    await db.delete(style)
    await db.commit()
    
    return {"status": "success", "message": "Style deleted"}

# ============ Blogs Endpoints ============

@app.get("/api/blogs", response_model=List[BlogResponse])
async def list_blogs(
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """List all blogs for the current user"""
    result = await db.execute(
        select(Blog).where(Blog.user_id == user.id).order_by(Blog.created_at.desc())
    )
    blogs = result.scalars().all()
    return [
        BlogResponse(
            id=str(b.id),
            title=b.title,
            youtube_url=b.youtube_url,
            content=b.content,
            style_id=str(b.style_id) if b.style_id else None,
            created_at=b.created_at
        ) for b in blogs
    ]

@app.get("/api/blogs/{blog_id}", response_model=BlogResponse)
async def get_blog(
    blog_id: str,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific blog"""
    result = await db.execute(
        select(Blog).where(Blog.id == blog_id, Blog.user_id == user.id)
    )
    blog = result.scalar_one_or_none()
    
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")
    
    return BlogResponse(
        id=str(blog.id),
        title=blog.title,
        youtube_url=blog.youtube_url,
        content=blog.content,
        style_id=str(blog.style_id) if blog.style_id else None,
        created_at=blog.created_at
    )

@app.delete("/api/blogs/{blog_id}")
async def delete_blog(
    blog_id: str,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """Delete a blog"""
    result = await db.execute(
        select(Blog).where(Blog.id == blog_id, Blog.user_id == user.id)
    )
    blog = result.scalar_one_or_none()
    
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")
    
    await db.delete(blog)
    await db.commit()
    
    return {"status": "success", "message": "Blog deleted"}

# ============ Core Endpoints ============

@app.post("/api/transcript", response_model=TranscriptResponse)
async def get_transcript(
    request: TranscriptRequest,
    user: User = Depends(get_current_user_required)
):
    """Fetch transcript from a YouTube video using captions (requires authentication)"""
    check_rate_limit(
        key=f"transcript:{user.id}",
        max_calls=10,
        window_sec=600,
        label="transcript requests",
    )
    try:
        logger.info(f"Fetching transcript for: {request.url} (user: {user.email})")
        result = await asyncio.to_thread(fetch_transcript_service, request.url)

        return TranscriptResponse(
            status="success",
            text=result["text"],
            title=result["title"],
            language=result["language"],
        )
    except TranscriptFetchError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcript fetch failed: {str(e)}")


@app.post("/api/analyze-style", response_model=StyleAnalyzeResponse)
async def analyze_writing_style(
    request: StyleAnalyzeRequest,
    user: User = Depends(get_current_user_required)
):
    """Analyze writing style from reference text (requires authentication)"""
    try:
        logger.info(f"Analyzing writing style (user: {user.email})")
        style_guide = await asyncio.to_thread(analyze_style, request.reference_text)
        
        return StyleAnalyzeResponse(
            status="success",
            style_guide=style_guide
        )
    except StyleAnalysisError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Style analysis failed: {str(e)}")


@app.post("/api/generate-blog", response_model=GenerateBlogResponse)
async def generate_blog(
    request: GenerateBlogRequest,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """Generate content from transcript with platform-specific formatting (requires authentication)"""
    check_rate_limit(
        key=f"generate:{user.id}",
        max_calls=10,
        window_sec=600,
        label="content generations",
    )
    try:
        logger.info(f"Generating {request.output_format or 'blog'} content (user: {user.email})")
        
        if not request.transcript or len(request.transcript.strip()) < 50:
            raise HTTPException(
                status_code=400,
                detail="Transcript must be at least 50 characters"
            )
        
        style = ""
        style_id = None
        
        if request.style_id:
            result = await db.execute(
                select(Style).where(Style.id == request.style_id, Style.user_id == user.id)
            )
            saved_style = result.scalar_one_or_none()
            if not saved_style:
                raise HTTPException(status_code=404, detail="Selected style not found")
            style = saved_style.style_guide
            style_id = saved_style.id
            user.default_style_id = saved_style.id
            await db.commit()
            logger.info(f"Using saved style: {saved_style.name} ({saved_style.id})")
        
        blog_content = await asyncio.to_thread(
            generate_blog_from_transcript, 
            request.transcript, 
            style,
            request.output_format or "blog",
            request.output_option,
            request.youtube_url,
        )
        
        # Auto-save blog (user is always authenticated now)
        blog = Blog(
            user_id=user.id,
            title=request.title,
            youtube_url=request.youtube_url,
            content=blog_content,
            style_id=style_id
        )
        db.add(blog)
        await db.commit()
        await db.refresh(blog)
        blog_id = str(blog.id)
        logger.info(f"Blog saved: {blog_id}")
        
        return GenerateBlogResponse(
            status="success",
            blog_content=blog_content,
            blog_id=blog_id
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Blog generation failed")
        raise HTTPException(status_code=500, detail=f"Blog generation failed: {str(e)}")
