from pydantic import BaseModel
from typing import List, Optional


class GoogleLoginRequest(BaseModel):
    """Google OAuth login request schema"""
    access_token: str


class UserSchema(BaseModel):
    """User response schema"""
    id: int
    username: str
    email: str
    display_name: Optional[str] = None
    notification_enabled: bool = True


class LoginResponse(BaseModel):
    """Login response schema"""
    access_token: str
    refresh_token: str
    user: UserSchema


class CharacterSchema(BaseModel):
    ocid: str
    character_name: str
    world_name: str
    character_class: str
    character_level: int


class AccountSchema(BaseModel):
    account_id: str
    character_list: List[CharacterSchema]


class CharacterListSchema(BaseModel):
    account_list: List[AccountSchema]
