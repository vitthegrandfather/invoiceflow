"""Login and current-user endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user
from app.core.errors import UnauthorizedError
from app.core.security import create_access_token, verify_demo_password
from app.db.session import get_session
from app.repositories.invoices import UserRepository
from app.schemas.auth import LoginRequest, LoginResponse, UserOut

router = APIRouter(tags=["auth"])


@router.post("/auth/login", response_model=LoginResponse)
async def login(body: LoginRequest, session: Annotated[AsyncSession, Depends(get_session)]) -> LoginResponse:
    if not verify_demo_password(body.password):
        raise UnauthorizedError("Invalid demo credentials. Use password demo-only.")
    user = await UserRepository(session).get_by_email(body.email.strip().lower())
    if user is None:
        # try original casing for seed emails
        user = await UserRepository(session).get_by_email(body.email.strip())
    if user is None:
        raise UnauthorizedError("Unknown demo user. Use one of the four Northwind Trading Demo accounts.")
    token = create_access_token(user_id=user.id, email=user.email, role=user.role, name=user.name)
    return LoginResponse(
        access_token=token,
        user=UserOut.model_validate(user),
    )


@router.get("/auth/me", response_model=UserOut)
async def me(user: Annotated[CurrentUser, Depends(get_current_user)]) -> UserOut:
    return UserOut(id=user.id, name=user.name, email=user.email, role=user.role, title=user.title)
