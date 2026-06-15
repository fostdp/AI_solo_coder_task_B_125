import asyncio
import aiohttp
import random
import json
import math
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import argparse
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - Simulator - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


FLOOR_CONFIG = {
    1: {"height": 9.23, "columns": 24, "diameter": 30.27},
    2: {"height": 8.50, "columns": 24, "diameter": 25.80},
    3: {"height": 7.80, "columns": 24, "diameter": 22.50},
    4: {"height": 7.20, "columns": 24, "diameter": 19.80},
    5: {"height": 6.50, "columns": 24, "diameter": 17.50},
}

MEASUREMENT_POINTS = [
    {"id": "disp_x", "name": "X向位移", "unit": "mm", "base": 0.0, "variance": 0.5},
    {"id": "disp_y", "name": "Y向位移", "unit": "mm", "base": 0.0, "variance": 0.5},
    {"id": "acc_x", "name": "X向加速度", "unit": "m/s2", "base": 0.0, "variance": 0.02},
    {"id": "acc_y", "name": "Y向加速度", "unit": "m/s2", "base": 0.0, "variance": 0.02},
    {"id": "temp", "name": "温度", "unit": "C", "base": 20.0, "variance": 5.0},
    {"id": "humidity", "name": "湿度", "unit": "%", "base": 50.0, "variance": 10.0},
    {"id": "moisture", "name": "木材含水率", "unit": "%", "base": 12.0, "variance": 2.0},
    {"id": "inclin", "name": "倾斜角", "unit": "deg", "base": 0.0, "variance": 0.1},
]

SENSOR_TYPE_MAP = {
    "disp_x": "displacement_x",
    "disp_y": "displacement_y",
    "acc_x": "acceleration_x",
    "acc_y": "acceleration_y",
    "temp": "temperature",
    "humidity": "humidity",
    "moisture": "moisture_content",
    "inclin": "inclination"
}


class EarthquakeInjector:
    def __init__(self, magnitude: float = 7.0, peak_accel: float = 0.1,
                 duration: float = 30.0, sample_rate: int = 50):
        self.magnitude = magnitude
        self.peak_accel = peak_accel
        self.duration = duration
        self.sample_rate = sample_rate
        self.wave: List[float] = []
        self._generate()

    def _generate(self):
        n = int(self.duration * self.sample_rate)
        t = [i / self.sample_rate for i in range(n)]

        freqs = [0.5, 1.0, 2.0, 3.0, 5.0, 8.0]
        amps = [0.3, 1.0, 0.8, 0.5, 0.2, 0.1]
        phases = [random.uniform(0, 2 * math.pi) for _ in freqs]

        raw = []
        for ti in t:
            val = sum(a * math.sin(2 * math.pi * f * ti + p)
                     for f, a, p in zip(freqs, amps, phases))
            raw.append(val)

        max_raw = max(abs(v) for v in raw) or 1.0
        self.wave = [v / max_raw * self.peak_accel for v in raw]

        ramp = int(0.15 * n)
        for i in range(ramp):
            self.wave[i] *= i / ramp
        decay_start = int(0.65 * n)
        for i in range(decay_start, n):
            factor = math.exp(-3.0 * (i - decay_start) / (n - decay_start))
            self.wave[i] *= factor

        logger.info(f"地震波生成: M{self.magnitude}, PGA={self.peak_accel}g, "
                     f"时长={self.duration}s, 采样率={self.sample_rate}Hz")

    def get_acceleration(self, time_offset: float) -> float:
        idx = int(time_offset * self.sample_rate)
        if 0 <= idx < len(self.wave):
            return self.wave[idx]
        return 0.0

    def is_active(self, time_offset: float) -> bool:
        return 0 <= time_offset <= self.duration


