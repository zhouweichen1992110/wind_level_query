# 风浪等级空间查询系统

基于 GeoPandas 的风浪等级空间查询工具，支持点位等级查询和距离计算。

## 功能特性

- ✅ **点位等级查询**：给定经纬度，判断其所在的风浪等级区域
- ✅ **距离计算**：计算查询点到各风浪等级区域的最近距离（千米）
- ✅ **搜索半径限制**：可选的最大搜索半径，过滤远距离区域
- ✅ **边界点处理**：精确处理位于多边形边界上的点（精度 < 1米）
- ✅ **经度归一化**：自动处理 0-360 和 -180~180 经度系统
- ✅ **多调用方式**：支持命令行和 Python API 两种使用方式

---

## 快速开始

### 1. 安装依赖

```bash
pip install geopandas shapely pyproj pyyaml
```

### 2. 项目结构

```
wind_level_query/
├── src/
│   ├── __init__.py          # 包初始化
│   ├── utils.py             # 工具函数（经度归一化、几何修复等）
│   ├── geo_query.py         # 空间查询核心逻辑
│   └── main.py              # 主程序（命令行/API接口）
├── config/
│   └── config.yaml          # 配置文件
├── test_data/
│   └── wind_level_18z.geojson  # 测试数据
├── tests/
│   └── test_query.py        # 测试脚本
├── docs/
│   └── README.md            # 本文档
└── query_result.json        # 查询结果示例
```

---

## 使用方法

### 方式一：命令行调用

#### 基本查询

```bash
python -m src.main --lon -160.5260550 --lat -4.0147083
```

#### 指定搜索半径（740 千米）

```bash
python -m src.main --lon -160.5260550 --lat -4.0147083 --radius 740
```

#### 指定数据文件

```bash
python -m src.main --lon -160.5260550 --lat -4.0147083 --geojson test_data/wind_level_18z.geojson
```

#### 不保存结果文件

```bash
python -m src.main --lon -160.5260550 --lat -4.0147083 --no-save
```

#### 保存到指定文件

```bash
python -m src.main --lon -160.5260550 --lat -4.0147083 --output my_result.json
```

---

### 方式二：Python API 调用

```python
from src.main import query_wind_level

# 基本查询
result = query_wind_level(
    lon=-160.5260550,
    lat=-4.0147083
)

# 指定搜索半径
result = query_wind_level(
    lon=-160.5260550,
    lat=-4.0147083,
    radius_km=740
)

# 指定数据文件和输出选项
result = query_wind_level(
    lon=-160.5260550,
    lat=-4.0147083,
    geojson_path="test_data/wind_level_18z.geojson",
    radius_km=740,
    save_output=True,
    output_path="result.json"
)

print(result)
```

---

## 输出格式

查询结果为 JSON 格式，包含以下字段：

```json
{
  "query_point": {
    "lon": -160.526055,
    "lat": -4.0147083
  },
  "current_level": {
    "in_polygon": true,
    "level": 4,
    "matched_info": {
      "level": 4,
      "properties": {
        "level": 4,
        "time": 1766880000
      }
    }
  },
  "level_distances": [
    {
      "level": 4,
      "distance_km": 0.0
    },
    {
      "level": 5,
      "distance_km": 1037.459
    },
    {
      "level": 6,
      "distance_km": 3120.784
    }
  ]
}
```

### 字段说明

- **query_point**: 查询点坐标
  - `lon`: 经度
  - `lat`: 纬度

- **current_level**: 当前点所在的风浪等级
  - `in_polygon`: 是否在某个等级区域内
  - `level`: 等级值（若不在任何区域内则为 `null`）
  - `matched_info`: 匹配的多边形详细信息

- **level_distances**: 到各等级区域的最近距离列表
  - `level`: 等级值
  - `distance_km`: 距离（千米）

---

## 配置说明

配置文件位于 `config/config.yaml`：

