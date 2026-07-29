from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.reproduction import inventory


ASSET_ROOTS = (
    "0.SubModules",
    "1.Hardware",
    "2.Firmware",
    "3.Software",
    "4.Model",
    "5.Docs",
)


class InventoryTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.workspace = Path(self.temp_dir.name)
        self.project_root = self.workspace / "Dummy-Robot-Reproduction"
        self.source_root = self.workspace / "Dummy-Robot"
        self.project_root.mkdir()
        self._create_source_checkout()

    def _git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(self.source_root), *args],
            check=check,
            capture_output=True,
            text=True,
        )

    def _create_source_checkout(self) -> None:
        self.source_root.mkdir()
        self._git("init", "-q")
        self._git(
            "remote",
            "add",
            "origin",
            "https://github.com/example/Dummy-Robot.git",
        )

        for index, root_name in enumerate(ASSET_ROOTS):
            root = self.source_root / root_name
            root.mkdir()
            (root / f"asset-{index}.txt").write_text(
                f"{root_name}\n", encoding="utf-8"
            )

        outside = self.source_root / "notes"
        outside.mkdir()
        (outside / "not-an-asset.txt").write_text("ignored\n", encoding="utf-8")

        self._git("add", ".")
        self._git(
            "-c",
            "user.name=Inventory Test",
            "-c",
            "user.email=inventory@example.invalid",
            "commit",
            "-q",
            "-m",
            "test fixture",
        )

    def _run_inventory(
        self,
        *,
        source_root: Path | None = None,
        output: Path | None = None,
        lock_output: Path | None = None,
    ) -> int:
        output = output or self.project_root / "inventory.csv"
        lock_output = lock_output or self.project_root / "source-lock.json"
        return inventory.main(
            [
                "--project-root",
                str(self.project_root),
                "--source-root",
                str(source_root or self.source_root),
                "--output",
                str(output),
                "--lock-output",
                str(lock_output),
                "--canonical-url",
                "https://github.com/peng-zhihui/Dummy-Robot.git",
            ]
        )

    def test_generates_sorted_inventory_and_stable_source_lock(self) -> None:
        output = self.project_root / "inventory.csv"
        lock_output = self.project_root / "source-lock.json"

        self.assertEqual(self._run_inventory(), 0)

        with output.open(newline="", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)
            rows = list(reader)

        self.assertEqual(
            reader.fieldnames,
            ["path", "top_level", "extension", "size_bytes", "sha256"],
        )
        paths = [row["path"] for row in rows]
        self.assertEqual(paths, sorted(paths))
        self.assertEqual(len(rows), len(ASSET_ROOTS))
        self.assertEqual({row["top_level"] for row in rows}, set(ASSET_ROOTS))
        self.assertNotIn("notes/not-an-asset.txt", paths)

        for row in rows:
            self.assertNotIn("\\", row["path"])
            self.assertRegex(row["sha256"], re.compile(r"^[0-9a-f]{64}$"))
            asset_path = self.source_root / Path(row["path"])
            self.assertEqual(int(row["size_bytes"]), asset_path.stat().st_size)
            self.assertEqual(
                row["sha256"],
                hashlib.sha256(asset_path.read_bytes()).hexdigest(),
            )

        lock = json.loads(lock_output.read_text(encoding="utf-8"))
        self.assertEqual(
            list(lock),
            [
                "schema_version",
                "source_root_hint",
                "canonical_url",
                "checkout_url",
                "checkout_commit",
                "asset_roots",
            ],
        )
        self.assertEqual(lock["schema_version"], 1)
        self.assertEqual(lock["source_root_hint"], "../Dummy-Robot")
        self.assertEqual(
            lock["canonical_url"],
            "https://github.com/peng-zhihui/Dummy-Robot.git",
        )
        self.assertEqual(
            lock["checkout_url"],
            "https://github.com/example/Dummy-Robot.git",
        )
        self.assertRegex(lock["checkout_commit"], re.compile(r"^[0-9a-f]{40}$"))
        self.assertEqual(lock["asset_roots"], list(ASSET_ROOTS))
        self.assertNotIn(str(self.workspace), lock_output.read_text(encoding="utf-8"))

    def test_outputs_are_byte_reproducible(self) -> None:
        first_csv = self.workspace / "first.csv"
        first_lock = self.workspace / "first-lock.json"
        second_csv = self.workspace / "second.csv"
        second_lock = self.workspace / "second-lock.json"

        self.assertEqual(
            self._run_inventory(output=first_csv, lock_output=first_lock), 0
        )
        self.assertEqual(
            self._run_inventory(output=second_csv, lock_output=second_lock), 0
        )
        self.assertEqual(first_csv.read_bytes(), second_csv.read_bytes())
        self.assertEqual(first_lock.read_bytes(), second_lock.read_bytes())

    def test_rejects_dirty_asset_root(self) -> None:
        dirty_file = self.source_root / ASSET_ROOTS[0] / "asset-0.txt"
        dirty_file.write_text("changed\n", encoding="utf-8")

        self.assertNotEqual(self._run_inventory(), 0)

    def test_ignores_dirty_paths_outside_asset_roots(self) -> None:
        (self.source_root / "local-note.txt").write_text("untracked\n", encoding="utf-8")

        self.assertEqual(self._run_inventory(), 0)

    def test_rejects_missing_asset_root(self) -> None:
        missing_root = self.source_root / ASSET_ROOTS[-1]
        for child in missing_root.iterdir():
            child.unlink()
        missing_root.rmdir()

        self.assertNotEqual(self._run_inventory(), 0)

    def test_rejects_non_git_source(self) -> None:
        non_git_source = self.workspace / "not-a-repository"
        non_git_source.mkdir()
        for root_name in ASSET_ROOTS:
            (non_git_source / root_name).mkdir()

        self.assertNotEqual(self._run_inventory(source_root=non_git_source), 0)

    def test_rejects_nested_project_and_source_roots(self) -> None:
        nested_project = self.source_root / "generated"
        nested_project.mkdir()

        result = inventory.main(
            [
                "--project-root",
                str(nested_project),
                "--source-root",
                str(self.source_root),
                "--output",
                str(self.workspace / "inventory.csv"),
                "--lock-output",
                str(self.workspace / "source-lock.json"),
                "--canonical-url",
                "https://github.com/peng-zhihui/Dummy-Robot.git",
            ]
        )

        self.assertNotEqual(result, 0)

    def test_rejects_output_inside_source_root(self) -> None:
        output = self.source_root / ASSET_ROOTS[0] / "inventory.csv"

        self.assertNotEqual(self._run_inventory(output=output), 0)
        self.assertFalse(output.exists())

    def test_rejects_checkout_url_with_embedded_credentials(self) -> None:
        self._git(
            "remote",
            "set-url",
            "origin",
            "https://user:placeholder@example.invalid/Dummy-Robot.git",
        )

        self.assertNotEqual(self._run_inventory(), 0)


if __name__ == "__main__":
    unittest.main()
