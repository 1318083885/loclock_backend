from pydantic import BaseModel, HttpUrl, Field
from datetime import datetime
from typing import Optional
from decimal import Decimal


# 短链接相关Schemas
class LinkBase(BaseModel):
    title: Optional[str] = None
    target_url: HttpUrl
    center_lat: float = Field(..., ge=-90, le=90, description="中心点纬度")
    center_lng: float = Field(..., ge=-180, le=180, description="中心点经度")
    radius_meters: int = Field(..., gt=0, description="允许访问的半径（米）")
    location_name: Optional[str] = Field(None, max_length=255, description="位置名称")
    contact_wechat: Optional[str] = Field(None, max_length=100, description="管理员微信号")
    expire_at: Optional[datetime] = Field(None, description="过期时间")
    max_visits: Optional[int] = Field(None, ge=0, description="最大访问次数")


class LinkCreate(LinkBase):
    short_code: Optional[str] = Field(None, min_length=3, max_length=50, description="自定义短链接代码（可选）")


class LinkUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=100)
    target_url: Optional[HttpUrl] = None
    center_lat: Optional[float] = Field(None, ge=-90, le=90)
    center_lng: Optional[float] = Field(None, ge=-180, le=180)
    radius_meters: Optional[int] = Field(None, gt=0)
    location_name: Optional[str] = Field(None, max_length=255)
    contact_wechat: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None
    expire_at: Optional[datetime] = Field(None)
    max_visits: Optional[int] = Field(None, ge=0)


class LinkResponse(LinkBase):
    id: int
    short_code: str
    is_active: bool
    created_by: int
    visit_count: int
    success_count: int
    denied_count: int
    created_at: datetime
    updated_at: datetime
    creator_username: Optional[str] = None
    is_banned: bool = False
    
    class Config:
        from_attributes = True


class LinkStats(BaseModel):
    """短链接统计信息"""
    total_visits: int
    successful_visits: int
    denied_visits: int
    success_rate: float  # 成功率百分比


# 访问验证相关Schemas
class LocationVerifyRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90, description="访问者纬度")
    longitude: float = Field(..., ge=-180, le=180, description="访问者经度")


class LocationVerifyResponse(BaseModel):
    allowed: bool
    target_url: Optional[str] = None
    distance: float
    radius: int
    message: Optional[str] = None
    contact_wechat: Optional[str] = None  # 管理员微信号
    title: Optional[str] = None  # 链接标题


class PublicLinkInfo(BaseModel):
    """公开的链接信息（无需验证位置）"""
    short_code: str
    title: Optional[str] = None
    is_active: bool
    location_name: Optional[str] = None

