"""Configuration helpers that use Anki's collection/profile storage."""

from copy import deepcopy
from typing import Any, Dict, Optional

from aqt import mw


CONFIG_KEY = "cranki"
ADDON_PACKAGE = __name__.split(
    ".src.", 1)[0] if ".src." in __name__ else __name__

DEFAULT_DECK_META: Dict[str, Any] = {
    "enabled": False,
    "scheduled_time": "00:00",
    "last_rebuild_date": "",
}

DEFAULT_CONFIG: Dict[str, Any] = {
    "debug_mode": False,
    "per_deck": {},
}


def _collection():
    return getattr(mw, "col", None)


def _load_legacy_config() -> Optional[Dict[str, Any]]:
    manager = getattr(mw, "addonManager", None)
    if not manager:
        return None
    for key in {ADDON_PACKAGE, __name__}:
        try:
            data = manager.getConfig(key)
            if data:
                return data
        except Exception:
            continue
    return None


def _normalize_config(raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    cfg = deepcopy(DEFAULT_CONFIG)
    if isinstance(raw, dict):
        cfg["debug_mode"] = bool(raw.get("debug_mode", False))
        per_deck = raw.get("per_deck", {})
        if isinstance(per_deck, dict):
            for key, value in per_deck.items():
                entry = DEFAULT_DECK_META.copy()
                if isinstance(value, dict):
                    entry.update(value)
                cfg["per_deck"][str(key)] = entry
    return cfg


def load_config() -> Dict[str, Any]:
    col = _collection()
    if not col:
        return deepcopy(DEFAULT_CONFIG)
    getter = getattr(col, "get_config", None)
    raw = getter(CONFIG_KEY) if callable(getter) else col.conf.get(CONFIG_KEY)
    if not isinstance(raw, dict) or not raw:
        legacy = _load_legacy_config()
        if legacy:
            normalized = _normalize_config(legacy)
            save_config(normalized)
            return normalized
    return _normalize_config(raw)


def save_config(cfg: Dict[str, Any]) -> None:
    col = _collection()
    if not col:
        return
    normalized = _normalize_config(cfg)
    setter = getattr(col, "set_config", None)
    if callable(setter):
        setter(CONFIG_KEY, normalized)
    else:
        col.conf[CONFIG_KEY] = normalized
        col.setMod()


def get_debug_mode() -> bool:
    return load_config().get("debug_mode", False)


def set_debug_mode(enabled: bool) -> None:
    cfg = load_config()
    cfg["debug_mode"] = bool(enabled)
    save_config(cfg)


def debug_log(message: str) -> None:
    if get_debug_mode():
        print(f"[CrAnki] {message}")


def get_deck_meta(did: int, cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    data = cfg if cfg is not None else load_config()
    deck_key = str(did)
    stored = data.get("per_deck", {}).get(deck_key)
    base = DEFAULT_DECK_META.copy()
    if isinstance(stored, dict):
        base.update(stored)
    return base


def set_deck_meta(did: int, updates: Dict[str, Any]) -> None:
    cfg = load_config()
    per_deck = cfg.setdefault("per_deck", {})
    deck_key = str(did)
    if deck_key not in per_deck or not isinstance(per_deck[deck_key], dict):
        per_deck[deck_key] = DEFAULT_DECK_META.copy()
    per_deck[deck_key].update(updates)
    debug_log(f"Updated deck {deck_key} with {updates}")
    save_config(cfg)


def cleanup_missing_decks() -> None:
    col = _collection()
    if not col:
        return
    cfg = load_config()
    per_deck = cfg.get("per_deck", {})
    to_remove = []
    for deck_key, value in list(per_deck.items()):
        try:
            did = int(deck_key)
        except ValueError:
            to_remove.append(deck_key)
            continue
        deck = col.decks.get(did, default=False)
        if not deck:
            to_remove.append(deck_key)
    for deck_key in to_remove:
        del per_deck[deck_key]
    if to_remove:
        debug_log(f"Cleaning up missing decks: {to_remove}")
        save_config(cfg)
