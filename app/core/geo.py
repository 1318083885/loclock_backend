from math import radians, sin, cos, sqrt, atan2
from typing import Tuple


def calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    使用Haversine公式计算两点间距离（米）
    
    Args:
        lat1: 第一个点的纬度
        lng1: 第一个点的经度
        lat2: 第二个点的纬度
        lng2: 第二个点的经度
    
    Returns:
        两点间的距离（米）
    """
    R = 6371000  # 地球半径（米）
    
    φ1 = radians(lat1)
    φ2 = radians(lat2)
    Δφ = radians(lat2 - lat1)
    Δλ = radians(lng2 - lng1)
    
    a = sin(Δφ/2)**2 + cos(φ1) * cos(φ2) * sin(Δλ/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    distance = R * c
    return distance


def is_within_radius(
    visitor_lat: float, 
    visitor_lng: float,
    center_lat: float,
    center_lng: float,
    radius_meters: float
) -> Tuple[bool, float]:
    """
    检查访问者是否在允许范围内
    
    Args:
        visitor_lat: 访问者纬度
        visitor_lng: 访问者经度
        center_lat: 中心点纬度
        center_lng: 中心点经度
        radius_meters: 允许范围半径（米）
    
    Returns:
        (是否在范围内, 距离中心点的距离)
    """
    distance = calculate_distance(visitor_lat, visitor_lng, center_lat, center_lng)
    is_allowed = distance <= radius_meters
    return (is_allowed, distance)