```yaml
# 数据配置
data:
  geojson_path: "test_data/wind_level_18z.geojson"  # 风浪等级 GeoJSON 文件路径

# 查询配置
query:
  default_radius_km: null  # 默认搜索半径（千米），null 表示不限制
  distance_threshold_m: 1.0  # 边界点判断阈值（米），距离小于此值认为点在多边形内

# 输出配置
output:
  save_results: true  # 是否自动保存查询结果
  output_dir: "."  # 结果保存目录
  decimal_places: 3  # 距离保留小数位数
```

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `geojson_path` | GeoJSON 文件路径 | `test_data/wind_level_18z.geojson` |
| `default_radius_km` | 默认搜索半径（千米） | `null`（不限制） |
| `distance_threshold_m` | 边界点判断阈值（米） | `1.0` |
| `save_results` | 是否自动保存结果 | `true` |
| `output_dir` | 结果保存目录 | `"."` |
| `decimal_places` | 距离保留小数位数 | `3` |

---

## 算法逻辑

### 1. 经度归一化

由于全球海洋数据常使用 0-360° 经度系统，而常规地理坐标为 -180~180°，系统自动进行归一化处理：

```
if lon > 180:
    lon = lon - 360
```

处理后所有计算统一在 -180~180° 坐标系下进行。

### 2. 点位等级查询

查询点所在的风浪等级区域，处理流程：

1. **直接相交判断**：
   - 使用极小缓冲区（1e-9°）容错，判断点是否与多边形相交
   
2. **边界点处理**（若未相交）：
   - 使用方位等距投影将几何投影到以查询点为中心的本地坐标系
   - 计算点到每个多边形的精确距离（单位：米）
   - 距离 < `distance_threshold_m`（默认 1 米）则认为点在该区域内

3. **多边形冲突处理**：
   - 若点同时在多个多边形内，选择距离中心点最近的

### 3. 距离计算

计算查询点到各风浪等级区域的最近距离：

#### 投影选择

使用**方位等距投影**（Azimuthal Equidistant Projection）：

```python
proj_str = f"+proj=aeqd +lat_0={lat} +lon_0={lon} +ellps=WGS84 +units=m"
```

**优势**：
- 以查询点为中心，保证各方向距离计算准确
- 单位为米，便于直接计算真实地理距离
- 适用于全球任意位置

#### 计算步骤

1. **按等级聚合**：
   - 对每个风浪等级，将所有多边形合并为一个几何体（`unary_union`）

2. **投影转换**：
   - 将 GeoDataFrame 和查询点投影到本地坐标系
   - 修复投影后可能出现的无效几何

3. **距离计算**：
   - 计算点到合并几何的最短距离（单位：米）
   - 转换为千米，保留指定小数位

4. **半径过滤**（可选）：
   - 若设置了 `radius_km`，过滤超出范围的等级

### 4. 几何修复

处理无效几何体（拓扑错误）：

```python
if not geometry.is_valid:
    geometry = geometry.buffer(0)
```

`buffer(0)` 操作可修复大部分几何拓扑问题：
- 自相交
- 重复点
- 方向错误

---

## 依赖库

- **geopandas** (>=0.10.0): 地理数据处理
- **shapely** (>=1.8.0): 几何对象操作
- **pyproj** (>=3.0.0): 坐标投影转换
- **pyyaml** (>=5.4.0): YAML 配置解析

---

## 测试

运行测试脚本：

```bash
cd wind_level_query
python tests/test_query.py
```

测试脚本会执行两个场景：
1. 无搜索半径限制
2. 限制搜索半径 740 千米

---

## 常见问题

### Q1: 为什么距离为 0 但显示不在多边形内？

这种情况通常发生在点位于多边形边界上。系统会自动启用精确距离计算，若距离 < 1 米（可配置），则认为点在区域内。

### Q2: 如何处理跨日界线的数据？

系统自动将经度归一化到 -180~180°，并使用方位等距投影避免跨日界线计算错误。

### Q3: 查询速度慢怎么办？

- 使用 `radius_km` 限制搜索范围
- 数据量大时考虑建立空间索引（GeoPandas 自动优化）
- 减少查询的多边形数量

### Q4: 如何处理多个等级重叠的情况？

系统选择距离查询点中心最近的多边形作为当前等级。

---

## 版本信息

- **版本**: 1.0.0
- **作者**: [Your Name]
- **更新日期**: 2026-01-16

---

## 许可证

[待定]
