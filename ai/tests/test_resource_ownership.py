from __future__ import annotations

import unittest

from ai.bin.lib.resources import Access, ResourceAccess, Visibility, conflicts


class ResourceOwnershipTest(unittest.TestCase):
    def access(
        self, path: str, mode: Access, *, repo: str = "backend", symbol: str | None = None,
        whole_file_writer: bool = True,
    ) -> ResourceAccess:
        return ResourceAccess(repo, path, mode, Visibility.SHARED, symbol, whole_file_writer)

    def test_read_read_is_safe(self) -> None:
        self.assertFalse(conflicts(self.access("src/user.ts", Access.READ), self.access("src/user.ts", Access.READ)))

    def test_read_write_and_write_write_conflict(self) -> None:
        self.assertTrue(conflicts(self.access("src/user.ts", Access.READ), self.access("src/user.ts", Access.WRITE)))
        self.assertTrue(conflicts(self.access("src/user.ts", Access.WRITE), self.access("src/user.ts", Access.WRITE)))

    def test_different_symbols_still_conflict_for_whole_file_writer(self) -> None:
        left = self.access("src/user.ts", Access.WRITE, symbol="User.a")
        right = self.access("src/user.ts", Access.WRITE, symbol="User.b")
        self.assertTrue(conflicts(left, right))

    def test_symbol_writers_may_be_independent_only_when_explicit(self) -> None:
        left = self.access("src/user.ts", Access.WRITE, symbol="User.a", whole_file_writer=False)
        right = self.access("src/user.ts", Access.WRITE, symbol="User.b", whole_file_writer=False)
        self.assertFalse(conflicts(left, right))

    def test_repository_and_path_hierarchy(self) -> None:
        self.assertFalse(conflicts(self.access("src/user.ts", Access.WRITE), self.access("src/user.ts", Access.WRITE, repo="frontend")))
        self.assertTrue(conflicts(self.access("src", Access.WRITE), self.access("src/user.ts", Access.READ)))


if __name__ == "__main__":
    unittest.main()
