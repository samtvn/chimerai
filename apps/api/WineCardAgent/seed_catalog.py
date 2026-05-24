"""Load wine catalog entries directly from seed files (no DB required)."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from .models import InventoryItem


SEED_DIR = Path(__file__).resolve().parents[1] / "database" / "seeds" / "wines"


def _node_to_literal(node: ast.AST) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        value = _node_to_literal(node.operand)
        if isinstance(value, (int, float)):
            return -value
    return None


def _extract_wines_from_file(path: Path) -> list[dict[str, Any]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    wines: list[dict[str, Any]] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name) or node.func.id != "Wine":
            continue

        data: dict[str, Any] = {}
        for kw in node.keywords:
            if kw.arg is None:
                continue
            data[kw.arg] = _node_to_literal(kw.value)
        wines.append(data)

    return wines


def load_seed_inventory(default_quantity: int = 6) -> list[InventoryItem]:
    """Build InventoryItem rows from static seed files."""
    files = sorted(path for path in SEED_DIR.glob("*.py") if path.name != "__init__.py")
    rows: list[InventoryItem] = []

    for file_path in files:
        for wine in _extract_wines_from_file(file_path):
            market_price = wine.get("market_price")
            purchase_price = float(market_price) if isinstance(market_price, (int, float)) else 0.0
            vintage_value = wine.get("vintage")
            vintage = str(vintage_value) if vintage_value is not None else None

            rows.append(
                InventoryItem(
                    wine_id=int(wine.get("id", 0)),
                    producer=str(wine.get("producer") or "Unknown Producer"),
                    wine_name=str(wine.get("name") or "Unnamed Wine"),
                    region=wine.get("region"),
                    country=wine.get("country"),
                    appellation=wine.get("appellation"),
                    wine_color=wine.get("color"),
                    vintage=vintage,
                    grape_variety=wine.get("grape_variety"),
                    drink_from=wine.get("drink_from"),
                    drink_to=wine.get("drink_to"),
                    quantity=max(int(default_quantity), 1),
                    purchase_price_ht=round(purchase_price, 2),
                    avg_market_price=round(purchase_price, 2) if purchase_price > 0 else None,
                )
            )

    rows.sort(key=lambda item: ((item.wine_color or ""), item.producer, item.wine_name))
    return rows

