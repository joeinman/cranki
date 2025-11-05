"""
CrAnki - Auto Rebuild Filtered Decks
Automatically rebuilds filtered decks at user-specified times
"""

from datetime import datetime
from typing import Optional, Dict, Any

from aqt import mw, gui_hooks
from aqt.qt import QTimer, QTimeEdit, QLabel, QCheckBox, QHBoxLayout, QWidget, QTime
from aqt.utils import tooltip, showWarning


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
    cfg = mw.addonManager.getConfig(__name__)
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
    
    # Write back to config
    mw.addonManager.writeConfig(__name__, cfg)


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
        
        print(f"CrAnki: Creating UI controls for deck {did}")
        
        # Create UI components - import all Qt widgets at once
        from aqt.qt import QGroupBox, QVBoxLayout, QHBoxLayout, QScrollArea
        
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
        
        group_layout.addWidget(time_container)
        
        # Connect checkbox to time_edit enabled state
        def on_checkbox_changed(state):
            time_edit.setEnabled(bool(state))
            time_label.setEnabled(bool(state))
        
        checkbox.stateChanged.connect(on_checkbox_changed)
        
        # Store references on dialog
        dialog._cranki_enabled_cb = checkbox
        dialog._cranki_time_edit = time_edit
        dialog._cranki_deck_id = did
        dialog._cranki_group_box = group_box
        
        print("CrAnki: Widgets created, attempting to add to dialog...")
        
        # Try to add to the dialog - multiple strategies
        added = False
        
        # Strategy 0: Find the scroll area and insert into its widget's layout (most accurate)
        if not added:
            scroll_areas = dialog.findChildren(QScrollArea)
            print(f"CrAnki: Found {len(scroll_areas)} scroll areas")
            for i, scroll in enumerate(scroll_areas):
                widget = scroll.widget()
                if widget and hasattr(widget, 'layout') and callable(widget.layout):
                    inner_layout = widget.layout()
                    if inner_layout and hasattr(inner_layout, 'insertWidget'):
                        try:
                            # Insert near the end but before spacers/stretch
                            count = inner_layout.count()
                            print(f"CrAnki: Scroll area {i} inner layout has {count} items")
                            
                            # Try to insert before the last 1-2 items
                            insert_pos = max(0, count - 1)
                            inner_layout.insertWidget(insert_pos, group_box)
                            added = True
                            print(f"CrAnki: Inserted via scroll area {i} at position {insert_pos}")
                            break
                        except Exception as e:
                            print(f"CrAnki: Failed scroll area {i}: {e}")
        
        # Strategy 1: Add to main layout (after Options section)
        if not added and hasattr(dialog, 'layout') and callable(dialog.layout):
            main_layout = dialog.layout()
            if main_layout is not None and hasattr(main_layout, 'insertWidget'):
                try:
                    count = main_layout.count()
                    print(f"CrAnki: Main layout has {count} items")
                    
                    # The layout typically has:
                    # 0: Deck section
                    # 1: Filter section  
                    # 2: Options section
                    # 3: Auto Rebuild (us!) <- Insert here
                    # 4: Spacer/stretch items
                    # 5: "Show excluded cards" link
                    # 6: Button box
                    # Insert at position 4 (right after Options section and before spacers)
                    if count >= 5:
                        insert_pos = 4
                        main_layout.insertWidget(insert_pos, group_box)
                        added = True
                        print(f"CrAnki: Inserted via dialog.layout() at position {insert_pos}")
                except Exception as e:
                    print(f"CrAnki: Strategy 1 (insertWidget) failed: {e}")
        
        # Strategy 1b: Add to end if insert didn't work
        if not added and hasattr(dialog, 'layout') and callable(dialog.layout):
            main_layout = dialog.layout()
            if main_layout is not None and hasattr(main_layout, 'addWidget'):
                try:
                    main_layout.addWidget(group_box)
                    added = True
                    print("CrAnki: Added via dialog.layout()")
                except Exception as e:
                    print(f"CrAnki: Strategy 1b failed: {e}")
        
        # Strategy 2: Add to form
        if not added and hasattr(dialog, 'form'):
            form = dialog.form
            print(f"CrAnki: Found form, attributes: {[a for a in dir(form) if 'layout' in a.lower()]}")
            for attr_name in dir(form):
                if 'layout' in attr_name.lower():
                    attr = getattr(form, attr_name, None)
                    if attr and hasattr(attr, 'addWidget'):
                        try:
                            attr.addWidget(group_box)
                            added = True
                            print(f"CrAnki: Added via form.{attr_name}")
                            break
                        except Exception as e:
                            print(f"CrAnki: Failed to add via form.{attr_name}: {e}")
        
        # Strategy 3: Find the main content widget
        if not added:
            print("CrAnki: Searching for layouts in widget tree...")
            
            # Look for scroll areas first (common in Anki dialogs)
            scroll_areas = dialog.findChildren(QScrollArea)
            for scroll in scroll_areas:
                widget = scroll.widget()
                if widget and hasattr(widget, 'layout') and callable(widget.layout):
                    layout = widget.layout()
                    if layout and hasattr(layout, 'addWidget'):
                        try:
                            layout.addWidget(group_box)
                            added = True
                            print("CrAnki: Added via QScrollArea widget")
                            break
                        except Exception as e:
                            print(f"CrAnki: Failed scroll area: {e}")
        
        # Strategy 4: Find any suitable layout
        if not added:
            layouts = dialog.findChildren(QVBoxLayout)
            print(f"CrAnki: Found {len(layouts)} QVBoxLayout instances")
            for i, layout in enumerate(layouts):
                try:
                    layout.addWidget(group_box)
                    added = True
                    print(f"CrAnki: Added via QVBoxLayout #{i}")
                    break
                except Exception as e:
                    print(f"CrAnki: Failed QVBoxLayout #{i}: {e}")
        
        # Strategy 5: Insert into first available QVBoxLayout with insertWidget
        if not added:
            layouts = dialog.findChildren(QVBoxLayout)
            for i, layout in enumerate(layouts):
                if layout.count() > 0:
                    try:
                        layout.insertWidget(layout.count(), group_box)
                        added = True
                        print(f"CrAnki: Inserted via QVBoxLayout #{i}")
                        break
                    except Exception as e:
                        print(f"CrAnki: Failed insert QVBoxLayout #{i}: {e}")
        
        if added:
            print(f"CrAnki: ✓ Successfully added controls to dialog for deck {did}")
            # Force update
            group_box.show()
            dialog.adjustSize()
        else:
            print("CrAnki: ✗ Could not find suitable layout to add controls")
            print(f"CrAnki: Dialog type: {type(dialog)}")
            print(f"CrAnki: Dialog has layout: {hasattr(dialog, 'layout')}")
            print(f"CrAnki: Dialog has form: {hasattr(dialog, 'form')}")
        
    except Exception as e:
        print(f"CrAnki: Failed to add controls: {e}")
        import traceback
        traceback.print_exc()


