from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

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

DEFAULT_BASE_URL = "http://127.0.0.1:8420"
DEFAULT_KNOWLEDGE_BASE_URL = "http://127.0.0.1:8424"
DEFAULT_TIMEOUT_SECONDS = 10


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _timeout_seconds() -> int:
    config_timeout = DEFAULT_TIMEOUT_SECONDS
    try:
        from . import load_config

        config_timeout = int(load_config().get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS))
    except (TypeError, ValueError):
        pass
    raw = os.environ.get("AI_MEMORY_TIMEOUT_SECONDS", str(config_timeout)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise SystemExit(f"AI_MEMORY_TIMEOUT_SECONDS must be an integer, found {raw!r}") from exc
    if value <= 0:
        raise SystemExit("AI_MEMORY_TIMEOUT_SECONDS must be greater than zero")
    return value


class TencentDBMemoryProvider(MemoryProvider):
    """HTTP adapter for TencentDB Agent Memory (MemoryCore + MemoryKnowledge).

    Uses stdlib urllib only -- see ai/integrations/tencentdb-memory/README.md for why
    (no HTTP client dependency exists anywhere in ai/ today; the upstream Python SDK
    pulls in httpx and exposes far more surface than the five methods this needs).
    Every call fails soft: transport/HTTP errors become an "unavailable" result rather
    than a raised exception, so `optional` mode always has something to fall back to.
    """

    def __init__(self) -> None:
        self.base_url = os.environ.get("AI_MEMORY_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
        self.knowledge_base_url = os.environ.get(
            "AI_MEMORY_KNOWLEDGE_BASE_URL", DEFAULT_KNOWLEDGE_BASE_URL
        ).rstrip("/")
        self.api_key = os.environ.get("AI_MEMORY_API_KEY", "").strip()
        self.service_id = os.environ.get("AI_MEMORY_SERVICE_ID", "default").strip() or "default"
        self.team_id = os.environ.get("AI_MEMORY_TEAM_ID", "default").strip() or "default"
        self.agent_id = os.environ.get("AI_MEMORY_AGENT_ID", "claude").strip() or "claude"
        self.user_id = os.environ.get("AI_MEMORY_USER_ID", "workspace").strip() or "workspace"
        self.timeout = _timeout_seconds()

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json", "x-tdai-service-id": self.service_id}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _request(
        self,
        base_url: str,
        path: str,
        payload: dict[str, Any] | None = None,
        method: str = "GET",
    ) -> tuple[bool, int | None, dict[str, Any] | None]:
        """Return (ok, status_code, data). Never raises."""
        url = f"{base_url}{path}"
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(url, data=body, headers=self._headers(), method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read()
                data = json.loads(raw) if raw else {}
                return True, response.status, data
        except urllib.error.HTTPError as exc:
            try:
                data = json.loads(exc.read())
            except Exception:
                data = None
            return False, exc.code, data
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            return False, None, None

    @staticmethod
    def _unwrap(data: dict[str, Any] | None) -> tuple[bool, Any, str | None]:
        """Validate a Core v2/v3 or Knowledge response envelope."""
        if not isinstance(data, dict):
            return False, None, "malformed response"
        code = data.get("code")
        if code != 0:
            return False, data.get("data"), str(data.get("message") or f"business error {code}")
        return True, data.get("data"), None

    def _identity(self, task_id: str | None = None) -> dict[str, str]:
        result = {
            "team_id": self.team_id,
            "agent_id": self.agent_id,
            "user_id": self.user_id,
        }
        if task_id:
            result["task_id"] = task_id
        return result

    def health(self) -> MemoryHealth:
        core_ok, _, core_data = self._request(self.base_url, "/health")
        if not core_ok:
            return MemoryHealth(
                provider="tencentdb",
                available=False,
                reason=f"MemoryCore health check failed ({self.base_url}/health)",
            )
        knowledge_ok, _, _ = self._request(self.knowledge_base_url, "/health")
        core_data = core_data or {}
        authenticated = bool(self.api_key)
        return MemoryHealth(
            provider="tencentdb",
            available=True,
            api_version=core_data.get("version"),
            recall_supported=authenticated,
            publish_supported=authenticated,
            wiki_supported=knowledge_ok,
            code_graph_supported=knowledge_ok and authenticated,
            skill_supported=authenticated,
            reason=(
                "AI_MEMORY_API_KEY is required for Core v3 and Knowledge data-plane calls"
                if not authenticated
                else None if knowledge_ok
                else "MemoryKnowledge service unreachable; wiki/code_graph unavailable"
            ),
        )

    def recall(self, query: MemoryQuery) -> MemorySnapshot:
        payload = {
            # Do not scope retrieval by task_id: this layer exists specifically to
            # carry approved knowledge across tasks. The source task stays inside
            # the published JSON evidence and the local supersession ledger.
            **self._identity(),
            "query": query.text,
            "limit": query.max_items,
        }
        ok, _, response = self._request(self.base_url, "/v3/atomic/search", payload=payload, method="POST")
        envelope_ok, data, _ = self._unwrap(response) if ok else (False, None, None)
        generated_at = _now_iso()
        if not envelope_ok or not isinstance(data, dict):
            return MemorySnapshot(
                task_id=query.task_id,
                implementation_cycle=query.implementation_cycle,
                change_cycle=query.change_cycle,
                provider="tencentdb",
                query=query,
                items=[],
                generated_at=generated_at,
                content_sha256="",
                available=False,
                fallback="static_context",
                error_code="MEMORY_UNAVAILABLE",
            )
        items: list[MemoryItem] = []
        for raw_item in data.get("items", []) or []:
            if not isinstance(raw_item, dict):
                continue
            items.append(
                MemoryItem(
                    provider="tencentdb",
                    asset_type=str(raw_item.get("type") or "chat_memory"),
                    asset_id=str(raw_item.get("asset_id") or raw_item.get("id") or ""),
                    title=str(raw_item.get("background") or raw_item.get("content") or "")[:240],
                    retrieved_at=generated_at,
                    score=raw_item.get("score"),
                    source=None,
                    version=raw_item.get("version"),
                )
            )
        # Conversation writes are durable in L0 immediately, while L1 extraction is
        # asynchronous. Search L0 when L1 has no hit so a just-published entry is not
        # invisible to the next Claude run.
        if not items:
            ok, _, response = self._request(
                self.base_url,
                "/v3/conversation/search",
                payload=payload,
                method="POST",
            )
            conversation_ok, conversation_data, _ = (
                self._unwrap(response) if ok else (False, None, None)
            )
            if conversation_ok and isinstance(conversation_data, dict):
                for raw_item in conversation_data.get("messages", []) or []:
                    if not isinstance(raw_item, dict):
                        continue
                    content = str(raw_item.get("content") or "")
                    items.append(
                        MemoryItem(
                            provider="tencentdb",
                            asset_type="chat_memory",
                            asset_id=str(raw_item.get("id") or ""),
                            title=content[:240],
                            retrieved_at=generated_at,
                            score=raw_item.get("score"),
                            version=raw_item.get("version"),
                        )
                    )
        return MemorySnapshot(
            task_id=query.task_id,
            implementation_cycle=query.implementation_cycle,
            change_cycle=query.change_cycle,
            provider="tencentdb",
            query=query,
            items=items,
            generated_at=generated_at,
            content_sha256="",
            available=True,
        )

    def publish(self, request: MemoryPublishRequest) -> MemoryPublishResult:
        published: list[dict[str, Any]] = []
        errors: list[str] = []
        for entry in request.entries:
            content = json.dumps(
                {
                    "category": entry.category,
                    "target": entry.target,
                    "summary": entry.summary,
                    "content": entry.content,
                    "evidence": entry.evidence,
                    "change_cycle": request.change_cycle,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
            payload = {
                **self._identity(),
                "session_id": f"knowledge-{request.task_id}",
                "messages": [{"role": "user", "content": content}],
            }
            ok, _, response = self._request(
                self.base_url, "/v3/conversation/add", payload=payload, method="POST"
            )
            envelope_ok, data, reason = self._unwrap(response) if ok else (False, None, None)
            accepted_ids = data.get("accepted_ids", []) if isinstance(data, dict) else []
            if not envelope_ok or not accepted_ids:
                errors.append(f"publish failed for target={entry.target}: {reason or 'backend unavailable'}")
                continue
            asset_id = str(accepted_ids[0])
            published.append({"asset_id": asset_id, "category": entry.category, "target": entry.target})
        return MemoryPublishResult(
            published=published,
            superseded=[],
            errors=errors,
            generated_at=_now_iso(),
        )

    def search_code(self, ref: RepositoryMemoryRef, query: str) -> list[MemoryItem]:
        if not ref.supports_code_graph:
            return []
        if not ref.code_graph_id:
            return []
        payload = {"code_graph_id": ref.code_graph_id, "query": query, "limit": 10}
        ok, _, data = self._request(
            self.knowledge_base_url, "/code-graph/search", payload=payload, method="POST"
        )
        envelope_ok, payload_data, _ = self._unwrap(data) if ok else (False, None, None)
        if not envelope_ok or not isinstance(payload_data, dict):
            return []
        generated_at = _now_iso()
        items: list[MemoryItem] = []
        text = payload_data.get("text")
        if isinstance(text, str) and text:
            items.append(MemoryItem(provider="tencentdb", asset_type="code_graph", asset_id=ref.code_graph_id, title=text[:240], retrieved_at=generated_at, source=ref.remote_url))
        return items

    def sync_repository(self, ref: RepositoryMemoryRef) -> RepositoryMemoryRef:
        if not ref.supports_code_graph:
            return ref
        list_payload = {**self._identity(), "limit": 100, "offset": 0}
        ok, _, response = self._request(self.knowledge_base_url, "/code-graph/list", list_payload, "POST")
        envelope_ok, data, reason = self._unwrap(response) if ok else (False, None, None)
        if not envelope_ok or not isinstance(data, dict):
            return RepositoryMemoryRef(
                repo=ref.repo,
                path=ref.path,
                remote_url=ref.remote_url,
                supports_code_graph=False,
                reason=reason or "TencentDB CodeGraph list failed",
            )
        existing = None
        existing = next((item for item in data.get("items", []) if item.get("repo_url") == ref.remote_url), None)
        if existing:
            code_graph_id = str(existing.get("code_graph_id") or "")
            status = str(existing.get("status") or "")
            if status == "ready":
                ok, _, response = self._request(self.knowledge_base_url, "/code-graph/sync", {"code_graph_id": code_graph_id}, "POST")
                envelope_ok, data, reason = self._unwrap(response) if ok else (False, None, None)
                if not envelope_ok:
                    return RepositoryMemoryRef(repo=ref.repo, path=ref.path, remote_url=ref.remote_url, code_graph_id=code_graph_id, status=status, supports_code_graph=False, reason=reason or "TencentDB CodeGraph sync failed")
                status = str(data.get("status") or "pending") if isinstance(data, dict) else "pending"
            return RepositoryMemoryRef(repo=ref.repo, path=ref.path, remote_url=ref.remote_url, code_graph_id=code_graph_id, status=status, supports_code_graph=True)

        create_payload = {**self._identity(), "repo_url": ref.remote_url}
        ok, _, response = self._request(self.knowledge_base_url, "/code-graph/create", create_payload, "POST")
        envelope_ok, data, reason = self._unwrap(response) if ok else (False, None, None)
        if not envelope_ok or not isinstance(data, dict) or not data.get("code_graph_id"):
            return RepositoryMemoryRef(
                repo=ref.repo,
                path=ref.path,
                remote_url=ref.remote_url,
                supports_code_graph=False,
                reason=reason or "TencentDB CodeGraph create failed",
            )
        return RepositoryMemoryRef(repo=ref.repo, path=ref.path, remote_url=ref.remote_url, code_graph_id=str(data["code_graph_id"]), status=str(data.get("status") or "pending"), supports_code_graph=True)
