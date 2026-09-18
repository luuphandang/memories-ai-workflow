"""Canonical resource-access model and conservative conflict detection."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Access(str, Enum):
    READ = "READ"
    WRITE = "WRITE"


class Visibility(str, Enum):
    LOCAL = "LOCAL"
    TASK_SCOPED = "TASK_SCOPED"
    SHARED = "SHARED"


EXCLUSIVE_RESOURCE_KINDS = frozenset({
    "migration-sequence",
    "dependency-lockfile",
    "generated-contract",
    "composition-root",
    "shared-schema",
    "global-config",
})


@dataclass(frozen=True)
class ResourceAccess:
    repository: str
    path: str
    access: Access
    visibility: Visibility
    symbol: str | None = None
    whole_file_writer: bool = True


def overlaps(left: ResourceAccess, right: ResourceAccess) -> bool:
    if left.repository != right.repository:
        return False
    left_path = left.path.rstrip("/")
    right_path = right.path.rstrip("/")
    same_or_nested = (
        left_path == right_path
        or left_path.startswith(right_path + "/")
        or right_path.startswith(left_path + "/")
    )
    if not same_or_nested:
        return False
    if left_path != right_path:
        return True
    if not left.symbol or not right.symbol:
        return True
    if left.whole_file_writer or right.whole_file_writer:
        return True
    return left.symbol == right.symbol


def conflicts(left: ResourceAccess, right: ResourceAccess) -> bool:
    return overlaps(left, right) and Access.WRITE in {left.access, right.access}
