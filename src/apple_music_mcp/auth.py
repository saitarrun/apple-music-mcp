from __future__ import annotations

import json
import re
import subprocess
import time
from typing import Any

from apple_music_mcp.applescript import is_macos, run_applescript
from apple_music_mcp.config import config


def extract_tokens_from_safari() -> tuple[bool, dict[str, str]]:
    """Extract MusicKit developer token and user token directly from Safari web session."""
    if not is_macos():
        return False, {"error": "Safari extraction requires macOS"}

    script = """
    tell application "Safari"
        set windowCount to count of windows
        repeat with w from 1 to windowCount
            set tabCount to count of tabs of window w
            repeat with t from 1 to tabCount
                set tabUrl to URL of tab t of window w
                if tabUrl contains "music.apple.com" then
                    set devToken to do JavaScript "window.MusicKit ? window.MusicKit.getInstance().developerToken : ''" in tab t of window w
                    set userToken to do JavaScript "window.MusicKit ? window.MusicKit.getInstance().musicUserToken : ''" in tab t of window w
                    return devToken & "|||" & userToken
                end if
            end repeat
        end repeat
        return "NO_TAB"
    end tell
    """
    s, out = run_applescript(script)
    if not s:
        return False, {"error": f"Safari JavaScript execution failed: {out}"}
    if out == "NO_TAB":
        return False, {"error": "No open Safari tab found on music.apple.com"}

    parts = out.split("|||")
    dev_tok = parts[0].strip() if len(parts) > 0 else ""
    user_tok = parts[1].strip() if len(parts) > 1 else ""

    if not user_tok:
        return False, {"error": "music.apple.com tab found, but user is not signed in."}

    # Save to config
    config.web_token = dev_tok or config.web_token
    config.user_token = user_tok
    config.save()

    return True, {
        "developer_token": dev_tok,
        "user_token": user_tok,
        "source": "Safari",
    }


def get_auth_headers(is_user_library: bool = True) -> dict[str, str]:
    """Assemble authenticated headers for Apple Music API requests.
    
    Catalog endpoints (/catalog/...) ONLY require the Developer Bearer Token.
    User Library endpoints (/me/library/...) require BOTH Developer Token and Music-User-Token.
    """
    dev_tok = config.dev_token or config.web_token
    user_tok = config.user_token

    if not dev_tok or (is_user_library and not user_tok):
        if is_macos():
            s, _ = extract_tokens_from_safari()
            if s:
                dev_tok = config.dev_token or config.web_token
                user_tok = config.user_token

    headers = {
        "Origin": "https://music.apple.com",
        "Referer": "https://music.apple.com/",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    if dev_tok:
        headers["Authorization"] = f"Bearer {dev_tok}"
    
    # Only attach Music-User-Token for personal library endpoints
    if is_user_library and user_tok:
        headers["Music-User-Token"] = user_tok

    return headers


def get_auth_status() -> dict[str, Any]:
    """Check health and authentication status across native and API layers."""
    headers = get_auth_headers(is_user_library=True)
    has_dev = "Authorization" in headers
    has_user = "Music-User-Token" in headers
    
    return {
        "native_macos": is_macos(),
        "storefront": config.preferences.storefront,
        "developer_token_present": has_dev,
        "user_token_present": has_user,
        "authenticated": has_dev and has_user,
        "mode": config.preferences.mode,
        "pure_audio_only": config.preferences.pure_audio_only,
    }
