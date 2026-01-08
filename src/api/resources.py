from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from typing import List
import uuid
from datetime import datetime

from src.database.database import get_db
from src.database.models.user import User
from src.database.models.resource import Resource, ResourceCategory
from src.database.models.enums import ActionType
from src.core.dependencies import get_current_user
from src.core.services.permission_service import PermissionService
from src.core.dtos.resource import (
    ResourceCreate, 
    ResourceUpdate, 
    ResourceResponse,
    ResourceListResponse
)
from src.core.dtos.common import MessageResponse

router = APIRouter(prefix="/resources", tags=["Resources"])


@router.get("/categories")
async def list_categories(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    
    categories = await session.scalars(select(ResourceCategory))
    
    return [
        {
            "id": cat.id,
            "name": cat.name,
            "code": cat.code,
            "resource_type": cat.resource_type
        }
        for cat in categories
    ]


@router.get("", response_model=ResourceListResponse)
async def list_resources(
    category_code: str = None,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    permission_service = PermissionService(session)
    
    query = select(Resource).where(Resource.is_archived == False).options(
        selectinload(Resource.category),
        selectinload(Resource.owner).selectinload(User.department)
    )
    
    if category_code:
        category = await session.scalar(
            select(ResourceCategory).where(ResourceCategory.code == category_code)
        )
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        query = query.where(Resource.category_id == category.id)
    
    all_resources = await session.scalars(query)
    
    accessible_resources = []
    for resource in all_resources:
        if await permission_service.check_permission(
            current_user, resource, ActionType.READ, log_attempt=False
        ):
            accessible_resources.append(
                ResourceResponse(
                    id=resource.id,
                    title=resource.title,
                    content=resource.content,
                    category_code=resource.category.code,
                    owner_id=resource.owner_id,
                    is_public=resource.is_public,
                    is_archived=resource.is_archived,
                    created_at=resource.created_at,
                    updated_at=resource.updated_at
                )
            )
    
    return ResourceListResponse(
        total=len(accessible_resources),
        items=accessible_resources
    )


@router.get("/{resource_id}", response_model=ResourceResponse)
async def get_resource(
    resource_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    permission_service = PermissionService(session)
    
    result = await session.execute(
        select(Resource)
        .options(
            selectinload(Resource.category),
            selectinload(Resource.owner).selectinload(User.department)
        )
        .filter(Resource.id == resource_id)
    )
    resource = result.scalar_one_or_none()

    if not resource or resource.is_archived:
        raise HTTPException(status_code=404, detail="Resource not found")
    
    if not await permission_service.check_permission(
        current_user, resource, ActionType.READ
    ):
        raise HTTPException(status_code=403, detail="Access denied")
    
    return ResourceResponse(
        id=resource.id,
        title=resource.title,
        content=resource.content,
        category_code=resource.category.code,
        owner_id=resource.owner_id,
        is_public=resource.is_public,
        is_archived=resource.is_archived,
        created_at=resource.created_at,
        updated_at=resource.updated_at
    )


@router.post("", response_model=ResourceResponse, status_code=201)
async def create_resource(
    resource_data: ResourceCreate = Body(...),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    permission_service = PermissionService(session)
    
    category = await session.scalar(
        select(ResourceCategory).where(
            ResourceCategory.code == resource_data.category_code
        )
    )
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    temp_resource = Resource(
        id=uuid.uuid4(),
        category_id=category.id,
        owner_id=current_user.id,
        title="temp",
        content=""
    )
    
    if not await permission_service.check_permission(
        current_user, temp_resource, ActionType.CREATE, log_attempt=False
    ):
        raise HTTPException(
            status_code=403, 
            detail="You don't have permission to create resources in this category"
        )
    
    new_resource = Resource(
        id=uuid.uuid4(),
        category_id=category.id,
        owner_id=current_user.id,
        title=resource_data.title,
        content=resource_data.content,
        is_public=resource_data.is_public
    )
    
    session.add(new_resource)
    await session.commit()
    await session.refresh(new_resource)
    
    await permission_service._log_access(
        current_user, new_resource, ActionType.CREATE, True
    )
    await session.commit()
    
    return ResourceResponse(
        id=new_resource.id,
        title=new_resource.title,
        content=new_resource.content,
        category_code=category.code,
        owner_id=new_resource.owner_id,
        is_public=new_resource.is_public,
        is_archived=new_resource.is_archived,
        created_at=new_resource.created_at,
        updated_at=new_resource.updated_at
    )


@router.put("/{resource_id}", response_model=ResourceResponse)
async def update_resource(
    resource_id: uuid.UUID,
    resource_data: ResourceUpdate = Body(...),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    permission_service = PermissionService(session)
    
    result = await session.execute(
        select(Resource)
        .options(
            selectinload(Resource.category),
            selectinload(Resource.owner).selectinload(User.department)
        )
        .filter(Resource.id == resource_id)
    )
    resource = result.scalar_one_or_none()

    if not resource or resource.is_archived:
        raise HTTPException(status_code=404, detail="Resource not found")
    
    if not await permission_service.check_permission(
        current_user, resource, ActionType.UPDATE
    ):
        raise HTTPException(status_code=403, detail="Access denied")
    
    if resource_data.title is not None:
        resource.title = resource_data.title
    if resource_data.content is not None:
        resource.content = resource_data.content
    if resource_data.is_public is not None:
        resource.is_public = resource_data.is_public
    
    resource.updated_at = datetime.utcnow()
    
    await session.commit()
    await session.refresh(resource)
    
    return ResourceResponse(
        id=resource.id,
        title=resource.title,
        content=resource.content,
        category_code=resource.category.code,
        owner_id=resource.owner_id,
        is_public=resource.is_public,
        is_archived=resource.is_archived,
        created_at=resource.created_at,
        updated_at=resource.updated_at
    )


@router.delete("/{resource_id}", response_model=MessageResponse)
async def delete_resource(
    resource_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    permission_service = PermissionService(session)
    
    result = await session.execute(
        select(Resource)
        .options(
            selectinload(Resource.category),
            selectinload(Resource.owner).selectinload(User.department)
        )
        .filter(Resource.id == resource_id)
    )
    resource = result.scalar_one_or_none()

    if not resource or resource.is_archived:
        raise HTTPException(status_code=404, detail="Resource not found")
    
    if not await permission_service.check_permission(
        current_user, resource, ActionType.DELETE
    ):
        raise HTTPException(status_code=403, detail="Access denied")
    
    resource.is_archived = True
    resource.updated_at = datetime.utcnow()
    
    await session.commit()
    
    return MessageResponse(
        success=True,
        message="Resource deleted successfully"
    )