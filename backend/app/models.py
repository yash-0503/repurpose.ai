from pydantic import BaseModel
from typing import Optional,List
from datetime import datetime

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
