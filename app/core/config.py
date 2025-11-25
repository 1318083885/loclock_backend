from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # 数据库配置
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/loclock"
    
    # JWT配置
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24小时
    
    # CORS配置
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",  # Admin frontend
        "http://localhost:5174",  # Visitor frontend
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ]
    
    # 应用配置
    PROJECT_NAME: str = "LocLock"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"  # development, production
    
    # 短链接配置
    SHORT_CODE_LENGTH: int = 6
    SHORT_CODE_CHARS: str = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    
    # 2FA加密配置
    TOTP_ENCRYPTION_KEY: str = "your-encryption-key-change-in-production"
    
    class Config:
        env_file = ".env"


settings = Settings()
