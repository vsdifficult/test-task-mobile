import os
from functools import lru_cache

class Settings:
    """Production settings class"""
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./auth_db_prod.sqlite")
    SECRET_KEY = os.getenv("SECRET_KEY", "secret_key")

class DevSettings(Settings):
    """Development settings class"""
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./auth_db_dev.sqlite")

class TestSettings(Settings):
    """Test settings class"""
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./auth_db_test.sqlite")

@lru_cache
def get_settings():
    """Return settings based on ENV variable"""
    env = os.getenv("ENV", "dev")
    if env == "test":
        return TestSettings()
    if env == "dev":
        return DevSettings()
    return Settings()  