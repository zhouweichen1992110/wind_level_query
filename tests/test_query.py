"""
测试风浪等级查询功能
"""

import json
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.main import query_wind_level


if __name__ == "__main__":
    # 测试数据路径（使用相对路径）
    geojson_path = project_root / "test_data" / "wind_level_18z.geojson"
    
    # 测试点（与原脚本相同）
    query_lon = -160.5260550
    query_lat = -4.0147083
    
    print("=" * 80)
    print("风浪等级空间查询测试")
    print("=" * 80)
    print(f"查询点: 经度={query_lon}, 纬度={query_lat}\n")
    
    # 测试1：不限制半径
    print("\n【测试1】不限制搜索半径")
    print("-" * 80)
    result1 = query_wind_level(
        lon=query_lon,
        lat=query_lat,
        geojson_path=str(geojson_path),
        save_output=False
    )
    print(json.dumps(result1, ensure_ascii=False, indent=2))
    
    # 测试2：限制半径 740km
    print("\n【测试2】限制搜索半径 740km")
    print("-" * 80)
    result2 = query_wind_level(
        lon=query_lon,
        lat=query_lat,
        geojson_path=str(geojson_path),
        radius_km=740,
        save_output=False
    )
    print(json.dumps(result2, ensure_ascii=False, indent=2))
    
    # 保存结果
    output_path = project_root / "query_result.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "test1_no_radius_limit": result1,
            "test2_radius_740km": result2
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n结果已保存至: {output_path}")
