from __future__ import annotations

from datetime import datetime, timezone

from .models import (
    MemoryHealth,
    MemoryItem,
    MemoryPublishRequest,
    MemoryPublishResult,
    MemoryQuery,
    MemorySnapshot,
    RepositoryMemoryRef,
)
from .provider import MemoryProvider


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


class FakeMemoryProvider(MemoryProvider):
    """Deterministic, offline, always-available provider.

    Selected via AI_MEMORY_PROVIDER=fake. Used by `self-check --smoke` and unit tests
    so they can exercise the full enabled/recall/publish/sync path without a running
    TencentDB instance. Returns fixed, valid data -- it is not a fault-injecting fake;
    unavailable-path tests patch os.environ instead (see ai/tests/test_memory.py).
    """

    def health(self) -> MemoryHealth:
        return MemoryHealth(
            provider="fake",
            available=True,
            api_version="fake-1.0.0",
            wiki_supported=True,
            skill_supported=True,
            code_graph_supported=True,
            recall_supported=True,
            publish_supported=True,
        )

    def recall(self, query: MemoryQuery) -> MemorySnapshot:
        generated_at = _now_iso()
        items = [
            MemoryItem(
                provider="fake",
                asset_type="wiki",
                asset_id="wiki-fake-0001",
                title=f"Fake recall result for {query.task_id}",
                retrieved_at=generated_at,
                source="fake://wiki/0001",
            )
        ]
        return MemorySnapshot(
            task_id=query.task_id,
            implementation_cycle=query.implementation_cycle,
            change_cycle=query.change_cycle,
            provider="fake",
            query=query,
            items=items[: query.max_items] if query.max_items else items,
            generated_at=generated_at,
            content_sha256="",
            available=True,
        )

    def publish(self, request: MemoryPublishRequest) -> MemoryPublishResult:
        # asset_id includes task_id/change_cycle (not just a call-local counter) so
        # republishing the same task across change cycles yields distinct ids, the
        # way a real backend would -- callers rely on this for supersession tests.
        published = [
            {
                "asset_id": f"fake-{request.task_id}-{request.change_cycle}-{index:04d}",
                "category": entry.category,
                "target": entry.target,
            }
            for index, entry in enumerate(request.entries, start=1)
        ]
        return MemoryPublishResult(
            published=published,
            superseded=[],
            errors=[],
            generated_at=_now_iso(),
        )

    def search_code(self, ref: RepositoryMemoryRef, query: str) -> list[MemoryItem]:
        if not ref.supports_code_graph:
            return []
        return [
            MemoryItem(
                provider="fake",
                asset_type="code_graph",
                asset_id=f"cg-fake-{ref.repo}",
                title=f"Fake code graph result for {query!r} in {ref.repo}",
                retrieved_at=_now_iso(),
                source=ref.path,
            )
        ]

    def sync_repository(self, ref: RepositoryMemoryRef) -> RepositoryMemoryRef:
        return ref
