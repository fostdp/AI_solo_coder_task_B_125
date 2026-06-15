@echo off
REM ==========================================
REM  应县木塔健康监测系统 - 微服务启动脚本
REM ==========================================

echo ==========================================
echo  应县木塔健康监测系统 - 微服务架构
echo ==========================================
echo.

cd /d "%~dp0"

REM 检查Python环境
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请先安装Python 3.9+
    pause
    exit /b 1
)

echo [1/5] 启动 DTU数据采集服务 (端口 8001)...
start "DTU Receiver" cmd /k "cd /d %~dp0 && python services\dtu_receiver\main.py"
timeout /t 2 /nobreak >nul

echo [2/5] 启动 有限元仿真服务 (端口 8002)...
start "FEA Simulator" cmd /k "cd /d %~dp0 && python services\fea_simulator\main.py"
timeout /t 2 /nobreak >nul

echo [3/5] 启动 损伤识别服务 (端口 8003)...
start "Damage Detector" cmd /k "cd /d %~dp0 && python services\damage_detector\main.py"
timeout /t 2 /nobreak >nul

echo [4/5] 启动 告警WebSocket服务 (端口 8004)...
start "Alarm WS" cmd /k "cd /d %~dp0 && python services\alarm_ws\main.py"
timeout /t 2 /nobreak >nul

echo [5/5] 启动 API网关服务 (端口 8000)...
start "API Gateway" cmd /k "cd /d %~dp0 && python services\api_gateway\main.py"
timeout /t 3 /nobreak >nul

echo.
echo ==========================================
echo  所有服务已启动！
echo ==========================================
echo  API网关:    http://localhost:8000
echo  DTU采集:    http://localhost:8001
echo  仿真服务:   http://localhost:8002
echo  损伤识别:   http://localhost:8003
echo  告警WS:     http://localhost:8004
echo.
echo  健康检查:   http://localhost:8000/api/services/status
echo ==========================================
echo.
pause
