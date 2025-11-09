# Copyright (c) 2025, Joe Inman
#
# Licensed under the MIT License.
# You may obtain a copy of the License at:
#     https://opensource.org/licenses/MIT
#
# This file is part of the CrAnki Addon for Anki.

from aqt import mw
from aqt.qt import QCheckBox, QDialog, QDialogButtonBox, QVBoxLayout

from .config import get_debug_mode, set_debug_mode


class ConfigDialog(QDialog):
    """Minimal dialog that toggles debug mode."""

    def __init__(self, mw_instance):
        super().__init__(parent=mw_instance)
        self.setWindowTitle("CrAnki Configuration")

        self.layout = QVBoxLayout(self)
        self.debug_checkbox = QCheckBox("Enable debug mode")
        self.debug_checkbox.setChecked(get_debug_mode())
        self.layout.addWidget(self.debug_checkbox)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._persist_and_accept)
        buttons.rejected.connect(self.reject)
        self.layout.addWidget(buttons)

    def _persist_and_accept(self) -> None:
        set_debug_mode(self.debug_checkbox.isChecked())
        self.accept()


def show_config_dialog() -> None:
    if not mw:
        return
    dialog = ConfigDialog(mw)
    dialog.exec()
