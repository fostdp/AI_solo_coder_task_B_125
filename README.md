# 应县木塔结构抗风抗震仿真与健康监测系统

## 架构图

```
                          ┌──────────────────────────────────┐
                          │         Nginx (端口80)            │
                          │   Gzip压缩 / 静态资源 / SPA路由    │
                          │   WebSocket代理 → alarm-ws:8004   │
                          │   API代理 → api-gateway:8000      │
                          └──────────┬───────────────────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
             ┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐
             │  静态资源    │  │  API网关     │  │  WebSocket  │
             │  /dist       │  │  :8000       │  │  /ws        │
             └─────────────┘  └──────┬──────┘  └─────────────┘
                                     │
              ┌──────────┬───────────┼───────────┬──────────┐
              │          │           │           │          │
        ┌─────▼─────┐┌───▼────┐┌────▼────┐┌─────▼────┐┌───▼──────┐
        │dtu_       ││fea_    ││damage_  ││alarm_ws  ││simulator │
        │receiver   ││simulator││detector ││(告警WS) ││(模拟器)  │
        │:8001      ││:8002   ││:8003    ││:8004     ││(一次性)  │
        └─────┬─────┘└───┬────┘└────┬────┘└─────┬────┘└───┬──────┘
              │          │          │           │          │
              └──────────┴────┬─────┴───────────┘          │
                              │                            │
                     ┌────────▼────────┐          ┌───────▼────────┐
                     │  Redis Pub/Sub  │          │  TimescaleDB   │
                     │  (消息总线)      │          │  (时序数据库)   │
                     │  端口6379       │          │  端口5432       │
                     └─────────────────┘          └────────────────┘

事件流:
  DTU→dtu_receiver ──sensor.data.received──→ Redis ──→ alarm_ws(阈值检查)
                                            Redis ──→ damage_detector(频率趋势)
  前端→api_gateway→fea_simulator ──simulation.result──→ Redis ──→ alarm_ws→前端WS
  前端→api_gateway→damage_detector ──damage.result──→ Redis ──→ alarm_ws→前端WS
```

## 服务清单

| 服务 | 端口 | 职责 | Worker数 |
|------|------|------|----------|
| Nginx | 80 | 前端静态资源+反向代理 | - |
| api-gateway | 8000 | 统一API入口, 服务聚合 | 4 |
| dtu-receiver | 8001 | 传感器数据采集校验 | 2 |
| fea-simulator | 8002 | 有限元分析+动力响应 | 1 |
| damage-detector | 8003 | 神经网络损伤识别 | 1 |
| alarm-ws | 8004 | 告警评估+WebSocket推送 | 2 |
| TimescaleDB | 5432 | 时序数据存储+降采样 | - |
| Redis | 6379 | Pub/Sub消息总线 | - |

## 部署步骤

### 前提条件

- Docker 20.10+
- Docker Compose v2.0+
- 8GB+ RAM (推荐16GB, FEA仿真内存密集)
- 20GB+ 磁盘空间

### 1. 构建前端

```bash
cd frontend
npm install
npm run build
# 产物在 frontend/dist/ 目录
```

### 2. 一键启动

```bash
# 构建并启动所有服务
docker compose up -d --build

# 查看服务状态
docker compose ps

# 查看日志
docker compose logs -f api-gateway
docker compose logs -f dtu-receiver
```

### 3. 初始化验证

```bash
# 检查API网关健康状态
curl http://localhost/health

# 检查各微服务状态
curl http://localhost/api/services/status

# 检查TimescaleDB
docker compose exec timescaledb psql -U postgres -d pagoda_monitor -c "\dt"

# 检查Redis
docker compose exec redis redis-cli ping
```

### 4. 运行传感器模拟器

```bash
# 基础模式 - 持续上报数据 (60秒间隔)
docker compose run simulator \
  --api-url http://api-gateway:8000 \
  --interval 60 \
  --continuous

# 注入7级地震
docker compose run simulator \
  --api-url http://api-gateway:8000 \
  --earthquake 7.0 \
  --event-duration 30 \
  --continuous

# 注入台风 (30m/s基本风速)
docker compose run simulator \
  --api-url http://api-gateway:8000 \
  --wind-speed 30.0 \
  --event-duration 60 \
  --continuous

# 同时注入地震+台风
docker compose run simulator \
  --api-url http://api-gateway:8000 \
  --earthquake 7.0 \
  --wind-speed 25.0 \
  --event-duration 30 \
  --continuous

# 回溯填充3天历史数据
docker compose run simulator \
  --api-url http://api-gateway:8000 \
  --backfill 3

# 列出所有传感器设备
docker compose run simulator --list
```

