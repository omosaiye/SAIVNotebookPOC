from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class UserRecord(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    user_id: str = Field(alias="userId")
    email: str
    password_hash: str = Field(alias="passwordHash")
    is_active: bool = Field(default=True, alias="isActive")


class WorkspaceMembershipRecord(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    workspace_id: str = Field(alias="workspaceId")
    user_id: str = Field(alias="userId")
    role: str


class AuthSessionRecord(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    token: str
    user_id: str = Field(alias="userId")
    created_at: datetime = Field(alias="createdAt")
    expires_at: datetime = Field(alias="expiresAt")


class AuthContext(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    user_id: str = Field(alias="userId")
    email: str


class WorkspaceAccessContext(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    workspace_id: str = Field(alias="workspaceId")
    user_id: str = Field(alias="userId")
    role: str


class AuditEventRecord(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    actor_user_id: str | None = Field(default=None, alias="actorUserId")
    workspace_id: str | None = Field(default=None, alias="workspaceId")
    entity_type: str = Field(alias="entityType")
    entity_id: str | None = Field(default=None, alias="entityId")
    action: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(alias="createdAt")


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    access_token: str = Field(alias="accessToken")
    token_type: str = Field(default="bearer", alias="tokenType")
    expires_at: datetime = Field(alias="expiresAt")
    user_id: str = Field(alias="userId")
    email: str
    workspace_ids: list[str] = Field(default_factory=list, alias="workspaceIds")


class AuthProfileResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    user_id: str = Field(alias="userId")
    email: str
    workspace_ids: list[str] = Field(default_factory=list, alias="workspaceIds")

