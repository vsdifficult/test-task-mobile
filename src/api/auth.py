from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import time

from src.database.database import get_db
from src.database.models.user import User, Role, UserRole
from src.core.dependencies import get_current_user, get_token
from src.core.security import (
    hash_password, 
    verify_password, 
    create_access_token,
    decode_token,
    blacklist_token
)
from src.core.dtos.user import UserCreate, UserLogin, UserResponse
from src.core.dtos.common import AuthResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=AuthResponse)
async def register_user(
    user_data: UserCreate = Body(...),
    session: AsyncSession = Depends(get_db)
):

    if user_data.password != user_data.again_password:
        return AuthResponse(
            success=False,
            error="Passwords do not match"
        )
    
    existing_user = await session.scalar(
        select(User).where(User.email == user_data.email)
    )
    if existing_user:
        return AuthResponse(
            success=False,
            error="Email already registered"
        )
    
    default_role = await session.scalar(
        select(Role).where(Role.code == "user")
    )
    
    new_user = User(
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        department_id=user_data.department_id
    )
    session.add(new_user)
    await session.flush()
    
    if default_role:
        user_role = UserRole(
            user_id=new_user.id,
            role_id=default_role.id
        )
        session.add(user_role)
    
    await session.commit()
    
    return AuthResponse(
        success=True,
        message="User registered successfully"
    )


@router.post("/login", response_model=AuthResponse)
async def login_user(
    credentials: UserLogin = Body(...),
    session: AsyncSession = Depends(get_db)
):

    user = await session.scalar(
        select(User).where(User.email == credentials.email)
    )
    
    if not user or not user.is_active:
        return AuthResponse(
            success=False,
            error="Invalid credentials"
        )
    
    if not verify_password(credentials.password, user.password_hash):
        return AuthResponse(
            success=False,
            error="Invalid credentials"
        )
    
    user.last_login = datetime.utcnow()
    await session.commit()
    
    token = create_access_token({"sub": str(user.id)})
    
    return AuthResponse(
        success=True,
        message="Login successful",
        token=token
    )


@router.post("/logout", response_model=AuthResponse)
async def logout_user(token: str = Depends(get_token)):
    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    jti = payload.get("jti")
    exp = payload.get("exp")
    
    if not jti or not exp:
        raise HTTPException(status_code=400, detail="Invalid token payload")
    
    ttl = int(exp - time.time())
    if ttl <= 0:
        return AuthResponse(
            success=True,
            message="Token already expired"
        )
    
    await blacklist_token(jti, ttl)
    
    return AuthResponse(
        success=True,
        message="Logout successful"
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        department_id=current_user.department_id,
        is_active=current_user.is_active
    )


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(
    current_user: User = Depends(get_current_user)
):

    new_token = create_access_token({"sub": str(current_user.id)})
    
    return AuthResponse(
        success=True,
        message="Token refreshed",
        token=new_token
    )