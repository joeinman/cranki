"""Scheduler logic for CrAnki."""

from datetime import datetime
from typing import Optional

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

        if not per_deck:
            return

        for deck_key in per_deck.keys():
            try:
                did = int(deck_key)
            except ValueError:
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

            if not meta.get("enabled", False):
                continue

            scheduled_time = meta.get("scheduled_time", "00:00")
            last_rebuild_date = meta.get("last_rebuild_date", "")

            if last_rebuild_date == current_date:
                continue

            if current_time < scheduled_time:
                continue

            deck = mw.col.decks.get(did, default=False)
            if not deck or not deck.get("dyn", False):
                continue

            deck_name = deck.get("name", f"Deck {did}")
            debug_log(f"Attempting to rebuild deck {did} ({deck_name})")

            def rebuild_worker(target_did: int = did):
                try:
                    mw.col.sched.rebuild_filtered_deck(target_did)
                    return True, None
                except Exception as exc:  # pragma: no cover - defensive
                    debug_log(f"Rebuild error: {exc}")
                    return False, str(exc)

            def rebuild_done(
                future, target_did: int = did, target_name: str = deck_name
            ):
                try:
                    success, error = future.result()
                    if success:
                        set_deck_meta(
                            target_did,
                            {"last_rebuild_date": current_date},
                        )
                        tooltip(f"\u2713 Rebuilt filtered deck: {target_name}")
                        if getattr(mw, "deckBrowser", None):
                            mw.deckBrowser.refresh()
                    else:
                        showWarning(
                            f"Failed to rebuild filtered deck '{target_name}':\n{error}"
                        )
                except Exception as exc:  # pragma: no cover - defensive
                    showWarning(
                        f"Failed to rebuild filtered deck '{target_name}':\n{exc}"
                    )

            mw.taskman.run_in_background(rebuild_worker, rebuild_done)

    except Exception as exc:  # pragma: no cover - defensive
        debug_log(f"Error in check_and_rebuild_decks: {exc}")


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
