from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime
import secrets
from app.core.database import get_db
from app.core.security import require_admin, get_current_user
from app.core.geo import is_within_radius
from app.core.config import settings
from app.models.user import User
from app.models.link import Link, AccessLog
from app.schemas.link import (
    LinkCreate,
    LinkUpdate,
    LinkResponse,
    LinkStats,
    LocationVerifyRequest,
    LocationVerifyResponse,
    PublicLinkInfo,
)

router = APIRouter()


def generate_short_code() -> str:
    """生成随机短链接代码"""
    return ''.join(
        secrets.choice(settings.SHORT_CODE_CHARS)
        for _ in range(settings.SHORT_CODE_LENGTH)
    )


@router.get("/links", response_model=List[LinkResponse])
async def get_links(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    show_deleted: bool = False,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    获取当前管理员的短链接列表
    
    支持分页、搜索和查看已删除
    """
    # 如果是超级管理员，查看所有链接；否则只查看自己的
    if current_user.role == "super_admin":
        query = db.query(Link)
    else:
        query = db.query(Link).filter(Link.created_by == current_user.id)
    
    # 过滤已删除链接 (除非显式请求查看已删除)
    if show_deleted:
        query = query.filter(Link.is_deleted == True)
    else:
        query = query.filter(Link.is_deleted == False)
    
    # 搜索功能
    if search:
        query = query.filter(
            (Link.short_code.ilike(f"%{search}%")) |
            (Link.location_name.ilike(f"%{search}%")) |
            (Link.target_url.ilike(f"%{search}%"))
        )
    
    # 排序：最新创建的在前
    query = query.order_by(Link.created_at.desc())
    
    links = query.offset(skip).limit(limit).all()
    
    # 填充creator_username
    result = []
    for link in links:
        link_data = LinkResponse.from_orm(link)
        if link.creator:
            link_data.creator_username = link.creator.username
        result.append(link_data)
        
    return result


@router.get("/admin/stats")
async def get_global_stats(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    获取全局统计数据（仅超级管理员可见）
    """
    if current_user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问"
        )
        
    total_admins = db.query(User).count()
    total_links = db.query(Link).count()
    total_visits = db.query(func.sum(Link.visit_count)).scalar() or 0
    
    # 今日访问量 (这里简化处理，实际可能需要查询AccessLog或更复杂的逻辑)
    # 暂时返回总访问量，或者如果需要今日的，需要AccessLog表配合时间查询
    # 为了演示，我们先返回总访问量，后续可以优化
    
    return {
        "totalAdmins": total_admins,
        "totalLinks": total_links,
        "totalVisits": total_visits
    }


@router.get("/locations/history", response_model=List[dict])
async def get_location_history(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    获取当前用户使用过的位置历史记录（包含坐标和半径）
    用于前端自动补全
    """
    # 使用PostgreSQL的DISTINCT ON语法，获取每个位置名称的最新一条记录
    # 注意：DISTINCT ON 必须与 ORDER BY 的前缀匹配
    locations = db.query(
        Link.location_name,
        Link.center_lat,
        Link.center_lng,
        Link.radius_meters
    ).filter(Link.created_by == current_user.id)\
     .filter(Link.location_name.isnot(None))\
     .filter(Link.location_name != "")\
     .distinct(Link.location_name)\
     .order_by(Link.location_name, Link.created_at.desc())\
     .all()
    
    return [
        {
            "value": loc.location_name,  # 前端autocomplete默认使用value字段显示
            "center_lat": float(loc.center_lat),
            "center_lng": float(loc.center_lng),
            "radius_meters": loc.radius_meters
        }
        for loc in locations
    ]


@router.post("/links", response_model=LinkResponse, status_code=status.HTTP_201_CREATED)
async def create_link(
    link_data: LinkCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    创建新短链接
    """
    # 生成或使用自定义短链接代码
    if link_data.short_code:
        short_code = link_data.short_code
        # 检查short_code是否已存在
        existing = db.query(Link).filter(Link.short_code == short_code).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="该短链接代码已被使用"
            )
    else:
        # 生成随机短链接，确保唯一
        max_attempts = 10
        for _ in range(max_attempts):
            short_code = generate_short_code()
            # 检查short_code是否已存在 (包括已软删除的，防止重复使用)
            existing = db.query(Link).filter(Link.short_code == short_code).first()
            if not existing:
                break
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="生成短链接失败，请重试"
            )
    
    # 创建新链接
    new_link = Link(
        short_code=short_code,
        title=link_data.title,
        target_url=str(link_data.target_url),
        center_lat=link_data.center_lat,
        center_lng=link_data.center_lng,
        radius_meters=link_data.radius_meters,
        location_name=link_data.location_name,
        contact_wechat=link_data.contact_wechat,
        created_by=current_user.id,
        is_active=True,
        is_deleted=False # New links are not deleted
    )
    
    db.add(new_link)
    db.commit()
    db.refresh(new_link)
    
    return new_link


