from datetime import datetime
from typing import List, Optional, Union

from pydantic import BaseModel, field_validator


class OdaiUpdateRequest(BaseModel):
    tags: Optional[List[str]] = None
    used: Optional[bool] = None
    deleted: Optional[bool] = None


class TagCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None


class TagUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class TagPermissionRequest(BaseModel):
    tag_id: int
    allowed: bool
    reason: Optional[str] = None


class ScheduleRequest(BaseModel):
    id: Optional[int] = None
    channel_id: Union[int, str]
    time: str
    enabled: Optional[bool] = True
    tag_mode: Optional[str] = "all"
    tag_list: Optional[List[str]] = []

    @field_validator('channel_id', mode='before')
    @classmethod
    def coerce_channel_id(cls, v):
        return int(v)


class TestPostRequest(BaseModel):
    channel_id: Union[int, str]

    @field_validator('channel_id', mode='before')
    @classmethod
    def coerce_channel_id(cls, v):
        return int(v)
    tag_mode: Optional[str] = None
    tag_list: Optional[List[str]] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    role: str


class UserCreateRequest(BaseModel):
    username: str
    password: str
    role: Optional[str] = "user"


class UserUpdateRequest(BaseModel):
    password: Optional[str] = None
    role: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    created_at: datetime
    updated_at: datetime


class InviteRegisterRequest(BaseModel):
    invite_token: str
    password: Optional[str] = None


class InviteCreateRequest(BaseModel):
    username: str
    role: str = "user"


class InviteResponse(BaseModel):
    invite_token: str
    expires_at: str


class SettingsRequest(BaseModel):
    bot_enabled: Optional[bool] = None
    timezone: Optional[str] = None


class GuildInfo(BaseModel):
    guild_id: str
    guild_name: Optional[str] = None
    role: str


class GlobalLoginResponse(BaseModel):
    access_token: str
    token_type: str
    role: str
    guilds: List[GuildInfo]
