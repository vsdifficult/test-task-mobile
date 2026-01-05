from fastapi import Depends, HTTPException, Request, status
import jwt, uuid 

from src.core.security import decode_token
from src.database.models.user import User
from src.database.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> User:
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=401)

    token = auth.split(" ")[1]

    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.DecodeError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = await db.scalar(select(User).where(User.id == uuid.UUID(user_id)))

    if not user or not user.is_active:
        raise HTTPException(status_code=401)

    return user
