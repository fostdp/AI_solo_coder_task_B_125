#!/bin/bash
# ==========================================
#  应县木塔健康监测系统 - 微服务启动脚本 (Linux/Mac)
# ==========================================

set -e

echo "=========================================="
echo " 应县木塔健康监测系统 - 微服务架构"
echo "=========================================="

cd "$(dirname "$0")"

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未找到Python3，请先安装Python 3.9+"
    exit 1
fi

echo "[1/5] 启动 DTU数据采集服务 (端口 8001)..."
python3 services/dtu_receiver/main.py &
PID_DTU=$!
sleep 2

echo "[2/5] 启动 有限元仿真服务 (端口 8002)..."
python3 services/fea_simulator/main.py &
PID_FEA=$!
sleep 2

echo "[3/5] 启动 损伤识别服务 (端口 8003)..."
python3 services/damage_detector/main.py &
PID_DMG=$!
sleep 2

echo "[4/5] 启动 告警WebSocket服务 (端口 8004)..."
python3 services/alarm_ws/main.py &
PID_ALM=$!
sleep 2

echo "[5/5] 启动 API网关服务 (端口 8000)..."
python3 services/api_gateway/main.py &
PID_GW=$!
sleep 3

echo ""
echo "=========================================="
echo " 所有服务已启动！"
echo "=========================================="
echo " API网关:    http://localhost:8000"
echo " DTU采集:    http://localhost:8001"
echo " 仿真服务:   http://localhost:8002"
echo " 损伤识别:   http://localhost:8003"
echo " 告警WS:     http://localhost:8004"
echo ""
echo " 健康检查:   http://localhost:8000/api/services/status"
echo "=========================================="
echo ""
echo "PID: dtu=$PID_DTU fea=$PID_FEA dmg=$PID_DMG alm=$PID_ALM gw=$PID_GW"
echo ""
echo "按 Ctrl+C 停止所有服务"

trap "kill $PID_DTU $PID_FEA $PID_DMG $PID_ALM $PID_GW; echo ''; echo '所有服务已停止'" SIGINT SIGTERM

wait
