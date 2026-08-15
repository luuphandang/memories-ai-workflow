from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class RepositoryMemoryRef:
    repo: str
    path: str
    remote_url: str | None = None
    code_graph_id: str | None = None
    status: str | None = None
    supports_code_graph: bool = False
    reason: str | None = None


@dataclass
class MemoryQuery:
    task_id: str
    implementation_cycle: int
    change_cycle: int
    text: str
    repositories: list[str] = field(default_factory=list)
    asset_types: list[str] = field(default_factory=list)
    max_items: int = 8


@dataclass
class MemoryItem:
    provider: str
    asset_type: str
    asset_id: str
    title: str
    retrieved_at: str
    score: float | None = None
    source: str | None = None
    version: str | None = None


@dataclass
class MemorySnapshot:
    task_id: str
    implementation_cycle: int
    change_cycle: int
    provider: str
    query: MemoryQuery
    items: list[MemoryItem]
    generated_at: str
    content_sha256: str
    available: bool
    fallback: str | None = None
    error_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MemoryPublishEntry:
    category: str
    target: str
    summary: str
    content: str
    evidence: dict[str, Any]
    supersedes: str | None = None


@dataclass
class MemoryPublishRequest:
    task_id: str
    change_cycle: int
    entries: list[MemoryPublishEntry]


@dataclass
class MemoryPublishResult:
    published: list[dict[str, Any]]
    superseded: list[dict[str, Any]]
    errors: list[str]
    generated_at: str


@dataclass
class MemoryHealth:
    provider: str
    available: bool
    api_version: str | None = None
    wiki_supported: bool = False
    skill_supported: bool = False
    code_graph_supported: bool = False
    recall_supported: bool = False
    publish_supported: bool = False
    reason: str | None = None
