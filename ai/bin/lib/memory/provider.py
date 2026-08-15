from __future__ import annotations

import abc
import os

from .models import (
    MemoryHealth,
    MemoryItem,
    MemoryPublishRequest,
    MemoryPublishResult,
    MemoryQuery,
    MemorySnapshot,
    RepositoryMemoryRef,
)

VALID_PROVIDERS = {"tencentdb", "fake"}


class MemoryProvider(abc.ABC):
    """Vendor-neutral memory backend contract.

    Every method must fail soft (return a result describing unavailability, never
    raise) so callers in `optional` mode can proceed with a static-context fallback.
    Callers running in `required` mode decide whether to turn an unavailable result
    into a SystemExit — the provider itself never raises for reachability reasons.
    """

    @abc.abstractmethod
    def health(self) -> MemoryHealth: ...

    @abc.abstractmethod
    def recall(self, query: MemoryQuery) -> MemorySnapshot: ...

    @abc.abstractmethod
    def publish(self, request: MemoryPublishRequest) -> MemoryPublishResult: ...

    @abc.abstractmethod
    def search_code(self, ref: RepositoryMemoryRef, query: str) -> list[MemoryItem]: ...

    @abc.abstractmethod
    def sync_repository(self, ref: RepositoryMemoryRef) -> RepositoryMemoryRef: ...


def provider_name() -> str:
    name = os.environ.get("AI_MEMORY_PROVIDER", "tencentdb").strip().lower()
    if name not in VALID_PROVIDERS:
        raise SystemExit(
            f"Invalid AI_MEMORY_PROVIDER={name!r}; expected tencentdb or fake"
        )
    return name


def get_provider() -> MemoryProvider:
    name = provider_name()
    if name == "fake":
        from .fake import FakeMemoryProvider

        return FakeMemoryProvider()
    from .tencentdb import TencentDBMemoryProvider

    return TencentDBMemoryProvider()
