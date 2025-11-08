"""Main entry point for the CrAnki addon."""

from aqt import gui_hooks, mw
from aqt.qt import QAction


MODULE_NAME = __name__


def debug_log(message: str) -> None:
    """Print debug message only if debug mode is enabled."""
    try:
        cfg = mw.addonManager.getConfig(__name__)
        if cfg and cfg.get("debug_mode", False):
            debug_log(f"{message}")
    except Exception:
        pass


from .config import cleanup_missing_decks  # noqa: E402
from .config_dialog import show_config_dialog  # noqa: E402
from .gui import patch_filtered_deck_dialog  # noqa: E402
from .scheduler import (  # noqa: E402
    check_and_rebuild_decks,
    start_scheduler,
    stop_scheduler,
)


cfg = mw.addonManager.getConfig(__name__) if mw else None
if cfg and cfg.get("debug_mode", False):
    print("=" * 60)
    print("CrAnki - Auto Rebuild Filtered Decks")
    print("Version: 1.0")
    print("Debug mode: ENABLED")
    print("=" * 60)
else:
    print("CrAnki: Addon loaded (debug mode: OFF, enable in Tools > Add-ons > Config)")


patch_filtered_deck_dialog(module_name=MODULE_NAME)


def add_debug_menu() -> None:
    if not mw:
        return

    action = QAction("CrAnki: Test Scheduler Now", mw)
    action.triggered.connect(lambda: check_and_rebuild_decks(module_name=MODULE_NAME))
    mw.form.menuTools.addAction(action)

    config_action = QAction("CrAnki: Configuration...", mw)
    config_action.triggered.connect(lambda: show_config_dialog(MODULE_NAME))
    mw.form.menuTools.addAction(config_action)

    debug_log("Added debug menu items to Tools menu")


def register_config_action() -> None:
    if not mw or not getattr(mw, "addonManager", None):
        return

    def open_config() -> None:
        show_config_dialog(MODULE_NAME)

    for key in {MODULE_NAME, MODULE_NAME.split(".")[0]}:
        mw.addonManager.setConfigAction(key, open_config)


gui_hooks.profile_did_open.append(lambda: start_scheduler(module_name=MODULE_NAME))
gui_hooks.profile_will_close.append(stop_scheduler)
gui_hooks.profile_will_close.append(
    lambda: cleanup_missing_decks(module_name=MODULE_NAME)
)


if mw and mw.col:
    debug_log("Profile already open, starting scheduler immediately...")
    start_scheduler(module_name=MODULE_NAME)
    add_debug_menu()
    register_config_action()
else:
    debug_log("Waiting for profile to open...")
    gui_hooks.profile_did_open.append(add_debug_menu)
    gui_hooks.profile_did_open.append(register_config_action)


debug_log("Initialization complete")
