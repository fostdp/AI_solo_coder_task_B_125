import numpy as np
import uuid
import math


class WindVibrationCalculator:
    def __init__(self, floor_heights=[6.59, 5.49, 4.99, 4.59, 4.09],
                 base_diameter=30.27, damping_ratio=0.05, natural_frequency=0.42):
        self.floor_heights = floor_heights
        self.base_diameter = base_diameter
        self.damping_ratio = damping_ratio
        self.natural_frequency = natural_frequency
        self.E = 10.0e9
        self.wall_ratio = 0.15
        self.Cd = 1.2
        self.I10 = 0.14
        D = base_diameter
        d = D * (1 - 2 * self.wall_ratio)
        self.I_section = np.pi / 64 * (D ** 4 - d ** 4)
        self.EI = self.E * self.I_section

    def compute_wind_response(self, wind_speed: float, height: float, floor: int) -> dict:
        height_factor = (height / 10) ** 0.16 if height > 0 else 0.0
        Cd_factor = self.Cd
        mean_wind_pressure = 0.5 * 1.225 * 1.2 * Cd_factor * wind_speed ** 2
        wind_force = mean_wind_pressure * self.base_diameter * height * height_factor
        if self.EI > 0 and height > 0:
            x_mean = wind_force * height ** 3 / (3 * self.EI)
        else:
            x_mean = 0.0
        Iu = 0.14 * self.I10
        gu = 3.0
        x_dynamic = x_mean * (2 * gu / Iu) if Iu > 0 else 0.0
        x_total = x_mean + x_dynamic
        f = self.natural_frequency
        omega = 2 * np.pi * f
        acceleration_x = omega ** 2 * x_dynamic
        cross_wind_ratio = 0.35
        displacement_x_mm = x_total * 1000
        displacement_y_mm = x_total * cross_wind_ratio * 1000
        acceleration_y = acceleration_x * cross_wind_ratio
        if acceleration_x < 0.05:
            comfort_level = "无感"
        elif acceleration_x < 0.15:
            comfort_level = "有感"
        elif acceleration_x < 0.30:
            comfort_level = "不适"
        else:
            comfort_level = "难以忍受"
        perception_map = {
            "无感": "几乎感觉不到任何晃动，建筑稳固如常",
            "有感": "轻微晃动，可感知建筑在风中微微摇曳，类似于站在缓慢摆动的吊桥上",
            "不适": "明显晃动，身体需要调整重心保持平衡，物品可能发生位移，类似于船在中等波浪中",
            "难以忍受": "剧烈晃动，站立困难，必须抓紧固定物，有强烈的晕眩感，类似于强烈地震"
        }
        perception_description = perception_map[comfort_level]
        return {
            "height": height,
            "wind_speed": wind_speed,
            "height_factor": height_factor,
            "displacement_x_mm": displacement_x_mm,
            "displacement_y_mm": displacement_y_mm,
            "acceleration_x": acceleration_x,
            "acceleration_y": acceleration_y,
            "comfort_level": comfort_level,
            "perception_description": perception_description
        }

    def compute_sensory_data(self, floor: int, wind_speed: float, earthquake_pga: float = 0.0) -> dict:
        height = sum(self.floor_heights[:floor]) if floor <= len(self.floor_heights) else sum(self.floor_heights)
        wind_response = self.compute_wind_response(wind_speed, height, floor)
        sway_amplitude_mm = wind_response["displacement_x_mm"]
        if sway_amplitude_mm < 1:
            visual_desc = "建筑稳固，无明显可见晃动"
        elif sway_amplitude_mm < 5:
            visual_desc = "轻微晃动，仔细观察可察觉屋檐微微颤动"
        elif sway_amplitude_mm < 20:
            visual_desc = "可见晃动，悬挂物缓慢摆动，窗框发出轻微摩擦声"
        else:
            visual_desc = "明显晃动，远处景物相对移动，立柱与地面连接处可见位移"
        wind_noise_db = 20 + 30 * np.log10(wind_speed + 0.1) + 10 * (height / 50)
        wind_noise_db = float(max(0.0, min(120.0, wind_noise_db)))
        if wind_noise_db < 40:
            auditory_desc = "安静，仅可闻微风拂过屋檐的细声"
        elif wind_noise_db < 55:
            auditory_desc = "风声轻柔，如同低语，可闻门窗轻微振动"
        elif wind_noise_db < 70:
            auditory_desc = "风声明显，呼啸而过，木构件发出吱嘎声"
        else:
            auditory_desc = "风声咆哮，震耳欲聋，结构构件发出强烈响声"
        vibration_level = wind_response["acceleration_x"] + earthquake_pga * 9.81
        temperature = 15.0 - 0.6 * (height / 10)
        humidity = 60.0 + 5.0 * np.sin(height / 20)
        floor_tilt_degrees = np.degrees(np.arctan(wind_response["displacement_x_mm"] / (1000 * height))) if height > 0 else 0.0
        floor_tilt_degrees += earthquake_pga * 2.0
        stair_slope = 38.0 if floor < len(self.floor_heights) else 0.0
        handrail_force = wind_response["acceleration_x"] * 70 * 0.3
        return {
            "visual": {
                "sway_amplitude_mm": float(sway_amplitude_mm),
                "sway_magnitude_mm": float(sway_amplitude_mm),
                "description": visual_desc
            },
            "auditory": {
                "wind_noise_db": float(wind_noise_db),
                "noise_level_db": float(wind_noise_db),
                "description": auditory_desc
            },
            "tactile": {
                "vibration_level": float(vibration_level),
                "temperature": float(temperature),
                "humidity": float(humidity)
            },
            "kinesthetic": {
                "floor_tilt_degrees": float(floor_tilt_degrees),
                "stair_slope": float(stair_slope),
                "handrail_force": float(handrail_force)
            }
        }


