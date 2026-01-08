from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from sqlalchemy import select, func

from src.config import get_settings
from src.database.database import engine, AsyncSessionLocal, Base
from src.database.models.user import User, Role, UserRole, Department
from src.database.models.resource import ResourceCategory, Resource
from src.database.models.permission import RolePermission
from src.database.models.enums import ActionType, PermissionScope, ResourceType
from src.core.security import hash_password

from src.api import auth, resources

settings = get_settings()
logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    
    logger.info("Starting application...")
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSessionLocal() as session:
        user_count = await session.scalar(select(func.count(User.id)))
        
        if user_count == 0:
            logger.info("Initializing database with default data...")
            await initialize_default_data(session)
    
    logger.info("Application started successfully")
    
    yield
    
    logger.info("Shutting down application...")
    await engine.dispose()


async def initialize_default_data(session):
    
    it_dept = Department(name="IT Department", code="IT")
    hr_dept = Department(name="HR Department", code="HR")
    session.add_all([it_dept, hr_dept])
    await session.flush()
    
    admin_role = Role(name="Admin", code="admin", priority=80)
    manager_role = Role(name="Manager", code="manager", priority=50)
    user_role = Role(name="User", code="user", priority=10)
    viewer_role = Role(name="Viewer", code="viewer", priority=5)
    
    session.add_all([admin_role, manager_role, user_role, viewer_role])
    await session.flush()
    
    docs_category = ResourceCategory(
        name="Documents",
        code="documents",
        resource_type=ResourceType.DOCUMENT
    )
    projects_category = ResourceCategory(
        name="Projects",
        code="projects",
        resource_type=ResourceType.PROJECT
    )
    
    session.add_all([docs_category, projects_category])
    await session.flush()
    
    admin_perms = [
        RolePermission(
            role_id=admin_role.id,
            category_id=docs_category.id,
            action=ActionType.READ,
            scope=PermissionScope.ALL,
            is_allowed=True
        ),
        RolePermission(
            role_id=admin_role.id,
            category_id=docs_category.id,
            action=ActionType.CREATE,
            scope=PermissionScope.ALL,
            is_allowed=True
        ),
        RolePermission(
            role_id=admin_role.id,
            category_id=docs_category.id,
            action=ActionType.UPDATE,
            scope=PermissionScope.ALL,
            is_allowed=True
        ),
        RolePermission(
            role_id=admin_role.id,
            category_id=docs_category.id,
            action=ActionType.DELETE,
            scope=PermissionScope.ALL,
            is_allowed=True
        ),
    ]
    
    manager_perms = [
        RolePermission(
            role_id=manager_role.id,
            category_id=docs_category.id,
            action=ActionType.READ,
            scope=PermissionScope.DEPARTMENT,
            is_allowed=True
        ),
        RolePermission(
            role_id=manager_role.id,
            category_id=docs_category.id,
            action=ActionType.CREATE,
            scope=PermissionScope.ALL,
            is_allowed=True
        ),
        RolePermission(
            role_id=manager_role.id,
            category_id=docs_category.id,
            action=ActionType.UPDATE,
            scope=PermissionScope.DEPARTMENT,
            is_allowed=True
        ),
        RolePermission(
            role_id=manager_role.id,
            category_id=docs_category.id,
            action=ActionType.DELETE,
            scope=PermissionScope.OWN,
            is_allowed=True
        ),
        RolePermission(
            role_id=manager_role.id,
            category_id=docs_category.id,
            action=ActionType.SHARE,
            scope=PermissionScope.DEPARTMENT,
            is_allowed=True
        ),
    ]
    
    user_perms = [
        RolePermission(
            role_id=user_role.id,
            category_id=docs_category.id,
            action=ActionType.READ,
            scope=PermissionScope.OWN,
            is_allowed=True
        ),
        RolePermission(
            role_id=user_role.id,
            category_id=docs_category.id,
            action=ActionType.CREATE,
            scope=PermissionScope.ALL,
            is_allowed=True
        ),
        RolePermission(
            role_id=user_role.id,
            category_id=docs_category.id,
            action=ActionType.UPDATE,
            scope=PermissionScope.OWN,
            is_allowed=True
        ),
        RolePermission(
            role_id=user_role.id,
            category_id=docs_category.id,
            action=ActionType.DELETE,
            scope=PermissionScope.OWN,
            is_allowed=True
        ),
    ]
    
    viewer_perms = [
        RolePermission(
            role_id=viewer_role.id,
            category_id=docs_category.id,
            action=ActionType.READ,
            scope=PermissionScope.ALL,
            is_allowed=True
        ),
    ]
    
    session.add_all(admin_perms + manager_perms + user_perms + viewer_perms)
    
    admin_user = User(
        email="admin@example.com",
        password_hash=hash_password("admin123"),
        first_name="Admin",
        last_name="User",
        department_id=it_dept.id,
        is_superuser=False
    )
    
    manager_user = User(
        email="manager@example.com",
        password_hash=hash_password("manager123"),
        first_name="Manager",
        last_name="User",
        department_id=it_dept.id
    )
    
    regular_user = User(
        email="user@example.com",
        password_hash=hash_password("user123"),
        first_name="Regular",
        last_name="User",
        department_id=it_dept.id
    )
    
    viewer_user = User(
        email="viewer@example.com",
        password_hash=hash_password("viewer123"),
        first_name="Viewer",
        last_name="User",
        department_id=hr_dept.id
    )
    
    session.add_all([admin_user, manager_user, regular_user, viewer_user])
    await session.flush()
    
    user_roles = [
        UserRole(user_id=admin_user.id, role_id=admin_role.id),
        UserRole(user_id=manager_user.id, role_id=manager_role.id),
        UserRole(user_id=regular_user.id, role_id=user_role.id),
        UserRole(user_id=viewer_user.id, role_id=viewer_role.id),
    ]
    session.add_all(user_roles)
    
    doc1 = Resource(
        category_id=docs_category.id,
        owner_id=admin_user.id,
        title="Admin's Document",
        content="This is admin's document",
        is_public=False
    )
    
    doc2 = Resource(
        category_id=docs_category.id,
        owner_id=regular_user.id,
        title="User's Private Document",
        content="This is user's private document",
        is_public=False
    )
    
    doc3 = Resource(
        category_id=docs_category.id,
        owner_id=regular_user.id,
        title="Public Document",
        content="This is a public document everyone can read",
        is_public=True
    )
    
    session.add_all([doc1, doc2, doc3])
    
    await session.commit()
    logger.info("Database initialized with default data")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth.router)
app.include_router(resources.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Permission System API",
        "version": settings.APP_VERSION,
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )