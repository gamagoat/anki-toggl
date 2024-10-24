"""Configuration management helpers for the add-on."""

from pathlib import Path
from typing import Any, Optional

from .constants import (
    CONFIG_API_TOKEN,
    CONFIG_AUTO_SYNC,
    CONFIG_DESCRIPTION,
    CONFIG_PROJECT_ID,
    CONFIG_TIMEZONE,
    CONFIG_WORKSPACE_ID,
    DEFAULT_DESCRIPTION,
    DEFAULT_TIMEZONE,
    MAX_DESCRIPTION_LENGTH,
    MIN_DESCRIPTION_LENGTH,
)
from .logger import get_module_logger
from .security_utils import sanitize_for_logging, validate_api_token_format
from .timezone import Timezone, validate_timezone_string


class ConfigValidationError(Exception):
    pass


DEFAULT_CONFIG: dict[str, object] = {
    CONFIG_API_TOKEN: "",
    CONFIG_WORKSPACE_ID: 0,
    CONFIG_PROJECT_ID: 0,
    CONFIG_DESCRIPTION: DEFAULT_DESCRIPTION,
    CONFIG_AUTO_SYNC: False,
    CONFIG_TIMEZONE: DEFAULT_TIMEZONE,
}

CONFIG_KEY = Path(__file__).parent.name
REQUIRED_FIELDS = [CONFIG_API_TOKEN, CONFIG_WORKSPACE_ID, CONFIG_PROJECT_ID]

logger = get_module_logger("config")

# NOTE: Do not import `aqt` at module import time to keep tests headless.
# This placeholder is populated at runtime by `src.__init__` or tests may patch it.
mw: Optional[Any] = None


def validate_config(config: dict[str, object]) -> dict[str, object]:
    for field in REQUIRED_FIELDS:
        if not config.get(field):
            raise ConfigValidationError(f"Missing required field: {field}")
    if not validate_api_token_format(str(config["api_token"])):
        raise ConfigValidationError("Invalid API token format")
    try:
        workspace_id = int(str(config["workspace_id"]))
        project_id = int(str(config["project_id"]))
    except Exception as e:
        raise ConfigValidationError(
            f"Workspace ID and Project ID must be integers: {e}"
        )
    if workspace_id <= 0 or project_id <= 0:
        raise ConfigValidationError(
            "Workspace ID and Project ID must be positive integers"
        )
    desc = str(config.get("description", ""))
    if not (MIN_DESCRIPTION_LENGTH <= len(desc) <= MAX_DESCRIPTION_LENGTH):
        raise ConfigValidationError(
            f"Description must be between {MIN_DESCRIPTION_LENGTH} and {MAX_DESCRIPTION_LENGTH} characters"
        )
    tz = str(config.get("timezone", "UTC"))
    if not validate_timezone_string(tz):
        raise ConfigValidationError(f"Invalid timezone: {tz}")
    auto_sync = bool(config.get("auto_sync", False))
    return {
        CONFIG_API_TOKEN: str(config[CONFIG_API_TOKEN]),
        CONFIG_WORKSPACE_ID: workspace_id,
        CONFIG_PROJECT_ID: project_id,
        CONFIG_DESCRIPTION: desc,
        CONFIG_AUTO_SYNC: auto_sync,
        CONFIG_TIMEZONE: tz,
    }


def get_config() -> dict[str, object]:
    if mw is None:
        logger.debug(
            "Anki main window (mw) is not available, returning default config."
        )
        return DEFAULT_CONFIG.copy()
    logger.debug(f"Using config key: {CONFIG_KEY}")
    config_dict = mw.addonManager.getConfig(CONFIG_KEY)
    if not config_dict:
        logger.info("No config found; saving default config.")
        mw.addonManager.writeConfig(CONFIG_KEY, DEFAULT_CONFIG.copy())
        return DEFAULT_CONFIG.copy()
    # Merge with defaults and coalesce blank optional fields
    merged = DEFAULT_CONFIG.copy()
    try:
        merged.update(dict(config_dict))
    except Exception:
        merged.update(config_dict)  # best effort if already a dict

    # Coalesce optional text fields when blank
    desc = str(merged.get(CONFIG_DESCRIPTION, "")).strip()
    if not desc:
        merged[CONFIG_DESCRIPTION] = DEFAULT_DESCRIPTION
    tz = str(merged.get(CONFIG_TIMEZONE, "")).strip()
    if not tz:
        merged[CONFIG_TIMEZONE] = DEFAULT_TIMEZONE

    # Ensure checkbox default exists
    if CONFIG_AUTO_SYNC not in merged:
        merged[CONFIG_AUTO_SYNC] = DEFAULT_CONFIG[CONFIG_AUTO_SYNC]

    return merged


def save_config(config: dict[str, object]) -> bool:
    if mw is None:
        logger.debug("Anki main window (mw) is not available, skipping config save.")
        return False
    logger.debug(f"Using config key: {CONFIG_KEY}")
    # Warn about missing fields but still persist for user flexibility
    missing_required = [
        f for f in REQUIRED_FIELDS if f not in config or not config.get(f)
    ]
    missing_optional = [
        f for f in DEFAULT_CONFIG if f not in config and f not in REQUIRED_FIELDS
    ]
    missing = missing_required + missing_optional
    if missing:
        logger.warning(f"Config being saved is missing fields: {missing}")
    logger.debug(f"Saving config: {_sanitize_config_for_logging(config)}")
    try:
        mw.addonManager.writeConfig(CONFIG_KEY, config)
        return True
    except (PermissionError, OSError) as e:
        logger.error(f"Failed to save config due to file system error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error saving config: {e}", exc_info=True)
        return False


def get_toggl_credentials() -> dict[str, object]:
    config = get_config()
    # Validate and normalize here for callers that need strict values
    try:
        validated = validate_config(config)
    except ConfigValidationError as e:
        raise e
    except Exception as e:
        raise ConfigValidationError(str(e))
    from typing import cast

    return {
        CONFIG_API_TOKEN: str(validated[CONFIG_API_TOKEN]),
        CONFIG_WORKSPACE_ID: cast("int", validated[CONFIG_WORKSPACE_ID]),
        CONFIG_PROJECT_ID: cast("int", validated[CONFIG_PROJECT_ID]),
        CONFIG_DESCRIPTION: str(validated[CONFIG_DESCRIPTION]),
    }


def is_configured() -> bool:
    try:
        config = get_config()
        token_ok = bool(str(config.get(CONFIG_API_TOKEN, "")).strip())
        ws = int(str(config.get(CONFIG_WORKSPACE_ID, "0")))
        proj = int(str(config.get(CONFIG_PROJECT_ID, "0")))
        return token_ok and ws > 0 and proj > 0
    except Exception:
        return False


def reset_config() -> bool:
    return save_config(DEFAULT_CONFIG.copy())


def update_config_field(field_name: str, value: object) -> bool:
    config = get_config()
    config[field_name] = value
    return save_config(config)


def _sanitize_config_for_logging(config: dict[str, object]) -> dict[str, object]:
    sanitized = config.copy()
    if CONFIG_API_TOKEN in sanitized:
        sanitized[CONFIG_API_TOKEN] = sanitize_for_logging(
            str(sanitized[CONFIG_API_TOKEN])
        )
    return sanitized


def get_timezone() -> Timezone:
    config = get_config()
    timezone_str = str(config[CONFIG_TIMEZONE])
    try:
        return Timezone(timezone_str)
    except Exception as e:
        raise ConfigValidationError(
            f"Invalid configured timezone '{timezone_str}': {e}"
        )
