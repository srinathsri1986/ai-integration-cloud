from typing import Literal

from pydantic import BaseModel, Field


UserRole = Literal[
    "CFO",
    "Finance Controller",
    "Integration Admin",
    "Viewer",
    "Developer",
]


class AuthUser(BaseModel):
    user_id: str = Field(alias="userId")
    email: str
    role: UserRole


class LoginRequest(BaseModel):
    email: str = "local-dev@example.com"
    role: UserRole = "Integration Admin"


class LoginResponse(BaseModel):
    access_token: str = Field(alias="accessToken")
    token_type: Literal["bearer"] = Field(default="bearer", alias="tokenType")
    user: AuthUser
