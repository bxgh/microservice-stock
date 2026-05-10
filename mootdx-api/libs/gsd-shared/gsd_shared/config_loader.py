import os
import yaml
from pathlib import Path
from typing import Dict, List, Any

# 默认配置文件路径
DEFAULT_CONFIG_PATH = Path(__file__).parent / "config" / "universe.yaml"

def load_universe_config(config_path: str = None) -> Dict[str, Any]:
    """
    加载股票全域配置文件
    """
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    
    if not path.exists():
        # 兜底配置，防止文件缺失导致崩溃
        return {
            "indices": ["000001", "399001", "399006", "000300", "000905", "000852", "000016", "000688"],
            "etf_prefixes": [],
            "market_prefixes": ["600", "601", "603", "605", "688", "000", "001", "002", "003", "300", "301"]
        }
        
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

# 单例缓存
_config_cache = None

def get_config() -> Dict[str, Any]:
    global _config_cache
    if _config_cache is None:
        _config_cache = load_universe_config()
    return _config_cache
