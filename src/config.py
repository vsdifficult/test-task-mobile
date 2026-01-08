
import os
from functools import lru_cache


class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./auth_db_prod.sqlite")
    SECRET_KEY = os.getenv("SECRET_KEY", "SUPER_SECRET_KEY_CHANGE_IN_PRODUCTION")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

    APP_NAME = "Permission System API"
    APP_VERSION = "1.0.0"
    DEBUG = False
    
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
    
    AUDIT_LOG_RETENTION_DAYS = int(os.getenv("AUDIT_LOG_RETENTION_DAYS", "90"))
    
    PERMISSION_CACHE_TTL = int(os.getenv("PERMISSION_CACHE_TTL", "300"))  # 5 minutes


class DevSettings(Settings):
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./auth_db_dev.sqlite")
    DEBUG = True


class TestSettings(Settings):
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./auth_db_test.sqlite")
    DEBUG = True


@lru_cache
def get_settings():
    env = os.getenv("ENV", "dev")
    if env == "test":
        return TestSettings()
    if env == "dev":
        return DevSettings()
    return Settings()