### 5. 访问系统

- 前端界面: http://localhost
- API文档: http://localhost/api/docs (各服务独立文档见端口8001-8004)
- WebSocket: ws://localhost/ws/alerts

### 停止与清理

```bash
# 停止所有服务
docker compose down

# 停止并删除数据卷
docker compose down -v
```

## 传感器模拟器用法

### 命令行参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--api-url` | http://localhost:8000 | API网关地址 |
| `--floors` | 5 | 木塔楼层数 |
| `--points-per-floor` | 4 | 每层测点数 (不同角度位置) |
| `--sensors-per-floor` | 8 | 每层传感器类型数 |
| `--interval` | 600 | 数据上报间隔(秒) |
| `--continuous` | - | 持续运行模式 |
| `--once` | - | 只上报一次 |
| `--hours N` | - | 运行N小时 |
| `--backfill N` | - | 回溯填充N天数据 |
| `--anomalies` | - | 随机注入2%异常数据 |
| `--earthquake MAG` | - | 注入地震, MAG为震级(5.0-9.0) |
| `--earthquake-pga G` | - | 地震峰值加速度(g), 不指定则自动计算 |
| `--wind-speed M/S` | - | 注入风场, 基本风速(m/s) |
| `--turbulence F` | 0.2 | 风场湍流强度 |
| `--event-duration SEC` | 60 | 地震/风场事件持续秒数 |
| `--list` | - | 列出所有传感器设备映射 |

### 传感器布局

5层木塔, 每层4个测点(0°/90°/180°/270°), 每个测点8种传感器:

| 传感器 | 类型ID | 单位 | 说明 |
|--------|--------|------|------|
| X向位移 | displacement_x | mm | 水平东西向 |
| Y向位移 | displacement_y | mm | 水平南北向 |
| X向加速度 | acceleration_x | m/s² | 水平东西向 |
| Y向加速度 | acceleration_y | m/s² | 水平南北向 |
| 温度 | temperature | ℃ | 环境温度 |
| 湿度 | humidity | % | 环境湿度 |
| 木材含水率 | moisture_content | % | 构件含水率 |
| 倾斜角 | inclination | ° | 竖向倾斜 |

每层传感器数 = 4测点 × 8类型 = **32个**
全塔传感器数 = 5层 × 32 = **160个**

### 地震注入效果

注入地震时, 位移和加速度传感器值会叠加地震波响应:
- 加速度: 叠加PGA × 楼层放大系数(1.0~2.2)
- 位移: 叠加PGA × 50 × 高度比
- 倾斜角: 叠加PGA × 2 × 楼层

支持震级: 5.0(轻微) ~ 8.0(特大), PGA自动换算

### 风场注入效果

注入风场时, 位移和加速度传感器值会叠加风振响应:
- 位移: 0.5ρCdAV² × 高度比 × 0.01
- 加速度: 风致位移 × 0.1
- 倾斜角: 风致位移 × 0.05

基于Davenport风速谱生成脉动风时程

## TimescaleDB 数据保留策略

| 聚合级别 | 保留时间 | 刷新间隔 | 用途 |
|----------|----------|----------|------|
| 原始数据 (sensor_data) | 90天 | - | 高精度回放 |
| 10分钟聚合 (sensor_data_10m) | 1年 | 5分钟 | 实时监控 |
| 1小时聚合 (sensor_data_1h) | 5年 | 15分钟 | 趋势分析 |
| 1天聚合 (sensor_data_1d) | 10年 | 1小时 | 长期对比 |

- 7天以上数据自动启用列式压缩 (压缩比约10:1)
- 压缩按sensor_id分段, time降序排列

## 配置文件

| 文件 | 说明 |
|------|------|
| `config/timber_properties.json` | 木材正交各向异性本构参数 (E_L/E_R/E_T/G/v/密度) |
| `config/nn_model_config.json` | 神经网络结构/数据增强/迁移学习配置 |
| `config/alert_thresholds.json` | 8类告警阈值 (位移/加速度/频率/温度/含水率) |

修改配置文件后重启对应服务即可生效, 无需重新构建镜像。

## Nginx Gzip 压缩

启用Gzip压缩的MIME类型:
- text/css, text/javascript, application/javascript
- application/json, application/xml
- image/svg+xml, font/opentype

压缩级别: 6 (CPU与压缩率平衡)
最小压缩阈值: 256字节
Vite构建的资源带hash文件名, 设置1年强缓存 (`immutable`)
