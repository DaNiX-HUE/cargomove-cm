"""
Pricing Service
================
Single source of truth for shipment price estimation, kept separate from
views/serializers so it stays easy to test and easy to tune if the
business rules change later (per the architecture doc's recommendation).

Rates below were set from research on Cameroonian/regional road freight
costs (Oct 2026): diesel at ~828 XAF/L, benchmark African small/medium
truck rates of roughly 270-840 XAF/km, and regional data showing West/
Central African road freight runs 1.5-2.2x higher than South African or
US rates. Since CargoMove pools multiple shipments onto one truck (LTL),
RATE_PER_KM is kept below a dedicated full-truck charter rate, with the
shared-load discount doing the work of making pooled trips cheaper for
customers while still filling a driver's truck. Revisit these numbers
once there's real usage data (driver acceptance rate, customer drop-off
at checkout) to tune further.
"""

BASE_FARE_XAF = 2500
RATE_PER_KM = 400
RATE_PER_KG = 18
RATE_PER_M3 = 6000

DELIVERY_TYPE_MULTIPLIERS = {
    'ECONOMY': 1.0,
    'EXPRESS': 1.5,
    'SCHEDULED': 1.1,
}

SHARED_LOAD_DISCOUNT = 0.80    # 20% off when the cargo shares a truck
LOADING_ASSISTANCE_FEE = 3500  # flat fee if the driver must load/unload
SPECIAL_HANDLING_FEE = 6000    # flat fee for fragile / special cargo


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
