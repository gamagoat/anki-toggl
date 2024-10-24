from .qt import *

class AddonManager:
    def getConfig(self, key: str) -> dict[str, object] | None: ...
    def writeConfig(self, key: str, config: dict[str, object]) -> None: ...
    def setWebExports(self, module: str, regex: str) -> None: ...

class _MainWindow:
    addonManager: AddonManager
    col: object | None

mw: _MainWindow | None

class _HooksList:
    def append(self, func: object) -> None: ...

class _GuiHooks:
    profile_did_open: _HooksList
    sync_did_finish: _HooksList

gui_hooks: _GuiHooks
