from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

# HTTP Bearer token scheme
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码 - 使用bcrypt"""
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """生成密码哈希 - 使用bcrypt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


# TOTP密钥加密/解密功能
from cryptography.fernet import Fernet

def encrypt_totp_secret(secret: str) -> str:
    """加密TOTP密钥"""
    cipher = Fernet(settings.TOTP_ENCRYPTION_KEY.encode())
    encrypted = cipher.encrypt(secret.encode())
    return encrypted.decode()  # 存储为字符串


def decrypt_totp_secret(encrypted_secret: str) -> str:
    """解密TOTP密钥"""
    cipher = Fernet(settings.TOTP_ENCRYPTION_KEY.encode())
    decrypted = cipher.decrypt(encrypted_secret.encode())
    return decrypted.decode()



def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建JWT token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """解码JWT token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        print(f"✅ JWT解码成功: {payload}")
        return payload
    except JWTError as e:
        print(f"❌ JWT解码失败: {type(e).__name__}: {e}")
        print(f"   SECRET_KEY: {settings.SECRET_KEY[:20]}...")
        print(f"   ALGORITHM: {settings.ALGORITHM}")
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """获取当前登录用户"""
    token = credentials.credentials
    print(f"🔍 收到token: {token[:30]}...")
    
    payload = decode_access_token(token)
    print(f"🔍 解码后的payload: {payload}")
    
    if payload is None:
        print("❌ payload is None")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭证",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id_str = payload.get("sub")
    print(f"🔍 user_id_str: {user_id_str}, type: {type(user_id_str)}")
    
    if user_id_str is None:
        print("❌ user_id_str is None")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭证"
        )
    
    # 将字符串转为整数
    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        print("❌ user_id转换失败")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的用户ID"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    print(f"🔍 查询到的user: {user}")
    
    if user is None:
        print("❌ user is None")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在"
        )
    
    if not user.is_active:
        print("❌ user is not active")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )
    
    print(f"✅ 返回用户: {user.username}")
    return user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """要求管理员权限（普通管理员或超级管理员）"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user


async def require_super_admin(current_user: User = Depends(get_current_user)) -> User:
    """要求超级管理员权限"""
    if current_user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要超级管理员权限"
        )
    return current_user
