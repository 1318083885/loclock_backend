from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Numeric
from sqlalchemy.sql import func
from app.core.database import Base


class Link(Base):
    """短链接模型"""
    __tablename__ = "links"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=True, comment="链接标题")
    short_code = Column(String(20), unique=True, index=True)
    target_url = Column(String(500), nullable=False)
    
    # 地理位置限制
    center_lat = Column(Numeric(10, 8), nullable=False)  # 中心点纬度
    center_lng = Column(Numeric(11, 8), nullable=False)  # 中心点经度
    radius_meters = Column(Integer, nullable=False)      # 允许范围半径（米）
    location_name = Column(String(255), nullable=True)   # 位置名称（便于识别）
    
    # 联系方式
    contact_wechat = Column(String(100), nullable=True)  # 管理员微信号（访问被拒时显示）

    # 限制条件
    expire_at = Column(DateTime(timezone=True), nullable=True)  # 过期时间
    max_visits = Column(Integer, nullable=True)  # 最大访问次数（0或空表示不限制）
    
    # 管理信息
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_banned = Column(Boolean, default=False, nullable=False, index=True)   # 超管封禁标记
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)  # 软删除标记
    
    # 统计信息
    visit_count = Column(Integer, default=0, nullable=False)
    success_count = Column(Integer, default=0, nullable=False)  # 成功访问次数
    denied_count = Column(Integer, default=0, nullable=False)   # 被拒绝次数
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # 关系
    from sqlalchemy.orm import relationship
    creator = relationship("User", backref="links")
    
    def __repr__(self):
        return f"<Link(id={self.id}, short_code='{self.short_code}', location='{self.location_name}')>"


class AccessLog(Base):
    """访问日志模型（用于审计）"""
    __tablename__ = "access_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    link_id = Column(Integer, ForeignKey("links.id"), nullable=False, index=True)
    
    # 访问者位置
    visitor_lat = Column(Numeric(10, 8), nullable=True)
    visitor_lng = Column(Numeric(11, 8), nullable=True)
    distance_meters = Column(Numeric(10, 2), nullable=True)
    
    # 访问结果
    access_granted = Column(Boolean, nullable=False)
    
    # 访问信息
    user_agent = Column(String, nullable=True)
    ip_address = Column(String(45), nullable=True)
    
    # 时间戳
    accessed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    def __repr__(self):
        return f"<AccessLog(id={self.id}, link_id={self.link_id}, granted={self.access_granted})>"
