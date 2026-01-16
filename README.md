# 风浪等级空间查询系统

基于 GeoPandas 的风浪等级空间查询工具，支持点位等级查询和距离计算。

**坐标系统说明**：
- 输入经度支持 **-180~180** 或 **0~360** 两种模式
- 内部统一转换为 **0~360** 坐标系进行计算和绘图
- 输出结果显示 **0~360** 经度

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 命令行使用

```bash
# 基本查询（支持 -180~180 或 0~360 经度）
python -m src.main --lon -160.5260550 --lat -4.0147083
# 等价于：python -m src.main --lon 199.473945 --lat -4.0147083

# 限制搜索半径
python -m src.main --lon -160.5260550 --lat -4.0147083 --radius 740

# 查询并绘制地图（180度附近的数据也能正确显示）
python -m src.main --lon 175.526055 --lat -37.0147083 --plot

# 使用 0~360 经度查询
python -m src.main --lon 185.0 --lat -37.0147083 --plot
# 等价于：python -m src.main --lon -175.0 --lat -37.0147083 --plot

# 指定地图输出路径
python -m src.main --lon 175.526055 --lat -37.0147083 --plot --plot-output my_map.png
```

### Python API 使用

```python
from src.main import query_wind_level
from src.visualize import plot_wind_level_map

# 基本查询（-160.526 自动转换为 199.474）
result = query_wind_level(
    lon=-160.5260550,  # 支持 -180~180
    lat=-4.0147083,
    radius_km=740
)
print(result)
# 输出的 query_point["lon"] 为 199.473945 (0~360模式)

# 直接使用 0~360 经度
result = query_wind_level(
    lon=199.473945,  # 支持 0~360
    lat=-4.0147083,
    radius_km=740
)

# 查询并绘图
result = query_wind_level(
    lon=175.526055,
    lat=-37.0147083,
    plot=True,
    plot_output="wind_map.png"
)

# 单独调用绘图函数
plot_wind_level_map(
    query_result=result,
    geojson_path="test_data/wind_level_18z.geojson",
    output_path="map.png"
)
```

## 测试

```bash
python tests/test_query.py
```

## 详细文档

完整使用说明和算法逻辑请查看：[docs/README.md](docs/README.md)

## 项目结构

```
wind_level_query/
├── src/              # 源代码
├── config/           # 配置文件
├── test_data/        # 测试数据
├── tests/            # 测试脚本
└── docs/             # 完整文档
```

## 依赖库

- geopandas >= 0.10.0
- shapely >= 1.8.0
- pyproj >= 3.0.0
- pyyaml >= 5.4.0
- matplotlib >= 3.5.0
