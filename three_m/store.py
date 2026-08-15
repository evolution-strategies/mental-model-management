"""Markdown-only persistent mental-model store."""

from __future__ import annotations

import os
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SAFE_NAME = re.compile(r"^[a-z0-9][a-z0-9_-]*\.md$")


class StoreError(ValueError):
    pass


class MarkdownStore:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.backups = self.root / ".backups"

    def list_names(self) -> list[str]:
        return sorted(path.name for path in self.root.glob("*.md") if path.is_file())

    def read(self, name: str) -> str:
        return self._path(name).read_text(encoding="utf-8")

    def snapshot(self, names: list[str] | None = None) -> dict[str, str]:
        selected = names if names is not None else self.list_names()
        return {name: self.read(name) for name in selected}

    def write_atomic(self, name: str, markdown: str) -> Path:
        path = self._path(name)
        content = markdown.strip() + "\n"
        if not content.startswith("#"):
            raise StoreError(f"{name}: Markdown must begin with a heading")
        if path.exists() and path.read_text(encoding="utf-8") == content:
            return path
        if path.exists():
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
            self.backups.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, self.backups / f"{path.stem}.{stamp}.md")
        fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=self.root, text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return path

    def _path(self, name: str) -> Path:
        if not SAFE_NAME.fullmatch(name):
            raise StoreError(f"Unsafe filename {name!r}; use lowercase slug.md")
        return self.root / name