class WindStormInjector:
    def __init__(self, basic_wind_speed: float = 25.0,
                 turbulence_intensity: float = 0.2, duration: float = 60.0):
        self.basic_wind_speed = basic_wind_speed
        self.turbulence_intensity = turbulence_intensity
        self.duration = duration
        self.wave: List[float] = []
        self._generate()

    def _generate(self):
        n = 600
        t = [i * self.duration / n for i in range(n)]

        davenport_freqs = [0.01 * (2 ** (i / 3)) for i in range(30)]
        raw = []
        for ti in t:
            val = 0
            for f in davenport_freqs:
                x = 1200 * f / (self.basic_wind_speed * 10)
                sv = 4 * 0.002 * self.basic_wind_speed ** 2 * x ** 2 / (
                    f * (1 + x ** 2) ** (4 / 3))
                amp = math.sqrt(2 * sv * 0.05)
                val += amp * math.sin(2 * math.pi * f * ti + random.uniform(0, 2 * math.pi))
            raw.append(self.basic_wind_speed + val)

        max_v = max(abs(v) for v in raw) or 1.0
        self.wave = [v / max_v * self.basic_wind_speed * 1.5 for v in raw]
        logger.info(f"风场生成: V10={self.basic_wind_speed}m/s, "
                     f"湍流强度={self.turbulence_intensity}, 时长={self.duration}s")

    def get_wind_speed(self, time_offset: float) -> float:
        idx = int(time_offset / self.duration * len(self.wave))
        if 0 <= idx < len(self.wave):
            return self.wave[idx]
        return self.basic_wind_speed

    def get_displacement(self, time_offset: float, floor: int) -> float:
        wind = self.get_wind_speed(time_offset)
        height_factor = floor / 5.0
        rho = 1.225
        cd = 1.2
        area = 10.0
        force = 0.5 * rho * cd * area * wind ** 2 * height_factor
        return force * 0.01

    def is_active(self, time_offset: float) -> bool:
        return 0 <= time_offset <= self.duration


