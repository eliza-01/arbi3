import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import RLock
from typing import Any

from app.local_settings.models import LocalSettings, settings_from_dict

DEFAULT_SETTINGS_PATH = "local_data/settings.json"


class LocalSettingsStore:
    def __init__(self, path: str | None = None) -> None:
        self.path = Path(path or os.getenv("LOCAL_SETTINGS_PATH") or DEFAULT_SETTINGS_PATH)
        self._lock = RLock()

    def load(self) -> LocalSettings:
        with self._lock:
            if not self.path.exists():
                settings = LocalSettings()
                self._save_unlocked(settings)
                return settings
            try:
                payload = json.loads(self.path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                payload = {}
            return settings_from_dict(payload if isinstance(payload, dict) else {})

    def save(self, settings: LocalSettings) -> None:
        with self._lock:
            self._save_unlocked(settings)

    def update(self, patch: dict[str, Any]) -> LocalSettings:
        with self._lock:
            current = self.load().to_dict()
            merged = _deep_merge(current, patch)
            settings = settings_from_dict(merged)
            self._save_unlocked(settings)
            return settings

    def _save_unlocked(self, settings: LocalSettings) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(settings.to_dict(), ensure_ascii=False, indent=2)
        with NamedTemporaryFile(
            "w",
            delete=False,
            encoding="utf-8",
            dir=str(self.path.parent),
        ) as temporary:
            temporary.write(payload)
            temporary_path = Path(temporary.name)
        temporary_path.replace(self.path)
        try:
            self.path.chmod(0o600)
        except OSError:
            pass


def _deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result
