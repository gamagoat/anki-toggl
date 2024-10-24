"""Security utilities for handling secrets and token-safe logging."""

import re
from typing import Any, Union


def sanitize_for_logging(
    data: Any, sensitive_fields: Union[list[str], None] = None
) -> Any:
    """
    Sanitize data for safe logging by masking sensitive fields.

    Args:
        data: Data to sanitize (dict, string, or other)
        sensitive_fields: List of field names to sanitize (defaults to common sensitive fields)

    Returns:
        Sanitized data safe for logging
    """
    if sensitive_fields is None:
        sensitive_fields = [
            "api_token",
            "token",
            "password",
            "secret",
            "key",
            "authorization",
            "auth",
            "credential",
            "credentials",
        ]

    if isinstance(data, dict):
        return _sanitize_dict(data, sensitive_fields)
    elif isinstance(data, str):
        return _sanitize_string(data, sensitive_fields)
    elif isinstance(data, (list, tuple)):
        return type(data)(_sanitize_item(item, sensitive_fields) for item in data)
    else:
        return data


def _sanitize_dict(data: dict[str, Any], sensitive_fields: list[str]) -> dict[str, Any]:
    """Sanitize a dictionary by masking sensitive fields."""
    sanitized: dict[str, Any] = {}

    for key, value in data.items():
        if any(field.lower() in key.lower() for field in sensitive_fields):
            sanitized[key] = _mask_sensitive_value(value)
        else:
            sanitized[key] = _sanitize_item(value, sensitive_fields)

    return sanitized


def _sanitize_string(data: str, sensitive_fields: list[str]) -> str:
    """Sanitize a string by masking patterns that look like tokens."""
    # Pattern for common token formats (alphanumeric strings of certain lengths)
    token_patterns = [
        r"\b[A-Za-z0-9]{20,}\b",  # Long alphanumeric strings (likely tokens)
        r"\b[A-Fa-f0-9]{32,}\b",  # Hex strings (likely tokens/hashes)
        r"Bearer\s+[A-Za-z0-9\-._~+/]+=*",  # Bearer tokens
        r"Basic\s+[A-Za-z0-9+/]+=*",  # Basic auth tokens
    ]

    sanitized = data
    for pattern in token_patterns:
        sanitized = re.sub(
            pattern, lambda m: _mask_sensitive_value(m.group()), sanitized
        )

    return sanitized


def _sanitize_item(item: Any, sensitive_fields: list[str]) -> Any:
    """Recursively sanitize an item."""
    if isinstance(item, dict):
        return _sanitize_dict(item, sensitive_fields)
    elif isinstance(item, str):
        return _sanitize_string(item, sensitive_fields)
    elif isinstance(item, (list, tuple)):
        return type(item)(
            _sanitize_item(sub_item, sensitive_fields) for sub_item in item
        )
    else:
        return item


def _mask_sensitive_value(value: Any) -> str:
    """Mask a sensitive value for logging."""
    if not value:
        return str(value)

    value_str = str(value)

    if len(value_str) <= 4:
        return "***"
    elif len(value_str) <= 8:
        return f"{value_str[:2]}***"
    else:
        # Show first 4 and last 4 characters with asterisks in between
        return f"{value_str[:4]}***{value_str[-4:]}"


def validate_api_token_format(token: str) -> bool:
    """
    Basic validation for API token format.

    Args:
        token: API token to validate

    Returns:
        True if token format is reasonable, False otherwise
    """
    if not token:
        return False

    # Basic checks: non-empty after stripping whitespace, reasonable length
    token = token.strip()
    return 10 <= len(token) <= 200