class SensorSimulator:
    def __init__(
        self,
        api_url: str = "http://localhost:8000",
        floors: int = 5,
        sensors_per_floor: int = 8,
        interval: int = 600,
        simulate_anomalies: bool = False,
        earthquake_magnitude: Optional[float] = None,
        wind_speed: Optional[float] = None,
        event_duration: int = 60,
        points_per_floor: int = 4,
    ):
        self.api_url = api_url
        self.floors = floors
        self.sensors_per_floor = sensors_per_floor
        self.interval = interval
        self.simulate_anomalies = simulate_anomalies
        self.points_per_floor = points_per_floor

        self.earthquake: Optional[EarthquakeInjector] = None
        self.wind_storm: Optional[WindStormInjector] = None

        if earthquake_magnitude:
            self.earthquake = EarthquakeInjector(
                magnitude=earthquake_magnitude,
                peak_accel=0.1 * (10 ** (earthquake_magnitude / 3.0 - 2.0)),
                duration=float(event_duration)
            )
        if wind_speed:
            self.wind_storm = WindStormInjector(
                basic_wind_speed=wind_speed,
                duration=float(event_duration)
            )

        self.device_map = self._build_device_map()
        self.last_values: Dict[str, float] = {}
        self.anomaly_counter = 0
        self.sim_start_time: Optional[datetime] = None

    def _build_device_map(self) -> Dict[str, Dict]:
        device_map = {}
        for floor in range(1, self.floors + 1):
            for point_idx in range(self.points_per_floor):
                angle = (point_idx / self.points_per_floor) * 2 * math.pi
                radius = (FLOOR_CONFIG[floor]["diameter"] / 2) * 0.8

                for sensor_idx in range(len(MEASUREMENT_POINTS)):
                    mp = MEASUREMENT_POINTS[sensor_idx]
                    device_id = f"DTU-F{floor:02d}-P{point_idx:02d}-{mp['id']}"
                    device_map[device_id] = {
                        'floor': floor,
                        'point_index': point_idx,
                        'sensor_type': SENSOR_TYPE_MAP[mp['id']],
                        'measurement_id': mp['id'],
                        'dtu_id': f"DTU-F{floor:02d}",
                        'angle': angle,
                        'radius': radius,
                        'x': radius * math.cos(angle),
                        'y': radius * math.sin(angle),
                    }
        return device_map

    def _generate_value(self, device_id: str, device_info: Dict,
                        elapsed_seconds: float) -> float:
        mp_id = device_info['measurement_id']
        mp = next((m for m in MEASUREMENT_POINTS if m['id'] == mp_id), None)
        if not mp:
            return 0.0

        base = mp['base']
        variance = mp['variance']
        floor = device_info['floor']
        last_value = self.last_values.get(device_id, base)

        drift = random.uniform(-variance * 0.1, variance * 0.1)
        noise = random.gauss(0, variance * 0.3)
        new_value = last_value + drift + noise

        if self.earthquake and self.earthquake.is_active(elapsed_seconds):
            eq_acc = self.earthquake.get_acceleration(elapsed_seconds)
            if mp_id in ('acc_x', 'acc_y'):
                floor_factor = 1.0 + (floor - 1) * 0.3
                new_value += eq_acc * 9.81 * floor_factor
            elif mp_id in ('disp_x', 'disp_y'):
                floor_factor = floor / 5.0
                new_value += eq_acc * 50.0 * floor_factor
            elif mp_id == 'inclin':
                new_value += eq_acc * 2.0 * floor

        if self.wind_storm and self.wind_storm.is_active(elapsed_seconds):
            wind_disp = self.wind_storm.get_displacement(elapsed_seconds, floor)
            if mp_id == 'disp_x':
                new_value += wind_disp
            elif mp_id == 'acc_x':
                new_value += wind_disp * 0.1
            elif mp_id == 'inclin':
                new_value += wind_disp * 0.05

        if self.simulate_anomalies and random.random() < 0.02:
            self.anomaly_counter += 1
            anomaly_factor = random.choice([5, 10, -5, -10])
            new_value += variance * anomaly_factor
            logger.warning(f"异常数据: {device_id} = {new_value:.4f}")

        if mp_id == 'humidity':
            new_value = max(0, min(100, new_value))
        elif mp_id == 'moisture':
            new_value = max(5, min(30, new_value))
        elif mp_id == 'temp':
            new_value = max(-30, min(60, new_value))

        self.last_values[device_id] = new_value
        return round(new_value, 6)

    def _generate_data_point(self, device_id: str, device_info: Dict,
                             timestamp: datetime, elapsed_seconds: float) -> Dict:
        value = self._generate_value(device_id, device_info, elapsed_seconds)
        mp_id = device_info['measurement_id']
        mp = next((m for m in MEASUREMENT_POINTS if m['id'] == mp_id), None)

        return {
            'device_id': device_id,
            'floor': device_info['floor'],
            'sensor_type': device_info['sensor_type'],
            'timestamp': timestamp.isoformat(),
            'value': value,
            'unit': mp['unit'] if mp else '',
            'raw_data': {
                'dtu_id': device_info['dtu_id'],
                'point_index': device_info['point_index'],
                'position_x': round(device_info['x'], 2),
                'position_y': round(device_info['y'], 2),
                'signal_strength': random.randint(-85, -50),
                'battery_voltage': round(random.uniform(3.3, 3.7), 2),
                'packet_id': random.randint(1, 99999),
                'earthquake_active': self.earthquake is not None and self.earthquake.is_active(elapsed_seconds),
                'wind_active': self.wind_storm is not None and self.wind_storm.is_active(elapsed_seconds),
            }
        }

    async def _send_data(self, session: aiohttp.ClientSession, data: Dict) -> bool:
        try:
            async with session.post(
                f"{self.api_url}/api/sensors/data",
                json=data,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"发送失败: {e}")
            return False

    async def _send_batch(self, session: aiohttp.ClientSession,
                          timestamp: datetime, elapsed_seconds: float) -> int:
        tasks = []
        for device_id, device_info in self.device_map.items():
            data = self._generate_data_point(device_id, device_info,
                                             timestamp, elapsed_seconds)
            tasks.append(self._send_data(session, data))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        success = sum(1 for r in results if r is True)

        eq_status = ""
        if self.earthquake and self.earthquake.is_active(elapsed_seconds):
            eq_status = f" [EQ M{self.earthquake.magnitude} active]"
        wind_status = ""
        if self.wind_storm and self.wind_storm.is_active(elapsed_seconds):
            wind_status = f" [Wind {self.wind_storm.basic_wind_speed}m/s active]"

        logger.info(f"上报完成: {success}/{len(tasks)}{eq_status}{wind_status}")
        return success

    async def run_once(self):
        timestamp = datetime.utcnow()
        elapsed = 0.0
        async with aiohttp.ClientSession() as session:
            await self._send_batch(session, timestamp, elapsed)

    async def run_continuous(self):
        self.sim_start_time = datetime.utcnow()
        total_sensors = len(self.device_map)
        logger.info(f"传感器模拟器启动 - {total_sensors} 个传感器, "
                     f"{self.floors}层 x {self.points_per_floor}测点 x {self.sensors_per_floor}类型")
        logger.info(f"API地址: {self.api_url}, 上报间隔: {self.interval}s")
        if self.earthquake:
            logger.info(f"地震注入: M{self.earthquake.magnitude}, "
                         f"PGA={self.earthquake.peak_accel}g, "
                         f"时长={self.earthquake.duration}s")
        if self.wind_storm:
            logger.info(f"风场注入: V={self.wind_storm.basic_wind_speed}m/s, "
                         f"时长={self.wind_storm.duration}s")

        iteration = 0
        while True:
            try:
                current_time = datetime.utcnow()
                elapsed = (current_time - self.sim_start_time).total_seconds()
                async with aiohttp.ClientSession() as session:
                    await self._send_batch(session, current_time, elapsed)
                iteration += 1
            except Exception as e:
                logger.error(f"模拟循环出错: {e}")

            await asyncio.sleep(self.interval)

    async def run_hours(self, hours: float):
        self.sim_start_time = datetime.utcnow()
        total_seconds = hours * 3600
        iterations = max(1, int(total_seconds / self.interval))

        logger.info(f"运行 {hours}h, 约 {iterations} 次上报")

        for i in range(iterations):
            try:
                current_time = self.sim_start_time + timedelta(seconds=i * self.interval)
                elapsed = i * self.interval
                async with aiohttp.ClientSession() as session:
                    await self._send_batch(session, current_time, elapsed)
            except Exception as e:
                logger.error(f"第 {i+1} 次上报出错: {e}")

        logger.info("模拟运行完成")

    async def run_backfill(self, days: int):
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)
        iterations = int(days * 86400 / self.interval)

        logger.info(f"回溯填充 {days} 天, 约 {iterations} 次")

        for i in range(iterations):
            current_time = start_time + timedelta(seconds=i * self.interval)
            elapsed = i * self.interval
            try:
                async with aiohttp.ClientSession() as session:
                    await self._send_batch(session, current_time, elapsed)
                if (i + 1) % 10 == 0:
                    logger.info(f"回溯进度: {(i+1)/iterations*100:.1f}%")
            except Exception as e:
                logger.error(f"回溯出错: {e}")

        logger.info("回溯完成")

    def print_device_map(self):
        print(f"\n{'='*60}")
        print(f"  应县木塔传感器设备映射 ({self.floors}层 x {self.points_per_floor}测点)")
        print(f"{'='*60}")
        for floor in range(1, self.floors + 1):
            fc = FLOOR_CONFIG[floor]
            print(f"\n  第{floor}层 (高{fc['height']}m, 直径{fc['diameter']}m, {fc['columns']}根立柱)")
            for point_idx in range(self.points_per_floor):
                angle = (point_idx / self.points_per_floor) * 360
                print(f"    测点{point_idx+1} ({angle:.0f}deg):")
                for mp in MEASUREMENT_POINTS:
                    device_id = f"DTU-F{floor:02d}-P{point_idx:02d}-{mp['id']}"
                    print(f"      {device_id}: {mp['name']} ({mp['unit']})")
        print(f"\n  总传感器数: {len(self.device_map)}")
        if self.earthquake:
            print(f"  地震注入: M{self.earthquake.magnitude}, PGA={self.earthquake.peak_accel}g")
        if self.wind_storm:
            print(f"  风场注入: V={self.wind_storm.basic_wind_speed}m/s")
        print()


