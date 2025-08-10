"""Shared constants used across the add-on."""

# Time-related constants
SECONDS_PER_DAY = 86400
MS_TO_SECONDS_DIVISOR = 1000


# Default values
DEFAULT_DESCRIPTION = "Anki Review Session"
DEFAULT_USER_AGENT = "AnkiToggl"
USER_AGENT_TEMPLATE = "{name}/{version} (+AnkiAddOn)"
DEFAULT_TIMEZONE = "UTC"

# HTTP status codes
HTTP_OK = 200
HTTP_BAD_REQUEST = 400
HTTP_NOT_FOUND = 404
HTTP_SERVICE_UNAVAILABLE = 503

# API endpoints
TOGGL_API_BASE_URL = "https://api.track.toggl.com/api/v9"
TOGGL_USER_ENDPOINT = "me"

# Network timeouts (seconds)
REQUEST_CONNECT_TIMEOUT_S = 5
REQUEST_READ_TIMEOUT_S = 30

# File and directory names
LOG_FILE_PREFIX = "anki_toggl_"
SYNC_STATE_DIR = "sync_state"
SYNC_STATE_FILE = "sync_state.json"

# Configuration field names
CONFIG_API_TOKEN = "api_token"  # nosec B105: configuration key name, not a secret
CONFIG_WORKSPACE_ID = "workspace_id"
CONFIG_PROJECT_ID = "project_id"
CONFIG_DESCRIPTION = "description"
CONFIG_AUTO_SYNC = "auto_sync"
CONFIG_TIMEZONE = "timezone"

# Logging
LOG_DATE_FORMAT = "%Y%m%d_%H%M%S"
LOG_MESSAGE_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
LOG_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"

# Validation limits
MIN_DESCRIPTION_LENGTH = 1
MAX_DESCRIPTION_LENGTH = 100
MIN_API_TOKEN_LENGTH = 10
MAX_API_TOKEN_LENGTH = 200
