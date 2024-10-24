from typing import Any, Optional


def get_mw_or_none() -> Optional[Any]:
    """Return Anki's mw if available, else None."""
    try:
        import aqt

        return getattr(aqt, "mw", None)
    except Exception:
        return None


def require_mw() -> Any:
    """Return mw or raise if not available."""
    mw = get_mw_or_none()
    if mw is None:
        raise RuntimeError("Anki not ready")
    return mw


def show_tooltip(message: str, parent: Any = None) -> None:
    """Show an Anki tooltip if available; otherwise no-op.

    The try/except is necessary because aqt.utils is only available when running
    inside Anki's environment. When testing or running outside Anki, this will
    fail to import, so we gracefully handle it.
    """
    try:
        from aqt.utils import tooltip

        tooltip(message, parent=parent)
    except Exception:
        # Outside Anki environment or import failed; ignore
        return
