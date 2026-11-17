from datetime import datetime
from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field

CEFRLevel = Literal["A1", "A2", "B1", "B2", "C1", "C2"]


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: Optional[str] = Field(default=None, max_length=100)
    native_language: str = Field(default="vi", max_length=10)
    target_language: str = Field(default="en", max_length=10)
    cefr_level: CEFRLevel = "B1"


class UserUpdate(BaseModel):
    display_name: Optional[str] = Field(default=None, max_length=100)
    native_language: Optional[str] = Field(default=None, max_length=10)
    target_language: Optional[str] = Field(default=None, max_length=10)
    cefr_level: Optional[CEFRLevel] = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    display_name: Optional[str] = None
    native_language: Optional[str] = None
    target_language: Optional[str] = None
    cefr_level: Optional[str] = None
    is_active: Optional[bool] = None
    created_at: Optional[datetime] = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
