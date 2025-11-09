# Copyright (c) 2025, Joe Inman
#
# Licensed under the MIT License.
# You may obtain a copy of the License at:
#     https://opensource.org/licenses/MIT
#
# This file is part of the CrAnki Addon for Anki.

from datetime import datetime
from typing import Dict, Iterable, Optional, Tuple, cast

from anki.decks import DeckId
from aqt import mw
from aqt.qt import QTimer
from aqt.utils import showWarning, tooltip

from .config import debug_log, get_deck_meta, load_config, set_deck_meta


scheduler_timer: Optional[QTimer] = None


def check_and_rebuild_decks() -> None:
    """Check for decks that need rebuilding and handle updates."""
    if not mw or not mw.col:
        return

    try:
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        current_date = now.strftime("%Y-%m-%d")
        debug_log(f"Scheduler check at {current_time}")

        cfg = load_config()
        per_deck = cfg.get("per_deck", {})
        debug_log(f"Checking {len(per_deck)} decks")

        for did, deck_name in _eligible_decks(per_deck, cfg, current_time, current_date):
            debug_log(f"Attempting to rebuild deck {did} ({deck_name})")
            _enqueue_rebuild(did, deck_name, current_date)

    except Exception as exc:  # pragma: no cover - defensive
        debug_log(f"Error in check_and_rebuild_decks: {exc}")


def _eligible_decks(
    per_deck: Dict[str, Dict], cfg: Dict[str, Dict], current_time: str, current_date: str
) -> Iterable[Tuple[int, str]]:
    for deck_key in per_deck.keys():
        did = _parse_deck_id(deck_key)
        if did is None:
            continue

        meta = get_deck_meta(did, cfg=cfg)
        debug_log(
            "Deck {deck_key}: enabled={enabled}, scheduled={time}, last_rebuild={last}".format(
                deck_key=deck_key,
                enabled=meta.get("enabled"),
                time=meta.get("scheduled_time"),
                last=meta.get("last_rebuild_date"),
            )
        )

        if not _should_rebuild(meta, current_time, current_date):
            continue

        deck = _get_filtered_deck(did)
        if not deck:
            continue

        yield did, deck.get("name", f"Deck {did}")


def _parse_deck_id(deck_key: str) -> Optional[int]:
    try:
        return int(deck_key)
    except ValueError:
        return None


def _should_rebuild(meta: Dict[str, str], current_time: str, current_date: str) -> bool:
    if not meta.get("enabled", False):
        return False
    if meta.get("last_rebuild_date", "") == current_date:
        return False
    if current_time < meta.get("scheduled_time", "00:00"):
        return False
    return True


def _get_filtered_deck(did: int) -> Optional[Dict]:
    deck = mw.col.decks.get(
        cast(DeckId, did), default=False) if mw and mw.col else None
    if not deck or not deck.get("dyn", False):
        return None
    return deck


def _enqueue_rebuild(did: int, deck_name: str, current_date: str) -> None:
    def rebuild_worker(target_did: int = did):
        try:
            if not mw or not mw.col:
                return False, "Collection not available"
            mw.col.sched.rebuild_filtered_deck(cast(DeckId, target_did))
            return True, None
        except Exception as exc:  # pragma: no cover - defensive
            debug_log(f"Rebuild error: {exc}")
            return False, str(exc)

    def rebuild_done(future, target_did: int = did, target_name: str = deck_name):
        try:
            success, error = future.result()
            if success:
                set_deck_meta(target_did, {"last_rebuild_date": current_date})
                tooltip(f"\u2713 Rebuilt filtered deck: {target_name}")
                if getattr(mw, "deckBrowser", None):
                    mw.deckBrowser.refresh()
            else:
                showWarning(
                    f"Failed to rebuild filtered deck '{target_name}':\n{error}"
                )
        except Exception as exc:  # pragma: no cover - defensive
            showWarning(
                f"Failed to rebuild filtered deck '{target_name}':\n{exc}")

    mw.taskman.run_in_background(rebuild_worker, rebuild_done)


def start_scheduler() -> None:
    """Start the timer that periodically checks decks."""
    global scheduler_timer
    debug_log("Starting scheduler...")

    if scheduler_timer is not None:
        scheduler_timer.stop()
        scheduler_timer.deleteLater()

    now = datetime.now()
    seconds_until_next_minute = 60 - now.second
    milliseconds_until_next_minute = (
        seconds_until_next_minute * 1000 - now.microsecond // 1000
    )
    debug_log(
        f"Syncing to clock - will first check in {seconds_until_next_minute} seconds"
    )

    def start_regular_timer():
        global scheduler_timer
        check_and_rebuild_decks()
        scheduler_timer = QTimer()
        scheduler_timer.setInterval(60000)
        scheduler_timer.timeout.connect(check_and_rebuild_decks)
        scheduler_timer.start()

    scheduler_timer = QTimer()
    scheduler_timer.setSingleShot(True)
    scheduler_timer.timeout.connect(start_regular_timer)
    scheduler_timer.start(milliseconds_until_next_minute)


def stop_scheduler() -> None:
    """Stop the scheduler timer."""
    global scheduler_timer
    if scheduler_timer is not None:
        scheduler_timer.stop()
        scheduler_timer.deleteLater()
        scheduler_timer = None
