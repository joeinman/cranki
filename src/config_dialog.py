"""Simple configuration dialog for CrAnki."""

from aqt import mw
from aqt.qt import QCheckBox, QDialog, QDialogButtonBox, QVBoxLayout


class ConfigDialog(QDialog):
    """Minimal dialog that toggles debug mode."""

    def __init__(self, mw_instance, module_name: str):
        super().__init__(parent=mw_instance)
        self._module_name = module_name
        self.setWindowTitle("CrAnki Configuration")

        self.layout = QVBoxLayout(self)
        self.debug_checkbox = QCheckBox("Enable debug mode")
        cfg = mw.addonManager.getConfig(self._module_name) or {}
        self.debug_checkbox.setChecked(cfg.get("debug_mode", False))
        self.layout.addWidget(self.debug_checkbox)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._persist_and_accept)
        buttons.rejected.connect(self.reject)
        self.layout.addWidget(buttons)

    def _persist_and_accept(self) -> None:
        cfg = mw.addonManager.getConfig(self._module_name) or {}
        cfg["debug_mode"] = self.debug_checkbox.isChecked()
        mw.addonManager.writeConfig(self._module_name, cfg)
        self.accept()


def show_config_dialog(module_name: str) -> None:
    dialog = ConfigDialog(mw, module_name)
    dialog.exec()
