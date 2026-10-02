"""
Tests for pricing.calculate_price().

These don't touch the database at all — calculate_price() is a pure
function (same inputs always give the same output), so plain
unittest-style assertions are enough. No Django test client needed here.
"""
from django.test import SimpleTestCase

from api.pricing import (
    calculate_price,
    BASE_FARE_XAF,
    RATE_PER_KM,
    RATE_PER_KG,
    RATE_PER_M3,
    DELIVERY_TYPE_MULTIPLIERS,
    SHARED_LOAD_DISCOUNT,
    LOADING_ASSISTANCE_FEE,
    SPECIAL_HANDLING_FEE,
)


class CalculatePriceTests(SimpleTestCase):

    def test_base_case_matches_hand_calculation(self):
        """
        With no distance/weight/volume, the price should be exactly the
        base fare — this pins down that nothing is added when there's
        nothing to charge for.
        """
        price = calculate_price(distance=0, weight=0, volume=0)
        self.assertEqual(price, BASE_FARE_XAF)

    def test_distance_weight_volume_all_add_up(self):
        """
        Price should equal base + distance*rate + weight*rate +
        volume*rate for ECONOMY (multiplier 1.0), with no discounts/fees.
        This is the formula's core promise — if this breaks, every price
        the app shows is wrong.
        """
        distance, weight, volume = 100, 50, 2
        expected = (
            BASE_FARE_XAF
            + distance * RATE_PER_KM
            + weight * RATE_PER_KG
            + volume * RATE_PER_M3
        )
        price = calculate_price(distance=distance, weight=weight, volume=volume)
        self.assertEqual(price, round(expected, 2))

    def test_express_multiplier_applied(self):
        """EXPRESS should cost exactly DELIVERY_TYPE_MULTIPLIERS['EXPRESS'] times the ECONOMY price."""
        economy = calculate_price(distance=100, delivery_type='ECONOMY', weight=50, volume=2)
        express = calculate_price(distance=100, delivery_type='EXPRESS', weight=50, volume=2)
        self.assertEqual(express, round(economy * DELIVERY_TYPE_MULTIPLIERS['EXPRESS'], 2))

    def test_unknown_delivery_type_falls_back_to_economy_rate(self):
        """
        An unrecognized delivery_type shouldn't crash or silently charge
        a wrong multiplier — it should fall back to 1.0 (same as ECONOMY).
        """
        price = calculate_price(distance=100, delivery_type='SOMETHING_INVALID', weight=0, volume=0)
        economy_price = calculate_price(distance=100, delivery_type='ECONOMY', weight=0, volume=0)
        self.assertEqual(price, economy_price)

    def test_shared_load_makes_it_cheaper(self):
        """Sharing a truck should always reduce the price, never increase it."""
        solo = calculate_price(distance=100, weight=50, volume=2, shared_load=False)
        shared = calculate_price(distance=100, weight=50, volume=2, shared_load=True)
        self.assertLess(shared, solo)
        self.assertEqual(shared, round(solo * SHARED_LOAD_DISCOUNT, 2))

    def test_loading_assistance_adds_flat_fee(self):
        """The loading assistance fee should be added after the discount, as a flat top-up."""
        without = calculate_price(distance=100, weight=50, volume=2)
        with_assist = calculate_price(distance=100, weight=50, volume=2, loading_assistance=True)
        self.assertEqual(with_assist, round(without + LOADING_ASSISTANCE_FEE, 2))

    def test_special_handling_adds_flat_fee(self):
        without = calculate_price(distance=100, weight=50, volume=2)
        with_handling = calculate_price(distance=100, weight=50, volume=2, special_handling=True)
        self.assertEqual(with_handling, round(without + SPECIAL_HANDLING_FEE, 2))

    def test_loading_and_special_handling_fees_stack(self):
        """Both flat fees should apply together, not just whichever comes last."""
        without = calculate_price(distance=100, weight=50, volume=2)
        with_both = calculate_price(
            distance=100, weight=50, volume=2,
            loading_assistance=True, special_handling=True,
        )
        self.assertEqual(
            with_both,
            round(without + LOADING_ASSISTANCE_FEE + SPECIAL_HANDLING_FEE, 2),
        )

    def test_price_never_negative(self):
        """Sanity check: no combination of real-world inputs should ever produce a negative price."""
        price = calculate_price(distance=0, delivery_type='ECONOMY', weight=0, volume=0, shared_load=True)
        self.assertGreaterEqual(price, 0)

    def test_result_is_rounded_to_2_decimal_places(self):
        price = calculate_price(distance=33.333, weight=17.777, volume=1.111)
        # round(x, 2) means at most 2 digits after the decimal point
        self.assertEqual(price, round(price, 2))
