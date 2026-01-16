"""
风浪等级查询结果可视化模块
提供地图绘制功能，展示查询点和周围风浪等级区域
"""

import os
import math
import random
from typing import Dict, Optional, Tuple, List
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
    return math.cos(math.radians(lat))


def _generate_random_colors(n: int) -> List[str]:
    """
    生成 n 个随机且区分度高的颜色
    """
    random.seed(42)  # 固定种子以保证可重复性
    colors = []
    for i in range(n):
        hue = (i / n + random.uniform(-0.05, 0.05)) % 1.0
        saturation = random.uniform(0.6, 0.9)
        value = random.uniform(0.7, 0.95)
        # HSV to RGB
        h_i = int(hue * 6)
        f = hue * 6 - h_i
        p = value * (1 - saturation)
        q = value * (1 - f * saturation)
        t = value * (1 - (1 - f) * saturation)
        if h_i == 0: r, g, b = value, t, p
        elif h_i == 1: r, g, b = q, value, p
        elif h_i == 2: r, g, b = p, value, t
        elif h_i == 3: r, g, b = p, q, value
        elif h_i == 4: r, g, b = t, p, value
        else: r, g, b = value, p, q
        colors.append(f'#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}')
    return colors


def _draw_bearing_arrows(
    ax,
    lon: float,
    lat: float,
    level_distances: List[Dict],
    max_distance: float,
    level_names: Dict[int, str]
) -> List:
    """
    绘制从查询点指向各等级最近位置的方位角箭头
    
    Args:
        ax: matplotlib axes
        lon, lat: 查询点坐标
        level_distances: 各等级距离和方位角信息
        max_distance: 最远距离（用于计算箭头长度）
        level_names: 等级名称映射
        
    Returns:
        箭头图例元素列表
    """
    # 过滤出有方位角的等级（distance > 0）
    arrows_data = [(d['level'], d['distance_km'], d['bearing_deg']) 
                   for d in level_distances if d.get('bearing_deg') is not None]
    
    if not arrows_data:
        return []
    
    # 生成随机颜色
    colors = _generate_random_colors(len(arrows_data))
    
    # 箭头长度为最远距离的 15%（地图坐标）
    arrow_len_km = max(max_distance * 0.15, 30)  # 至少30km
    arrow_len_lat = arrow_len_km / 111.0
    arrow_len_lon = arrow_len_km / (111.0 * abs(cos_lat(lat)))
    
    legend_elements = []
    
    for i, (level, dist_km, bearing_deg) in enumerate(arrows_data):
        color = colors[i]
        
        # bearing_deg: 0=北, 90=东, 180=南, 270=西
        # 转换为数学角度：北=90°, 东=0°
        angle_rad = math.radians(90 - bearing_deg)
        
        # 计算箭头终点（考虑经纬度比例）
        dx = arrow_len_lon * math.cos(angle_rad)
        dy = arrow_len_lat * math.sin(angle_rad)
        
        # 绘制箭头
        ax.annotate(
            '',
            xy=(lon + dx, lat + dy),
            xytext=(lon, lat),
            arrowprops=dict(
                arrowstyle='->,head_width=0.4,head_length=0.3',
                color=color,
                lw=2.5,
                shrinkA=8,  # 从查询点缩进一点
                shrinkB=0
            ),
            zorder=9
        )
        
        # 在箭头终点标注等级和距离
        label_text = f'L{level}\n{dist_km:.0f}km\n{bearing_deg:.0f}°'
        ax.text(
            lon + dx * 1.15, lat + dy * 1.15,
            label_text,
            fontsize=8,
            color=color,
            fontweight='bold',
            ha='center',
            va='center',
            bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.7, edgecolor=color)
        )
        
        # 添加到图例
        name = level_names.get(level, f'Level {level}')
        legend_elements.append(
            mpatches.FancyArrow(0, 0, 0.1, 0, width=0.02, color=color,
                               label=f'→ L{level} {name}: {dist_km:.1f}km, {bearing_deg:.1f}°')
        )
    
    return legend_elements


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
    
    # 绘制方位角箭头（指向各等级最近位置的方向）
    arrow_legend = _draw_bearing_arrows(
        ax, lon, lat, level_distances, max_distance, level_names
    )
    
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
    
    # 添加箭头图例
    legend_elements.extend(arrow_legend)
    
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
