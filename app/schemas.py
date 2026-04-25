"""
Pydantic schemas for input validation - prevents injection attacks.
"""
from pydantic import BaseModel, validator, Field
from typing import Optional
import re


class ImageUploadRequest(BaseModel):
    """Schema for image upload request."""
    
    filename: str = Field(..., min_length=1, max_length=255)
    file_size: int = Field(..., gt=0, le=10_000_000)  # Max 10MB
    content_type: str
    
    @validator('filename')
    def validate_filename(cls, v):
        # Only allow safe characters
        if not re.match(r'^[\w\-\.]+$', v):
            raise ValueError('Invalid filename characters')
        return v
    
    @validator('content_type')
    def validate_content_type(cls, v):
        allowed = {'image/jpeg', 'image/png', 'image/gif', 'image/webp'}
        if v not in allowed:
            raise ValueError(f'Invalid file type. Allowed: {allowed}')
        return v


class GenerateAltTextRequest(BaseModel):
    """Schema for alt text generation request."""
    
    image_id: str = Field(..., min_length=1, max_length=100)
    context: Optional[str] = Field(None, max_length=1000)
    
    @validator('image_id')
    def validate_image_id(cls, v):
        # Sanitize to prevent injection
        if not re.match(r'^[\w\-]+$', v):
            raise ValueError('Invalid image ID format')
        return v
    
    @validator('context')
    def validate_context(cls, v):
        if v:
            # Remove potential XSS characters
            return re.sub(r'[<>"\';]', '', v)
        return v


class UserRegisterRequest(BaseModel):
    """Schema for user registration."""
    
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    name: str = Field(..., min_length=2, max_length=100)
    
    @validator('email')
    def validate_email(cls, v):
        v = v.lower().strip()
        if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', v):
            raise ValueError('Invalid email format')
        return v
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain a number')
        return v
    
    @validator('name')
    def validate_name(cls, v):
        return re.sub(r'[<>"\';]', '', v.strip())
