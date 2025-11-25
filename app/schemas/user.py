from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional


# 用户相关Schemas
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)
    role: str = Field(default="admin", pattern="^(admin|super_admin)$")


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None


class UserProfileUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=6)


class UserResponse(UserBase):
    id: int
    role: str
    is_active: bool
    created_by: Optional[int]
    created_at: datetime
    updated_at: datetime
    is_2fa_enabled: bool = False
    
    class Config:
        from_attributes = True


# 认证相关Schemas
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    requires_2fa: bool = False  # 是否需要2FA验证


class TokenData(BaseModel):
    user_id: Optional[int] = None


class LoginRequest(BaseModel):
    username: str
    password: str
    totp_code: Optional[str] = None  # 2FA验证码（可选）

