#!/usr/bin/env python3
"""
创建超级管理员账号的脚本

使用方法:
python scripts/create_superadmin.py --username admin --email admin@example.com --password yourpassword
"""

import argparse
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.user import User


def create_super_admin(username: str, email: str, password: str):
    """创建超级管理员"""
    db = SessionLocal()
    
    try:
        # 检查用户是否已存在
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            print(f"❌ 用户名 '{username}' 已存在")
            return False
        
        existing_email = db.query(User).filter(User.email == email).first()
        if existing_email:
            print(f"❌ 邮箱 '{email}' 已被使用")
            return False
        
        # Bcrypt限制密码不能超过72字节，手动截断
        password_bytes = password.encode('utf-8')[:72]
        password_truncated = password_bytes.decode('utf-8', errors='ignore')
        
        # 创建超级管理员
        super_admin = User(
            username=username,
            email=email,
            hashed_password=get_password_hash(password_truncated),
            role="super_admin",
            is_active=True,
            created_by=None  # 超级管理员没有创建者
        )
        
        db.add(super_admin)
        db.commit()
        db.refresh(super_admin)
        
        print(f"✅ 超级管理员创建成功!")
        print(f"   用户名: {super_admin.username}")
        print(f"   邮箱: {super_admin.email}")
        print(f"   角色: {super_admin.role}")
        print(f"   ID: {super_admin.id}")
        
        return True
        
    except Exception as e:
        db.rollback()
        print(f"❌ 创建失败: {str(e)}")
        return False
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description='创建超级管理员账号')
    parser.add_argument('--username', required=True, help='用户名')
    parser.add_argument('--email', required=True, help='邮箱地址')
    parser.add_argument('--password', required=True, help='密码')
    
    args = parser.parse_args()
    
    success = create_super_admin(args.username, args.email, args.password)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
