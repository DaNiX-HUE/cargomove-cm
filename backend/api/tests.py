from django.test import TestCase
from .pricing import calculate_price


class PricingServiceTests(TestCase):
    """Pure-function tests — no database needed, run instantly."""

    def test_base_economy_price(self):
        price = calculate_price(distance=10, delivery_type='ECONOMY', weight=100, volume=1)
        # base 2000 + 10*250 + 100*15 + 1*5000 = 2000+2500+1500+5000 = 11000
        self.assertEqual(price, 11000.0)

    def test_express_is_more_expensive_than_economy(self):
        economy = calculate_price(distance=20, delivery_type='ECONOMY', weight=50, volume=0.5)
        express = calculate_price(distance=20, delivery_type='EXPRESS', weight=50, volume=0.5)
        self.assertGreater(express, economy)

    def test_shared_load_is_cheaper(self):
        normal = calculate_price(distance=20, weight=50, volume=0.5)
        shared = calculate_price(distance=20, weight=50, volume=0.5, shared_load=True)
        self.assertLess(shared, normal)

    def test_loading_assistance_and_special_handling_add_flat_fees(self):
        base = calculate_price(distance=5, weight=10, volume=0.1)
        with_extras = calculate_price(
            distance=5, weight=10, volume=0.1,
            loading_assistance=True, special_handling=True,
        )
        self.assertEqual(with_extras, base + 3000 + 5000)

    def test_unknown_delivery_type_falls_back_to_economy_rate(self):
        default = calculate_price(distance=10, delivery_type='ECONOMY')
        unknown = calculate_price(distance=10, delivery_type='NOT_A_REAL_TYPE')
        self.assertEqual(default, unknown)
