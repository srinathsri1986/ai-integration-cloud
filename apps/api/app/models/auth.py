from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


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


# --- Registration ---

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: UserRole = "Integration Admin"

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit.")
        return v


class RegisterResponse(BaseModel):
    message: str
    email: str


# --- Login ---

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str = Field(alias="accessToken")
    token_type: Literal["bearer"] = Field(default="bearer", alias="tokenType")
    user: AuthUser


# --- Token refresh ---

class RefreshRequest(BaseModel):
    refresh_token: str = Field(alias="refreshToken")


# --- Password reset ---

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit.")
        return v


class MessageResponse(BaseModel):
    message: str


# --- Legacy placeholder (kept for test compatibility) ---

class LegacyLoginRequest(BaseModel):
    email: str = "local-dev@example.com"
    role: UserRole = "Integration Admin"
