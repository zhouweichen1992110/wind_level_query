"""
风浪等级查询主程序
支持命令行调用和函数库调用两种方式
"""

import os
import sys
import json
import yaml
import argparse
from pathlib import Path
from typing import Optional, Dict

from .geo_query import query_wind_level_info
from .visualize import plot_wind_level_map
from .utils import convert_lon_to_360


def load_config(config_path: Optional[str] = None) -> Dict:
    """
    加载配置文件
    
    Args:
        config_path: 配置文件路径，默认为 config/config.yaml
        
    Returns:
        配置字典
    """
    if config_path is None:
        # 获取项目根目录
        project_root = Path(__file__).parent.parent
        config_path = project_root / "config" / "config.yaml"
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    return config


def query_wind_level(
    lon: float,
    lat: float,
    geojson_path: Optional[str] = None,
    radius_km: Optional[float] = None,
    config_path: Optional[str] = None,
    save_output: Optional[bool] = None,
    output_path: Optional[str] = None,
    plot: bool = False,
    plot_output: Optional[str] = None
) -> Dict:
    """
    查询风浪等级（Python API 接口）
    
    Args:
        lon: 经度（支持 -180~180 或 0~360，内部统一转换为 0~360）
        lat: 纬度
        geojson_path: GeoJSON 文件路径，若不指定则从配置读取
        radius_km: 搜索半径（千米），若不指定则从配置读取
        config_path: 配置文件路径
        save_output: 是否保存结果，若不指定则从配置读取
        output_path: 输出文件路径
        plot: 是否绘制地图
        plot_output: 地图输出路径，若不指定则自动生成
        
    Returns:
        查询结果字典（经度为 0~360 模式）
    """
    # 将经度转换为 0-360 模式
    lon = convert_lon_to_360(lon)
    
    # 加载配置
    config = load_config(config_path)
    
    # 参数优先级：函数参数 > 配置文件
    if geojson_path is None:
        project_root = Path(__file__).parent.parent
        geojson_path = project_root / config['data']['geojson_path']
    
    if radius_km is None:
        radius_km = config['query'].get('default_radius_km')
    
    distance_threshold_m = config['query'].get('distance_threshold_m', 1.0)
    decimal_places = config['output'].get('decimal_places', 3)
    
    # 执行查询
    result = query_wind_level_info(
        lon=lon,
        lat=lat,
        geojson_path=str(geojson_path),
        radius_km=radius_km,
        distance_threshold_m=distance_threshold_m,
        decimal_places=decimal_places
    )
    
    # 保存结果
    if save_output is None:
        save_output = config['output'].get('save_results', False)
    
    if save_output:
        if output_path is None:
            output_dir = config['output'].get('output_dir', '.')
            output_path = Path(output_dir) / f"query_result_lon{lon}_lat{lat}.json"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"结果已保存至: {output_path}")
    
    # 绘制地图
    if plot:
        if plot_output is None:
            plot_config = config.get('plot', {})
            plot_dir = plot_config.get('output_dir', 'plots')
            plot_format = plot_config.get('format', 'png')
            plot_output = Path(plot_dir) / f"wind_level_map_lon{lon}_lat{lat}.{plot_format}"
        
        plot_config = config.get('plot', {})
        plot_wind_level_map(
            query_result=result,
            geojson_path=str(geojson_path),
            output_path=str(plot_output),
            figure_size=tuple(plot_config.get('figure_size', [12, 10])),
            dpi=plot_config.get('dpi', 150),
            buffer_ratio=plot_config.get('buffer_ratio', 0.2)
        )
    
    return result


def main():
    """
    命令行入口
    """
    parser = argparse.ArgumentParser(
        description='风浪等级空间查询工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 基本查询
  python -m src.main --lon -160.5260550 --lat -4.0147083
  
  # 指定搜索半径
  python -m src.main --lon -160.5260550 --lat -4.0147083 --radius 740
  
  # 指定数据文件
  python -m src.main --lon -160.5260550 --lat -4.0147083 --geojson test_data/wind_level_18z.geojson
  
  # 保存结果到指定文件
  python -m src.main --lon -160.5260550 --lat -4.0147083 --output result.json
        """
    )
    
    parser.add_argument('--lon', type=float, required=True, help='查询点经度（支持 -180~180 或 0~360）')
    parser.add_argument('--lat', type=float, required=True, help='查询点纬度')
    parser.add_argument('--geojson', type=str, help='GeoJSON 文件路径（可选）')
    parser.add_argument('--radius', type=float, help='搜索半径（千米，可选）')
    parser.add_argument('--config', type=str, help='配置文件路径（可选）')
    parser.add_argument('--output', type=str, help='输出文件路径（可选）')
    parser.add_argument('--no-save', action='store_true', help='不保存结果到文件')
    parser.add_argument('--plot', action='store_true', help='绘制风浪等级地图')
    parser.add_argument('--plot-output', type=str, help='地图输出路径（可选）')
    
    args = parser.parse_args()
    
    try:
        result = query_wind_level(
            lon=args.lon,
            lat=args.lat,
            geojson_path=args.geojson,
            radius_km=args.radius,
            config_path=args.config,
            save_output=not args.no_save,
            output_path=args.output,
            plot=args.plot,
            plot_output=args.plot_output
        )
        
        # 打印结果
        print("\n" + "="*80)
        print("查询结果")
        print("="*80)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
