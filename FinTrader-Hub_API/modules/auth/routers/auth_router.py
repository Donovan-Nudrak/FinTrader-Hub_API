from typing import Annotated

from fastapi import APIRouter, Depends, status

from core.schemas import APIResponse
from modules.auth.dependencies import get_auth_service, get_current_user
from modules.auth.models.user import User
from modules.auth.schemas import (
    AccessTokenResponse,
    LoginUserRequest,
    LogoutUserRequest,
    RefreshTokenRequest,
    RegisterUserRequest,
    TokenResponse,
    UserResponse,
)
from modules.auth.services import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=APIResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
)
def register_user(
    request: RegisterUserRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> APIResponse[UserResponse]:
    user = auth_service.register_user(request)
    return APIResponse(message="User registered successfully", data=user)


@router.post("/login", response_model=APIResponse[TokenResponse])
def login_user(
    request: LoginUserRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> APIResponse[TokenResponse]:
    tokens = auth_service.login_user(request.email, request.password)
    return APIResponse(message="Login successful", data=tokens)


@router.post("/refresh", response_model=APIResponse[AccessTokenResponse])
def refresh_access_token(
    request: RefreshTokenRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> APIResponse[AccessTokenResponse]:
    tokens = auth_service.refresh_access_token(request.refresh_token)
    return APIResponse(message="Access token refreshed successfully", data=tokens)


@router.post("/logout", response_model=APIResponse[None])
def logout_user(
    request: LogoutUserRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> APIResponse[None]:
    auth_service.logout_user(request.refresh_token)
    return APIResponse(message="Logout successful", data=None)


@router.get("/profile", response_model=APIResponse[UserResponse])
def get_user_profile(
    current_user: Annotated[User, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> APIResponse[UserResponse]:
    profile = auth_service.get_user_profile(current_user.id)
    return APIResponse(message="Profile retrieved successfully", data=profile)
