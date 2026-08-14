from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Callable, TypeVar

from apple_music_mcp.config import config

T = TypeVar("T")


class CacheManager:
    """High-efficiency in-memory and disk cache for catalog queries and track metadata."""

    def __init__(self, cache_dir: Path | None = None, ttl_seconds: int = 3600):
        self.cache_dir = cache_dir or config.get_cache_dir()
        self.ttl = ttl_seconds
        self._memory_cache: dict[str, tuple[float, Any]] = {}

    def _hash_key(self, namespace: str, key: str) -> str:
        raw = f"{namespace}:{key}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(self, namespace: str, key: str) -> Any | None:
        if not config.preferences.enable_cache:
            return None

        h = self._hash_key(namespace, key)
        now = time.time()

        # Check memory first
        if h in self._memory_cache:
            ts, val = self._memory_cache[h]
            if now - ts < self.ttl:
                return val
            del self._memory_cache[h]

        # Check disk
        fpath = self.cache_dir / f"{h}.json"
        if fpath.exists():
            try:
                data = json.loads(fpath.read_text(encoding="utf-8"))
                ts = data.get("ts", 0)
                if now - ts < self.ttl:
                    val = data.get("val")
                    self._memory_cache[h] = (ts, val)
                    return val
                fpath.unlink(missing_ok=True)
            except Exception:
                fpath.unlink(missing_ok=True)
        return None

    def set(self, namespace: str, key: str, value: Any, ttl: int | None = None) -> None:
        if not config.preferences.enable_cache:
            return

        h = self._hash_key(namespace, key)
        now = time.time()
        effective_ttl = ttl or self.ttl

        self._memory_cache[h] = (now, value)

        fpath = self.cache_dir / f"{h}.json"
        try:
            fpath.write_text(
                json.dumps({"ts": now, "ttl": effective_ttl, "val": value}, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    def clear(self) -> int:
        count = 0
        self._memory_cache.clear()
        for f in self.cache_dir.glob("*.json"):
            try:
                f.unlink()
                count += 1
            except Exception:
                pass
        return count


cache = CacheManager()
