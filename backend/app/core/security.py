"""Demo JWT auth. Password is the shared fictional demo-only secret."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from app.core.config import get_settings
from app.core.constants import APPROVER_ROLES, MANAGER_ROLES
from app.core.errors import ForbiddenError, UnauthorizedError


def create_access_token(*, user_id: str, email: str, role: str, name: str) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "name": name,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.jwt_expire_minutes)).timestamp()),
        "iss": "invoiceflow-demo",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise UnauthorizedError("Invalid or expired demo token.") from exc


def verify_demo_password(password: str) -> bool:
    settings = get_settings()
    return password == settings.demo_password


def require_role(role: str, allowed: frozenset[str], action: str) -> None:
    if role not in allowed:
        raise ForbiddenError(f"Role '{role}' cannot {action}.")


def require_approver(role: str) -> None:
    require_role(role, APPROVER_ROLES, "approve, reject, correct fields, or decide duplicates")


def require_manager(role: str) -> None:
    require_role(role, MANAGER_ROLES, "retry delivery or edit vendors")


def require_admin(role: str) -> None:
    require_role(role, frozenset({"admin"}), "reset the demo workspace")