@router.get("/links/{link_id}", response_model=LinkResponse)
async def get_link(
    link_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    获取单个短链接详情
    """
    link = db.query(Link).filter(Link.id == link_id).first()
    if not link or link.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="短链接不存在"
        )
    
    # 检查权限（超级管理员可以查看所有，普通管理员只能查看自己的）
    if current_user.role != "super_admin" and link.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权查看此短链接"
        )
        
    return link


@router.put("/links/{link_id}", response_model=LinkResponse)
async def update_link(
    link_id: int,
    link_data: LinkUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    更新短链接信息
    """
    link = db.query(Link).filter(Link.id == link_id).first()
    if not link or link.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="短链接不存在"
        )
    
    # 检查权限
    if current_user.role != "super_admin" and link.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权修改此短链接"
        )
    
    # 更新字段
    if link_data.title is not None:
        link.title = link_data.title
    if link_data.target_url is not None:
        link.target_url = str(link_data.target_url)
    if link_data.center_lat is not None:
        link.center_lat = link_data.center_lat
    if link_data.center_lng is not None:
        link.center_lng = link_data.center_lng
    if link_data.radius_meters is not None:
        link.radius_meters = link_data.radius_meters
    if link_data.location_name is not None:
        link.location_name = link_data.location_name
    if link_data.contact_wechat is not None:
        link.contact_wechat = link_data.contact_wechat
    if link_data.is_active is not None:
        # 如果链接被封禁，普通用户不能启用
        if link.is_banned and link_data.is_active and current_user.role != "super_admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="此链接已被管理员封禁，无法启用"
            )
        # 如果是超级管理员，可以解除封禁（通过设置is_active=True隐含解除，或者需要显式解除？）
        # 这里逻辑：如果超管设置is_active=True，自动解除封禁
        if current_user.role == "super_admin" and link_data.is_active:
            link.is_banned = False
            
        link.is_active = link_data.is_active
    if link_data.expire_at is not None:
        link.expire_at = link_data.expire_at
    if link_data.max_visits is not None:
        link.max_visits = link_data.max_visits
    
    db.commit()
    db.refresh(link)
    
    return link


@router.delete("/links/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_link(
    link_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    删除短链接（软删除）
    """
    link = db.query(Link).filter(Link.id == link_id).first()
    if not link or link.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="短链接不存在"
        )
    
    # 检查权限
    if current_user.role != "super_admin" and link.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权删除此短链接"
        )
    
    # 逻辑分流：
    # 1. 如果是超级管理员删除别人的链接 -> 封禁 (is_banned=True, is_active=False)
    # 2. 如果是用户删除自己的链接 (或超管删自己的) -> 软删除 (is_deleted=True, is_active=False)
    
    if current_user.role == "super_admin" and link.created_by != current_user.id:
        # 封禁模式
        link.is_banned = True
        link.is_active = False
    else:
        # 软删除模式
        link.is_deleted = True
        link.is_active = False
        # 如果之前被封禁了，软删除后是否要重置封禁状态？
        # 保持封禁状态可能更好，防止用户通过某种方式恢复
    
    db.commit()
    return None


@router.post("/links/{link_id}/restore", response_model=LinkResponse)
async def restore_link(
    link_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    恢复已删除的短链接
    """
    link = db.query(Link).filter(Link.id == link_id).first()
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="短链接不存在"
        )
    
    # 检查权限
    if current_user.role != "super_admin" and link.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权恢复此短链接"
        )
        
    if not link.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该链接未被删除"
        )
        
    # 恢复链接
    link.is_deleted = False
    link.is_active = True # 恢复时自动启用
    
    db.commit()
    db.refresh(link)
    return link


