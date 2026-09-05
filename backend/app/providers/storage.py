"""In-memory / local sandbox object storage. Never talks to S3."""

from __future__ import annotations

from app.core.errors import ProviderMisconfiguredError


class SandboxObjectStorage:
    def __init__(self) -> None:
        self._objects: dict[str, tuple[bytes, str]] = {}

    async def put(self, key: str, data: bytes, content_type: str) -> str:
        self._objects[key] = (data, content_type)
        return f"sandbox://northwind/{key}"

    async def exists(self, key: str) -> bool:
        return key in self._objects


_STORAGE = SandboxObjectStorage()


def get_sandbox_storage() -> SandboxObjectStorage:
    return _STORAGE


class S3ObjectStorage:
    def __init__(self, bucket: str | None, access_key: str | None, secret_key: str | None) -> None:
        if not bucket or not access_key or not secret_key:
            raise ProviderMisconfiguredError(
                "OBJECT_STORAGE_PROVIDER=s3 requires bucket and credentials. "
                "InvoiceFlow will not silently fall back to sandbox storage."
            )
        raise ProviderMisconfiguredError("Live S3 is disabled in this fictional demonstration.")

    async def put(self, key: str, data: bytes, content_type: str) -> str:
        raise ProviderMisconfiguredError("Live S3 is disabled in this demonstration.")

    async def exists(self, key: str) -> bool:
        raise ProviderMisconfiguredError("Live S3 is disabled in this demonstration.")
