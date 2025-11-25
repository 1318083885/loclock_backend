from pydantic import BaseModel, Field, IPvAnyAddress
from datetime import datetime
from typing import Optional

class BlockedIpBase(BaseModel):
    ip_address: str = Field(..., description="被封禁的IP地址")
    reason: Optional[str] = Field(None, max_length=255, description="封禁原因")

class BlockedIpCreate(BlockedIpBase):
    pass

class BlockedIpResponse(BlockedIpBase):
    id: int
    created_by: int
    created_at: datetime

    class Config:
        from_attributes = True