class VirtualClimbingPath:
    def __init__(self, path_id: str, waypoints: list, floor_heights: list):
        self.path_id = path_id
        self.waypoints = waypoints
        self.floor_heights = floor_heights
        self._compute_segments()

    def _compute_segments(self):
        self.segment_lengths = []
        self.total_length = 0.0
        for i in range(len(self.waypoints) - 1):
            p1 = np.array([self.waypoints[i]["x"], self.waypoints[i]["y"], self.waypoints[i]["z"]])
            p2 = np.array([self.waypoints[i + 1]["x"], self.waypoints[i + 1]["y"], self.waypoints[i + 1]["z"]])
            length = np.linalg.norm(p2 - p1)
            self.segment_lengths.append(length)
            self.total_length += length

    def get_position_at_time(self, t: float) -> dict:
        if not self.waypoints:
            return {"x": 0, "y": 0, "z": 0, "floor": 1, "waypoint_name": "", "progress": 0.0}
        if t <= 0:
            wp = self.waypoints[0]
            return {"x": wp["x"], "y": wp["y"], "z": wp["z"], "floor": wp.get("floor", 1),
                    "waypoint_name": wp.get("name", ""), "progress": 0.0}
        total_time = len(self.waypoints) - 1
        if t >= total_time:
            wp = self.waypoints[-1]
            return {"x": wp["x"], "y": wp["y"], "z": wp["z"], "floor": wp.get("floor", len(self.floor_heights)),
                    "waypoint_name": wp.get("name", ""), "progress": 1.0}
        seg_idx = int(t)
        if seg_idx >= len(self.waypoints) - 1:
            seg_idx = len(self.waypoints) - 2
        frac = t - seg_idx
        wp1 = self.waypoints[seg_idx]
        wp2 = self.waypoints[seg_idx + 1]
        x = wp1["x"] + (wp2["x"] - wp1["x"]) * frac
        y = wp1["y"] + (wp2["y"] - wp1["y"]) * frac
        z = wp1["z"] + (wp2["z"] - wp1["z"]) * frac
        floor = wp1.get("floor", 1) if frac < 0.5 else wp2.get("floor", 1)
        waypoint_name = wp1.get("name", "") if frac < 0.5 else wp2.get("name", "")
        progress = t / total_time if total_time > 0 else 1.0
        return {"x": x, "y": y, "z": z, "floor": floor, "waypoint_name": waypoint_name, "progress": progress}

    def get_floor_at_position(self, y: float) -> int:
        cumulative = 0.0
        for i, h in enumerate(self.floor_heights):
            cumulative += h
            if y <= cumulative:
                return i + 1
        return len(self.floor_heights)


