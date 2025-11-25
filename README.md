# LocLock Backend

> 基于地理位置的访问控制系统 - 后端服务

## 📝 项目简介

LocLock 是一个创新的访问控制系统，通过地理位置验证来限制短链接的访问权限。只有在指定地理范围内的用户才能访问目标资源，适用于门店活动、线下推广、区域限定内容等场景。

## ✨ 核心功能

### 🔐 认证与授权
- JWT 身份验证
- 双因素认证 (2FA/TOTP)
- 基于角色的访问控制 (超级管理员/普通管理员)

### 📍 地理位置控制
- 基于圆形半径的地理围栏
- 实时位置验证
- 支持 WGS-84 坐标系统

### 🔗 短链接管理
- 自定义短链接代码
- 链接标题设置
- 访问次数限制
- 过期时间控制
- 软删除与恢复
- 管理员封禁功能

### 📊 数据分析
- 时间维度统计（小时/天/周/月）
- 设备类型统计（设备/浏览器/操作系统）
- 地理位置热力图
- 访问成功率分析

### 🛡️ 安全特性
- IP 黑名单
- API 限流保护
- TOTP 密钥加密存储
- 环境变量隔离

## 🛠️ 技术栈

- **框架**: FastAPI 0.104+
- **数据库**: PostgreSQL 13+
- **ORM**: SQLAlchemy 2.0
- **迁移**: Alembic
- **认证**: python-jose, passlib, pyotp
- **加密**: cryptography (Fernet)
- **限流**: slowapi
- **包管理**: uv

## 📦 项目结构

```
backend/
├── alembic/                 # 数据库迁移
│   └── versions/           # 迁移脚本
├── app/
│   ├── api/                # API 路由
│   │   ├── admin.py       # 管理员接口
│   │   ├── auth.py        # 认证接口
│   │   └── links.py       # 链接管理接口
│   ├── core/               # 核心模块
│   │   ├── config.py      # 配置管理
│   │   ├── database.py    # 数据库连接
│   │   ├── geo.py         # 地理计算
│   │   ├── middleware.py  # 中间件
│   │   ├── rate_limit.py  # 限流配置
│   │   └── security.py    # 安全工具
│   ├── models/             # 数据模型
│   │   ├── blocked_ip.py
│   │   ├── link.py
│   │   └── user.py
│   ├── schemas/            # Pydantic 模式
│   │   ├── blocked_ip.py
│   │   ├── link.py
│   │   └── user.py
│   └── main.py            # 应用入口
├── scripts/               # 工具脚本
│   ├── create_superadmin.py
│   └── generate_test_data.py
├── .env.example          # 环境变量示例
├── requirements.txt      # Python 依赖
└── pyproject.toml       # UV 配置
```

## 🚀 快速开始

### 前置要求

- Python 3.11+
- PostgreSQL 13+
- uv (推荐) 或 pip

### 安装步骤

1. **克隆仓库**
```bash
git clone https://github.com/1318083885/loclock_backend.git
cd loclock_backend
```

2. **安装依赖**

使用 uv (推荐):
```bash
uv sync
```

或使用 pip:
```bash
pip install -r requirements.txt
```

3. **配置环境变量**
```bash
cp .env.example .env
# 编辑 .env 文件，配置数据库连接等信息
```

4. **生成加密密钥**
```bash
# 生成 JWT 密钥
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 生成 TOTP 加密密钥
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

5. **初始化数据库**
```bash
# 创建数据库迁移
uv run alembic upgrade head

# 创建超级管理员
uv run python scripts/create_superadmin.py
```

6. **启动服务**
```bash
# 开发模式
uv run uvicorn app.main:app --reload --port 8000

# 生产模式
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## ⚙️ 环境变量配置

### 必需配置

```env
# 数据库
DATABASE_URL=postgresql://user:password@localhost:5432/loclock

# JWT 密钥
SECRET_KEY=your-secret-key-change-in-production

# 2FA 加密密钥
TOTP_ENCRYPTION_KEY=your-fernet-key-change-in-production
```

### 可选配置

```env
# 环境 (development/production)
ENVIRONMENT=development

# CORS 允许的来源
BACKEND_CORS_ORIGINS=["http://localhost:5173"]

# JWT 过期时间 (分钟)
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# 短链接配置
SHORT_CODE_LENGTH=6
SHORT_CODE_CHARS=abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789
```

## 📡 API 文档

启动服务后访问:

- **Swagger UI**: `http://localhost:8000/docs` (开发环境)
- **ReDoc**: `http://localhost:8000/redoc` (开发环境)

> 注意: 生产环境 (`ENVIRONMENT=production`) 会自动禁用文档页面

### 主要 API 端点

#### 认证
- `POST /api/auth/login` - 用户登录
- `GET /api/auth/me` - 获取当前用户信息
- `POST /api/auth/2fa/setup` - 设置 2FA
- `POST /api/auth/2fa/enable` - 启用 2FA

#### 链接管理
- `GET /api/links` - 获取链接列表
- `POST /api/links` - 创建链接
- `PUT /api/links/{id}` - 更新链接
- `DELETE /api/links/{id}` - 删除链接
- `POST /api/links/{id}/restore` - 恢复链接

#### 访问验证
- `GET /api/public/{short_code}` - 获取链接信息
- `POST /api/verify/{short_code}` - 验证位置并访问

#### 数据分析
- `GET /api/links/{id}/time-stats` - 时间统计
- `GET /api/links/{id}/device-stats` - 设备统计
- `GET /api/links/{id}/heatmap` - 访问热力图

## 🗄️ 数据库迁移

```bash
# 创建新迁移
uv run alembic revision --autogenerate -m "description"

# 应用迁移
uv run alembic upgrade head

# 回退迁移
uv run alembic downgrade -1

# 查看迁移历史
uv run alembic history
```

## 🔧 开发工具

### 创建超级管理员
```bash
uv run python scripts/create_superadmin.py
```

### 生成测试数据
```bash
uv run python scripts/generate_test_data.py
```

## 🐳 Docker 部署

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install uv && uv sync

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 📝 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📧 联系方式

如有问题，请通过 GitHub Issues 联系我们。