@router.get("/links/{link_id}/stats", response_model=LinkStats)
async def get_link_stats(
    link_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    获取短链接访问统计
    """
    link = db.query(Link).filter(Link.id == link_id).first()
    if not link or link.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="短链接不存在"
        )
    
    # 检查权限
    if current_user.role != "super_admin" and link.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此链接统计"
        )
    
    # 计算成功率
    success_rate = 0.0
    if link.visit_count > 0:
        success_rate = round((link.success_count / link.visit_count) * 100, 2)
    
    return LinkStats(
        total_visits=link.visit_count,
        successful_visits=link.success_count,
        denied_visits=link.denied_count,
        success_rate=success_rate
    )


# 访问验证API（无需认证）
@router.get("/public/{short_code}", response_model=PublicLinkInfo)
async def get_public_link_info(
    short_code: str,
    db: Session = Depends(get_db)
):
    """
    获取公开的链接信息（无需验证位置）
    用于前端展示标题等信息
    """
    link = db.query(Link).filter(Link.short_code == short_code).first()
    if not link or link.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="链接不存在"
        )
        
    return {
        "short_code": link.short_code,
        "title": link.title,
        "is_active": link.is_active,
        "location_name": link.location_name
    }


@router.post("/verify/{short_code}", response_model=LocationVerifyResponse)
async def verify_location(
    short_code: str,
    location: LocationVerifyRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    验证访问者地理位置
    
    此接口无需认证，供前端访问页面调用
    """
    # 查找短链接
    link = db.query(Link).filter(Link.short_code == short_code).first()
    
    if not link or link.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="短链接不存在"
        )
    
    # 检查是否启用
    if not link.is_active:
        detail = "此链接已被禁用"
        if link.is_banned:
            detail = "此链接已被管理员封禁"
            
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )
    
    # 验证地理位置
    allowed, distance = is_within_radius(
        visitor_lat=location.latitude,
        visitor_lng=location.longitude,
        center_lat=float(link.center_lat),
        center_lng=float(link.center_lng),
        radius_meters=link.radius_meters
    )
    
    # 更新访问统计
    link.visit_count += 1
    if allowed:
        link.success_count += 1
    else:
        link.denied_count += 1
    
    # 记录访问日志
    access_log = AccessLog(
        link_id=link.id,
        visitor_lat=location.latitude,
        visitor_lng=location.longitude,
        distance_meters=round(distance, 2),
        access_granted=allowed,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None
    )
    db.add(access_log)
    
    db.commit()
    
    # 构造响应
    message = None
    contact_wechat = None
    if not allowed:
        message = "您不在允许访问的地理范围内"
        contact_wechat = link.contact_wechat

    return LocationVerifyResponse(
        allowed=allowed,
        target_url=link.target_url if allowed else None,
        distance=round(distance, 2),
        radius=link.radius_meters,
        message=message,
        contact_wechat=contact_wechat,
        title=link.title
    )
# 时间维度统计接口已添加到 links.py 末尾

from datetime import datetime, timedelta
from typing import Literal
from sqlalchemy import case

