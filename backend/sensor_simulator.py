import asyncio
import aiohttp
import random
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import argparse
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SensorSimulator:
    def __init__(
        self,
        api_url: str = "http://localhost:8000",
        floors: int = 5,
        sensors_per_floor: int = 8,
        interval: int = 600,
        simulate_anomalies: bool = False
    ):
        self.api_url = api_url
        self.floors = floors
        self.sensors_per_floor = sensors_per_floor
        self.interval = interval
        self.simulate_anomalies = simulate_anomalies
        
        self.sensor_types = {
            'displacement_x': {'unit': 'mm', 'base': 0.0, 'variance': 0.5},
            'displacement_y': {'unit': 'mm', 'base': 0.0, 'variance': 0.5},
            'acceleration_x': {'unit': 'm/s²', 'base': 0.0, 'variance': 0.02},
            'acceleration_y': {'unit': 'm/s²', 'base': 0.0, 'variance': 0.02},
            'temperature': {'unit': '°C', 'base': 20.0, 'variance': 5.0},
            'humidity': {'unit': '%', 'base': 50.0, 'variance': 10.0},
            'moisture': {'unit': '%', 'base': 12.0, 'variance': 2.0},
            'inclination': {'unit': '°', 'base': 0.0, 'variance': 0.1}
        }
        
        self.device_map = self._build_device_map()
        self.last_values = {}
        self.anomaly_counter = 0

    def _build_device_map(self) -> Dict[str, Dict]:
        device_map = {}
        sensor_type_list = list(self.sensor_types.keys())
        
        for floor in range(1, self.floors + 1):
            for sensor_idx in range(self.sensors_per_floor):
                sensor_type = sensor_type_list[sensor_idx % len(sensor_type_list)]
                device_id = f"DTU-{floor:02d}-{sensor_idx:03d}"
                device_map[device_id] = {
                    'floor': floor,
                    'sensor_type': sensor_type,
                    'dtu_id': f"DTU-{floor:02d}"
                }
        
        return device_map

    def _generate_value(self, device_id: str, sensor_type: str) -> float:
        config = self.sensor_types[sensor_type]
        base = config['base']
        variance = config['variance']
        
        last_value = self.last_values.get(device_id, base)
        
        drift = random.uniform(-variance * 0.1, variance * 0.1)
        noise = random.gauss(0, variance * 0.3)
        new_value = last_value + drift + noise
        
        if self.simulate_anomalies and random.random() < 0.02:
            self.anomaly_counter += 1
            anomaly_factor = random.choice([5, 10, -5, -10])
            new_value += variance * anomaly_factor
            logger.warning(f"生成异常数据: {device_id} = {new_value:.4f} {config['unit']}")
        
        if sensor_type == 'humidity':
            new_value = max(0, min(100, new_value))
        elif sensor_type == 'moisture':
            new_value = max(5, min(30, new_value))
        elif sensor_type == 'temperature':
            new_value = max(-30, min(60, new_value))
        
        self.last_values[device_id] = new_value
        return round(new_value, 6)

    def _generate_data_point(self, device_id: str, device_info: Dict, timestamp: datetime) -> Dict:
        sensor_type = device_info['sensor_type']
        value = self._generate_value(device_id, sensor_type)
        config = self.sensor_types[sensor_type]
        
        return {
            'device_id': device_id,
            'floor': device_info['floor'],
            'sensor_type': sensor_type,
            'timestamp': timestamp.isoformat(),
            'value': value,
            'unit': config['unit'],
            'raw_data': {
                'dtu_id': device_info['dtu_id'],
                'signal_strength': random.randint(-85, -50),
                'battery_voltage': round(random.uniform(3.3, 3.7), 2),
                'packet_id': random.randint(1, 99999)
            }
        }

    async def _send_data(self, session: aiohttp.ClientSession, data: Dict) -> bool:
        try:
            async with session.post(
                f"{self.api_url}/api/sensors/data",
                json=data,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get('alerts_count', 0) > 0:
                        logger.info(f"数据上报成功，触发 {result['alerts_count']} 条告警")
                    return True
                else:
                    text = await response.text()
                    logger.error(f"数据上报失败 [{response.status}]: {text}")
                    return False
        except Exception as e:
            logger.error(f"发送数据异常: {e}")
            return False

    async def _send_batch(self, session: aiohttp.ClientSession, timestamp: datetime) -> int:
        tasks = []
        for device_id, device_info in self.device_map.items():
            data = self._generate_data_point(device_id, device_info, timestamp)
            tasks.append(self._send_data(session, data))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        success_count = sum(1 for r in results if r is True)
        
        logger.info(f"批量上报完成: {success_count}/{len(tasks)} 成功, 累计异常: {self.anomaly_counter}")
        return success_count

    async def run_once(self):
        timestamp = datetime.utcnow()
        async with aiohttp.ClientSession() as session:
            await self._send_batch(session, timestamp)

    async def run_continuous(self):
        logger.info(f"传感器模拟器启动 - {len(self.device_map)} 个传感器, 间隔 {self.interval} 秒")
        logger.info(f"API地址: {self.api_url}")
        logger.info(f"异常模拟: {'开启' if self.simulate_anomalies else '关闭'}")
        
        while True:
            try:
                await self.run_once()
            except Exception as e:
                logger.error(f"模拟循环出错: {e}")
            
            await asyncio.sleep(self.interval)

    async def run_hours(self, hours: float):
        total_seconds = hours * 3600
        iterations = int(total_seconds / self.interval)
        logger.info(f"将运行 {hours} 小时, 约 {iterations} 次上报")
        
        start_time = datetime.utcnow()
        
        for i in range(iterations):
            try:
                current_time = start_time + timedelta(seconds=i * self.interval)
                async with aiohttp.ClientSession() as session:
                    await self._send_batch(session, current_time)
                
                remaining = (iterations - i - 1) * self.interval
                logger.info(f"进度: {i+1}/{iterations}, 剩余约 {remaining/60:.1f} 分钟")
                
            except Exception as e:
                logger.error(f"第 {i+1} 次上报出错: {e}")
        
        logger.info("模拟运行完成")

    async def run_backfill(self, days: int):
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)
        
        total_seconds = days * 86400
        iterations = int(total_seconds / self.interval)
        
        logger.info(f"回溯填充 {days} 天数据, 约 {iterations} 条记录/传感器")
        
        for i in range(iterations):
            current_time = start_time + timedelta(seconds=i * self.interval)
            
            try:
                async with aiohttp.ClientSession() as session:
                    await self._send_batch(session, current_time)
                
                if (i + 1) % 10 == 0:
                    progress = (i + 1) / iterations * 100
                    logger.info(f"回溯进度: {progress:.1f}% ({i+1}/{iterations})")
                    
            except Exception as e:
                logger.error(f"第 {i+1} 次回溯出错: {e}")
        
        logger.info("回溯填充完成")


