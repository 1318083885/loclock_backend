from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.security import get_password_hash, require_super_admin
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserResponse

router = APIRouter()


@router.get("/users", response_model=List[UserResponse])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    获取管理员列表（仅超级管理员）
    """
    users = db.query(User).offset(skip).limit(limit).all()
    return users


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    创建新管理员（仅超级管理员）
    """
    # 检查用户名是否已存在
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )
    
    # 检查邮箱是否已存在
    existing_email = db.query(User).filter(User.email == user_data.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已被使用"
        )
    
    # 创建新用户
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        role=user_data.role,
        created_by=current_user.id,
        is_active=True
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    更新管理员信息（仅超级管理员）
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    # 防止超级管理员修改自己的状态
    if user.id == current_user.id and user_data.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能禁用自己的账号"
        )
    
    # 更新用户信息
    if user_data.email is not None:
        # 检查邮箱是否被其他用户使用
        existing_email = db.query(User).filter(
            User.email == user_data.email,
            User.id != user_id
        ).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱已被其他用户使用"
            )
        user.email = user_data.email
    
    if user_data.is_active is not None:
        user.is_active = user_data.is_active
    
    db.commit()
    db.refresh(user)
    
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    删除管理员（仅超级管理员）
    
    实际上是禁用账号，而不是物理删除
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    # 防止删除自己
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能删除自己的账号"
        )
    
    # 标记为不活跃（软删除）
    user.is_active = False
    db.commit()
    
    return None


# IP黑名单管理接口

from app.models.blocked_ip import BlockedIp
from app.schemas.blocked_ip import BlockedIpCreate, BlockedIpResponse

@router.get("/blocked-ips", response_model=List[BlockedIpResponse])
async def get_blocked_ips(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """获取IP黑名单列表"""
    return db.query(BlockedIp).offset(skip).limit(limit).all()

@router.post("/blocked-ips", response_model=BlockedIpResponse, status_code=status.HTTP_201_CREATED)
async def block_ip(
    ip_data: BlockedIpCreate,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """添加IP到黑名单"""
    # 检查IP是否已存在
    existing_ip = db.query(BlockedIp).filter(BlockedIp.ip_address == ip_data.ip_address).first()
    if existing_ip:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该IP已在黑名单中"
        )
    
    new_blocked_ip = BlockedIp(
        ip_address=ip_data.ip_address,
        reason=ip_data.reason,
        created_by=current_user.id
    )
    
    db.add(new_blocked_ip)
    db.commit()
    db.refresh(new_blocked_ip)
    return new_blocked_ip

@router.delete("/blocked-ips/{ip_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unblock_ip(
    ip_id: int,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """从黑名单移除IP"""
    blocked_ip = db.query(BlockedIp).filter(BlockedIp.id == ip_id).first()
    if not blocked_ip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="IP记录不存在"
        )
    
    db.delete(blocked_ip)
    db.commit()
    return None
