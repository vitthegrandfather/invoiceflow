"""Auth schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class LoginRequest(BaseModel):
    email: str = Field(..., examples=["maya.chen@invoiceflow.example"])
    password: str = Field(..., examples=["demo-only"])


class UserOut(ORMModel):
    id: str
    name: str
    email: str
    role: str
    title: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
    workspace: str = "Northwind Trading Demo"
    note: str = "Demo credentials only. Password is the shared fictional secret demo-only."
