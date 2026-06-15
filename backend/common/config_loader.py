import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ServiceConfig:
    """服务配置"""
    service_name: str
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    redis_url: str = "redis://localhost:6379/0"
    database_url: str = ""
    timescaledb_url: str = ""
    debug: bool = True

    @classmethod
    def from_env(cls, service_name: str) -> 'ServiceConfig':
        return cls(
            service_name=service_name,
            host=os.getenv(f"{service_name.upper()}_HOST", "0.0.0.0"),
            port=int(os.getenv(f"{service_name.upper()}_PORT", "8000")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            database_url=os.getenv("DATABASE_URL", ""),
            timescaledb_url=os.getenv("TIMESCALEDB_URL", ""),
            debug=os.getenv("DEBUG", "true").lower() == "true"
        )


def load_json_config(filename: str) -> Dict[str, Any]:
    """加载JSON配置文件"""
    config_dir = Path(__file__).parent.parent.parent / "config"
    config_path = config_dir / filename

    if not config_path.exists():
        logger.warning(f"配置文件不存在: {config_path}")
        return {}

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        logger.info(f"加载配置文件: {filename}")
        return config
    except Exception as e:
        logger.error(f"加载配置文件失败 {filename}: {e}")
        return {}


def load_timber_properties() -> Dict[str, float]:
    """加载木材材料参数"""
    config = load_json_config("timber_properties.json")
    if not config:
        logger.warning("木材参数配置文件不存在，使用默认值")
        return {
            "E_L": 10000.0,
            "E_R": 800.0,
            "E_T": 500.0,
            "G_LR": 700.0,
            "G_LT": 600.0,
            "G_RT": 100.0,
            "v_LR": 0.35,
            "v_LT": 0.45,
            "v_RT": 0.55,
            "density": 450.0
        }
    return config


def load_nn_model_config() -> Dict[str, Any]:
    """加载神经网络模型配置"""
    config = load_json_config("nn_model_config.json")
    if not config:
        logger.warning("神经网络配置文件不存在，使用默认值")
        return {
            "n_features": 50,
            "n_floors": 5,
            "hidden_dims": [256, 128, 64],
            "dropout": 0.3,
            "use_data_augmentation": True,
            "use_transfer_learning": False,
            "pretrained_model_path": ""
        }
    return config


def load_alert_thresholds() -> Dict[str, Any]:
    """加载告警阈值配置"""
    return load_json_config("alert_thresholds.json")
