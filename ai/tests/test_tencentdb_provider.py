#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bin"))

from lib.memory.models import MemoryPublishEntry, MemoryPublishRequest, MemoryQuery, RepositoryMemoryRef
from lib.memory.tencentdb import TencentDBMemoryProvider


class StubTencentDBProvider(TencentDBMemoryProvider):
    def __init__(self, responses):
        self.calls = []
        self.responses = iter(responses)
        super().__init__()

    def _request(self, base_url, path, payload=None, method="GET"):
        self.calls.append((base_url, path, payload, method))
        return next(self.responses)


class TencentDBProviderContractTest(unittest.TestCase):
    def env(self):
        return patch.dict(
            os.environ,
            {
                "AI_MEMORY_API_KEY": "test-only-key",
                "AI_MEMORY_SERVICE_ID": "svc",
                "AI_MEMORY_TEAM_ID": "team",
                "AI_MEMORY_AGENT_ID": "claude",
                "AI_MEMORY_USER_ID": "workspace",
            },
            clear=False,
        )

    def query(self):
        return MemoryQuery("TASK-1", 1, 0, "find invariant", [], [], 3)

    def test_recall_uses_atomic_search_and_unwraps_items(self):
        with self.env():
            provider = StubTencentDBProvider([(True, 200, {"code": 0, "message": "ok", "data": {"items": [{"id": "mem-1", "version": "v1", "type": "instruction", "content": "Keep transactions atomic", "score": 0.91}]}})])
            snapshot = provider.recall(self.query())
        self.assertTrue(snapshot.available)
        self.assertEqual(snapshot.items[0].asset_id, "mem-1")
        _, path, payload, method = provider.calls[0]
        self.assertEqual((path, method), ("/v3/atomic/search", "POST"))
        self.assertNotIn("task_id", payload)
        self.assertNotIn("asset_types", payload)

    def test_http_200_business_error_is_unavailable(self):
        with self.env():
            provider = StubTencentDBProvider([(True, 200, {"code": 401, "message": "invalid key", "data": None})])
            snapshot = provider.recall(self.query())
        self.assertFalse(snapshot.available)

    def test_recall_falls_back_to_l0_while_l1_extraction_is_pending(self):
        responses = [
            (True, 200, {"code": 0, "message": "ok", "data": {"items": []}}),
            (True, 200, {"code": 0, "message": "ok", "data": {"messages": [{"id": "msg-1", "version": "v1", "role": "user", "content": "new durable note", "score": 0.8}]}}),
        ]
        with self.env():
            provider = StubTencentDBProvider(responses)
            snapshot = provider.recall(self.query())
        self.assertEqual(snapshot.items[0].asset_id, "msg-1")
        self.assertEqual(provider.calls[1][1], "/v3/conversation/search")

    def test_publish_uses_conversation_add_and_requires_accepted_id(self):
        entry = MemoryPublishEntry("known_issue", "ai/repos/a.md", "summary", "content", {"task_id": "TASK-1"})
        with self.env():
            provider = StubTencentDBProvider([(True, 200, {"code": 0, "message": "ok", "data": {"accepted_ids": ["msg-1"], "accepted_versions": ["v1"], "total_count": 1}})])
            result = provider.publish(MemoryPublishRequest("TASK-1", 0, [entry]))
        self.assertEqual(result.published[0]["asset_id"], "msg-1")
        _, path, payload, _ = provider.calls[0]
        self.assertEqual(path, "/v3/conversation/add")
        self.assertEqual(payload["session_id"], "knowledge-TASK-1")
        self.assertEqual(payload["messages"][0]["role"], "user")

    def test_code_graph_create_returns_id_and_pending_status(self):
        responses = [
            (True, 200, {"code": 0, "message": "ok", "data": {"items": [], "total": 0}}),
            (True, 201, {"code": 0, "message": "ok", "data": {"code_graph_id": "cg-1", "status": "pending"}}),
        ]
        with self.env():
            provider = StubTencentDBProvider(responses)
            result = provider.sync_repository(RepositoryMemoryRef("backend", "apps/backend", "https://example.test/repo.git", supports_code_graph=True))
        self.assertEqual(result.code_graph_id, "cg-1")
        self.assertEqual(result.status, "pending")
        self.assertEqual([call[1] for call in provider.calls], ["/code-graph/list", "/code-graph/create"])

    def test_code_graph_sync_uses_existing_id(self):
        responses = [
            (True, 200, {"code": 0, "message": "ok", "data": {"items": [{"code_graph_id": "cg-1", "repo_url": "https://example.test/repo.git", "status": "ready"}]}}),
            (True, 202, {"code": 0, "message": "ok", "data": {"code_graph_id": "cg-1", "status": "pending"}}),
        ]
        with self.env():
            provider = StubTencentDBProvider(responses)
            result = provider.sync_repository(RepositoryMemoryRef("backend", "apps/backend", "https://example.test/repo.git", supports_code_graph=True))
        self.assertEqual(provider.calls[1][2], {"code_graph_id": "cg-1"})
        self.assertEqual(result.status, "pending")

    def test_code_graph_list_error_does_not_create_duplicate(self):
        with self.env():
            provider = StubTencentDBProvider([(True, 200, {"code": 503, "message": "store down", "data": None})])
            result = provider.sync_repository(RepositoryMemoryRef("backend", "apps/backend", "https://example.test/repo.git", supports_code_graph=True))
        self.assertFalse(result.supports_code_graph)
        self.assertEqual(len(provider.calls), 1)


if __name__ == "__main__":
    unittest.main()
