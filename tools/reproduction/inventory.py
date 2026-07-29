#!/usr/bin/env python3
"""Create a deterministic inventory of the read-only Dummy Robot source checkout."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Sequence
from urllib.parse import urlsplit


ASSET_ROOTS = (
    "0.SubModules",
    "1.Hardware",
    "2.Firmware",
    "3.Software",
    "4.Model",
    "5.Docs",
)
CSV_FIELDS = ("path", "top_level", "extension", "size_bytes", "sha256")
SKIPPED_DIRECTORY_NAMES = {
    ".git",
    ".metadata",
    ".settings",
    "__pycache__",
    "build",
    "debug",
    "release",
}
SHA1_PATTERN = re.compile(r"^[0-9a-f]{40}$")
HASH_CHUNK_SIZE = 1024 * 1024


class InventoryError(RuntimeError):
    """Raised when the source checkout violates the inventory contract."""


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inventory the six versioned Dummy Robot asset roots."
    )
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--lock-output", required=True, type=Path)
    parser.add_argument("--canonical-url", required=True)
    return parser.parse_args(argv)


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _resolve_existing_directory(path: Path, label: str) -> Path:
    try:
        resolved = path.expanduser().resolve(strict=True)
    except OSError as error:
        raise InventoryError(f"{label} does not exist: {path}") from error
    if not resolved.is_dir():
        raise InventoryError(f"{label} is not a directory: {path}")
    return resolved


def _resolve_output(path: Path, project_root: Path) -> Path:
    candidate = path if path.is_absolute() else project_root / path
    return candidate.expanduser().resolve(strict=False)


def _run_git(source_root: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(source_root), *args],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as error:
        raise InventoryError("git executable was not found") from error
    except subprocess.CalledProcessError as error:
        message = error.stderr.strip() or error.stdout.strip() or "git command failed"
        raise InventoryError(message) from error
    return result.stdout.strip()


def _validate_roots(project_root: Path, source_root: Path) -> None:
    if (
        project_root == source_root
        or _is_relative_to(project_root, source_root)
        or _is_relative_to(source_root, project_root)
    ):
        raise InventoryError("project root and source root must be disjoint")

    git_root = Path(
        _run_git(source_root, "rev-parse", "--show-toplevel")
    ).resolve(strict=True)
    if git_root != source_root:
        raise InventoryError("source root must be the Git checkout root")

    missing_roots = [
        root_name
        for root_name in ASSET_ROOTS
        if not (source_root / root_name).is_dir()
    ]
    if missing_roots:
        raise InventoryError(
            "missing source asset roots: " + ", ".join(missing_roots)
        )

    dirty = _run_git(
        source_root,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
        "--",
        *ASSET_ROOTS,
    )
    if dirty:
        raise InventoryError("source asset roots contain uncommitted changes")


def _validate_outputs(
    output: Path,
    lock_output: Path,
    source_root: Path,
) -> None:
    if output == lock_output:
        raise InventoryError("CSV output and lock output must be different files")
    for candidate in (output, lock_output):
        if candidate == source_root or _is_relative_to(candidate, source_root):
            raise InventoryError("output paths must not be inside the source root")


def _validate_repository_url(url: str, label: str) -> str:
    normalized = url.strip()
    if not normalized:
        raise InventoryError(f"{label} is empty")

    parsed = urlsplit(normalized)
    if parsed.scheme == "file" or Path(normalized).expanduser().is_absolute():
        raise InventoryError(f"{label} must not expose a local absolute path")
    if parsed.username is not None or parsed.password is not None:
        raise InventoryError(f"{label} contains embedded credentials")
    return normalized


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source_file:
        while chunk := source_file.read(HASH_CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def _inventory_rows(source_root: Path) -> list[dict[str, str | int]]:
    rows: list[dict[str, str | int]] = []
    for root_name in ASSET_ROOTS:
        asset_root = source_root / root_name
        for current_dir, directory_names, file_names in os.walk(asset_root):
            directory_names[:] = sorted(
                name
                for name in directory_names
                if name.casefold() not in SKIPPED_DIRECTORY_NAMES
            )
            current_path = Path(current_dir)
            for file_name in sorted(file_names):
                asset_path = current_path / file_name
                if not asset_path.is_file():
                    continue
                relative_path = asset_path.relative_to(source_root)
                rows.append(
                    {
                        "path": relative_path.as_posix(),
                        "top_level": root_name,
                        "extension": asset_path.suffix.lower(),
                        "size_bytes": asset_path.stat().st_size,
                        "sha256": _sha256(asset_path),
                    }
                )
    rows.sort(key=lambda row: str(row["path"]))
    return rows


def _render_csv(rows: list[dict[str, str | int]]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=CSV_FIELDS,
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def _source_lock(
    project_root: Path,
    source_root: Path,
    canonical_url: str,
) -> dict[str, object]:
    checkout_url = _validate_repository_url(
        _run_git(source_root, "remote", "get-url", "origin"),
        "checkout URL",
    )
    checkout_commit = _run_git(source_root, "rev-parse", "--verify", "HEAD")
    if not SHA1_PATTERN.fullmatch(checkout_commit):
        raise InventoryError("checkout commit is not a 40-character SHA-1")

    source_root_hint = Path(
        os.path.relpath(source_root, start=project_root)
    ).as_posix()
    return {
        "schema_version": 1,
        "source_root_hint": source_root_hint,
        "canonical_url": _validate_repository_url(canonical_url, "canonical URL"),
        "checkout_url": checkout_url,
        "checkout_commit": checkout_commit,
        "asset_roots": list(ASSET_ROOTS),
    }


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_file.write(content)
            temporary_path = Path(temporary_file.name)
        temporary_path.replace(path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def generate_inventory(args: argparse.Namespace) -> None:
    project_root = _resolve_existing_directory(args.project_root, "project root")
    source_root = _resolve_existing_directory(args.source_root, "source root")
    output = _resolve_output(args.output, project_root)
    lock_output = _resolve_output(args.lock_output, project_root)

    _validate_roots(project_root, source_root)
    _validate_outputs(output, lock_output, source_root)

    rows = _inventory_rows(source_root)
    lock = _source_lock(
        project_root,
        source_root,
        args.canonical_url,
    )
    lock_text = json.dumps(lock, ensure_ascii=False, indent=2) + "\n"

    _atomic_write_text(output, _render_csv(rows))
    _atomic_write_text(lock_output, lock_text)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        generate_inventory(args)
    except (InventoryError, OSError) as error:
        print(f"inventory: error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
