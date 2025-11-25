from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base


class User(Base):
    """用户模型"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, index=True)  # 'super_admin' 或 'admin'
    is_active = Column(Boolean, default=True, nullable=False)
    
    # 创建者ID（超级管理员创建的普通管理员）
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # 双因素认证
    totp_secret = Column(String(200), nullable=True)  # TOTP密钥（加密后存储）
    is_2fa_enabled = Column(Boolean, default=False, nullable=False)  # 是否启用2FA
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"
