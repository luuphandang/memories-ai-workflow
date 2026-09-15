#!/usr/bin/env python3
"""Regression coverage for workflow_issue.md #7: port allocation and per-task compose
generation must never collide, and must derive from the real
apps/backend/docker/docker-compose.yml infrastructure profile rather than a hand-duplicated
second file that could silently drift out of sync. No Docker daemon needed for these --
docker_infra.py's real up/health-check/teardown lifecycle is exercised separately in
test_docker_infra_lifecycle.py, which does require Docker.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import socket
import tempfile
import unittest

import yaml

AI_BIN = Path(__file__).resolve().parents[1] / "bin"


def load_docker_infra():
    import sys
    sys.path.insert(0, str(AI_BIN))
    spec = importlib.util.spec_from_file_location("docker_infra_test", AI_BIN / "lib" / "docker_infra.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


FIXTURE_COMPOSE = {
    "name": "memories-backend",
    "services": {
        "postgres": {
            "image": "postgres:16-alpine",
            "profiles": ["infrastructure"],
            "environment": {"POSTGRES_USER": "memories", "POSTGRES_PASSWORD": "memories", "POSTGRES_DB": "memories"},
            "ports": ["5432:5432"],
            "volumes": ["postgres_data:/var/lib/postgresql/data"],
            "healthcheck": {"test": ["CMD-SHELL", "pg_isready -U memories"]},
        },
        "redis": {
            "image": "redis:7-alpine",
            "profiles": ["infrastructure"],
            "ports": ["6379:6379"],
            "volumes": ["redis_data:/data"],
        },
        "minio": {
            "image": "minio/minio:latest",
            "profiles": ["infrastructure"],
            "ports": ["9000:9000", "9001:9001"],
            "volumes": ["minio_data:/data"],
        },
        "minio-init": {
            "image": "minio/mc:latest",
            "profiles": ["infrastructure"],
            "depends_on": {"minio": {"condition": "service_healthy"}},
        },
        "api": {
            "image": "should-not-appear",
            "profiles": ["development"],
            "ports": ["3000:3000"],
        },
    },
    "volumes": {"postgres_data": None, "redis_data": None, "minio_data": None},
}


class AllocateFreePortsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.docker_infra = load_docker_infra()

    def test_ports_are_distinct_and_bindable(self) -> None:
        ports = self.docker_infra.allocate_free_ports(6)
        self.assertEqual(len(ports), len(set(ports)))
        for port in ports:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                s.bind(("127.0.0.1", port))
            finally:
                s.close()


class GenerateComposeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.docker_infra = load_docker_infra()

    def _write_fixture(self, root: Path) -> Path:
        path = root / "docker-compose.yml"
        path.write_text(yaml.safe_dump(FIXTURE_COMPOSE, sort_keys=False), encoding="utf-8")
        return path

    def test_only_infrastructure_profile_services_are_kept(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = self._write_fixture(root)
            output = root / "generated.yml"
            self.docker_infra.generate_compose("TEST-1", source, output)
            generated = yaml.safe_load(output.read_text(encoding="utf-8"))
            self.assertEqual(set(generated["services"]), {"postgres", "redis", "minio", "minio-init"})
            self.assertNotIn("api", generated["services"])

    def test_ports_and_volumes_and_project_name_are_task_scoped(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = self._write_fixture(root)
            output_a = root / "a.yml"
            output_b = root / "b.yml"
            manifest_a = self.docker_infra.generate_compose("TASK-A", source, output_a)
            manifest_b = self.docker_infra.generate_compose("TASK-B", source, output_b)

            self.assertEqual(manifest_a["project_name"], "memories-backend-task-a")
            self.assertEqual(manifest_b["project_name"], "memories-backend-task-b")

            ports_a = set(manifest_a["ports"].values())
            ports_b = set(manifest_b["ports"].values())
            self.assertEqual(len(ports_a), 4)
            self.assertEqual(ports_a & ports_b, set())  # no collision across two tasks

            generated_a = yaml.safe_load(output_a.read_text(encoding="utf-8"))
            self.assertEqual(set(generated_a["volumes"]), {"task-a_postgres_data", "task-a_redis_data", "task-a_minio_data"})
            self.assertNotIn("profiles", generated_a["services"]["postgres"])

    def test_container_ports_are_preserved_only_host_side_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = self._write_fixture(root)
            output = root / "generated.yml"
            manifest = self.docker_infra.generate_compose("TEST-2", source, output)
            generated = yaml.safe_load(output.read_text(encoding="utf-8"))
            postgres_port_spec = generated["services"]["postgres"]["ports"][0]
            self.assertTrue(postgres_port_spec.endswith(":5432"))
            self.assertEqual(int(postgres_port_spec.split(":")[0]), manifest["ports"]["postgres"])
            minio_specs = generated["services"]["minio"]["ports"]
            self.assertTrue(minio_specs[0].endswith(":9000"))
            self.assertTrue(minio_specs[1].endswith(":9001"))

    def test_missing_expected_service_fails_clearly(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            broken = dict(FIXTURE_COMPOSE)
            broken["services"] = {k: v for k, v in FIXTURE_COMPOSE["services"].items() if k != "redis"}
            path = root / "docker-compose.yml"
            path.write_text(yaml.safe_dump(broken, sort_keys=False), encoding="utf-8")
            with self.assertRaises(SystemExit) as ctx:
                self.docker_infra.generate_compose("TEST-3", path, root / "generated.yml")
            self.assertIn("redis", str(ctx.exception))


class InfraEnvForManifestTest(unittest.TestCase):
    def setUp(self) -> None:
        self.docker_infra = load_docker_infra()

    def test_env_points_at_localhost_allocated_ports(self) -> None:
        manifest = {"ports": {"postgres": 15432, "redis": 16379, "minio_api": 19000, "minio_console": 19001}}
        env = self.docker_infra.infra_env_for_manifest(manifest)
        self.assertEqual(env["DATABASE_HOST"], "localhost")
        self.assertEqual(env["DATABASE_PORT"], "15432")
        self.assertEqual(env["REDIS_PORT"], "16379")
        self.assertEqual(env["BULLMQ_REDIS_PORT"], "16379")
        self.assertEqual(env["S3_ENDPOINT"], "http://localhost:19000")


if __name__ == "__main__":
    unittest.main()
