"""
Configuration Loader for Agentic RAG system.

Loads and manages configuration from YAML files.
"""
import os
import yaml
import logging
from typing import Any, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class ConfigLoader:
    """
    Load configuration from YAML files with environment variable overrides.

    Usage:
        config = ConfigLoader('config/rag_config.yaml')
        agent_config = config.get('agent')
        timeout = config.get('agent.timeout_seconds', default=30)
    """

    _instance: Optional['ConfigLoader'] = None
    _config: Dict[str, Any] = {}
    _config_path: str = ''

    def __new__(cls, config_path: str = None):
        """Singleton pattern - only one config instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            if config_path:
                cls._instance._load_config(config_path)
        return cls._instance

    def _load_config(self, config_path: str) -> None:
        """
        Load configuration from YAML file.

        Args:
            config_path: Path to YAML configuration file
        """
        self._config_path = config_path

        if not os.path.exists(config_path):
            logger.warning(f'Config file not found: {config_path}, using defaults')
            return

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f) or {}
            logger.info(f'Loaded config from {config_path}')
        except Exception as e:
            logger.error(f'Failed to load config: {e}')
            self._config = {}

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-notation key.

        Args:
            key: Dot-notation key (e.g., 'agent.timeout_seconds')
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                # Check environment variable override
                env_key = key.replace('.', '_').upper()
                if env_key in os.environ:
                    return os.environ[env_key]
                return default

        return value

    def get_all(self) -> Dict[str, Any]:
        """Get the entire configuration dictionary."""
        return self._config

    def reload(self) -> None:
        """Reload configuration from file."""
        if self._config_path:
            self._load_config(self._config_path)
        else:
            logger.warning('No config path set, cannot reload')


# Global config instance
def get_config() -> ConfigLoader:
    """Get or create the global configuration loader."""
    config_path = os.environ.get('RAG_CONFIG_PATH', 'config/rag_config.yaml')
    return ConfigLoader(config_path)
