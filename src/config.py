"""Configuration helpers for CrAnki."""

from typing import Any, Dict, Optional

from aqt import mw

from .main import debug_log


DEFAULT_DECK_META: Dict[str, Any] = {
    "enabled": False,
    "scheduled_time": "00:00",
    "last_rebuild_date": "",
}


def _ensure_config(module_name: str) -> Dict[str, Any]:
    cfg = mw.addonManager.getConfig(module_name) if mw else None
    if not cfg:
        cfg = {"per_deck": {}}
    elif "per_deck" not in cfg:
        cfg["per_deck"] = {}
    return cfg


def get_deck_meta(
    did: int,
    module_name: str = __name__,
    cfg: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Return stored metadata for a deck or defaults if missing."""
    data = cfg if cfg is not None else _ensure_config(module_name)
    deck_key = str(did)
    return data.get("per_deck", {}).get(deck_key, DEFAULT_DECK_META.copy())


def set_deck_meta(did: int, updates: Dict[str, Any], module_name: str = __name__) -> None:
    """Merge updates into the stored deck metadata."""
    debug_log(
        f"set_deck_meta called for deck {did} with updates: {updates} (module={module_name})"
    )
    cfg = _ensure_config(module_name)
    deck_key = str(did)
    if deck_key not in cfg["per_deck"]:
        cfg["per_deck"][deck_key] = DEFAULT_DECK_META.copy()
    cfg["per_deck"][deck_key].update(updates)
    debug_log(f"Writing config using module name: {module_name}")
    mw.addonManager.writeConfig(module_name, cfg)
    debug_log("Config written successfully")


def cleanup_missing_decks(module_name: str = __name__) -> None:
    """Strip metadata entries for decks that no longer exist."""
    cfg = mw.addonManager.getConfig(module_name) if mw else None
    if not cfg or "per_deck" not in cfg or not mw or not mw.col:
        return
    per_deck = cfg["per_deck"]
    to_remove = []
    for deck_key in list(per_deck.keys()):
        try:
            did = int(deck_key)
            if not mw.col.decks.get(did, default=False):
                to_remove.append(deck_key)
        except (ValueError, AttributeError):
            to_remove.append(deck_key)
    for deck_key in to_remove:
        del per_deck[deck_key]
    if to_remove:
        debug_log(f"Cleaning up missing decks: {to_remove}")
        mw.addonManager.writeConfig(module_name, cfg)