@router.get("/links/{link_id}/time-stats")
async def get_time_stats(
    link_id: int,
    granularity: Literal["hour", "day", "week", "month"] = "day",
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取链接的时间维度访问统计
    
    参数:
    - granularity: 时间粒度 (hour/day/week/month)
    - days: 查询最近N天的数据（默认30天）
    """
    # 获取链接并检查权限
    link = db.query(Link).filter(Link.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="链接不存在")
    
    # 权限检查
    if current_user.role != "super_admin" and link.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问此链接")
    
    # 计算时间范围
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=days)
    
    # 根据粒度选择不同的聚合方式
    if granularity == "hour":
        time_group = func.date_trunc('hour', AccessLog.accessed_at)
    elif granularity == "day":
        time_group = func.date_trunc('day', AccessLog.accessed_at)
    elif granularity == "week":
        time_group = func.date_trunc('week', AccessLog.accessed_at)
    else:  # month
        time_group = func.date_trunc('month', AccessLog.accessed_at)
    
    # 聚合查询
    results = db.query(
        time_group.label('time_bucket'),
        func.count(AccessLog.id).label('total'),
        func.sum(case((AccessLog.access_granted == True, 1), else_=0)).label('granted'),
        func.sum(case((AccessLog.access_granted == False, 1), else_=0)).label('denied')
    ).filter(
        AccessLog.link_id == link_id,
        AccessLog.accessed_at >= start_time,
        AccessLog.accessed_at <= end_time
    ).group_by('time_bucket').order_by('time_bucket').all()
    
    # 格式化返回数据
    data = [
        {
            "time": row.time_bucket.isoformat() if row.time_bucket else None,
            "total": int(row.total or 0),
            "granted": int(row.granted or 0),
            "denied": int(row.denied or 0)
        }
        for row in results
    ]
    
    return {
        "granularity": granularity,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "data": data
    }

@router.get("/links/{link_id}/device-stats")
async def get_device_stats(
    link_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取链接的设备和浏览器统计
    
    解析user-agent字符串，返回设备类型、浏览器、操作系统的分布
    """
    # 获取链接并检查权限
    link = db.query(Link).filter(Link.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="链接不存在")
    
    # 权限检查
    if current_user.role != "super_admin" and link.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问此链接")
    
    # 查询所有访问日志
    logs = db.query(AccessLog).filter(
        AccessLog.link_id == link_id,
        AccessLog.user_agent.isnot(None)
    ).all()
    
    # 解析user-agent
    from user_agents import parse
    
    devices = {}
    browsers = {}
    os_list = {}
    
    for log in logs:
        try:
            ua = parse(log.user_agent)
            
            # 设备类型
            if ua.is_mobile:
                device = "Mobile"
            elif ua.is_tablet:
                device = "Tablet"
            elif ua.is_pc:
                device = "Desktop"
            else:
                device = "Unknown"
            devices[device] = devices.get(device, 0) + 1
            
            # 浏览器
            browser = ua.browser.family if ua.browser.family else "Unknown"
            browsers[browser] = browsers.get(browser, 0) + 1
            
            # 操作系统
            os_name = ua.os.family if ua.os.family else "Unknown"
            os_list[os_name] = os_list.get(os_name, 0) + 1
        except Exception as e:
            # 解析失败，归类为Unknown
            devices["Unknown"] = devices.get("Unknown", 0) + 1
            browsers["Unknown"] = browsers.get("Unknown", 0) + 1
            os_list["Unknown"] = os_list.get("Unknown", 0) + 1
    
    # 格式化返回数据（按数量降序排序）
    return {
        "devices": sorted([{"name": k, "count": v} for k, v in devices.items()], key=lambda x: x['count'], reverse=True),
        "browsers": sorted([{"name": k, "count": v} for k, v in browsers.items()], key=lambda x: x['count'], reverse=True),
        "os": sorted([{"name": k, "count": v} for k, v in os_list.items()], key=lambda x: x['count'], reverse=True)
    }

@router.get("/links/{link_id}/heatmap")
async def get_link_heatmap(
    link_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取链接的访问热力图数据
    
    返回所有访问位置点，用于在地图上绘制热力图
    """
    # 获取链接并检查权限
    link = db.query(Link).filter(Link.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="链接不存在")
    
    # 权限检查
    if current_user.role != "super_admin" and link.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问此链接")
    
    # 查询所有有位置信息的访问记录
    logs = db.query(AccessLog).filter(
        AccessLog.link_id == link_id,
        AccessLog.visitor_lat.isnot(None),
        AccessLog.visitor_lng.isnot(None)
    ).all()
    
    # 聚合相近位置（使用网格聚合，精度约100米）
    # 将经纬度四舍五入到3位小数（约111米精度）
    location_counts = {}
    for log in logs:
        lat = round(float(log.visitor_lat), 3)
        lng = round(float(log.visitor_lng), 3)
        key = f"{lat},{lng}"
        location_counts[key] = location_counts.get(key, 0) + 1
    
    # 转换为热力图数据格式
    points = []
    for key, count in location_counts.items():
        lat, lng = key.split(',')
        points.append({
            "lat": float(lat),
            "lng": float(lng),
            "weight": count
        })
    
    # 返回数据
    return {
        "points": points,
        "center": {
            "lat": float(link.center_lat),
            "lng": float(link.center_lng)
        },
        "allowed_area": {
            "lat": float(link.center_lat),
            "lng": float(link.center_lng),
            "radius": link.radius_meters
        }
    }
