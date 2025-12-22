# src/config/config_manager.py
import os
import json
from typing import Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class ConfigManager:
    """配置管理器"""
    
    def __init__(self):
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置"""
        config = {}
        
        # 1. 默认配置
        config.update(self._get_default_config())
        
        # 2. 从环境变量加载
        config.update(self._load_from_env())
        
        # 3. 从配置文件加载
        config.update(self._load_from_file())
        
        return config
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "deepseek": {
                "api_key": "",
                "base_url": "https://api.deepseek.com",
                "default_model": "deepseek-chat",
                "timeout": 60,
                "max_retries": 3
            },
            "api": {
                "host": "0.0.0.0",
                "port": 8000,
                "workers": 4,
                "reload": True
            },
            "frontend": {
                "host": "0.0.0.0",
                "port": 8501
            },
            "knowledge_base": {
                "vector_db_path": "./data/knowledge_base",
                "relational_db_path": "./data/knowledge_base/knowledge.db",
                "embedding_model": "all-MiniLM-L6-v2"
            }
        }
    
    def _load_from_env(self) -> Dict[str, Any]:
        """从环境变量加载配置"""
        env_config = {}
        
        # DeepSeek 配置
        api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("deepseek")
        if api_key:
            env_config["deepseek"] = {"api_key": api_key}
        
        # API 配置
        api_host = os.getenv("API_HOST")
        api_port = os.getenv("API_PORT")
        if api_host or api_port:
            env_config["api"] = {}
            if api_host:
                env_config["api"]["host"] = api_host
            if api_port:
                env_config["api"]["port"] = int(api_port)
        
        return env_config
    
    def _load_from_file(self) -> Dict[str, Any]:
        """从配置文件加载"""
        config_files = [
            Path(".env"),
            Path("config/.env"),
            Path("config/config.json"),
            Path("config/config.yaml")
        ]
        
        for config_file in config_files:
            if config_file.exists():
                try:
                    if config_file.suffix == '.json':
                        with open(config_file, 'r') as f:
                            return json.load(f)
                    elif config_file.suffix == '.yaml' or config_file.suffix == '.yml':
                        import yaml
                        with open(config_file, 'r') as f:
                            return yaml.safe_load(f)
                    elif config_file.name == '.env':
                        # 简单解析 .env 文件
                        env_config = {}
                        with open(config_file, 'r') as f:
                            for line in f:
                                line = line.strip()
                                if line and not line.startswith('#'):
                                    if '=' in line:
                                        key, value = line.split('=', 1)
                                        key = key.strip()
                                        value = value.strip().strip('"').strip("'")
                                        env_config[key] = value
                        return self._parse_env_config(env_config)
                except Exception as e:
                    logger.warning(f"加载配置文件 {config_file} 失败: {str(e)}")
        
        return {}
    
    def _parse_env_config(self, env_vars: Dict[str, str]) -> Dict[str, Any]:
        """解析环境变量配置"""
        config = {}
        
        if "DEEPSEEK_API_KEY" in env_vars:
            config.setdefault("deepseek", {})["api_key"] = env_vars["DEEPSEEK_API_KEY"]
        elif "deepseek" in env_vars:
            config.setdefault("deepseek", {})["api_key"] = env_vars["deepseek"]
        
        if "API_HOST" in env_vars:
            config.setdefault("api", {})["host"] = env_vars["API_HOST"]
        
        if "API_PORT" in env_vars:
            try:
                config.setdefault("api", {})["port"] = int(env_vars["API_PORT"])
            except ValueError:
                pass
        
        return config
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_deepseek_api_key(self) -> str:
        """获取DeepSeek API密钥"""
        api_key = self.get("deepseek.api_key")
        
        if not api_key:
            logger.warning("DeepSeek API密钥未设置，使用测试密钥")
            api_key = "test_api_key_for_development"
        
        return api_key

# 单例实例
_config_manager = None

def get_config_manager() -> ConfigManager:
    """获取配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager