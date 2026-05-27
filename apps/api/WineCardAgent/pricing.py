"""Pricing helpers for restaurant wine menu generation."""

from __future__ import annotations

from .models import PricingResult, VatCountry


# Country VAT constants for restaurant pricing rollout in nearby markets.
VAT_RATES_BY_COUNTRY: dict[VatCountry, float] = {
    VatCountry.LU: 0.17,
    VatCountry.FR: 0.20,
    VatCountry.BE: 0.21,
    VatCountry.DE: 0.19,
}
DEFAULT_VAT_COUNTRY = VatCountry.LU


def get_markup_coefficient(purchase_price_ht: float) -> float:
    if purchase_price_ht <= 10:
        return 3.2
    if purchase_price_ht <= 20:
        return 2.8
    if purchase_price_ht <= 40:
        return 2.4
    if purchase_price_ht <= 80:
        return 2.1
    if purchase_price_ht <= 150:
        return 1.8
    return 1.6


def _round_menu_price(value: float) -> float:
    if value <= 0:
        return 0.0
    # Restaurant-style rounded pricing: nearest 0.50 EUR step.
    return round(value * 2) / 2


def get_vat_rate(country: VatCountry | str = DEFAULT_VAT_COUNTRY) -> float:
    if isinstance(country, str):
        country = VatCountry(country.upper())
    return VAT_RATES_BY_COUNTRY.get(country, VAT_RATES_BY_COUNTRY[DEFAULT_VAT_COUNTRY])


def calculate_restaurant_price_ttc(
    purchase_price_ht: float,
    vat_country: VatCountry | str = DEFAULT_VAT_COUNTRY,
) -> PricingResult:
    safe_purchase_price = max(float(purchase_price_ht or 0.0), 0.0)
    resolved_country = (
        VatCountry(vat_country.upper()) if isinstance(vat_country, str) else vat_country
    )
    vat_rate = get_vat_rate(resolved_country)
    coef = get_markup_coefficient(safe_purchase_price)

    selling_ht = safe_purchase_price * coef
    selling_ttc_raw = selling_ht * (1 + vat_rate)
    selling_ttc = _round_menu_price(selling_ttc_raw)

    glass_ttc_raw = selling_ttc / 5 if selling_ttc > 0 else 0
    glass_ttc = _round_menu_price(max(glass_ttc_raw, 5.0 if selling_ttc > 0 else 0.0))

    return PricingResult(
        purchase_price_ht=round(safe_purchase_price, 2),
        vat_country=resolved_country,
        markup_coefficient=coef,
        vat_rate=vat_rate,
        selling_price_ht=round(selling_ht, 2),
        selling_price_ttc=round(selling_ttc, 2),
        glass_price_ttc=round(glass_ttc, 2),
    )