def get_floor_sensors(floor: int) -> List[str]:
    sensor_types = [
        'displacement_x', 'displacement_y',
        'acceleration_x', 'acceleration_y',
        'temperature', 'humidity',
        'moisture', 'inclination'
    ]
    return [f"DTU-{floor:02d}-{i:03d}" for i in range(len(sensor_types))]


def print_sensor_map():
    print("\n=== 传感器设备映射 ===")
    for floor in range(1, 6):
        sensors = get_floor_sensors(floor)
        print(f"\n第 {floor} 层:")
        sensor_types = [
            'displacement_x', 'displacement_y',
            'acceleration_x', 'acceleration_y',
            'temperature', 'humidity',
            'moisture', 'inclination'
        ]
        for i, device_id in enumerate(sensors):
            print(f"  {device_id}: {sensor_types[i]}")
    print("\n")


def main():
    parser = argparse.ArgumentParser(description='应县木塔传感器模拟器')
    parser.add_argument('--api-url', default='http://localhost:8000', help='API地址')
    parser.add_argument('--floors', type=int, default=5, help='楼层数')
    parser.add_argument('--sensors-per-floor', type=int, default=8, help='每层传感器数')
    parser.add_argument('--interval', type=int, default=600, help='上报间隔（秒）')
    parser.add_argument('--once', action='store_true', help='只运行一次')
    parser.add_argument('--hours', type=float, help='运行指定小时数')
    parser.add_argument('--backfill', type=int, help='回溯填充天数')
    parser.add_argument('--anomalies', action='store_true', help='开启异常数据模拟')
    parser.add_argument('--list', action='store_true', help='列出所有传感器')
    
    args = parser.parse_args()
    
    if args.list:
        print_sensor_map()
        return
    
    simulator = SensorSimulator(
        api_url=args.api_url,
        floors=args.floors,
        sensors_per_floor=args.sensors_per_floor,
        interval=args.interval,
        simulate_anomalies=args.anomalies
    )
    
    try:
        if args.backfill:
            asyncio.run(simulator.run_backfill(args.backfill))
        elif args.hours:
            asyncio.run(simulator.run_hours(args.hours))
        elif args.once:
            asyncio.run(simulator.run_once())
        else:
            asyncio.run(simulator.run_continuous())
    except KeyboardInterrupt:
        logger.info("模拟器已停止")
        sys.exit(0)
    except Exception as e:
        logger.error(f"模拟器异常退出: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
