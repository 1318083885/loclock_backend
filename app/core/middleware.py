from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.blocked_ip import BlockedIp
import time

class IPBlockMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.blocked_ips = set()
        self.last_update = 0
        self.update_interval = 60  # 每60秒更新一次缓存

    def _update_blocked_ips(self):
        """从数据库更新IP黑名单缓存"""
        current_time = time.time()
        if current_time - self.last_update > self.update_interval:
            db = SessionLocal()
            try:
                ips = db.query(BlockedIp.ip_address).all()
                self.blocked_ips = {ip[0] for ip in ips}
                self.last_update = current_time
            finally:
                db.close()

    async def dispatch(self, request: Request, call_next):
        # 检查是否需要更新缓存
        self._update_blocked_ips()
        
        client_ip = request.client.host
        if client_ip in self.blocked_ips:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Your IP address has been blocked."}
            )
            
        response = await call_next(request)
        return response
