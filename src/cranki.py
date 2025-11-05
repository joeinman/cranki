# Copyright (c) 2025, Joe Inman
#
# Licensed under the MIT License.
# You may obtain a copy of the License at:
#     https://opensource.org/licenses/MIT
#
# This file is part of the CrAnki Addon for Anki.

from datetime import datetime
from typing import Optional, Dict, Any

from aqt import mw, gui_hooks
from aqt.filtered_deck import FilteredDeckConfigDialog
from aqt.qt import (
    QTimer, QTimeEdit, QLabel, QCheckBox, QHBoxLayout, QWidget, QTime, QAction,
    QGroupBox, QVBoxLayout
)
from aqt.utils import tooltip, showWarning


# =============================================================================
# Debug Logging
# =============================================================================

def debug_log(message: str) -> None:
    """
    Print debug message only if debug mode is enabled.
    """
    try:
        cfg = mw.addonManager.getConfig(__name__)
        if cfg and cfg.get("debug_mode", False):
            debug_log(f"{message}")
    except:
        # If we can't check config, don't log
        pass


# =============================================================================
# Config Helper Functions
# =============================================================================

def get_deck_meta(did: int) -> Dict[str, Any]:
    """
    Load per-deck settings from addon config.
    Returns default values if deck not found in config.
    """
    cfg = mw.addonManager.getConfig(__name__)
    if not cfg:
        cfg = {"per_deck": {}}
    
    per_deck = cfg.get("per_deck", {})
    deck_key = str(did)
    
    if deck_key in per_deck:
        return per_deck[deck_key]
    else:
        return {
            "enabled": False,
            "scheduled_time": "00:00",
            "last_rebuild_date": ""
        }


def set_deck_meta(did: int, updates: Dict[str, Any]) -> None:
    """
    Update per-deck settings in addon config.
    Merges updates with existing settings.
    """
    debug_log(f"set_deck_meta called for deck {did} with updates: {updates}")
    
    cfg = mw.addonManager.getConfig(__name__)
    debug_log(f"Current config before update: {cfg}")
    
    if not cfg:
        cfg = {"per_deck": {}}
    
    if "per_deck" not in cfg:
        cfg["per_deck"] = {}
    
    deck_key = str(did)
    
    # Get existing settings or defaults
    if deck_key not in cfg["per_deck"]:
        cfg["per_deck"][deck_key] = {
            "enabled": False,
            "scheduled_time": "00:00",
            "last_rebuild_date": ""
        }
    
    # Merge updates
    cfg["per_deck"][deck_key].update(updates)
    
    debug_log(f"Config after update: {cfg}")
    debug_log(f"Writing config using module name: {__name__}")
    
    # Write back to config
    mw.addonManager.writeConfig(__name__, cfg)
    
    debug_log(f"Config written successfully")


def cleanup_missing_decks() -> None:
    """
    Remove config entries for decks that no longer exist.
    Called when profile is closing.
    """
    cfg = mw.addonManager.getConfig(__name__)
    if not cfg or "per_deck" not in cfg:
        return
    
    per_deck = cfg["per_deck"]
    to_remove = []
    
    for deck_key in per_deck.keys():
        try:
            did = int(deck_key)
            # Check if deck still exists
            if not mw.col.decks.get(did, default=False):
                to_remove.append(deck_key)
        except (ValueError, AttributeError):
            to_remove.append(deck_key)
    
    # Remove missing decks
    for deck_key in to_remove:
        del per_deck[deck_key]
    
    if to_remove:
        mw.addonManager.writeConfig(__name__, cfg)


# =============================================================================
# UI Patching
# =============================================================================

