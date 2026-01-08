from datetime import datetime, timedelta
import uuid
from passlib.context import CryptContext
import jwt
import redis.asyncio as redis

from src.config import get_settings

settings = get_settings()

redis_client = redis.from_url(settings.REDIS_URL)

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def hash_password(password: str) -> str:
    truncated_password = password[:72]  
    return pwd_context.hash(truncated_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    
    jti = str(uuid.uuid4())
    
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "jti": jti,
        "iat": datetime.utcnow()
    })
    
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


async def blacklist_token(jti: str, ttl: int):
    await redis_client.setex(f"jwt_blacklist:{jti}", ttl, 1)


async def is_token_blacklisted(jti: str) -> bool:
    return await redis_client.exists(f"jwt_blacklist:{jti}") > 0