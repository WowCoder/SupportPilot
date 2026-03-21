"""
Backward compatibility layer - imports from new app package

This file allows existing code to continue working during migration.
Deprecated: Use 'from app.config import ...' instead.
"""
from app.config import (
    Config,
    ProductionConfig,
    DevelopmentConfig,
    TestingConfig,
    get_config,
    config
)

__all__ = [
    'Config',
    'ProductionConfig',
    'DevelopmentConfig',
    'TestingConfig',
    'get_config',
    'config'
]
