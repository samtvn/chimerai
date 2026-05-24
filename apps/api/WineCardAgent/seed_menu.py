"""Generate an editable wine menu from seed catalog files (no DB)."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from .models import Season, VatCountry
from .service import WineCardService


async def main():
    parser = argparse.ArgumentParser(
        description="Generate editable markdown menu from seed wines."
    )
    parser.add_argument("--season", default="winter", choices=["spring", "summer", "autumn", "winter"])
    parser.add_argument("--vat-country", default="LU", choices=["LU", "FR", "BE", "DE"])
    parser.add_argument("--default-quantity", type=int, default=6)
    parser.add_argument(
        "--output",
        default="seed_wine_menu.md",
        help="Output markdown path (relative to apps/api).",
    )
    args = parser.parse_args()

    service = WineCardService()
    menu = await service.export_editable_menu_from_seeds(
        season=Season(args.season),
        vat_country=VatCountry(args.vat_country),
        default_quantity=args.default_quantity,
    )
    analysis = await service.analyze_seed_catalog(
        season=Season(args.season),
        vat_country=VatCountry(args.vat_country),
        default_quantity=args.default_quantity,
    )

    output = Path(args.output)
    output.write_text(menu.markdown, encoding="utf-8")

    print(f"Generated: {output.resolve()}")
    print(f"Items: {menu.items_count}")
    print(f"Missing categories: {', '.join(analysis.missing_categories) or 'none'}")
    print(f"By-the-glass suggestions: {len(analysis.by_the_glass_suggestions)}")


if __name__ == "__main__":
    asyncio.run(main())