class VirtualExperienceService:
    DEFAULT_PATH = [
        {"x": 0.0, "y": 0.0, "z": 0.0, "floor": 1, "name": "塔基入口"},
        {"x": 5.0, "y": 0.0, "z": 5.0, "floor": 1, "name": "一层大厅"},
        {"x": 5.0, "y": 6.59, "z": 5.0, "floor": 2, "name": "一层至二层楼梯"},
        {"x": 3.0, "y": 12.08, "z": 3.0, "floor": 2, "name": "二层回廊"},
        {"x": 3.0, "y": 17.07, "z": 3.0, "floor": 3, "name": "三层暗层"},
        {"x": 2.0, "y": 22.06, "z": 2.0, "floor": 4, "name": "四层佛殿"},
        {"x": 2.0, "y": 26.65, "z": 2.0, "floor": 5, "name": "五层明层"},
        {"x": 0.0, "y": 30.74, "z": 0.0, "floor": 5, "name": "塔顶观景台"}
    ]

    def __init__(self):
        self.calculator = WindVibrationCalculator()
        self.paths = {}
        self.sessions = {}
        default_path = VirtualClimbingPath("default", self.DEFAULT_PATH, self.calculator.floor_heights)
        self.paths["default"] = default_path

    def start_experience(self, user_id: int, path_id: str = "default") -> dict:
        path = self.paths.get(path_id, self.paths["default"])
        session_id = str(uuid.uuid4())
        session = {
            "session_id": session_id,
            "user_id": user_id,
            "path_id": path_id,
            "time_elapsed": 0.0,
            "current_position": path.get_position_at_time(0.0),
            "wind_speed": 0.0,
            "earthquake_pga": 0.0,
            "active": True
        }
        self.sessions[session_id] = session
        return {
            "session_id": session_id,
            "user_id": user_id,
            "path_id": path_id,
            "start_position": session["current_position"],
            "total_waypoints": len(path.waypoints),
            "status": "active"
        }

    def update_experience(self, session_id: str, time_elapsed: float, wind_speed: float,
                          earthquake_pga: float = 0.0) -> dict:
        session = self.sessions.get(session_id)
        if not session or not session["active"]:
            return {"error": "Invalid or inactive session"}
        session["time_elapsed"] = time_elapsed
        session["wind_speed"] = wind_speed
        session["earthquake_pga"] = earthquake_pga
        path = self.paths.get(session["path_id"], self.paths["default"])
        position = path.get_position_at_time(time_elapsed)
        session["current_position"] = position
        floor = position["floor"]
        height = position["y"]
        wind_response = self.calculator.compute_wind_response(wind_speed, height, floor)
        sensory_data = self.calculator.compute_sensory_data(floor, wind_speed, earthquake_pga)
        floor_description = self.get_floor_description(floor)
        return {
            "session_id": session_id,
            "time_elapsed": time_elapsed,
            "position": position,
            "wind_response": wind_response,
            "sensory_data": sensory_data,
            "floor_description": floor_description,
            "active": True
        }

    def get_floor_description(self, floor: int) -> dict:
        floor_info = {
            1: {
                "name": "一层释迦佛像",
                "architecture_features": "高大内槽空间，24根立柱环绕，梁架结构宏大",
                "buddha_info": "释迦牟尼佛像端坐中央，高约11米，庄严肃穆",
                "view_description": "四周立柱排列有序，光线从门窗射入，照亮佛面"
            },
            2: {
                "name": "二层平座回廊",
                "architecture_features": "外槽围廊，平座出挑，斗拱承托",
                "buddha_info": "四周供奉小型佛像与壁画，描绘佛教故事",
                "view_description": "可远眺周边景致，凭栏而望，风光尽收眼底"
            },
            3: {
                "name": "三层暗层",
                "architecture_features": "结构加固层，斜撑密布，增强整体刚度",
                "buddha_info": "无佛像供奉，为结构功能层",
                "view_description": "内部空间狭窄昏暗，木构件交错，可感受古人匠心"
            },
            4: {
                "name": "四层佛殿",
                "architecture_features": "内槽佛像，斗拱精美，层层叠叠",
                "buddha_info": "殿内供奉佛像，四周飞天壁画，栩栩如生",
                "view_description": "斗拱结构精巧绝伦，木构之美令人叹为观止"
            },
            5: {
                "name": "五层明层",
                "architecture_features": "最高佛殿，全景视野，结构收分明显",
                "buddha_info": "顶层佛殿供奉毗卢遮那佛，光明普照",
                "view_description": "全景视野开阔，可俯瞰全城，远山近水尽收眼底"
            }
        }
        return floor_info.get(floor, {
            "name": "未知楼层",
            "architecture_features": "无相关描述",
            "buddha_info": "无相关描述",
            "view_description": "无相关描述"
        })
