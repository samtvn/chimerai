"""Pytest configuration for the API package."""
from __future__ import annotations

import importlib
import sys


def _alias_database_package() -> None:
    """Alias api.database.* to database.* to avoid duplicate SQLModel registrations."""
    try:
        db_pkg = importlib.import_module("database")
    except Exception:
        return

    sys.modules.setdefault("api.database", db_pkg)

    # Mirror any already-loaded database submodules under api.database.*
    for name, module in list(sys.modules.items()):
        if name.startswith("database."):
            sys.modules.setdefault(f"api.{name}", module)


_alias_database_package()
