"""Qt dialog for configuring the add-on."""

from typing import Any

from .config import (
    ConfigValidationError,
    _sanitize_config_for_logging,
    get_config,
    reset_config,
    save_config,
    validate_config,
)
from .config_schema import CONFIG_SCHEMA
from .logger import get_module_logger
from .timezone import get_common_timezones


def _import_qt_components() -> tuple[Any, ...]:
    """Import Qt components dynamically to avoid imports at module level."""
    # Import the qt module and fetch attributes dynamically to keep type checker happy
    from aqt import qt as aqt_qt

    return (
        aqt_qt.QCheckBox,
        aqt_qt.QComboBox,
        aqt_qt.QDialog,
        aqt_qt.QFormLayout,
        aqt_qt.QGroupBox,
        aqt_qt.QHBoxLayout,
        aqt_qt.QLabel,
        aqt_qt.QLineEdit,
        aqt_qt.QMessageBox,
        aqt_qt.QPushButton,
        aqt_qt.QTextEdit,
        aqt_qt.QVBoxLayout,
    )


class ConfigDialog:
    """Configuration dialog for Toggl credentials and settings."""

    def __init__(self, parent: Any = None) -> None:
        # Import Qt components when dialog is actually created
        (
            self.QCheckBox,
            self.QComboBox,
            self.QDialog,
            self.QFormLayout,
            self.QGroupBox,
            self.QHBoxLayout,
            self.QLabel,
            self.QLineEdit,
            self.QMessageBox,
            self.QPushButton,
            self.QTextEdit,
            self.QVBoxLayout,
        ) = _import_qt_components()

        # Initialize the actual dialog
        self._dialog = self.QDialog(parent)
        self.logger: Any = get_module_logger("config_dialog")
        self._dialog.setWindowTitle("AnkiToggl Configuration")
        self._dialog.setModal(True)
        self._dialog.resize(500, 600)

        # field widgets
        self.fields: dict[str, Any] = {}

        self.setup_ui()
        self.load_config()

    def setup_ui(self):
        """Set up the user interface."""
        layout = self.QVBoxLayout()

        title = self.QLabel("AnkiToggl Configuration")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)

        desc = self.QLabel(
            "Configure your Toggl Track credentials and sync settings below."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("margin-bottom: 15px;")
        layout.addWidget(desc)

        # Form layout for fields
        form_layout = self.QFormLayout()

        # Add fields based on schema
        for field_name, field_config in CONFIG_SCHEMA.items():
            if field_config["type"] == "text":
                if field_name == "description":
                    widget = self.QTextEdit()
                    widget.setMaximumHeight(60)
                    widget.setPlaceholderText("Enter description for time entries")
                else:
                    widget = self.QLineEdit()
                    if field_name == "api_token":
                        widget.setEchoMode(self.QLineEdit.EchoMode.Password)
                        widget.setPlaceholderText("Enter your Toggl API token")
                    elif field_name in ["workspace_id", "project_id"]:
                        widget.setPlaceholderText("Enter numeric ID")
                        widget.setText("")  # Default to empty
                    else:
                        widget.setPlaceholderText(f"Enter {field_config['label']}")

                self.fields[field_name] = widget
                form_layout.addRow(str(field_config["label"]), widget)

            elif field_config["type"] == "checkbox":
                widget = self.QCheckBox()
                widget.setToolTip(str(field_config["description"]))
                self.fields[field_name] = widget
                form_layout.addRow(str(field_config["label"]), widget)

            elif field_config["type"] == "dropdown":
                widget = self.QComboBox()
                widget.setEditable(False)
                widget.setToolTip(str(field_config["description"]))

                for tz in get_common_timezones():
                    widget.addItem(tz)

                self.fields[field_name] = widget
                form_layout.addRow(str(field_config["label"]), widget)

        layout.addLayout(form_layout)
        layout.addSpacing(16)

        help_group = self.QGroupBox("How to get your Toggl credentials:")
        help_layout = self.QVBoxLayout()
        help_text = self.QLabel(
            "1. Go to https://track.toggl.com/profile\n"
            + "2. Scroll down to 'API Token' and copy it\n"
            + "3. Find your Workspace ID and Project ID in your Toggl dashboard\n"
            + "4. Enter these values above and click 'Save'"
        )
        help_text.setWordWrap(True)
        help_text.setStyleSheet("font-size: 13px; margin: 4px 0 4px 0;")
        help_layout.addWidget(help_text)
        help_group.setLayout(help_layout)
        layout.addWidget(help_group)
        layout.addSpacing(16)

        button_layout = self.QHBoxLayout()
        save_button = self.QPushButton("Save")
        save_button.clicked.connect(self.save_config)
        save_button.setDefault(True)
        cancel_button = self.QPushButton("Cancel")
        cancel_button.clicked.connect(self._dialog.reject)
        reset_button = self.QPushButton("Reset to Defaults")
        reset_button.clicked.connect(self.reset_config)
        button_layout.addWidget(reset_button)
        button_layout.addStretch()
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(save_button)
        layout.addLayout(button_layout)
        self._dialog.setLayout(layout)
        self.logger.debug(
            f"Fields in config dialog after setup: {list(self.fields.keys())}"
        )

    def load_config(self):
        """Load current configuration into the dialog."""
        config = get_config()

        # Hide sensitive data
        sanitized_config = _sanitize_config_for_logging(config)
        self.logger.debug(f"Config dict being loaded into dialog: {sanitized_config}")

        for field_name, widget in self.fields.items():
            value = config.get(field_name, "")

            if hasattr(widget, "setChecked") and hasattr(widget, "isChecked"):
                # QCheckBox
                widget.setChecked(bool(value))
            elif hasattr(widget, "setPlainText") and hasattr(widget, "toPlainText"):
                # QTextEdit
                widget.setPlainText(str(value) if value else "")
            elif hasattr(widget, "currentText") and hasattr(widget, "findText"):
                # QComboBox
                if value:
                    index = widget.findText(str(value))
                    if index >= 0:
                        widget.setCurrentIndex(index)
            elif hasattr(widget, "setText") and hasattr(widget, "text"):
                # QLineEdit
                widget.setText(str(value) if value else "")

    def save_config(self):
        """Save configuration from the dialog."""
        config_dict = {}
        for field_name, widget in self.fields.items():
            if hasattr(widget, "setChecked") and hasattr(widget, "isChecked"):
                # QCheckBox
                config_dict[field_name] = widget.isChecked()
            elif hasattr(widget, "setPlainText") and hasattr(widget, "toPlainText"):
                # QTextEdit
                config_dict[field_name] = widget.toPlainText().strip()
            elif hasattr(widget, "currentText") and hasattr(widget, "findText"):
                # QComboBox
                config_dict[field_name] = widget.currentText().strip()
            elif hasattr(widget, "setText") and hasattr(widget, "text"):
                # QLineEdit
                config_dict[field_name] = widget.text().strip()
        try:
            config = validate_config(config_dict)
            if save_config(config):
                self.logger.info("Configuration saved successfully from dialog")
                self._dialog.accept()
            else:
                self.logger.error("Failed to save configuration from dialog")
        except ConfigValidationError as e:
            self.logger.error(f"Configuration validation failed: {e}")
            self.QMessageBox.warning(
                self._dialog,
                "Configuration Error",
                f"Configuration validation failed: {e}",
            )

    def reset_config(self):
        """Reset configuration to defaults."""
        if reset_config():
            self.logger.info("Configuration reset to defaults")
            self.load_config()
        else:
            self.logger.error("Failed to reset configuration")

    def exec(self) -> Any:
        """Execute the dialog and return result."""
        return self._dialog.exec()


def open_config_dialog(parent: Any = None) -> bool:
    """
    Open the configuration dialog.

    Args:
        parent: Parent widget

    Returns:
        True if configuration was saved, False if cancelled
    """
    dialog = ConfigDialog(parent)
    result = dialog.exec()
    # Import QDialog dynamically to get the enum value
    from aqt import qt as aqt_qt

    return result == aqt_qt.QDialog.DialogCode.Accepted
