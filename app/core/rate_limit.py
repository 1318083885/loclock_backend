from slowapi import Limiter
from slowapi.util import get_remote_address

# 初始化Limiter，使用请求的客户端IP地址作为限制键
# default_limits=["100/minute"] 表示默认每个IP每分钟最多100个请求
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])
