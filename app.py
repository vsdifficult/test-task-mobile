
from fastapi import FastAPI, Request, status, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from contextlib import asynccontextmanager
from pydantic import BaseModel
import uuid
import logging as log

from src.database.database import *
from src.core.security import *
from src.core.dtos.user import *
from src.database.models.user import *
from src.database.models.permissions import *
from src.core.dependecies import get_current_user
from sqlalchemy import select, func

log.basicConfig(
    level=log.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = log.getLogger(__name__)

async def check_permission(session: AsyncSession, user: User, element_code: str, action: str) -> bool:
    element = await session.scalar(select(BusinessElement).where(BusinessElement.code == element_code))
    if not element:
        return False

    for role in user.roles:
        rule = await session.scalar(
            select(AccessRule).where(
                AccessRule.role_id == role.id,
                AccessRule.element_id == element.id
            )
        )
        if rule:
            if action == "read" and rule.read_permission:
                return True
            elif action == "read_all" and rule.read_all_permission:
                return True
            elif action == "create" and rule.create_permission:
                return True
            elif action == "update" and rule.update_permission:
                return True
            elif action == "update_all" and rule.update_all_permission:
                return True
            elif action == "delete" and rule.delete_permission:
                return True
            elif action == "delete_all" and rule.delete_all_permission:
                return True
    return False

def is_admin(user: User) -> bool:
    return any(role.name == "admin" for role in user.roles)

async def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        async with AsyncSessionLocal() as session:
            user_count = await session.scalar(select(func.count(User.id)))
            if user_count == 0:
                admin_role = Role(name="admin")
                user_role = Role(name="user")
                session.add_all([admin_role, user_role])
                await session.flush()

                docs_element = BusinessElement(code="documents")
                session.add(docs_element)
                await session.flush()

                admin_rule = AccessRule(
                    role_id=admin_role.id,
                    element_id=docs_element.id,
                    read_permission=True,
                    read_all_permission=True,
                    create_permission=True,
                    update_permission=True,
                    update_all_permission=True,
                    delete_permission=True,
                    delete_all_permission=True
                )
                user_rule = AccessRule(
                    role_id=user_role.id,
                    element_id=docs_element.id,
                    read_permission=True,
                    read_all_permission=False,
                    create_permission=False,
                    update_permission=False,
                    update_all_permission=False,
                    delete_permission=False,
                    delete_all_permission=False
                )
                session.add_all([admin_rule, user_rule])

                admin_user = User(
                    id=uuid.uuid4(),
                    email="admin@example.com",
                    password_hash=hash_password("admin123"),
                    first_name="Admin",
                    last_name="User"
                )
                regular_user = User(
                    id=uuid.uuid4(),
                    email="user@example.com",
                    password_hash=hash_password("user123"),
                    first_name="Regular",
                    last_name="User"
                )
                session.add_all([admin_user, regular_user])
                await session.flush()

                admin_user_role = UserRole(user_id=admin_user.id, role_id=admin_role.id)
                user_user_role = UserRole(user_id=regular_user.id, role_id=user_role.id)
                session.add_all([admin_user_role, user_user_role])

                await session.commit()

    yield

app = FastAPI(lifespan=lifespan)

security_scheme = HTTPBearer()

app.openapi_schema = None

original_openapi = app.openapi

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = original_openapi()
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    openapi_schema["security"] = [{"BearerAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

class AuthResponse(BaseModel):
    success: bool
    message: str | None = None
    error: str | None = None
    token: str | None = None

import time

@app.post("/logout")
async def logout_user(request: Request):
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=401)

    token = auth.split(" ")[1]

    payload = decode_token(token)

    jti = payload.get("jti")
    exp = payload.get("exp")

    if not jti or not exp:
        raise HTTPException(status_code=400, detail="Invalid token payload")

    ttl = int(exp - time.time())
    if ttl <= 0:
        return AuthResponse(success=True, message="token already expired")

    await redis_client.setex(
        f"jwt_blacklist:{jti}",
        ttl,
        1
    )

    return AuthResponse(
        success=True,
        message="logout successful"
    )



@app.post("/login")
async def login_user(session: AsyncSession = Depends(get_db),
                     user_login: UserLogin = None):
    user = await session.scalar(select(User).where(User.email == user_login.email))
    if not user or not user.is_active or not verify_password(user_login.password, user.password_hash):
        return AuthResponse(
            success=False,
            error="invalid credentials"
        )

    token = create_access_token({"sub": str(user.id)})
    return AuthResponse(
        success=True,
        message="login successful",
        token=token
    )


@app.post("/update")
async def update_user(session: AsyncSession = Depends(get_db),
                      current_user: User = Depends(get_current_user),
                      user_update: UserUpdate = None):
    if user_update.email:
        existing = await session.scalar(
            select(User).where(User.email == user_update.email, User.id != current_user.id)
        )
        if existing:
            return AuthResponse(
                success=False,
                error="email already in use"
            )
        current_user.email = user_update.email

    if user_update.first_name:
        current_user.first_name = user_update.first_name
    if user_update.last_name:
        current_user.last_name = user_update.last_name

    await session.commit()
    return AuthResponse(
        success=True,
        message="profile updated"
    )


@app.post("/register")
async def register_user(session: AsyncSession = Depends(get_db),
                        user: UserCreate = None):
    if user.password != user.again_password:
        return AuthResponse(
            success=False,
            error="passwords do not match"
        )

    existing_user = await session.scalar(select(User).where(User.email == user.email))
    if existing_user:
        return AuthResponse(
            success=False,
            error="email already registered"
        )

    usr = User(id=uuid.uuid4(),
               password_hash=hash_password(user.password),
               first_name=user.first_name,
               last_name=user.last_name,
               email=user.email)
    session.add(usr)
    await session.commit()
    return AuthResponse(
        success=True,
        message="user created"
    )

@app.delete("/delete")
async def delete_user(session: AsyncSession = Depends(get_db),
                      current_user: User = Depends(get_current_user)):
    current_user.is_active = False
    await session.commit()
    return AuthResponse(
        success=True,
        message="account deactivated"
    )

@app.get(
    "/documents",
)
async def list_documents(session: AsyncSession = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    if not await check_permission(session, current_user, "documents", "read"):
        raise HTTPException(status_code=403, detail="Forbidden")
    return [
        {"id": 1, "owner_id": "u1"},
        {"id": 2, "owner_id": "u2"}
    ]
