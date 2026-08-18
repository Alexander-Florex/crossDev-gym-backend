from pydantic import BaseModel, EmailStr

from app.schemas.user import UserResponse


class RegisterRequest(BaseModel):
    tenant_name: str
    tenant_slug: str
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    phone: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class RegisterResponse(BaseModel):
    user: UserResponse
    tokens: TokenResponse
