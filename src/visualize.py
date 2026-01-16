"""
风浪等级查询结果可视化模块
提供地图绘制功能，展示查询点和周围风浪等级区域
"""

import os
from typing import Dict, Optional, Tuple
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib import rcParams
import geopandas as gpd

from .utils import load_wind_level_gdf


# 设置中文字体支持
rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
rcParams['axes.unicode_minus'] = False


def _get_level_colors() -> Dict[int, str]:
    """
    获取风浪等级颜色映射
    
    Returns:
        等级到颜色的映射字典
    """
    return {
        4: '#A6CEE3',  # 轻浪 - 浅蓝
        5: '#FFFF99',  # 中浪 - 黄色
        6: '#FDB462',  # 大浪 - 橙色
        7: '#E31A1C',  # 巨浪 - 红色
        8: '#B22222',  # 狂浪 - 深红
        9: '#6A3D9A',  # 狂涛 - 紫色
    }


def _get_level_names() -> Dict[int, str]:
    """
    获取风浪等级中文名称
    
    Returns:
        等级到名称的映射字典
    """
    return {
        4: '轻浪',
        5: '中浪',
        6: '大浪',
        7: '巨浪',
        8: '狂浪',
        9: '狂涛',
    }


def _calculate_plot_extent(
    lon: float,
    lat: float,
    max_distance_km: float,
    buffer_ratio: float = 0.2
) -> Tuple[float, float, float, float]:
    """
    计算绘图范围边界
    
    Args:
        lon: 查询点经度
        lat: 查询点纬度
        max_distance_km: 最远距离（千米）
        buffer_ratio: 缓冲比例，默认0.2（在最远距离基础上增加20%）
        
    Returns:
        (min_lon, max_lon, min_lat, max_lat)
    """
    # 如果最远距离为0或很小，使用默认范围
    if max_distance_km < 10:
        max_distance_km = 50
    
    # 添加缓冲
    radius_km = max_distance_km * (1 + buffer_ratio)
    
    # 粗略转换：1度纬度约111km，经度根据纬度调整
    lat_range = radius_km / 111.0
    lon_range = radius_km / (111.0 * abs(cos_lat(lat)))
    
    return (
        lon - lon_range,
        lon + lon_range,
        lat - lat_range,
        lat + lat_range
    )


def cos_lat(lat: float) -> float:
    """计算纬度的余弦值（用于经度距离校正）"""
    import math
    return math.cos(math.radians(lat))


def plot_wind_level_map(
    query_result: Dict,
    geojson_path: str,
    output_path: Optional[str] = None,
    figure_size: Tuple[int, int] = (12, 10),
    dpi: int = 150,
    buffer_ratio: float = 0.2
) -> None:
    """
    绘制风浪等级地图（统一使用 0-360 度坐标系）
    
    Args:
        query_result: 查询结果字典（来自 query_wind_level_info，经度为 0~360）
        geojson_path: GeoJSON 文件路径
        output_path: 输出图片路径，如果为None则不保存
        figure_size: 图片尺寸（宽, 高），单位英寸
        dpi: 图片分辨率
        buffer_ratio: 地图范围缓冲比例
    """
    # 提取查询点信息（已经是 0-360 模式）
    query_point = query_result['query_point']
    lon, lat = query_point['lon'], query_point['lat']
    current_level = query_result['current_level']['level']
    level_distances = query_result['level_distances']
    
    # 计算最远距离
    max_distance = max([d['distance_km'] for d in level_distances]) if level_distances else 50
    
    # 加载 GeoJSON 数据（保持 0-360 坐标）
    gdf = load_wind_level_gdf(geojson_path)
    
    # 计算绘图范围
    min_lon, max_lon, min_lat, max_lat = _calculate_plot_extent(
        lon, lat, max_distance, buffer_ratio
    )
    
    # 过滤在范围内的多边形（数据和查询点都在 0-360 坐标系，直接选择）
    gdf_filtered = gdf.cx[min_lon:max_lon, min_lat:max_lat]
    
    # 创建图形
    fig, ax = plt.subplots(figsize=figure_size, dpi=dpi)
    
    # 获取颜色和名称映射
    level_colors = _get_level_colors()
    level_names = _get_level_names()
    
    # 绘制不同等级的区域
    for level in sorted(gdf_filtered['level'].unique()):
        level_data = gdf_filtered[gdf_filtered['level'] == level]
        color = level_colors.get(int(level), '#CCCCCC')
        level_data.plot(
            ax=ax,
            color=color,
            edgecolor='gray',
            linewidth=0.5,
            alpha=0.7,
            label=f'Level {int(level)}'
        )
    
    # 绘制查询点
    ax.plot(lon, lat, marker='*', color='red', markersize=20, 
            markeredgecolor='darkred', markeredgewidth=1.5, zorder=10)
    
    # 标注查询点坐标
    ax.text(lon, lat, f'  ({lon:.2f}, {lat:.2f})', 
            fontsize=10, color='darkred', va='bottom', ha='left',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
    
    # 设置地图范围
    ax.set_xlim(min_lon, max_lon)
    ax.set_ylim(min_lat, max_lat)
    
    # 设置标签和网格
    ax.set_xlabel('经度 (Longitude)', fontsize=12)
    ax.set_ylabel('纬度 (Latitude)', fontsize=12)
    ax.grid(True, linestyle='--', alpha=0.5)
    ax.set_aspect('equal')
    
    # 创建图例
    legend_elements = []
    for level in sorted(gdf_filtered['level'].unique()):
        level_int = int(level)
        color = level_colors.get(level_int, '#CCCCCC')
        name = level_names.get(level_int, f'Level {level_int}')
        legend_elements.append(
            mpatches.Patch(color=color, label=f'Level {level_int} - {name}')
        )
    
    # 添加查询点图例
    legend_elements.append(
        plt.Line2D([0], [0], marker='*', color='w', markerfacecolor='red',
                   markersize=15, markeredgecolor='darkred', 
                   label=f'查询点 (Level {current_level if current_level else "N/A"})')
    )
    
    ax.legend(handles=legend_elements, loc='upper right', fontsize=10, 
              framealpha=0.9)
    
    # 设置标题
    title = f'风浪等级分布图\n查询点: ({lon:.4f}, {lat:.4f})'
    if current_level:
        title += f' | 当前等级: {current_level}'
    ax.set_title(title, fontsize=14, fontweight='bold', pad=15)
    
    # 调整布局
    plt.tight_layout()
    
    # 保存或显示
    if output_path:
        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
        print(f"图片已保存至: {output_path}")
    
    plt.close()
