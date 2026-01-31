import os
import asyncio
from contextlib import asynccontextmanager
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from app.services.audio_downloader import download_audio as download_audio_service, AudioDownloadError, cleanup_audio_file
from app.services.transcriber import transcribe_audio as transcribe_audio_service, TranscriptionError
from app.services.style_analyzer import analyze_style, StyleAnalysisError
from app.services.generate_blog_from_style import generate_blog_from_transcript
from app.database import get_db, User, Style, Blog, init_db
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

# ============ Pydantic Models ============

class DownloadRequest(BaseModel):
    url: str

class DownloadResponse(BaseModel):
    status: str
    audio_path: str
    title: str

class TranscribeRequest(BaseModel):
    audio_path: str

class TranscribeResponse(BaseModel):
    status: str
    language: str
    text: str

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

# User models
class UserResponse(BaseModel):
    id: str
    email: str
    name: Optional[str]
    avatar_url: Optional[str]
    
    class Config:
        from_attributes = True

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
    # Startup
    try:
        await init_db()
        print("✅ Database initialized")
    except Exception as e:
        print(f"⚠️ Database initialization skipped: {e}")
    
    yield  # App runs here
    
    # Shutdown (if needed)
    print("👋 Shutting down...")

# ============ FastAPI App ============

app = FastAPI(
    title="Repurpose.ai API",
    description="Convert YouTube videos into blog posts with optional style matching",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
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
    from app.auth import GOOGLE_CLIENT_ID
    
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=500,
            detail="Google OAuth not configured. Add GOOGLE_CLIENT_ID to .env file"
        )
    
    redirect_uri = str(request.url_for("google_callback"))
    print(f"🔐 OAuth redirect URI: {redirect_uri}")
    oauth_url = get_google_oauth_url(redirect_uri)
    print(f"🔗 OAuth URL: {oauth_url[:100]}...")
    return {"auth_url": oauth_url}

@app.get("/auth/callback")
async def google_callback(
    code: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Handle Google OAuth callback"""
    redirect_uri = str(request.url_for("google_callback"))
    
    # Exchange code for tokens
    tokens = await get_google_tokens(code, redirect_uri)
    
    # Get user info from Google
    google_user = await get_google_user_info(tokens["access_token"])
    
    # Create or update user in database
    user = await get_or_create_user(db, google_user)
    
    # Create JWT token
    access_token = create_access_token({"sub": str(user.id)})
    
    # Redirect to frontend with token (use path that won't be proxied)
    frontend_url = f"http://localhost:5173/?token={access_token}"
    return RedirectResponse(url=frontend_url)

@app.get("/auth/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user_required)):
    """Get current authenticated user"""
    return UserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url
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
    """Create a new style"""
    style = Style(
        user_id=user.id,
        name=style_data.name,
        style_guide=style_data.style_guide
    )
    db.add(style)
    await db.commit()
    await db.refresh(style)
    
    return StyleResponse(
        id=str(style.id),
        name=style.name,
        style_guide=style.style_guide,
        created_at=style.created_at
    )

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

@app.post("/api/download", response_model=DownloadResponse)
async def download_audio(
    request: DownloadRequest,
    user: User = Depends(get_current_user_required)
):
    """Download audio from a YouTube URL to temporary storage (requires authentication)"""
    try:
        print(f"📥 Downloading audio from: {request.url} (user: {user.email})")
        audio_path, title = await asyncio.to_thread(download_audio_service, request.url, use_temp=True)
        
        return DownloadResponse(
            status="success",
            audio_path=audio_path,
            title=title
        )
    except AudioDownloadError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")


@app.post("/api/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(
    request: TranscribeRequest,
    user: User = Depends(get_current_user_required)
):
    """Transcribe an audio file using Whisper and cleanup temp file (requires authentication)"""
    try:
        print(f"🎙️ Transcribing audio: {request.audio_path} (user: {user.email})")
        
        # Transcribe audio
        result = await asyncio.to_thread(transcribe_audio_service, request.audio_path)
        
        # Cleanup temp file after transcription
        cleanup_audio_file(request.audio_path)
        
        return TranscribeResponse(
            status="success",
            language=result.get('language', 'unknown'),
            text=result['text']
        )
    except TranscriptionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


@app.post("/api/analyze-style", response_model=StyleAnalyzeResponse)
async def analyze_writing_style(
    request: StyleAnalyzeRequest,
    user: User = Depends(get_current_user_required)
):
    """Analyze writing style from reference text (requires authentication)"""
    try:
        print(f"✍️ Analyzing writing style... (user: {user.email})")
        
        # Run in thread to avoid asyncio.run() conflict with FastAPI's event loop
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
    try:
        format_label = {
            "blog": "📝 Blog",
            "linkedin": "💼 LinkedIn Post",
            "twitter": "🐦 Twitter/X"
        }.get(request.output_format, "📝 Blog")
        print(f"{format_label} - Generating content...")
        
        if not request.transcript or len(request.transcript.strip()) < 50:
            raise HTTPException(
                status_code=400,
                detail="Transcript must be at least 50 characters"
            )
        
        # Get style guide - either from request or from saved style
        style = ""
        style_id = None
        
        # Option 1: User selected a saved style
        if request.style_id:
            result = await db.execute(
                select(Style).where(Style.id == request.style_id, Style.user_id == user.id)
            )
            saved_style = result.scalar_one_or_none()
            if saved_style:
                style = saved_style.style_guide
                style_id = saved_style.id
                print(f"📌 Using saved style: {saved_style.name}")
        
        # Option 2: User provided custom text to analyze - analyze and save as "My Style"
        elif request.style_guide and len(request.style_guide.strip()) >= 100:
            print("✍️ Analyzing custom style text...")
            analyzed_style = await asyncio.to_thread(analyze_style, request.style_guide)
            style = analyzed_style
            
            # Save as "My Style"
            # Check if user already has "My Style"
            result = await db.execute(
                select(Style).where(Style.user_id == user.id, Style.name == "My Style")
            )
            existing_style = result.scalar_one_or_none()
            
            if existing_style:
                # Update existing style
                existing_style.style_guide = analyzed_style
                style_id = existing_style.id
                print("🔄 Updated existing 'My Style'")
            else:
                # Create new style
                new_style = Style(
                    user_id=user.id,
                    name="My Style",
                    style_guide=analyzed_style
                )
                db.add(new_style)
                await db.flush()
                style_id = new_style.id
                print("✨ Saved new 'My Style'")
        
        # Run in thread to avoid asyncio.run() conflict with FastAPI's event loop
        blog_content = await asyncio.to_thread(
            generate_blog_from_transcript, 
            request.transcript, 
            style,
            request.output_format or "blog",
            request.output_option
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
        print(f"💾 Blog auto-saved with ID: {blog_id}")
        
        return GenerateBlogResponse(
            status="success",
            blog_content=blog_content,
            blog_id=blog_id
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Blog generation failed: {str(e)}")
