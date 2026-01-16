"""
风浪等级空间查询核心模块
提供点位等级查询和距离计算功能
"""

import geopandas as gpd
from shapely.geometry import Point
from shapely.ops import unary_union
from pyproj import CRS
from typing import Optional, Dict, List

from .utils import load_wind_level_gdf, fix_invalid_geometry

# 全局缓存：避免重复加载 GeoJSON
_GDF_CACHE = {}


def query_point_level(lon: float, lat: float, gdf: gpd.GeoDataFrame, distance_threshold_m: float = 1.0) -> Dict:
    """
    查询给定点所在的风浪等级
    如果点在多个 polygon 内，选择最近的（一般不会出现重叠，这里按距离中心点最近选择）
    
    Args:
        lon: 经度 (0~360)
        lat: 纬度
        gdf: 风浪等级 GeoDataFrame
        distance_threshold_m: 边界点判断阈值（米），默认 1.0
        
    Returns:
        {
            "in_polygon": bool,
            "level": int or None,
            "matched_info": dict or None
        }
    """
    pt = Point(lon, lat)
    
    # 找到包含该点的所有多边形（使用小缓冲区容错）
    pt_buffer = pt.buffer(1e-9)  # 极小缓冲区，避免边界判断问题
    containing = gdf[gdf.geometry.intersects(pt_buffer)]
    
    # 如果没有直接相交，尝试找距离为 0 的多边形（可能在边界上）
    if len(containing) == 0:
        # 使用投影计算精确距离
        proj_str = f"+proj=aeqd +lat_0={lat} +lon_0={lon} +ellps=WGS84 +units=m +no_defs"
        local_crs = CRS.from_proj4(proj_str)
        
        try:
            gdf_proj = gdf.to_crs(local_crs)
            gdf_proj['geometry'] = gdf_proj['geometry'].apply(fix_invalid_geometry)
            pt_gdf = gpd.GeoDataFrame(geometry=[pt], crs="EPSG:4326")
            pt_proj = pt_gdf.to_crs(local_crs).geometry.iloc[0]
            
            # 计算每个多边形的距离
            gdf_proj['dist_to_point'] = gdf_proj.geometry.apply(lambda geom: pt_proj.distance(geom))
            
            # 找到距离小于阈值的多边形（认为在边界上）
            near_zero = gdf_proj[gdf_proj['dist_to_point'] < distance_threshold_m]
            if len(near_zero) > 0:
                # 获取原始索引
                containing = gdf.loc[near_zero.index]
        except Exception as e:
            print(f"Warning: Projection failed in query_point_level: {e}")
    
    if len(containing) == 0:
        return {
            "in_polygon": False,
            "level": None,
            "matched_info": None
        }
    
    if len(containing) == 1:
        row = containing.iloc[0]
        level_val = row.get("level")
        # 转换为 Python 原生类型
        if hasattr(level_val, 'item'):
            level_val = level_val.item()
        return {
            "in_polygon": True,
            "level": int(level_val) if level_val is not None else None,
            "matched_info": {
                "level": int(level_val) if level_val is not None else None,
                "properties": {k: (v.item() if hasattr(v, 'item') else v) 
                               for k, v in row.drop("geometry").to_dict().items()}
            }
        }
    
    # 多个命中，选择最高等级（风浪等级越高表示风险越大）
    containing = containing.copy()
    # 按 level 降序排列，取最高等级
    highest = containing.sort_values('level', ascending=False).iloc[0]
    level_val = highest.get("level")
    # 转换为 Python 原生类型
    if hasattr(level_val, 'item'):
        level_val = level_val.item()
    
    return {
        "in_polygon": True,
        "level": int(level_val) if level_val is not None else None,
        "matched_info": {
            "level": int(level_val) if level_val is not None else None,
            "properties": {k: (v.item() if hasattr(v, 'item') else v) 
                           for k, v in highest.drop("geometry").to_dict().items()}
        }
    }


