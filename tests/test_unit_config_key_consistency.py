"""Test config key consistency fix."""

from unittest.mock import Mock, patch

from src.config import _resolve_config_key


class TestConfigKeyConsistency:
    """Test that config key resolution is consistent."""

    def setup_method(self):
        """Reset config key cache before each test."""
        # Reset cache by writing directly
        import src.config as cfg

        cfg._cached_config_key = None  # type: ignore[attr-defined]

    def test_config_key_is_cached_and_consistent(self):
        """Test that config key is cached and returns same value on multiple calls."""
        mock_mw = Mock()
        mock_mw.addonManager.addonFromModule.return_value = "test_addon_key"

        with patch("src.config.mw", mock_mw):
            # First call should resolve and cache the key
            key1 = _resolve_config_key()

            # Second call should return cached value
            key2 = _resolve_config_key()

            # Both should be the same
            assert key1 == key2 == "test_addon_key"

            # addonFromModule should only be called once (first time)
            assert mock_mw.addonManager.addonFromModule.call_count == 1

    def test_config_key_fallback_is_cached(self):
        """Test that fallback config key is also cached."""
        mock_mw = Mock()
        mock_mw.addonManager.addonFromModule.side_effect = Exception(
            "Failed to resolve"
        )

        with patch("src.config.mw", mock_mw):
            # First call should use fallback and cache it
            key1 = _resolve_config_key()

            # Second call should return cached value
            key2 = _resolve_config_key()

            # Both should be the same (fallback value)
            assert key1 == key2
            assert key1 == "src"  # CONFIG_KEY fallback

            # addonFromModule should only be called once
            assert mock_mw.addonManager.addonFromModule.call_count == 1

    def test_config_key_no_mw_returns_fallback(self):
        """Test config key resolution when mw is None."""
        with patch("src.config.mw", None):
            key = _resolve_config_key()
            assert key == "src"  # CONFIG_KEY fallback

    def test_reset_config_key_cache_works(self):
        """Test that resetting cache allows re-resolution."""
        mock_mw = Mock()
        mock_mw.addonManager.addonFromModule.return_value = "test_addon_key"

        with patch("src.config.mw", mock_mw):
            # First resolution
            key1 = _resolve_config_key()
            assert key1 == "test_addon_key"

            # Reset cache
            import src.config as cfg

            cfg._cached_config_key = None  # type: ignore[attr-defined]

            # Change mock return value
            mock_mw.addonManager.addonFromModule.return_value = "different_key"

            # Second resolution should get new value
            key2 = _resolve_config_key()
            assert key2 == "different_key"

            # Should have been called twice now
            assert mock_mw.addonManager.addonFromModule.call_count == 2
