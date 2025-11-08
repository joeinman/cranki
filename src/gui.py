"""GUI helpers for CrAnki."""

from aqt import gui_hooks, mw
from aqt.filtered_deck import FilteredDeckConfigDialog
from aqt.qt import (
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QTime,
    QTimeEdit,
    QTimer,
    QVBoxLayout,
    QWidget,
)

from .config import debug_log, get_deck_meta, set_deck_meta


def add_cranki_controls_to_dialog(dialog, did: int) -> None:
    """Add controls for scheduling inside the filtered deck dialog."""
    try:
        meta = get_deck_meta(did)
        debug_log(f"Creating UI controls for deck {did}")

        group_box = QGroupBox("Auto Rebuild")
        group_box.setStyleSheet("")
        group_layout = QVBoxLayout()
        group_layout.setContentsMargins(10, 15, 10, 10)
        group_box.setLayout(group_layout)

        checkbox = QCheckBox("Auto-rebuild at scheduled time")
        checkbox.setChecked(meta["enabled"])
        group_layout.addWidget(checkbox)

        time_container = QWidget()
        time_layout = QHBoxLayout()
        time_layout.setContentsMargins(20, 5, 0, 5)
        time_layout.setSpacing(10)
        time_container.setLayout(time_layout)

        time_label = QLabel("Rebuild at:")
        time_label.setMinimumWidth(80)
        time_layout.addWidget(time_label)

        time_edit = QTimeEdit()
        time_edit.setDisplayFormat("HH:mm")
        time_edit.setEnabled(meta["enabled"])
        time_edit.setMinimumWidth(100)

        try:
            hour, minute = map(int, meta["scheduled_time"].split(":"))
            time_edit.setTime(QTime(hour, minute))
        except (ValueError, AttributeError):
            time_edit.setTime(QTime(0, 0))

        time_layout.addWidget(time_edit)
        time_layout.addStretch()
        group_layout.addWidget(time_container)
        group_layout.addSpacing(5)

        def on_checkbox_changed(state):
            time_edit.setEnabled(bool(state))
            time_label.setEnabled(bool(state))
            enabled = checkbox.isChecked()
            scheduled_time = time_edit.time().toString("HH:mm")
            set_deck_meta(did, {"enabled": enabled, "scheduled_time": scheduled_time})
            debug_log(f"Auto-saved on checkbox change: enabled={enabled}")

        def on_time_changed():
            enabled = checkbox.isChecked()
            scheduled_time = time_edit.time().toString("HH:mm")
            set_deck_meta(
                did,
                {
                    "enabled": enabled,
                    "scheduled_time": scheduled_time,
                    "last_rebuild_date": "",
                },
            )
            debug_log(
                f"Auto-saved on time change: time={scheduled_time}, cleared last rebuild date"
            )

        checkbox.stateChanged.connect(on_checkbox_changed)
        time_edit.timeChanged.connect(on_time_changed)

        main_layout = dialog.layout()
        if main_layout and hasattr(main_layout, "insertWidget"):
            insert_pos = 4
            main_layout.insertWidget(insert_pos, group_box)
            group_box.show()
            dialog.adjustSize()
        else:
            debug_log("Could not add controls - no suitable layout found")

    except Exception as exc:  # pragma: no cover - defensive
        debug_log(f"Failed to add controls: {exc}")
        import traceback

        traceback.print_exc()


def patch_filtered_deck_dialog() -> None:
    """Patch the filtered deck dialog so it gets CrAnki controls."""
    _dialog_deck_ids = {}

    try:
        debug_log("Patching FilteredDeckConfigDialog.__init__")
        original_init = FilteredDeckConfigDialog.__init__

        def patched_init(self, *args, **kwargs):
            deck_id = kwargs.get("deck_id")
            debug_log(f"__init__ called with args={args}, kwargs={kwargs}")
            if deck_id is not None:
                _dialog_deck_ids[id(self)] = deck_id
                debug_log(f"Captured deck_id from kwargs: {deck_id}")
            result = original_init(self, *args, **kwargs)
            for attr in ["deck_id", "_deck_id", "did", "_did"]:
                if hasattr(self, attr):
                    val = getattr(self, attr)
                    if isinstance(val, int) and val not in _dialog_deck_ids.values():
                        _dialog_deck_ids[id(self)] = val
                        debug_log(f"Captured deck_id from attribute {attr}: {val}")
                        break
            return result

        FilteredDeckConfigDialog.__init__ = patched_init
        debug_log("Successfully patched FilteredDeckConfigDialog.__init__")

    except Exception as exc:  # pragma: no cover - defensive
        debug_log(f"Error patching __init__: {exc}")
        import traceback

        traceback.print_exc()
        return

    try:

        def on_dialog_open(dialog_manager, dialog_name: str, dialog_instance):
            try:
                if dialog_name != "FilteredDeckConfigDialog":
                    return

                dialog = dialog_instance
                debug_log(
                    f"Detected filtered deck dialog (type: {type(dialog).__name__})"
                )
                did = _dialog_deck_ids.get(id(dialog))

                if did is None:
                    filtered_decks = []
                    for deck in mw.col.decks.all_names_and_ids():
                        deck_obj = mw.col.decks.get(deck.id)
                        if deck_obj.get("dyn", False):
                            filtered_decks.append(deck.id)
                    if len(filtered_decks) == 1:
                        did = filtered_decks[0]
                    else:
                        debug_log("Unable to determine filtered deck")
                        return

                deck = mw.col.decks.get(did, default=False)
                if not deck or not deck.get("dyn", False):
                    return

                def add_controls_delayed():
                    try:
                        add_cranki_controls_to_dialog(dialog, did)
                    except Exception as exc_inner:  # pragma: no cover
                        debug_log(f"Error adding controls delayed: {exc_inner}")
                        import traceback

                        traceback.print_exc()

                QTimer.singleShot(100, add_controls_delayed)

            except Exception as exc_inner:  # pragma: no cover - defensive
                debug_log(f"Error in dialog hook: {exc_inner}")
                import traceback

                traceback.print_exc()

        if hasattr(gui_hooks, "dialog_manager_did_open_dialog"):
            gui_hooks.dialog_manager_did_open_dialog.append(on_dialog_open)
            debug_log("Registered dialog hook (dialog_manager_did_open_dialog)")
        else:
            debug_log("dialog_manager_did_open_dialog hook not available")

    except Exception as exc:  # pragma: no cover - defensive
        debug_log(f"Failed to patch filtered deck dialog: {exc}")
        import traceback

        traceback.print_exc()