def query_level_min_distance(
    lon: float, 
    lat: float, 
    gdf: gpd.GeoDataFrame,
    radius_km: Optional[float] = None,
    decimal_places: int = 3
) -> List[Dict]:
    """
    计算给定点到各风浪等级区域的最近距离
    
    Args:
        lon: 经度 (0~360)
        lat: 纬度
        gdf: 风浪等级 GeoDataFrame
        radius_km: 可选，最大搜索半径（千米），超出此范围的等级不返回
        decimal_places: 距离保留小数位数，默认 3
        
    Returns:
        [
            {"level": int, "distance_km": float},
            ...
        ]
        按 level 升序排列
    """
    from shapely.geometry import box
    
    pt = Point(lon, lat)
    
    # 构造以查询点为中心的方位等距投影（单位：米）
    proj_str = f"+proj=aeqd +lat_0={lat} +lon_0={lon} +ellps=WGS84 +units=m +no_defs"
    local_crs = CRS.from_proj4(proj_str)
    
    # 获取所有 level 值
    levels = sorted(gdf['level'].dropna().unique())
    
    results = []
    radius_m = radius_km * 1000 if radius_km is not None else None
    
    # 如果设置了半径，提前粗筛选（使用 bbox 过滤）
    if radius_km is not None:
        # 1.5倍安全系数，避免漏掉边界数据
        buffer_deg = (radius_km * 1.5) / 111.0
        bbox_filter = box(lon - buffer_deg, lat - buffer_deg, 
                         lon + buffer_deg, lat + buffer_deg)
        gdf_filtered = gdf[gdf.intersects(bbox_filter)]
    else:
        gdf_filtered = gdf
    
    for level in levels:
        # 该等级的所有多边形
        level_gdf = gdf_filtered[gdf_filtered['level'] == level].copy()
        if len(level_gdf) == 0:
            continue
        
        # 分别投影
        try:
            level_gdf_proj = level_gdf.to_crs(local_crs)
            # 投影后修复无效几何
            level_gdf_proj['geometry'] = level_gdf_proj['geometry'].apply(fix_invalid_geometry)
            
            pt_gdf = gpd.GeoDataFrame(geometry=[pt], crs="EPSG:4326")
            pt_proj = pt_gdf.to_crs(local_crs).geometry.iloc[0]
            
            geom_union = unary_union(level_gdf_proj.geometry)
            
            # 计算距离（米）
            dist_m = pt_proj.distance(geom_union)
            
            # 如果设置了半径限制，且超出范围，跳过
            if radius_m is not None and dist_m > radius_m:
                continue
            
            dist_km = dist_m / 1000.0
            
            results.append({
                "level": int(level),
                "distance_km": round(dist_km, decimal_places)
            })
        except Exception as e:
            # 投影失败（可能是跨日界线问题），跳过该等级
            print(f"Warning: Failed to project level {level}: {e}")
            continue
    
    return results


def query_wind_level_info(
    lon: float,
    lat: float,
    geojson_path: str,
    radius_km: Optional[float] = None,
    distance_threshold_m: float = 1.0,
    decimal_places: int = 3
) -> Dict:
    """
    综合查询：返回点的风浪等级和到各等级的距离
    
    Args:
        lon: 经度 (0~360)
        lat: 纬度
        geojson_path: GeoJSON 文件路径
        radius_km: 可选，最大搜索半径（千米）
        distance_threshold_m: 边界点判断阈值（米）
        decimal_places: 距离保留小数位数
        
    Returns:
        {
            "query_point": {"lon": float, "lat": float},
            "current_level": {
                "in_polygon": bool,
                "level": int or None,
                "matched_info": dict or None
            },
            "level_distances": [
                {"level": int, "distance_km": float},
                ...
            ]
        }
    """
    # 使用缓存（首次加载后缓存，后续查询直接使用）
    global _GDF_CACHE
    cache_key = geojson_path
    
    if cache_key not in _GDF_CACHE:
        _GDF_CACHE[cache_key] = load_wind_level_gdf(geojson_path)
    
    gdf = _GDF_CACHE[cache_key]
    
    point_level_info = query_point_level(lon, lat, gdf, distance_threshold_m)
    distance_info = query_level_min_distance(lon, lat, gdf, radius_km, decimal_places)
    
    return {
        "query_point": {"lon": lon, "lat": lat},
        "current_level": point_level_info,
        "level_distances": distance_info
    }