def add_cranki_controls_to_dialog(dialog, did: int) -> None:
    """
    Add CrAnki controls to a filtered deck dialog.
    """
    try:
        # Load current settings
        meta = get_deck_meta(did)
        
        debug_log(f"Creating UI controls for deck {did}")
        
        group_box = QGroupBox("Auto Rebuild")
        group_box.setStyleSheet("")  # Use default Anki styling
        group_layout = QVBoxLayout()
        group_layout.setContentsMargins(10, 15, 10, 10)  # Match Anki's group box margins
        group_box.setLayout(group_layout)
        
        # Checkbox for enabling auto-rebuild
        checkbox = QCheckBox("Auto-rebuild at scheduled time")
        checkbox.setChecked(meta["enabled"])
        group_layout.addWidget(checkbox)
        
        # Time picker container with proper spacing
        time_container = QWidget()
        time_layout = QHBoxLayout()
        time_layout.setContentsMargins(20, 5, 0, 5)  # Add left margin for indentation
        time_layout.setSpacing(10)  # Add spacing between widgets
        time_container.setLayout(time_layout)
        
        time_label = QLabel("Rebuild at:")
        time_label.setMinimumWidth(80)  # Ensure label has consistent width
        time_layout.addWidget(time_label)
        
        time_edit = QTimeEdit()
        time_edit.setDisplayFormat("HH:mm")
        time_edit.setEnabled(meta["enabled"])
        time_edit.setMinimumWidth(100)  # Make time picker wider
        
        # Parse and set time
        try:
            hour, minute = map(int, meta["scheduled_time"].split(":"))
            time_edit.setTime(QTime(hour, minute))
        except (ValueError, AttributeError):
            time_edit.setTime(QTime(0, 0))
        
        time_layout.addWidget(time_edit)
        time_layout.addStretch()  # Push everything to the left
        
        group_layout.addWidget(time_container)
        
        # Add some spacing at the bottom
        group_layout.addSpacing(5)
        
        # Connect checkbox to time_edit enabled state
        def on_checkbox_changed(state):
            time_edit.setEnabled(bool(state))
            time_label.setEnabled(bool(state))
            # Auto-save when checkbox changes
            enabled = checkbox.isChecked()
            time = time_edit.time()
            scheduled_time = time.toString("HH:mm")
            set_deck_meta(did, {
                "enabled": enabled,
                "scheduled_time": scheduled_time
            })
            debug_log(f"Auto-saved on checkbox change: enabled={enabled}")
        
        def on_time_changed():
            # Auto-save when time changes
            # Clear last rebuild date so it can rebuild at the new time
            enabled = checkbox.isChecked()
            time = time_edit.time()
            scheduled_time = time.toString("HH:mm")
            set_deck_meta(did, {
                "enabled": enabled,
                "scheduled_time": scheduled_time,
                "last_rebuild_date": ""  # Clear so it can rebuild at new time
            })
            debug_log(f"Auto-saved on time change: time={scheduled_time}, cleared last rebuild date")
        
        checkbox.stateChanged.connect(on_checkbox_changed)
        time_edit.timeChanged.connect(on_time_changed)
        
        debug_log("Widgets created, adding to dialog...")
        
        # Add to main layout at position 4 (after Options section, before spacers)
        main_layout = dialog.layout()
        if main_layout and hasattr(main_layout, 'insertWidget'):
            count = main_layout.count()
            debug_log(f"Main layout has {count} items")
            insert_pos = 4  # After Deck, Filter, and Options sections
            main_layout.insertWidget(insert_pos, group_box)
            debug_log(f"✓ Inserted at position {insert_pos}")
            group_box.show()
            dialog.adjustSize()
        else:
            debug_log("✗ Could not add controls - no suitable layout found")
        
    except Exception as e:
        debug_log(f"Failed to add controls: {e}")
        import traceback
        traceback.print_exc()


