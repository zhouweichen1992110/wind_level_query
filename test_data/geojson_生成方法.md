# SWH风浪等级处理程序

将有效波高(Significant Wave Height)NC数据转换为风浪等级GeoJSON文件。

## 项目结构

```
O_07_SWH_process/
├── src/
│   ├── __init__.py
│   ├── main.py                  # 主程序入口
│   ├── nc_reader.py             # NC文件读取模块
│   ├── wave_level_calculator.py # 风浪等级计算模块
│   ├── geojson_exporter.py      # GeoJSON导出模块
│   └── utils.py                 # 工具函数
├── config/
│   ├── settings.yaml            # 全局配置
│   └── wave_level_config.yaml   # 风浪等级配置
├── log/                         # 日志目录
├── README.md
└── requirements.txt
```

## 风浪等级标准

| 等级 | SWH范围(m) | 中文名称 | 英文描述 |
|:---:|:---:|:---:|:---:|
| 4 | 1.25~2.5 | 轻浪 | Moderate |
| 5 | 2.5~4.0 | 中浪 | Rough |
| 6 | 4.0~6.0 | 大浪 | Very Rough |
| 7 | 6.0~9.0 | 巨浪 | High |
| 8 | 9.0~14.0 | 狂浪 | Very High |
| 9 | >14.0 | 狂涛 | Phenomenal |

## 使用方法

### 基础用法

```bash
# 激活conda环境
conda activate wind_level

# 处理指定日期的所有时间段
python src/main.py -d 2025_12_23

# 处理指定时间段
python src/main.py -d 2025_12_23 -t 00z
```

### 完整参数

```bash
python src/main.py -i <输入目录> -o <输出目录> -d <日期> -t <时间段>
```

参数说明:
- `-i, --input`: 输入基础目录 (默认: D:/data2/download_luigi)
- `-o, --output`: 输出基础目录 (默认: /data2/wind_level)
- `-d, --date`: 日期字符串 (格式: YYYY_MM_DD)
- `-t, --time-slot`: 时间段 (00z/06z/12z/18z)，不指定则处理所有

## 输入数据格式

- 路径: `{input_dir}/{date}/significant_wave_height/{time_slot}/significant_wave_height.nc`
- 变量: `swh` (time, latitude, longitude)
- 维度: 57 × 721 × 1440
- 分辨率: 0.25°

## 输出数据格式

- 路径: `{output_dir}/{date}/wind_level_{time_slot}.geojson`
- 格式: GeoJSON FeatureCollection

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[lon1, lat1], [lon2, lat2], ...]]
      },
      "properties": {
        "level": 5,
        "time": 1735084800
      }
    }
  ]
}
```

## 配置文件

### settings.yaml

```yaml
input:
  base_dir: "D:/data2/download_luigi"
  time_slots: ["00z", "06z", "12z", "18z"]
  
output:
  base_dir: "/data2/wind_level"
  filename_template: "wind_level_{time_slot}.geojson"

processing:
  skip_first_timestep: true
  simplify_tolerance: 0.01
```

### wave_level_config.yaml

配置风浪等级的阈值范围，可根据需要调整。

## 依赖

- Python >= 3.8
- xarray
- numpy
- rasterio
- shapely
- pyyaml

