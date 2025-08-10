"""
Unit tests for the configuration system.
"""

import json
import logging
import os
from typing import Any, cast
from unittest.mock import Mock, mock_open, patch

import pytest

from src.config import (
    CONFIG_KEY,
    DEFAULT_CONFIG,
    ConfigValidationError,
    get_config,
    get_toggl_credentials,
    is_configured,
    reset_config,
    save_config,
    update_config_field,
)
from tests.test_constants import TEST_API_TOKEN, TEST_PROJECT_ID, TEST_WORKSPACE_ID


class TestConfig:
    """Test configuration management functions."""

    @pytest.mark.unit
    def test_get_config_with_no_mw(self) -> None:
        """Test get_config when mw is None."""
        with patch("src.config.mw", None):
            config = get_config()
            assert config == DEFAULT_CONFIG.copy()

    @pytest.mark.unit
    def test_get_config_with_no_existing_config(self) -> None:
        """Test get_config when no configuration exists."""
        mock_mw = Mock()
        mock_mw.addonManager.getConfig.return_value = None
        with patch("src.config.mw", mock_mw):
            config = get_config()
            assert config == DEFAULT_CONFIG.copy()
            mock_mw.addonManager.writeConfig.assert_called_once_with(
                CONFIG_KEY, DEFAULT_CONFIG.copy()
            )

    @pytest.mark.unit
    def test_get_config_with_existing_config(self) -> None:
        """Test get_config when configuration exists and merges defaults for missing optionals."""
        existing_config = {
            "api_token": TEST_API_TOKEN,
            "workspace_id": str(TEST_WORKSPACE_ID),
            "project_id": str(TEST_PROJECT_ID),
            "description": "Test Description",
        }

        mock_mw = Mock()
        mock_mw.addonManager.getConfig.return_value = existing_config

        with patch("src.config.mw", mock_mw):
            config = get_config()
            # Should preserve provided values
            assert config["api_token"] == TEST_API_TOKEN
            assert config["workspace_id"] == str(TEST_WORKSPACE_ID)
            assert config["project_id"] == str(TEST_PROJECT_ID)
            assert config["description"] == "Test Description"
            # Should include defaults for missing optional fields
            assert "auto_sync" in config
            assert "timezone" in config

    @pytest.mark.unit
    def test_save_config_success(self) -> None:
        """Test successful configuration save."""
        test_config = {
            "api_token": TEST_API_TOKEN,
            "workspace_id": TEST_WORKSPACE_ID,
            "project_id": TEST_PROJECT_ID,
        }
        mock_mw = Mock()
        # Patch manifest.json reading to return the fallback package name
        with patch("src.config.mw", mock_mw):
            with patch("src.config.CONFIG_KEY", "anki_toggl_dev"):
                result = save_config(cast("dict[str, object]", test_config))
                assert result is True
                mock_mw.addonManager.writeConfig.assert_called_once_with(
                    "anki_toggl_dev", test_config
                )

    @pytest.mark.unit
    def test_save_config_with_no_mw(self) -> None:
        """Test save_config when mw is None."""
        with patch("src.config.mw", None):
            result = save_config(cast("dict[str, object]", {"test": "value"}))
            assert result is False

    @pytest.mark.unit
    def test_save_config_exception(self) -> None:
        """Test save_config when an exception occurs."""
        mock_mw = Mock()
        mock_mw.addonManager.writeConfig.side_effect = Exception("Test error")
        with patch("src.config.mw", mock_mw):
            result = save_config(cast("dict[str, object]", {"test": "value"}))
            assert result is False

    @pytest.mark.unit
    def test_get_toggl_credentials_valid(self) -> None:
        """Test get_toggl_credentials with valid configuration."""
        valid_config = {
            "api_token": TEST_API_TOKEN,
            "workspace_id": str(TEST_WORKSPACE_ID),
            "project_id": str(TEST_PROJECT_ID),
            "description": "Test Description",
        }

        with patch("src.config.get_config", return_value=valid_config):
            credentials = get_toggl_credentials()

            assert credentials is not None
            assert credentials["api_token"] == TEST_API_TOKEN
            assert credentials["workspace_id"] == TEST_WORKSPACE_ID
            assert credentials["project_id"] == TEST_PROJECT_ID
            assert credentials["description"] == "Test Description"

    @pytest.mark.unit
    def test_get_toggl_credentials_missing_fields(self) -> None:
        """Test get_toggl_credentials with missing required fields."""
        invalid_config = {
            "api_token": TEST_API_TOKEN,
            # Missing workspace_id and project_id
        }

        with patch("src.config.get_config", return_value=invalid_config):
            with pytest.raises(ConfigValidationError) as exc_info:
                get_toggl_credentials()

            # Verify specific error message
            error_msg = str(exc_info.value)
            assert "Missing required field" in error_msg

    @pytest.mark.unit
    def test_get_toggl_credentials_invalid_numeric(self) -> None:
        """Test get_toggl_credentials with invalid numeric fields."""
        invalid_config = {
            "api_token": TEST_API_TOKEN,
            "workspace_id": "not_a_number",
            "project_id": "456",
        }

        with patch("src.config.get_config", return_value=invalid_config):
            with pytest.raises(ConfigValidationError) as exc_info:
                get_toggl_credentials()

            # Verify specific error message for numeric validation
            error_msg = str(exc_info.value)
            assert "must be integers" in error_msg

    @pytest.mark.unit
    def test_is_configured_true(self) -> None:
        """Test is_configured when properly configured."""
        valid_config = {
            "api_token": TEST_API_TOKEN,
            "workspace_id": str(TEST_WORKSPACE_ID),
            "project_id": str(TEST_PROJECT_ID),
        }

        with patch("src.config.get_config", return_value=valid_config):
            assert is_configured() is True

    @pytest.mark.unit
    def test_is_configured_false(self) -> None:
        """Test is_configured when not properly configured."""
        invalid_config = {
            "api_token": TEST_API_TOKEN,
            # Missing workspace_id and project_id
        }

        with patch("src.config.get_config", return_value=invalid_config):
            assert is_configured() is False

    @pytest.mark.unit
    def test_reset_config(self) -> None:
        """Test reset_config function."""
        with patch("src.config.save_config", return_value=True) as mock_save:
            result = reset_config()

            assert result is True
            mock_save.assert_called_once_with(DEFAULT_CONFIG.copy())

    @pytest.mark.unit
    def test_update_config_field(self) -> None:
        """Test update_config_field function."""
        existing_config = {"api_token": "old_token"}
        updated_config = {"api_token": "new_token"}

        with patch("src.config.get_config", return_value=existing_config):
            with patch("src.config.save_config", return_value=True) as mock_save:
                result = update_config_field("api_token", "new_token")

                assert result is True
                mock_save.assert_called_once_with(updated_config)

    def test_get_config_logs_key_and_contents(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_mw = Mock()
        mock_mw.addonManager.getConfig.return_value = {"api_token": "abc"}
        with patch("src.config.mw", mock_mw):
            with caplog.at_level("DEBUG"):
                config = get_config()
                assert config["api_token"] == "abc"
                assert any("Using config key" in r.message for r in caplog.records)

    def test_save_config_logs_key_and_contents(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_mw = Mock()
        with patch("src.config.mw", mock_mw):
            with caplog.at_level("DEBUG"):
                result = save_config(cast("dict[str, object]", {"api_token": "abc"}))
                assert result is True
                assert any("Using config key" in r.message for r in caplog.records)

    def test_get_config_missing_logs_stack(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_mw = Mock()
        mock_mw.addonManager.getConfig.return_value = None
        with patch("src.config.mw", mock_mw):
            with caplog.at_level("INFO"):
                config = get_config()
                assert config == DEFAULT_CONFIG.copy()
                assert any(
                    "No config found; saving default config." in r.message
                    for r in caplog.records
                )

    def test_config_persistence_with_dynamic_key(self) -> None:
        dummy_package = "dummy_addon_package"
        dummy_config = {
            "api_token": "dummy_token",
            "workspace_id": 1,
            "project_id": 2,
        }
        # Patch manifest.json reading
        manifest_data = json.dumps({"package": dummy_package})
        with patch("builtins.open", mock_open(read_data=manifest_data)):
            # Patch mw and its addonManager
            mock_mw = Mock()
            # Simulate config present after save
            mock_mw.addonManager.getConfig.return_value = dummy_config
            # Patch CONFIG_KEY to match dummy_package
            with patch("src.config.mw", mock_mw):
                with patch("src.config.CONFIG_KEY", dummy_package):
                    # Patch save_config so that after saving, getConfig returns dummy_config
                    def save_config_side_effect(c: Any) -> bool:
                        return True

                    with patch(
                        "src.config.save_config", side_effect=save_config_side_effect
                    ):
                        # Save dummy config
                        result = save_config(cast("dict[str, object]", dummy_config))
                        assert result is True
                        # Now get config (should return dummy_config)
                        config = get_config()
                        # Should preserve stored values
                        assert config["api_token"] == dummy_config["api_token"]
                        assert config["workspace_id"] == dummy_config["workspace_id"]
                        assert config["project_id"] == dummy_config["project_id"]
                        # And merge in defaults for optionals
                        assert "description" in config
                        assert "auto_sync" in config
                        assert "timezone" in config
                        # Ensure correct key was used
                        mock_mw.addonManager.writeConfig.assert_called_with(
                            dummy_package, dummy_config
                        )
                        mock_mw.addonManager.getConfig.assert_called_with(dummy_package)

    def test_config_dialog_loads_all_fields_and_warns_on_missing(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        from collections.abc import Mapping

        from src.config_schema import CONFIG_SCHEMA

        class DummyDialog:
            fields: dict[str, "DummyWidget"]

            def __init__(self, fields: dict[str, "DummyWidget"]):
                self.fields = fields

            def load_config(self, config: Mapping[str, object]) -> None:
                missing = [k for k in CONFIG_SCHEMA if k not in config]
                if missing:
                    logging.warning(
                        f"Config being loaded into dialog is missing fields: {missing}"
                    )
                for field_name, widget in self.fields.items():
                    value = config.get(field_name, "")
                    if hasattr(widget, "setText"):
                        widget.setText(value)
                    elif hasattr(widget, "setChecked"):
                        widget.setChecked(value)

        class DummyWidget:
            set_called: bool

            def __init__(self):
                self.set_called = False

            def setText(self, val: object) -> None:
                self.set_called = True

            def setChecked(self, val: object) -> None:
                self.set_called = True

        fields = {k: DummyWidget() for k in CONFIG_SCHEMA}
        dialog = DummyDialog(fields)
        # All fields present
        config = {
            k: (
                123 if k == "workspace_id" else 456 if k == "project_id" else f"val_{k}"
            )
            for k in CONFIG_SCHEMA
        }
        with caplog.at_level("DEBUG"):
            dialog.load_config(config)
            assert not any("missing fields" in r for r in caplog.text.splitlines())
        # Missing fields
        config_missing = {"description": "desc", "workspace_id": 123, "project_id": 456}
        with caplog.at_level("DEBUG"):
            dialog.load_config(config_missing)
            assert any("missing fields" in r for r in caplog.text.splitlines())

    def test_save_config_with_only_description(self, caplog) -> None:
        """Test saving a config dict with only 'description' field."""
        from src.config import save_config

        mock_mw = Mock()
        config = {
            "description": "Test desc",
            "workspace_id": 1,
            "project_id": 2,
            "api_token": "token",
        }
        with patch("src.config.mw", mock_mw):
            result = save_config(cast("dict[str, object]", config))
            assert result is True
            mock_mw.addonManager.writeConfig.assert_called_once()
            # Should warn about missing fields
            assert any("missing fields" in r for r in caplog.text.splitlines())

    def test_save_config_with_missing_required_fields(self, caplog) -> None:
        """Test saving a config dict missing required fields triggers warning."""
        from src.config import save_config

        mock_mw = Mock()
        config = {"api_token": "token", "workspace_id": 1}
        with patch("src.config.mw", mock_mw):
            result = save_config(cast("dict[str, object]", config))
            assert result is True
            mock_mw.addonManager.writeConfig.assert_called_once()
            # Should warn about missing fields
            assert any("missing fields" in r for r in caplog.text.splitlines())

    def test_save_and_load_config_with_all_fields(self, caplog) -> None:
        """Test saving and loading a config dict with all fields persists correctly."""
        from src.config import get_config, save_config
        from src.config_schema import CONFIG_SCHEMA

        mock_mw = Mock()
        config = {
            k: (123 if k == "workspace_id" else 456 if k == "project_id" else "x")
            for k, v in CONFIG_SCHEMA.items()
        }
        with patch("src.config.mw", mock_mw):
            mock_mw.addonManager.getConfig.return_value = config
            result = save_config(cast("dict[str, object]", config))
            assert result is True
            loaded = get_config()
            assert loaded == config
            # Should not warn about missing fields
            assert not any("missing fields" in r for r in caplog.text.splitlines())

    def test_config_key_is_addon_folder_name(self) -> None:
        """Test that CONFIG_KEY is set to the add-on folder name."""
        expected = os.path.basename(os.path.dirname(os.path.abspath("src/config.py")))
        assert expected == CONFIG_KEY

    @pytest.mark.unit
    def test_get_config_uses_addon_manager_mapping_key(self) -> None:
        """get_config should resolve key via addonFromModule(__name__) when available."""
        from src import config as cfg

        mock_mw = Mock()
        mock_mw.addonManager.addonFromModule.return_value = "addon-folder-xyz"
        # Provide a minimal valid config to avoid default-save path
        mock_mw.addonManager.getConfig.return_value = {
            "api_token": TEST_API_TOKEN,
            "workspace_id": str(TEST_WORKSPACE_ID),
            "project_id": str(TEST_PROJECT_ID),
        }

        with patch("src.config.mw", mock_mw):
            loaded = cfg.get_config()
            assert loaded["api_token"] == TEST_API_TOKEN
            mock_mw.addonManager.addonFromModule.assert_called_once()
            # Should use resolved key for reads
            mock_mw.addonManager.getConfig.assert_called_with("addon-folder-xyz")

    @pytest.mark.unit
    def test_save_config_uses_addon_manager_mapping_key(self) -> None:
        """save_config should use addonFromModule(__name__) result for writes."""
        from src import config as cfg

        mock_mw = Mock()
        mock_mw.addonManager.addonFromModule.return_value = "addon-folder-xyz"

        config = {
            "api_token": TEST_API_TOKEN,
            "workspace_id": TEST_WORKSPACE_ID,
            "project_id": TEST_PROJECT_ID,
        }

        with patch("src.config.mw", mock_mw):
            ok = cfg.save_config(cast("dict[str, object]", config))
            assert ok is True
            mock_mw.addonManager.writeConfig.assert_called_with(
                "addon-folder-xyz", config
            )

    @pytest.mark.unit
    @pytest.mark.parametrize("returned", [None, "", Exception("boom")])
    def test_resolve_config_key_fallbacks(self, returned: object) -> None:
        """When addonFromModule fails/empty, fall back to CONFIG_KEY (folder name)."""
        from src import config as cfg

        mock_mw = Mock()
        if isinstance(returned, Exception):
            mock_mw.addonManager.addonFromModule.side_effect = returned
        else:
            mock_mw.addonManager.addonFromModule.return_value = returned  # type: ignore[assignment]
        mock_mw.addonManager.getConfig.return_value = None

        with patch("src.config.mw", mock_mw):
            # Trigger read which also triggers default write path
            loaded = cfg.get_config()
            assert isinstance(loaded, dict)
            # Should have fallen back to CONFIG_KEY (folder name 'src')
            fallback_key = CONFIG_KEY
            mock_mw.addonManager.getConfig.assert_called_with(fallback_key)
            mock_mw.addonManager.writeConfig.assert_called_with(
                fallback_key, DEFAULT_CONFIG.copy()
            )

    def test_get_config_uses_default_for_missing_optional_fields(self) -> None:
        from src.constants import DEFAULT_DESCRIPTION, DEFAULT_TIMEZONE

        existing_config = {
            "api_token": TEST_API_TOKEN,
            "workspace_id": str(TEST_WORKSPACE_ID),
            "project_id": str(TEST_PROJECT_ID),
            # intentionally omit description, auto_sync, timezone
        }

        mock_mw = Mock()
        mock_mw.addonManager.getConfig.return_value = existing_config

        with patch("src.config.mw", mock_mw):
            config = get_config()
            assert config["description"] == DEFAULT_DESCRIPTION
            assert config["timezone"] == DEFAULT_TIMEZONE
            assert config["auto_sync"] is False

    def test_get_config_uses_default_when_description_blank(self) -> None:
        from src.constants import DEFAULT_DESCRIPTION

        existing_config = {
            "api_token": TEST_API_TOKEN,
            "workspace_id": str(TEST_WORKSPACE_ID),
            "project_id": str(TEST_PROJECT_ID),
            "description": "",  # blank should coalesce to default
        }

        mock_mw = Mock()
        mock_mw.addonManager.getConfig.return_value = existing_config

        with patch("src.config.mw", mock_mw):
            config = get_config()
            assert config["description"] == DEFAULT_DESCRIPTION

    def test_get_config_uses_default_when_timezone_blank(self) -> None:
        from src.constants import DEFAULT_TIMEZONE

        existing_config = {
            "api_token": TEST_API_TOKEN,
            "workspace_id": str(TEST_WORKSPACE_ID),
            "project_id": str(TEST_PROJECT_ID),
            "timezone": "",  # blank should coalesce to default
        }

        mock_mw = Mock()
        mock_mw.addonManager.getConfig.return_value = existing_config

        with patch("src.config.mw", mock_mw):
            config = get_config()
            assert config["timezone"] == DEFAULT_TIMEZONE


class TestTimezoneConfig:
    """Test timezone configuration functions."""

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "timezone,expected",
        [
            ("UTC", True),
            ("America/New_York", True),
            ("Europe/London", True),
            ("Asia/Tokyo", True),
            ("Australia/Sydney", True),
            ("America/Los_Angeles", True),
            ("Invalid/Timezone", False),
            ("", False),
            ("America/NonExistent", False),
            ("Random/String", False),
        ],
    )
    def test_validate_timezone(self, timezone: str, expected: bool) -> None:
        """Test validate_timezone with different timezone names."""
        from src.timezone import validate_timezone_string as validate_timezone

        result = validate_timezone(timezone)
        assert result is expected, (
            f"'{timezone}' should be {'valid' if expected else 'invalid'}"
        )

    @pytest.mark.unit
    @pytest.mark.parametrize("timezone_abbrev", ["PST", "EDT"])
    def test_validate_timezone_abbreviations(self, timezone_abbrev: str) -> None:
        """Test validate_timezone with timezone abbreviations."""
        from src.timezone import validate_timezone_string as validate_timezone

        # These are often invalid IANA names, but some systems might accept them
        # We'll just test that the function returns a boolean
        result = validate_timezone(timezone_abbrev)
        assert isinstance(result, bool), f"'{timezone_abbrev}' should return a boolean"

    def test_get_common_timezones(self) -> None:
        """Test get_common_timezones returns expected timezone list."""
        from src.timezone import get_common_timezones

        common_tz = get_common_timezones()

        # Should return a list
        assert isinstance(common_tz, list)

        # Should have reasonable number of timezones
        assert len(common_tz) > 10
        assert len(common_tz) < 100  # Not too many to overwhelm UI

        # Should include UTC
        assert "UTC" in common_tz

        # Should include some major timezones
        major_timezones = ["America/New_York", "Europe/London", "Asia/Tokyo"]
        for tz in major_timezones:
            assert tz in common_tz, f"'{tz}' should be in common timezones"

        # All returned timezones should be valid
        from src.timezone import validate_timezone_string as validate_timezone

        for tz in common_tz:
            assert validate_timezone(tz), f"'{tz}' should be a valid timezone"
