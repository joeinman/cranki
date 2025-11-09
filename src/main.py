"""Main entry point for the CrAnki addon."""

from aqt import gui_hooks, mw
from aqt.qt import QAction

from .config import cleanup_missing_decks, debug_log, get_debug_mode
from .config_dialog import show_config_dialog
from .gui import patch_filtered_deck_dialog
from .scheduler import check_and_rebuild_decks, start_scheduler, stop_scheduler


ADDON_MODULE = __name__
ADDON_PACKAGE = (
    ADDON_MODULE.split(".src.", 1)[
        0] if ".src." in ADDON_MODULE else ADDON_MODULE
)

_tools_menu_added = False
_config_action_registered = False
_startup_announced = False


def announce_startup() -> None:
    global _startup_announced
    if _startup_announced:
        return
    _startup_announced = True
    if get_debug_mode():
        print("=" * 60)
        print("CrAnki - Auto Rebuild Filtered Decks")
        print("Version: 1.0")
        print("Debug mode: ENABLED")
        print("=" * 60)
    else:
        print("CrAnki: Addon loaded (enable debug via Tools > CrAnki > Configuration)")


def add_tools_menu_actions() -> None:
    global _tools_menu_added
    if _tools_menu_added or not mw:
        return

    action = QAction("CrAnki: Test Scheduler Now", mw)
    action.triggered.connect(check_and_rebuild_decks)
    mw.form.menuTools.addAction(action)

    config_action = QAction("CrAnki: Configuration...", mw)
    config_action.triggered.connect(show_config_dialog)
    mw.form.menuTools.addAction(config_action)

    _tools_menu_added = True
    debug_log("Added Tools menu actions")


def register_config_action() -> None:
    global _config_action_registered
    if _config_action_registered or not mw or not getattr(mw, "addonManager", None):
        return

    def open_config() -> None:
        show_config_dialog()

    registered = False
    module_candidates = {ADDON_PACKAGE, ADDON_PACKAGE.lower(), ADDON_MODULE}
    for module_name in module_candidates:
        if not module_name:
            continue
        try:
            mw.addonManager.setConfigAction(module_name, open_config)
            registered = True
        except Exception:
            continue

    if registered:
        _config_action_registered = True
        debug_log("Registered config action")


def handle_profile_open() -> None:
    announce_startup()
    start_scheduler()
    add_tools_menu_actions()
    register_config_action()


patch_filtered_deck_dialog()

gui_hooks.profile_will_close.append(stop_scheduler)
gui_hooks.profile_will_close.append(cleanup_missing_decks)

if mw and mw.col:
    handle_profile_open()
else:
    gui_hooks.profile_did_open.append(handle_profile_open)


debug_log("Initialization complete")