def save_cranki_settings(dialog) -> None:
    """
    Save CrAnki settings from dialog.
    """
    try:
        if not hasattr(dialog, '_cranki_enabled_cb'):
            return
        
        enabled = dialog._cranki_enabled_cb.isChecked()
        time = dialog._cranki_time_edit.time()
        scheduled_time = time.toString("HH:mm")
        
        set_deck_meta(dialog._cranki_deck_id, {
            "enabled": enabled,
            "scheduled_time": scheduled_time
        })
        print(f"CrAnki: Saved settings for deck {dialog._cranki_deck_id}: enabled={enabled}, time={scheduled_time}")
    except Exception as e:
        print(f"CrAnki: Failed to save settings: {e}")
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
        from aqt.filtered_deck import FilteredDeckConfigDialog
        
        print("CrAnki: Patching FilteredDeckConfigDialog.__init__")
        
        # Store original __init__
        original_init = FilteredDeckConfigDialog.__init__
        
        def patched_init(self, *args, **kwargs):
            # Capture deck_id before calling original init
            deck_id = kwargs.get('deck_id')
            
            print(f"CrAnki: __init__ called with args={args}, kwargs={kwargs}")
            
            if deck_id is not None:
                _dialog_deck_ids[id(self)] = deck_id
                print(f"CrAnki: Captured deck_id from kwargs: {deck_id}")
            else:
                print("CrAnki: No deck_id in kwargs")
            
            # Call original initialization
            result = original_init(self, *args, **kwargs)
            
            # Check if deck_id was set as an attribute during init
            for attr in ['deck_id', '_deck_id', 'did', '_did']:
                if hasattr(self, attr):
                    val = getattr(self, attr)
                    if isinstance(val, int) and val not in _dialog_deck_ids.values():
                        _dialog_deck_ids[id(self)] = val
                        print(f"CrAnki: Captured deck_id from attribute {attr}: {val}")
                        break
            
            return result
        
        # Apply patch
        FilteredDeckConfigDialog.__init__ = patched_init
        print("CrAnki: Successfully patched FilteredDeckConfigDialog.__init__")
        
    except ImportError as e:
        print(f"CrAnki: Could not import FilteredDeckConfigDialog: {e}")
        return
    except Exception as e:
        print(f"CrAnki: Error patching __init__: {e}")
        import traceback
        traceback.print_exc()
        return
    
    try:
        # Now set up hook-based approach (Anki 2.1.50+)
        try:
            from aqt import gui_hooks as hooks
            
            def on_dialog_open(dialog_manager, dialog_name: str, dialog_instance):
                try:
                    # Only process FilteredDeckConfigDialog
                    if dialog_name != "FilteredDeckConfigDialog":
                        return
                    
                    dialog = dialog_instance
                    dialog_type = type(dialog).__name__
                    
                    print(f"CrAnki: Detected filtered deck dialog (type: {dialog_type})")
                    print(f"CrAnki: Dialog manager type: {type(dialog_manager)}")
                    
                    # The deck_id should have been stored during __init__
                    # Let's check if we stored it
                    did = _dialog_deck_ids.get(id(dialog))
                    
                    if did is not None:
                        print(f"CrAnki: Found deck_id from init interception: {did}")
                    else:
                        print("CrAnki: deck_id not found in init interception")
                        # Fall back to heuristic
                        filtered_decks = []
                        for deck in mw.col.decks.all_names_and_ids():
                            deck_obj = mw.col.decks.get(deck.id)
                            if deck_obj.get('dyn', False):
                                filtered_decks.append(deck.id)
                        
                        if len(filtered_decks) == 1:
                            did = filtered_decks[0]
                            print(f"CrAnki: Only one filtered deck found, using: {did}")
                        else:
                            print(f"CrAnki: Found {len(filtered_decks)} filtered decks, cannot determine which one")
                            return
                    
                    # Verify it's a filtered deck
                    deck = mw.col.decks.get(did, default=False)
                    if not deck:
                        print(f"CrAnki: Deck {did} not found")
                        return
                    
                    if not deck.get('dyn', False):
                        print(f"CrAnki: Deck {did} is not a filtered deck")
                        return
                    
                    print(f"CrAnki: Processing filtered deck {did} - {deck.get('name', 'Unknown')}")
                    
                    # Use QTimer to add controls after dialog is fully initialized
                    from aqt.qt import QTimer
                    
                    def add_controls_delayed():
                        try:
                            print("CrAnki: Adding controls (delayed)...")
                            add_cranki_controls_to_dialog(dialog, did)
                            
                            # Patch the accept method
                            if hasattr(dialog, 'accept'):
                                original_accept = dialog.accept
                                
                                def patched_accept():
                                    save_cranki_settings(dialog)
                                    original_accept()
                                
                                dialog.accept = patched_accept
                                print(f"CrAnki: Patched accept method for deck {did}")
                            else:
                                print("CrAnki: Warning - dialog has no accept method")
                        except Exception as e:
                            print(f"CrAnki: Error adding controls delayed: {e}")
                            import traceback
                            traceback.print_exc()
                    
                    # Add controls after a short delay to ensure dialog is fully constructed
                    QTimer.singleShot(100, add_controls_delayed)
                    
                except Exception as e:
                    print(f"CrAnki: Error in dialog hook: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Register hook
            if hasattr(hooks, 'dialog_manager_did_open_dialog'):
                hooks.dialog_manager_did_open_dialog.append(on_dialog_open)
                print("CrAnki: Registered dialog hook (dialog_manager_did_open_dialog)")
            else:
                print("CrAnki: dialog_manager_did_open_dialog hook not available")
        except Exception as e:
            print(f"CrAnki: Hook registration failed: {e}")
            import traceback
            traceback.print_exc()
        
    except Exception as e:
        print(f"CrAnki: Failed to patch filtered deck dialog: {e}")
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
        
        # Load config
        cfg = mw.addonManager.getConfig(__name__)
        if not cfg or "per_deck" not in cfg:
            return
        
        per_deck = cfg["per_deck"]
        
        # Check each deck
        for deck_key, settings in per_deck.items():
            if not settings.get("enabled", False):
                continue
            
            scheduled_time = settings.get("scheduled_time", "00:00")
            last_rebuild_date = settings.get("last_rebuild_date", "")
            
            # Check if it's time to rebuild
            if scheduled_time != current_time:
                continue
            
            # Check if already rebuilt today
            if last_rebuild_date == current_date:
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
                
                # Define background worker
                def rebuild_worker():
                    try:
                        mw.col.rebuild_filtered_deck(did)
                        return True, None
                    except Exception as e:
                        return False, str(e)
                
                # Define done callback
                def rebuild_done(future):
                    try:
                        success, error = future.result()
                        
                        if success:
                            # Update last rebuild date
                            set_deck_meta(did, {"last_rebuild_date": current_date})
                            tooltip(f"✓ Rebuilt filtered deck: {deck_name}")
                        else:
                            showWarning(
                                f"Failed to rebuild filtered deck '{deck_name}':\n{error}"
                            )
                    except Exception as e:
                        showWarning(
                            f"Failed to rebuild filtered deck '{deck_name}':\n{str(e)}"
                        )
                
                # Run in background
                mw.taskman.run_in_background(rebuild_worker, rebuild_done)
                
            except ValueError:
                # Invalid deck ID in config
                continue
            except Exception as e:
                print(f"CrAnki: Error rebuilding deck {deck_key}: {e}")
                continue
    
    except Exception as e:
        print(f"CrAnki: Error in check_and_rebuild_decks: {e}")


def start_scheduler() -> None:
    """
    Start the scheduler timer when profile opens.
    """
    global scheduler_timer
    
    if scheduler_timer is not None:
        scheduler_timer.stop()
        scheduler_timer.deleteLater()
    
    scheduler_timer = QTimer()
    scheduler_timer.setInterval(60000)  # 60 seconds
    scheduler_timer.timeout.connect(check_and_rebuild_decks)
    scheduler_timer.start()


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

print("="*60)
print("CrAnki - Auto Rebuild Filtered Decks")
print("Version: 1.0")
print("Initializing addon...")
print("="*60)

# Patch the filtered deck dialog
patch_filtered_deck_dialog()

# Connect hooks
gui_hooks.profile_did_open.append(start_scheduler)
gui_hooks.profile_will_close.append(stop_scheduler)
gui_hooks.profile_will_close.append(cleanup_missing_decks)

print("CrAnki: Initialization complete")
