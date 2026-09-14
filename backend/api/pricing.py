"""
Pricing Service
================
Single source of truth for shipment price estimation, kept separate from
views/serializers so it stays easy to test and easy to tune if the
business rules change later (per the architecture doc's recommendation).

ASSUMPTION: the doc specifies the function signature but not the exact
tariff. The constants below are placeholder rates (in XAF) — replace
them with the real numbers your team agrees on before going to
production. Everything that depends on price (offers, dashboards) reads
through calculate_price(), so changing the constants here is enough.
"""

BASE_FARE_XAF = 2000
RATE_PER_KM = 250
RATE_PER_KG = 15
RATE_PER_M3 = 5000

DELIVERY_TYPE_MULTIPLIERS = {
    'ECONOMY': 1.0,
    'EXPRESS': 1.5,
    'SCHEDULED': 1.1,
}

SHARED_LOAD_DISCOUNT = 0.85    # 15% off when the cargo shares a truck
LOADING_ASSISTANCE_FEE = 3000  # flat fee if the driver must load/unload
SPECIAL_HANDLING_FEE = 5000    # flat fee for fragile / special cargo


def calculate_price(
    distance,
    delivery_type='ECONOMY',
    weight=0,
    volume=0,
    shared_load=False,
    loading_assistance=False,
    special_handling=False,
):
    """
    Estimate the price (in XAF) for a shipment.

    distance: kilometers between pickup and drop-off
    delivery_type: 'ECONOMY' | 'EXPRESS' | 'SCHEDULED'
    weight: total weight in kg
    volume: total volume in m3
    shared_load / loading_assistance / special_handling: booleans

    Returns a float rounded to 2 decimal places.
    """
    delivery_type = (delivery_type or 'ECONOMY').upper()
    multiplier = DELIVERY_TYPE_MULTIPLIERS.get(delivery_type, 1.0)

    price = BASE_FARE_XAF
    price += distance * RATE_PER_KM
    price += weight * RATE_PER_KG
    price += volume * RATE_PER_M3

    price *= multiplier

    if shared_load:
        price *= SHARED_LOAD_DISCOUNT
    if loading_assistance:
        price += LOADING_ASSISTANCE_FEE
    if special_handling:
        price += SPECIAL_HANDLING_FEE

    return round(price, 2)
