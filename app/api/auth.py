from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_password, create_access_token, get_current_user, get_password_hash
from app.core.security import encrypt_totp_secret, decrypt_totp_secret
from app.core.rate_limit import limiter
from app.models.user import User
from app.schemas.user import LoginRequest, Token, UserResponse, UserProfileUpdate

router = APIRouter()


@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
async def login(request: Request, login_data: LoginRequest, db: Session = Depends(get_db)):
    """
    用户登录接口
    
    验证用户名和密码，返回JWT token
    如果用户启用了2FA，需要提供验证码
    """
    # 查找用户
    user = db.query(User).filter(User.username == login_data.username).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    # 验证密码
    if not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    # 检查用户是否被禁用
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被禁用"
        )
    
    # 如果用户启用了2FA
    if user.is_2fa_enabled:
        if not login_data.totp_code:
            # 密码正确但缺少2FA验证码，返回特殊响应
            return Token(access_token="", token_type="bearer", requires_2fa=True)
        
        # 验证2FA代码
        import pyotp
        decrypted_secret = decrypt_totp_secret(user.totp_secret)
        totp = pyotp.TOTP(decrypted_secret)
        if not totp.verify(login_data.totp_code, valid_window=1):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="验证码错误"
            )
    
    # 创建访问token（sub必须是字符串）
    access_token = create_access_token(data={"sub": str(user.id)})
    
    return Token(access_token=access_token, token_type="bearer", requires_2fa=False)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    获取当前登录用户信息
    """
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_profile(
    user_update: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    更新个人资料（用户名、邮箱、密码）
    """
    # 检查用户名是否已存在（如果修改了用户名）
    if user_update.username and user_update.username != current_user.username:
        existing_user = db.query(User).filter(User.username == user_update.username).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名已存在"
            )
        current_user.username = user_update.username
    
    # 更新邮箱
    if user_update.email:
        current_user.email = user_update.email
    
    # 更新密码
    if user_update.password:
        current_user.hashed_password = get_password_hash(user_update.password)
    
    db.commit()
    db.refresh(current_user)
    return current_user


# 2FA (双因素认证) 相关接口

import pyotp
import io
import base64
from pydantic import BaseModel

class TwoFactorSetupResponse(BaseModel):
    secret: str
    qr_code_url: str

class TwoFactorVerifyRequest(BaseModel):
    code: str

@router.post("/2fa/setup", response_model=TwoFactorSetupResponse)
async def setup_2fa(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    生成2FA密钥和二维码URL
    """
    # 生成TOTP密钥
    secret = pyotp.random_base32()
    
    # 生成OTP URI (用于二维码)
    totp = pyotp.TOTP(secret)
    qr_code_url = totp.provisioning_uri(
        name=current_user.username,
        issuer_name="LocLock"
    )
    
    # 加密并保存密钥到数据库（但不启用2FA）
    encrypted_secret = encrypt_totp_secret(secret)
    current_user.totp_secret = encrypted_secret
    db.commit()
    
    return TwoFactorSetupResponse(
        secret=secret,
        qr_code_url=qr_code_url
    )

@router.post("/2fa/enable")
async def enable_2fa(
    verify_data: TwoFactorVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    验证2FA代码并启用2FA
    """
    if not current_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请先设置2FA"
        )
    
    # 解密密钥并验证提供的验证码
    decrypted_secret = decrypt_totp_secret(current_user.totp_secret)
    totp = pyotp.TOTP(decrypted_secret)
    if not totp.verify(verify_data.code, valid_window=1):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码错误"
        )
    
    # 启用2FA
    current_user.is_2fa_enabled = True
    db.commit()
    
    return {"message": "2FA已启用"}

@router.post("/2fa/disable")
async def disable_2fa(
    verify_data: TwoFactorVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    禁用2FA（需要验证当前验证码）
    """
    if not current_user.is_2fa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA未启用"
        )
    
    # 解密密钥并验证提供的验证码
    decrypted_secret = decrypt_totp_secret(current_user.totp_secret)
    totp = pyotp.TOTP(decrypted_secret)
    if not totp.verify(verify_data.code, valid_window=1):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码错误"
        )
    
    # 禁用2FA并清除密钥
    current_user.is_2fa_enabled = False
    current_user.totp_secret = None
    db.commit()
    
    return {"message": "2FA已禁用"}

