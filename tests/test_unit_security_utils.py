import pytest


@pytest.mark.unit
def test_sanitize_for_logging_masks_in_dict() -> None:
    from src.security_utils import sanitize_for_logging

    data = {"api_token": "abcd1234efgh5678", "nested": {"password": "supersecret"}}
    sanitized = sanitize_for_logging(data)
    assert sanitized["api_token"].startswith("ab") and sanitized["api_token"].endswith(
        "78"
    )
    assert "***" in sanitized["nested"]["password"]


@pytest.mark.unit
def test_sanitize_for_logging_masks_in_string() -> None:
    from src.security_utils import sanitize_for_logging

    s = "Authorization: Basic QWxhZGRpbjpvcGVuIHNlc2FtZQ=="
    out = sanitize_for_logging(s)
    assert out != s
    assert "***" in out


@pytest.mark.unit
def test_sanitize_for_logging_masks_in_list() -> None:
    from src.security_utils import sanitize_for_logging

    lst = [
        {"token": "A" * 40},
        "Bearer abcdefghijklmnopqrstuvwxyz0123456789",
    ]
    out = sanitize_for_logging(lst)
    assert isinstance(out, list)
    # Dict entry masked
    assert out[0]["token"].startswith("AAAA") and out[0]["token"].endswith("AAAA")
    # Bearer masked
    assert "***" in out[1]


@pytest.mark.unit
@pytest.mark.parametrize(
    "value,expected",
    [
        ("a", "***"),
        ("abcd", "***"),
        ("abcdef", "ab***"),
        ("abcdefghijk", "abcd***hijk"),
    ],
)
def test_mask_sensitive_value_variants(value: str, expected: str) -> None:
    from src.security_utils import _mask_sensitive_value

    assert _mask_sensitive_value(value) == expected


@pytest.mark.unit
@pytest.mark.parametrize(
    "token,valid",
    [
        ("", False),
        ("short", False),
        ("a" * 9, False),
        ("a" * 10, True),
        ("a" * 200, True),
        ("a" * 201, False),
    ],
)
def test_validate_api_token_format_bounds(token: str, valid: bool) -> None:
    from src.security_utils import validate_api_token_format

    assert validate_api_token_format(token) is valid
