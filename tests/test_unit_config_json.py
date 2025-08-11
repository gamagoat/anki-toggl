"""Test config.json file exists and has correct structure."""

import json
from pathlib import Path

import pytest

from src.config import DEFAULT_CONFIG


class TestConfigJson:
    """Test config.json file for Anki add-on compatibility."""

    @pytest.mark.unit
    def test_config_json_exists(self):
        """Test that config.json file exists in src directory."""
        config_json_path = Path(__file__).parent.parent / "src" / "config.json"
        assert config_json_path.exists(), (
            "config.json file is required for Anki add-on config system"
        )

    @pytest.mark.unit
    def test_config_json_valid_json(self):
        """Test that config.json contains valid JSON."""
        config_json_path = Path(__file__).parent.parent / "src" / "config.json"
        try:
            with open(config_json_path) as f:
                json.load(f)
        except json.JSONDecodeError as e:
            pytest.fail(f"config.json contains invalid JSON: {e}")

    @pytest.mark.unit
    def test_config_json_matches_defaults(self):
        """Test that config.json contains the same fields as DEFAULT_CONFIG."""
        config_json_path = Path(__file__).parent.parent / "src" / "config.json"

        with open(config_json_path) as f:
            config_json = json.load(f)

        # Check that all DEFAULT_CONFIG keys are present in config.json
        for key in DEFAULT_CONFIG:
            assert key in config_json, f"config.json missing required key: {key}"

        # Check that config.json doesn't have extra keys
        for key in config_json:
            assert key in DEFAULT_CONFIG, f"config.json has unexpected key: {key}"

    @pytest.mark.unit
    def test_config_json_default_values(self):
        """Test that config.json has expected default values."""
        config_json_path = Path(__file__).parent.parent / "src" / "config.json"

        with open(config_json_path) as f:
            config_json = json.load(f)

        # Test specific default values
        assert config_json["api_token"] == "", (
            "API token should default to empty string"
        )
        assert config_json["workspace_id"] == 0, "Workspace ID should default to 0"
        assert config_json["project_id"] == 0, "Project ID should default to 0"
        assert config_json["description"] == "anki", (
            "Description should have default value"
        )
        assert config_json["auto_sync"] is False, "Auto sync should default to False"
        assert config_json["timezone"] == "UTC", "Timezone should default to UTC"

    @pytest.mark.unit
    def test_config_md_exists(self):
        """Test that config.md documentation file exists."""
        config_md_path = Path(__file__).parent.parent / "src" / "config.md"
        assert config_md_path.exists(), (
            "config.md file provides user documentation for configuration"
        )
