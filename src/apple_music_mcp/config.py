from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Preferences:
    storefront: str = "in"
    mode: str = "auto"  # "auto", "native", "api"
    pure_audio_only: bool = True
    batch_size: int = 25
    request_timeout: float = 15.0
    enable_cache: bool = True
    cache_ttl_seconds: int = 3600
    auto_add_missing: bool = True


@dataclass
class Config:
    preferences: Preferences = field(default_factory=Preferences)
    dev_token: str | None = None
    user_token: str | None = None
    web_token: str | None = None

    @classmethod
    def get_config_dir(cls) -> Path:
        # Check standard paths and legacy applemusic-mcp config path
        override = os.environ.get("APPLE_MUSIC_CONFIG_DIR")
        if override:
            p = Path(override).expanduser()
        else:
            legacy = Path("~/.config/applemusic-mcp").expanduser()
            if legacy.exists():
                return legacy
            p = Path("~/.config/apple-music-mcp").expanduser()
        p.mkdir(parents=True, exist_ok=True)
        return p

    @classmethod
    def get_cache_dir(cls) -> Path:
        override = os.environ.get("APPLE_MUSIC_CACHE_DIR")
        if override:
            p = Path(override).expanduser()
        else:
            p = Path("~/.cache/apple-music-mcp").expanduser()
        p.mkdir(parents=True, exist_ok=True)
        return p

    @classmethod
    def load(cls) -> Config:
        cfg_dir = cls.get_config_dir()
        cfg_file = cfg_dir / "config.json"
        
        pref = Preferences()
        dev_token = None
        user_token = None
        web_token = None

        if cfg_file.exists():
            try:
                data = json.loads(cfg_file.read_text(encoding="utf-8"))
                pref_data = data.get("preferences", {})
                pref = Preferences(
                    storefront=pref_data.get("storefront", "in"),
                    mode=pref_data.get("mode", "auto"),
                    pure_audio_only=pref_data.get("pure_audio_only", True),
                    batch_size=pref_data.get("batch_size", 25),
                    request_timeout=float(pref_data.get("request_timeout", 15.0)),
                    enable_cache=pref_data.get("enable_cache", True),
                    cache_ttl_seconds=int(pref_data.get("cache_ttl_seconds", 3600)),
                    auto_add_missing=pref_data.get("auto_add_missing", True),
                )
                dev_token = data.get("dev_token")
                user_token = data.get("user_token")
                web_token = data.get("web_token")
            except Exception:
                pass

        # Check separate token files if present
        dev_file = cfg_dir / "developer_token.txt"
        if dev_file.exists() and not dev_token:
            dev_token = dev_file.read_text(encoding="utf-8").strip()

        user_file = cfg_dir / "user_token.txt"
        if user_file.exists() and not user_token:
            user_token = user_file.read_text(encoding="utf-8").strip()

        web_file = cfg_dir / "web_token.txt"
        if web_file.exists() and not web_token:
            web_token = web_file.read_text(encoding="utf-8").strip()

        return cls(
            preferences=pref,
            dev_token=dev_token,
            user_token=user_token,
            web_token=web_token,
        )

    def save(self) -> None:
        cfg_dir = self.get_config_dir()
        cfg_file = cfg_dir / "config.json"
        data = {
            "preferences": asdict(self.preferences),
            "dev_token": self.dev_token,
            "user_token": self.user_token,
            "web_token": self.web_token,
        }
        cfg_file.write_text(json.dumps(data, indent=2), encoding="utf-8")


config = Config.load()
