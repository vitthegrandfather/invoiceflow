"""FastAPI dependencies: DB session, current user, request id."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import UnauthorizedError
from app.core.security import decode_access_token
from app.db.session import get_session
from app.repositories.invoices import UserRepository, WorkspaceRepository
from app.services.invoices import InvoiceService


async def db_session(session: Annotated[AsyncSession, Depends(get_session)]) -> AsyncIterator[AsyncSession]:
    yield session


@dataclass
class CurrentUser:
    id: str
    name: str
    email: str
    role: str
    title: str
    workspace_id: str


async def get_current_user(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    authorization: Annotated[str | None, Header()] = None,
) -> CurrentUser:
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise UnauthorizedError("Missing Authorization Bearer token.")
    payload = decode_access_token(token)
    repo = UserRepository(session)
    user = await repo.get(str(payload.get("sub") or ""))
    if user is None:
        raise UnauthorizedError("User no longer exists in the demo workspace.")
    request.state.user_id = user.id
    request.state.role = user.role
    return CurrentUser(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        title=user.title,
        workspace_id=user.workspace_id,
    )


async def get_invoice_service(session: Annotated[AsyncSession, Depends(get_session)]) -> InvoiceService:
    return InvoiceService(session)


async def demo_workspace_id(session: Annotated[AsyncSession, Depends(get_session)]) -> str:
    ws = await WorkspaceRepository(session).get_demo()
    if ws is None:
        raise UnauthorizedError("Demo workspace is not seeded.")
    return ws.id


def actor_from(user: CurrentUser) -> dict[str, str]:
    return {"actor": user.name, "actor_role": user.role, "actor_id": user.id}