def patch_filtered_deck_dialog() -> None:
    """
    Patch the filtered deck options dialog to add scheduling controls.
    Uses gui_hooks for modern Anki versions.
    """
    # Store deck_id when dialog is created
    _dialog_deck_ids = {}
    
    # Patch the class __init__ FIRST before any hooks
    try:
        debug_log("Patching FilteredDeckConfigDialog.__init__")
        
        # Store original __init__
        original_init = FilteredDeckConfigDialog.__init__
        
        def patched_init(self, *args, **kwargs):
            # Capture deck_id before calling original init
            deck_id = kwargs.get('deck_id')
            
            debug_log(f"__init__ called with args={args}, kwargs={kwargs}")
            
            if deck_id is not None:
                _dialog_deck_ids[id(self)] = deck_id
                debug_log(f"Captured deck_id from kwargs: {deck_id}")
            else:
                debug_log("No deck_id in kwargs")
            
            # Call original initialization
            result = original_init(self, *args, **kwargs)
            
            # Check if deck_id was set as an attribute during init
            for attr in ['deck_id', '_deck_id', 'did', '_did']:
                if hasattr(self, attr):
                    val = getattr(self, attr)
                    if isinstance(val, int) and val not in _dialog_deck_ids.values():
                        _dialog_deck_ids[id(self)] = val
                        debug_log(f"Captured deck_id from attribute {attr}: {val}")
                        break
            
            return result
        
        # Apply patch
        FilteredDeckConfigDialog.__init__ = patched_init
        debug_log("Successfully patched FilteredDeckConfigDialog.__init__")
        
    except ImportError as e:
        debug_log(f"Could not import FilteredDeckConfigDialog: {e}")
        return
    except Exception as e:
        debug_log(f"Error patching __init__: {e}")
        import traceback
        traceback.print_exc()
        return
    
    try:
        # Now set up hook-based approach (Anki 2.1.50+)
        try:
            def on_dialog_open(dialog_manager, dialog_name: str, dialog_instance):
                try:
                    # Only process FilteredDeckConfigDialog
                    if dialog_name != "FilteredDeckConfigDialog":
                        return
                    
                    dialog = dialog_instance
                    dialog_type = type(dialog).__name__
                    
                    debug_log(f"Detected filtered deck dialog (type: {dialog_type})")
                    debug_log(f"Dialog manager type: {type(dialog_manager)}")
                    
                    # The deck_id should have been stored during __init__
                    # Let's check if we stored it
                    did = _dialog_deck_ids.get(id(dialog))
                    
                    if did is not None:
                        debug_log(f"Found deck_id from init interception: {did}")
                    else:
                        debug_log("deck_id not found in init interception")
                        # Fall back to heuristic
                        filtered_decks = []
                        for deck in mw.col.decks.all_names_and_ids():
                            deck_obj = mw.col.decks.get(deck.id)
                            if deck_obj.get('dyn', False):
                                filtered_decks.append(deck.id)
                        
                        if len(filtered_decks) == 1:
                            did = filtered_decks[0]
                            debug_log(f"Only one filtered deck found, using: {did}")
                        else:
                            debug_log(f"Found {len(filtered_decks)} filtered decks, cannot determine which one")
                            return
                    
                    # Verify it's a filtered deck
                    deck = mw.col.decks.get(did, default=False)
                    if not deck:
                        debug_log(f"Deck {did} not found")
                        return
                    
                    if not deck.get('dyn', False):
                        debug_log(f"Deck {did} is not a filtered deck")
                        return
                    
                    debug_log(f"Processing filtered deck {did} - {deck.get('name', 'Unknown')}")
                    
                    # Use QTimer to add controls after dialog is fully initialized
                    def add_controls_delayed():
                        try:
                            debug_log("Adding controls (delayed)...")
                            add_cranki_controls_to_dialog(dialog, did)
                        except Exception as e:
                            debug_log(f"Error adding controls delayed: {e}")
                            import traceback
                            traceback.print_exc()
                    
                    # Add controls after a short delay to ensure dialog is fully constructed
                    QTimer.singleShot(100, add_controls_delayed)
                    
                except Exception as e:
                    debug_log(f"Error in dialog hook: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Register hook
            if hasattr(gui_hooks, 'dialog_manager_did_open_dialog'):
                gui_hooks.dialog_manager_did_open_dialog.append(on_dialog_open)
                debug_log("Registered dialog hook (dialog_manager_did_open_dialog)")
            else:
                debug_log("dialog_manager_did_open_dialog hook not available")
        except Exception as e:
            debug_log(f"Hook registration failed: {e}")
            import traceback
            traceback.print_exc()
        
    except Exception as e:
        debug_log(f"Failed to patch filtered deck dialog: {e}")
        import traceback
        traceback.print_exc()


# =============================================================================
# Scheduler Implementation
# =============================================================================

scheduler_timer: Optional[QTimer] = None


def check_and_rebuild_decks() -> None:
    """
    Check if any decks need to be rebuilt at the current time.
    Called every 60 seconds by the scheduler timer.
    """
    if not mw or not mw.col:
        return
    
    try:
        # Get current time and date
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        current_date = now.strftime("%Y-%m-%d")
        
        debug_log(f"Scheduler check at {current_time}")
        
        # Load config
        debug_log(f"Loading config using module name: {__name__}")
        cfg = mw.addonManager.getConfig(__name__)
        debug_log(f"Config loaded: {cfg}")
        
        if not cfg or "per_deck" not in cfg:
            debug_log("No config found or no per_deck key")
            return
        
        per_deck = cfg["per_deck"]
        debug_log(f"Checking {len(per_deck)} decks")
        
        # Check each deck
        for deck_key, settings in per_deck.items():
            debug_log(f"Deck {deck_key}: enabled={settings.get('enabled')}, scheduled={settings.get('scheduled_time')}, last_rebuild={settings.get('last_rebuild_date')}")
            
            if not settings.get("enabled", False):
                debug_log(f"Deck {deck_key} not enabled, skipping")
                continue
            
            scheduled_time = settings.get("scheduled_time", "00:00")
            last_rebuild_date = settings.get("last_rebuild_date", "")
            
            # Check if already rebuilt today - if so, skip regardless of time
            if last_rebuild_date == current_date:
                debug_log(f"Deck {deck_key} already rebuilt today ({current_date}), skipping")
                continue
            
            # Check if it's time to rebuild (current time >= scheduled time)
            if current_time >= scheduled_time:
                debug_log(f"Deck {deck_key}: current_time={current_time} >= scheduled_time={scheduled_time}, ready to rebuild!")
            else:
                debug_log(f"Deck {deck_key}: current_time={current_time} < scheduled_time={scheduled_time}, not yet time")
                continue
            
            # Rebuild this deck
            try:
                did = int(deck_key)
                
                # Verify deck still exists
                deck = mw.col.decks.get(did, default=False)
                if not deck:
                    continue
                
                # Verify it's a filtered deck
                if not deck.get('dyn', False):
                    continue
                
                deck_name = deck.get('name', f'Deck {did}')
                
                debug_log(f"Attempting to rebuild deck {did} ({deck_name})")
                
                # Capture variables for closures to avoid loop variable issues
                _did = did
                _deck_name = deck_name
                _current_date = current_date
                
                # Define background worker
                def rebuild_worker():
                    try:
                        # In modern Anki, use sched.rebuild_filtered_deck()
                        mw.col.sched.rebuild_filtered_deck(_did)
                        return True, None
                    except Exception as e:
                        debug_log(f"Rebuild error: {e}")
                        import traceback
                        traceback.print_exc()
                        return False, str(e)
                
                # Define done callback
                def rebuild_done(future):
                    try:
                        success, error = future.result()
                        
                        if success:
                            # Update last rebuild date
                            set_deck_meta(_did, {"last_rebuild_date": _current_date})
                            tooltip(f"✓ Rebuilt filtered deck: {_deck_name}")
                            
                            # Refresh the deck browser to show updated card counts
                            if hasattr(mw, 'deckBrowser') and mw.deckBrowser:
                                mw.deckBrowser.refresh()
                                debug_log("Refreshed deck browser")
                        else:
                            showWarning(
                                f"Failed to rebuild filtered deck '{_deck_name}':\n{error}"
                            )
                    except Exception as e:
                        showWarning(
                            f"Failed to rebuild filtered deck '{_deck_name}':\n{str(e)}"
                        )
                
                # Run in background
                mw.taskman.run_in_background(rebuild_worker, rebuild_done)
                
            except ValueError:
                # Invalid deck ID in config
                continue
            except Exception as e:
                debug_log(f"Error rebuilding deck {deck_key}: {e}")
                continue
    
    except Exception as e:
        debug_log(f"Error in check_and_rebuild_decks: {e}")


def start_scheduler() -> None:
    """
    Start the scheduler timer when profile opens.
    Syncs to check at the start of each minute.
    """
    global scheduler_timer
    
    debug_log("Starting scheduler...")
    
    if scheduler_timer is not None:
        debug_log("Stopping existing scheduler...")
        scheduler_timer.stop()
        scheduler_timer.deleteLater()
    
    # Calculate delay until next whole minute
    now = datetime.now()
    seconds_until_next_minute = 60 - now.second
    milliseconds_until_next_minute = seconds_until_next_minute * 1000 - now.microsecond // 1000
    
    debug_log(f"Syncing to clock - will first check in {seconds_until_next_minute} seconds")
    
    # Use a one-shot timer to sync to the next minute
    def start_regular_timer():
        global scheduler_timer
        
        # Run the first check
        check_and_rebuild_decks()
        
        # Now start the regular 60-second timer
        scheduler_timer = QTimer()
        scheduler_timer.setInterval(60000)  # 60 seconds
        scheduler_timer.timeout.connect(check_and_rebuild_decks)
        scheduler_timer.start()
        
        debug_log(f"Regular scheduler started! Timer active: {scheduler_timer.isActive()}, interval: {scheduler_timer.interval()}ms")
    
    # Start with a single-shot timer to sync to the next minute
    scheduler_timer = QTimer()
    scheduler_timer.setSingleShot(True)
    scheduler_timer.timeout.connect(start_regular_timer)
    scheduler_timer.start(milliseconds_until_next_minute)
    
    debug_log("Scheduler will sync to next whole minute.")


def stop_scheduler() -> None:
    """
    Stop the scheduler timer when profile closes.
    """
    global scheduler_timer
    
    if scheduler_timer is not None:
        scheduler_timer.stop()
        scheduler_timer.deleteLater()
        scheduler_timer = None


# =============================================================================
# Initialization
# =============================================================================

# Always show addon loaded message
cfg = mw.addonManager.getConfig(__name__) if mw else None
if cfg and cfg.get("debug_mode", False):
    print("="*60)
    print("CrAnki - Auto Rebuild Filtered Decks")
    print("Version: 1.0")
    print("Debug mode: ENABLED")
    print("="*60)
else:
    print("CrAnki: Addon loaded (debug mode: OFF, enable in Tools > Add-ons > Config)")

# Patch the filtered deck dialog
patch_filtered_deck_dialog()

# Connect hooks
gui_hooks.profile_did_open.append(start_scheduler)
gui_hooks.profile_will_close.append(stop_scheduler)
gui_hooks.profile_will_close.append(cleanup_missing_decks)

# Add menu action to manually test scheduler
def add_debug_menu():
    if not mw:
        return
    
    action = QAction("CrAnki: Test Scheduler Now", mw)
    action.triggered.connect(lambda: check_and_rebuild_decks())
    mw.form.menuTools.addAction(action)
    debug_log("Added debug menu item to Tools menu")

# Start scheduler immediately if profile is already open
if mw and mw.col:
    debug_log("Profile already open, starting scheduler immediately...")
    start_scheduler()
    add_debug_menu()
else:
    debug_log("Waiting for profile to open...")
    gui_hooks.profile_did_open.append(add_debug_menu)

debug_log("Initialization complete")
