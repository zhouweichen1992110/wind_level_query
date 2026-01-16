"""
工具函数模块
包含经度转换、几何修复、GeoJSON加载等基础功能
"""

import geopandas as gpd
from pyproj import CRS


def convert_lon_to_360(lon: float) -> float:
    """
    将经度转换为 0-360 度模式
    
    Args:
        lon: 经度值（支持 -180~180 或 0~360）
        
    Returns:
        0-360 范围的经度值
    """
    if lon < 0:
        return lon + 360
    return lon


def fix_invalid_geometry(geometry):
    """
    修复无效几何体
    
    Args:
        geometry: Shapely 几何对象
        
    Returns:
        修复后的几何对象
    """
    if geometry is None:
        return geometry
    if not geometry.is_valid:
        return geometry.buffer(0)
    return geometry


def load_wind_level_gdf(geojson_path: str) -> gpd.GeoDataFrame:
    """
    加载风浪等级 GeoJSON 文件（保持原始 0-360 度经度）
    
    Args:
        geojson_path: GeoJSON 文件路径
        
    Returns:
        GeoDataFrame，CRS 为 EPSG:4326，经度保持 0-360
    """
    gdf = gpd.read_file(geojson_path)
    
    # 确保 CRS 是 EPSG:4326
    if gdf.crs is None:
        gdf.set_crs("EPSG:4326", inplace=True)
    elif gdf.crs != CRS("EPSG:4326"):
        gdf = gdf.to_crs("EPSG:4326")
    
    # 修复无效几何体
    gdf['geometry'] = gdf['geometry'].apply(fix_invalid_geometry)
    
    # 强制创建空间索引（加速查询）
    _ = gdf.sindex
    
    return gdf
