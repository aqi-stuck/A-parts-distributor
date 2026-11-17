"""Temporary probe: start the API with numpy/scipy imports blocked.

Simulates the Windows Application Control policy that blocks scipy's native
DLLs (ImportError: DLL load failed while importing _zeros), to prove the
backend still boots and answers requests.
"""

import importlib.abc
import sys


class BlockScientificStack(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in ("numpy", "scipy"):
            raise ImportError(
                "DLL load failed while importing _zeros: "
                "An Application Control policy has blocked this file. (simulated)"
            )
        return None


sys.meta_path.insert(0, BlockScientificStack())

import uvicorn  # noqa: E402

uvicorn.run("app.main:app", host="127.0.0.1", port=8011, log_level="warning")
