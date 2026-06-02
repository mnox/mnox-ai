"""Shared helper to load the plugin's standalone helper scripts as modules.

The scripts are not an installable package; they live in nested
``plugins/<skill>/skills/<skill>/scripts/`` directories. We load each by file
path via ``importlib`` so tests can call their functions directly without
polluting ``sys.path`` permanently.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGINS = REPO_ROOT / "plugins"


def _script(skill: str, script: str) -> Path:
    """Resolve a helper script under ``plugins/<skill>/skills/<skill>/scripts/``."""
    return PLUGINS / skill / "skills" / skill / "scripts" / script


SCRIPTS = {
    "compute_progress": _script("curriculum", "compute_progress.py"),
    "scaffold": _script("curriculum", "scaffold.py"),
    "append_assessment": _script("curriculum", "append_assessment.py"),
    "init_workspace": _script("strangler-fig", "init_workspace.py"),
    "collect_signals": _script("debut", "collect_signals.py"),
}


def load_script(name: str) -> ModuleType:
    """Load a helper script by its logical name and return the module object.

    A unique module name is used so repeated loads in one process do not clash.
    """
    path = SCRIPTS[name]
    mod_name = f"_mnoxai_script_{name}"
    spec = importlib.util.spec_from_file_location(mod_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not build import spec for {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return module
