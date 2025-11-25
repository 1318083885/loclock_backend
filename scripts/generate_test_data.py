"""
生成多样化的访问日志测试数据
"""
from app.core.database import SessionLocal
from app.models.link import Link, AccessLog
from datetime import datetime, timedelta
import random

# 各种真实的User-Agent字符串
USER_AGENTS = [
    # iPhone
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/116.0.5845.118 Mobile/15E148 Safari/604.1",
    
    # Android手机
    "Mozilla/5.0 (Linux; Android 13; SM-S908B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 11; Mi 11) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36",
    
    # iPad
    "Mozilla/5.0 (iPad; CPU OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
    
    # Windows PC
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/116.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36 Edg/115.0.1901.188",
    
    # Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/116.0",
]

def generate_test_data(link_id: int, count: int = 50):
    """
    为指定链接生成测试数据
    """
    db = SessionLocal()
    
    try:
        # 获取链接
        link = db.query(Link).filter(Link.id == link_id).first()
        if not link:
            print(f"链接 {link_id} 不存在")
            return
        
        center_lat = float(link.center_lat)
        center_lng = float(link.center_lng)
        radius = link.radius_meters
        
        print(f"为链接 {link_id} 生成 {count} 条测试数据...")
        print(f"中心点: ({center_lat}, {center_lng}), 半径: {radius}米")
        
        created_count = 0
        for i in range(count):
            # 随机选择user-agent
            user_agent = random.choice(USER_AGENTS)
            
            # 70%概率在范围内，30%在范围外
            in_range = random.random() < 0.7
            
            if in_range:
                # 在范围内：随机偏移小于半径
                angle = random.uniform(0, 2 * 3.14159)
                distance = random.uniform(0, radius * 0.9)  # 90%半径内
                # 1度约等于111000米
                lat_offset = (distance * random.choice([-1, 1])) / 111000
                lng_offset = (distance * random.choice([-1, 1])) / (111000 * 0.9)  # 纬度修正
                
                visitor_lat = center_lat + lat_offset
                visitor_lng = center_lng + lng_offset
                access_granted = True
                distance_meters = distance
            else:
                # 在范围外：偏移超过半径
                angle = random.uniform(0, 2 * 3.14159)
                distance = random.uniform(radius * 1.2, radius * 3)
                lat_offset = (distance * random.choice([-1, 1])) / 111000
                lng_offset = (distance * random.choice([-1, 1])) / (111000 * 0.9)
                
                visitor_lat = center_lat + lat_offset
                visitor_lng = center_lng + lng_offset
                access_granted = False
                distance_meters = distance
            
            # 随机IP
            ip = f"192.168.{random.randint(1, 255)}.{random.randint(1, 255)}"
            
            # 随机时间（最近7天）
            accessed_at = datetime.utcnow() - timedelta(
                days=random.randint(0, 7),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59)
            )
            
            # 创建访问日志
            log = AccessLog(
                link_id=link_id,
                visitor_lat=visitor_lat,
                visitor_lng=visitor_lng,
                distance_meters=distance_meters,
                access_granted=access_granted,
                user_agent=user_agent,
                ip_address=ip,
                accessed_at=accessed_at
            )
            db.add(log)
            created_count += 1
        
        db.commit()
        print(f"✅ 成功创建 {created_count} 条测试数据")
        
    except Exception as e:
        db.rollback()
        print(f"❌ 错误: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    # 获取第一个链接的ID
    db = SessionLocal()
    link = db.query(Link).first()
    db.close()
    
    if link:
        print(f"找到链接 ID: {link.id}")
        generate_test_data(link.id, count=50)
    else:
        print("没有找到任何链接")