def main():
    parser = argparse.ArgumentParser(
        description='应县木塔传感器模拟器 (增强版)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 基础运行 (5层8传感器/层, 10分钟间隔)
  python simulator.py --api-url http://localhost:8000 --continuous

  # 注入7级地震
  python simulator.py --earthquake 7.0 --event-duration 30 --continuous

  # 注入台风 (30m/s)
  python simulator.py --wind-speed 30.0 --event-duration 60 --continuous

  # 同时注入地震+台风
  python simulator.py --earthquake 7.0 --wind-speed 25.0 --continuous

  # 回溯填充3天数据
  python simulator.py --backfill 3

  # 列出所有传感器
  python simulator.py --list
        """
    )
    parser.add_argument('--api-url', default='http://localhost:8000', help='API地址')
    parser.add_argument('--floors', type=int, default=5, help='楼层数 (默认5)')
    parser.add_argument('--sensors-per-floor', type=int, default=8, help='每层传感器类型数')
    parser.add_argument('--points-per-floor', type=int, default=4, help='每层测点数 (默认4)')
    parser.add_argument('--interval', type=int, default=600, help='上报间隔秒 (默认600)')
    parser.add_argument('--once', action='store_true', help='只运行一次')
    parser.add_argument('--continuous', action='store_true', help='持续运行')
    parser.add_argument('--hours', type=float, help='运行指定小时数')
    parser.add_argument('--backfill', type=int, help='回溯填充天数')
    parser.add_argument('--anomalies', action='store_true', help='开启异常数据模拟')

    parser.add_argument('--earthquake', type=float, metavar='MAGNITUDE',
                        help='注入地震 (震级, 如6.0/7.0/8.0)')
    parser.add_argument('--earthquake-pga', type=float, default=None,
                        help='地震峰值加速度(g), 不指定则根据震级计算')
    parser.add_argument('--wind-speed', type=float, metavar='M/S',
                        help='注入风场 (基本风速m/s, 如25/30/40)')
    parser.add_argument('--turbulence', type=float, default=0.2,
                        help='风场湍流强度 (默认0.2)')
    parser.add_argument('--event-duration', type=int, default=60,
                        help='地震/风场事件持续秒数 (默认60)')

    parser.add_argument('--list', action='store_true', help='列出所有传感器')

    args = parser.parse_args()

    simulator = SensorSimulator(
        api_url=args.api_url,
        floors=args.floors,
        sensors_per_floor=args.sensors_per_floor,
        interval=args.interval,
        simulate_anomalies=args.anomalies,
        earthquake_magnitude=args.earthquake,
        wind_speed=args.wind_speed,
        event_duration=args.event_duration,
        points_per_floor=args.points_per_floor,
    )

    if args.earthquake_pga and simulator.earthquake:
        simulator.earthquake.peak_accel = args.earthquake_pga

    if args.list:
        simulator.print_device_map()
        return

    try:
        if args.backfill:
            asyncio.run(simulator.run_backfill(args.backfill))
        elif args.hours:
            asyncio.run(simulator.run_hours(args.hours))
        elif args.once:
            asyncio.run(simulator.run_once())
        elif args.continuous:
            asyncio.run(simulator.run_continuous())
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
