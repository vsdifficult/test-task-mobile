from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from datetime import datetime
import json

from src.database.models.user import User, Role
from src.database.models.resource import Resource, ResourceCategory
from src.database.models.permission import RolePermission, UserPermission
from src.database.models.audit import AuditLog
from src.database.models.enums import ActionType, PermissionScope


class PermissionService:
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def check_permission(
        self,
        user: User,
        resource: Resource,
        action: ActionType,
        log_attempt: bool = True
    ) -> bool:
        
        if user.is_superuser:
            if log_attempt:
                await self._log_access(user, resource, action, True, "superuser")
            return True
        
        personal_perm = await self._check_user_permission(
            user.id, resource.id, action
        )
        if personal_perm is not None:
            if log_attempt:
                await self._log_access(user, resource, action, personal_perm, "personal")
            return personal_perm
        
        if resource.owner_id == user.id:
            if log_attempt:
                await self._log_access(user, resource, action, True, "owner")
            return True
        
        if resource.is_public and action == ActionType.READ:
            if log_attempt:
                await self._log_access(user, resource, action, True, "public")
            return True
        
        role_permission = await self._check_role_permissions(user, resource, action)
        if log_attempt:
            await self._log_access(
                user, resource, action, role_permission, 
                "role" if role_permission else "denied"
            )
        
        return role_permission
    
    async def _check_user_permission(
        self,
        user_id,
        resource_id,
        action: ActionType
    ) -> Optional[bool]:
        
        result = await self.session.scalar(
            select(UserPermission)
            .where(
                and_(
                    UserPermission.user_id == user_id,
                    UserPermission.resource_id == resource_id,
                    UserPermission.action == action,
                    or_(
                        UserPermission.expires_at.is_(None),
                        UserPermission.expires_at > datetime.utcnow()
                    )
                )
            )
            .order_by(UserPermission.granted_at.desc())
            .limit(1)
        )
        
        return result.is_allowed if result else None
    
    async def _check_role_permissions(
        self,
        user: User,
        resource: Resource,
        action: ActionType
    ) -> bool:
        
        all_roles = await self._get_all_user_roles(user)
        
        sorted_roles = sorted(all_roles, key=lambda r: r.priority, reverse=True)
        
        for role in sorted_roles:
            permissions = await self.session.scalars(
                select(RolePermission).where(
                    and_(
                        RolePermission.role_id == role.id,
                        RolePermission.category_id == resource.category_id,
                        RolePermission.action == action
                    )
                )
            )
            
            for perm in permissions:
                if await self._check_scope(user, resource, perm.scope):
                    if await self._check_conditions(user, resource, perm.conditions):
                        return perm.is_allowed
        
        return False
    
    async def _get_all_user_roles(self, user: User) -> List[Role]:
        
        all_roles = []
        roles_to_process = list(user.roles)
        processed_ids = set()
        
        while roles_to_process:
            role = roles_to_process.pop(0)
            
            if role.id in processed_ids:
                continue
            
            processed_ids.add(role.id)
            all_roles.append(role)
            
            if role.parent_role_id:
                parent = await self.session.get(Role, role.parent_role_id)
                if parent and parent.is_active:
                    roles_to_process.append(parent)
        
        return all_roles
    
    async def _check_scope(
        self,
        user: User,
        resource: Resource,
        scope: PermissionScope
    ) -> bool:
        
        if scope == PermissionScope.ALL:
            return True
        
        if scope == PermissionScope.OWN:
            return resource.owner_id == user.id
        
        if scope == PermissionScope.DEPARTMENT:
            if user.department_id and resource.owner.department_id:
                return user.department_id == resource.owner.department_id
            return False
        
        return False
    
    async def _check_conditions(
        self,
        user: User,
        resource: Resource,
        conditions: Optional[str]
    ) -> bool:
        
        if not conditions:
            return True
        
        try:
            cond_dict = json.loads(conditions)
            
            for key, value in cond_dict.items():
                if key == "resource.is_archived":
                    if resource.is_archived != value:
                        return False
                
                elif key == "user.department.code":
                    if not user.department or user.department.code != value:
                        return False
            
            return True
            
        except json.JSONDecodeError:
            return True
    
    async def _log_access(
        self,
        user: User,
        resource: Resource,
        action: ActionType,
        success: bool,
        reason: Optional[str] = None
    ):
        
        log_entry = AuditLog(
            user_id=user.id,
            resource_id=resource.id,
            action=action,
            resource_type=resource.category.resource_type.value,
            success=success,
            details=json.dumps({"reason": reason}) if reason else None
        )
        
        self.session.add(log_entry)
    
    async def grant_user_permission(
        self,
        granter: User,
        target_user_id,
        resource: Resource,
        action: ActionType,
        expires_at: Optional[datetime] = None
    ) -> bool:
        
        can_share = await self.check_permission(
            granter, resource, ActionType.SHARE, log_attempt=False
        )
        
        if not can_share and resource.owner_id != granter.id:
            return False
        
        existing = await self.session.scalar(
            select(UserPermission).where(
                and_(
                    UserPermission.user_id == target_user_id,
                    UserPermission.resource_id == resource.id,
                    UserPermission.action == action
                )
            )
        )
        
        if existing:
            existing.is_allowed = True
            existing.granted_by = granter.id
            existing.granted_at = datetime.utcnow()
            existing.expires_at = expires_at
        else:
            perm = UserPermission(
                user_id=target_user_id,
                resource_id=resource.id,
                action=action,
                is_allowed=True,
                granted_by=granter.id,
                expires_at=expires_at
            )
            self.session.add(perm)
        
        await self.session.commit()
        return True
    
    async def revoke_user_permission(
        self,
        granter: User,
        target_user_id,
        resource: Resource,
        action: ActionType
    ) -> bool:
        
        can_revoke = (
            resource.owner_id == granter.id or
            await self._is_permission_granter(
                granter.id, target_user_id, resource.id, action
            )
        )
        
        if not can_revoke:
            return False
        
        perm = await self.session.scalar(
            select(UserPermission).where(
                and_(
                    UserPermission.user_id == target_user_id,
                    UserPermission.resource_id == resource.id,
                    UserPermission.action == action
                )
            )
        )
        
        if perm:
            await self.session.delete(perm)
            await self.session.commit()
            return True
        
        return False
    
    async def _is_permission_granter(
        self, granter_id, user_id, resource_id, action: ActionType
    ) -> bool:
        
        result = await self.session.scalar(
            select(UserPermission).where(
                and_(
                    UserPermission.user_id == user_id,
                    UserPermission.resource_id == resource_id,
                    UserPermission.action == action,
                    UserPermission.granted_by == granter_id
                )
            )
        )
        
        return result is not None