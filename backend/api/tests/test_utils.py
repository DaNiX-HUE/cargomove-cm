"""
Tests for utils.py: distance calculation, the matching algorithm, and the
booking state machine. These touch the database (creating real Users,
Drivers, Vehicles, Shipments), so they use Django's TestCase, which wraps
each test in a transaction and rolls it back afterward — tests can't
leak data into each other.
"""
from datetime import date

from django.test import TestCase

from api.models import User, Customer, Driver, Vehicle, Shipment, TransportOffer
from api.utils import (
    haversine_distance_km,
    ROAD_DISTANCE_CORRECTION_FACTOR,
    get_committed_capacity,
    find_matching_vehicles,
    transition_shipment_status,
    accept_transport_offer,
    ALLOWED_SHIPMENT_TRANSITIONS,
)


class HaversineDistanceTests(TestCase):

    def test_same_point_is_zero_distance(self):
        self.assertEqual(haversine_distance_km(3.848, 11.502, 3.848, 11.502), 0)

    def test_yaounde_to_douala_is_close_to_real_road_distance(self):
        """
        Straight-line Yaounde->Douala is ~194km; real road distance is
        ~239-241km. With the correction factor applied, our estimate
        should land close to the real figure (within ~10km), not the
        uncorrected straight-line one.
        """
        distance = haversine_distance_km(3.8480, 11.5021, 4.0511, 9.7679)
        self.assertAlmostEqual(distance, 240, delta=10)

    def test_correction_factor_is_applied(self):
        """The corrected distance should be exactly straight-line * ROAD_DISTANCE_CORRECTION_FACTOR."""
        # Two points ~1 degree of latitude apart (~111km straight-line)
        corrected = haversine_distance_km(0, 0, 1, 0)
        uncorrected_estimate = 111.19  # known straight-line km per degree of latitude
        self.assertAlmostEqual(
            corrected, uncorrected_estimate * ROAD_DISTANCE_CORRECTION_FACTOR, delta=1,
        )


class MatchingAlgorithmTests(TestCase):

    def setUp(self):
        self.customer_user = User.objects.create_user(
            username='sender1', password='pass1234', role='SENDER',
        )
        self.customer = Customer.objects.create(user=self.customer_user)

        self.driver_user = User.objects.create_user(
            username='driver1', password='pass1234', role='DRIVER',
        )
        self.driver = Driver.objects.create(user=self.driver_user, license_number='LIC-001')

        # Vehicle parked right at the shipment's origin, with plenty of capacity
        self.vehicle = Vehicle.objects.create(
            driver=self.driver, vehicle_type='Canter', license_plate='CE-100-AB',
            max_weight_kg=5000, max_volume_m3=20,
            is_available=True, current_lat=3.8480, current_lng=11.5021,
        )

        self.shipment = Shipment.objects.create(
            sender=self.customer,
            origin_city='Yaounde', origin_lat=3.8480, origin_lng=11.5021,
            destination_city='Douala', destination_lat=4.0511, destination_lng=9.7679,
            pickup_date=date.today(),
            total_weight_kg=1000, total_volume_m3=2,
        )

    def test_vehicle_at_origin_is_matched(self):
        matches = find_matching_vehicles(self.shipment)
        vehicle_ids = [m['vehicle'].id for m in matches]
        self.assertIn(self.vehicle.id, vehicle_ids)

    def test_unavailable_vehicle_is_excluded(self):
        self.vehicle.is_available = False
        self.vehicle.save()
        matches = find_matching_vehicles(self.shipment)
        self.assertEqual(len(matches), 0)

    def test_vehicle_without_gps_is_excluded(self):
        self.vehicle.current_lat = None
        self.vehicle.current_lng = None
        self.vehicle.save()
        matches = find_matching_vehicles(self.shipment)
        self.assertEqual(len(matches), 0)

    def test_vehicle_with_insufficient_weight_capacity_is_excluded(self):
        self.vehicle.max_weight_kg = 500  # less than shipment's 1000kg
        self.vehicle.save()
        matches = find_matching_vehicles(self.shipment)
        self.assertEqual(len(matches), 0)

    def test_vehicle_with_insufficient_volume_capacity_is_excluded(self):
        self.vehicle.max_volume_m3 = 1  # less than shipment's 2m3
        self.vehicle.save()
        matches = find_matching_vehicles(self.shipment)
        self.assertEqual(len(matches), 0)

    def test_vehicle_too_far_away_is_excluded(self):
        # Far-away coordinates (another region of Cameroon, well past 100km)
        self.vehicle.current_lat = 2.0
        self.vehicle.current_lng = 15.0
        self.vehicle.save()
        matches = find_matching_vehicles(self.shipment, max_distance_km=100)
        self.assertEqual(len(matches), 0)

    def test_committed_capacity_counts_only_active_accepted_offers(self):
        """
        A vehicle with an ACCEPTED offer on a shipment still IN_TRANSIT
        should have that capacity counted as committed; once the
        shipment is DELIVERED/CANCELLED it should no longer count.
        """
        other_shipment = Shipment.objects.create(
            sender=self.customer,
            origin_city='A', origin_lat=0, origin_lng=0,
            destination_city='B', destination_lat=1, destination_lng=1,
            pickup_date=date.today(),
            total_weight_kg=2000, total_volume_m3=5,
        )
        offer = TransportOffer.objects.create(
            shipment=other_shipment, vehicle=self.vehicle,
            offered_fare_xaf=10000, status='ACCEPTED',
        )

        other_shipment.status = 'IN_TRANSIT'
        other_shipment.save()
        committed_weight, committed_volume = get_committed_capacity(self.vehicle)
        self.assertEqual(committed_weight, 2000)
        self.assertEqual(committed_volume, 5)

        other_shipment.status = 'DELIVERED'
        other_shipment.save()
        committed_weight, committed_volume = get_committed_capacity(self.vehicle)
        self.assertEqual(committed_weight, 0)
        self.assertEqual(committed_volume, 0)


class ShipmentStateMachineTests(TestCase):

    def setUp(self):
        customer_user = User.objects.create_user(username='sender2', password='x', role='SENDER')
        customer = Customer.objects.create(user=customer_user)
        self.shipment = Shipment.objects.create(
            sender=customer,
            origin_city='A', origin_lat=0, origin_lng=0,
            destination_city='B', destination_lat=1, destination_lng=1,
            pickup_date=date.today(),
        )

    def test_legal_transition_succeeds(self):
        transition_shipment_status(self.shipment, 'MATCHED')
        self.assertEqual(self.shipment.status, 'MATCHED')

    def test_illegal_transition_raises_value_error(self):
        """PENDING can't jump straight to DELIVERED — must go through MATCHED/IN_TRANSIT first."""
        with self.assertRaises(ValueError):
            transition_shipment_status(self.shipment, 'DELIVERED')
        # and the shipment's status should NOT have changed
        self.shipment.refresh_from_db()
        self.assertEqual(self.shipment.status, 'PENDING')

    def test_terminal_states_allow_no_further_transitions(self):
        for terminal_status in ('DELIVERED', 'CANCELLED'):
            self.assertEqual(ALLOWED_SHIPMENT_TRANSITIONS[terminal_status], [])

    def test_full_happy_path(self):
        """PENDING -> MATCHED -> IN_TRANSIT -> DELIVERED should all succeed in order."""
        transition_shipment_status(self.shipment, 'MATCHED')
        transition_shipment_status(self.shipment, 'IN_TRANSIT')
        transition_shipment_status(self.shipment, 'DELIVERED')
        self.assertEqual(self.shipment.status, 'DELIVERED')


class AcceptTransportOfferTests(TestCase):

    def setUp(self):
        customer_user = User.objects.create_user(username='sender3', password='x', role='SENDER')
        customer = Customer.objects.create(user=customer_user)
        self.shipment = Shipment.objects.create(
            sender=customer,
            origin_city='A', origin_lat=0, origin_lng=0,
            destination_city='B', destination_lat=1, destination_lng=1,
            pickup_date=date.today(),
        )

        driver_user1 = User.objects.create_user(username='driver_a', password='x', role='DRIVER')
        driver1 = Driver.objects.create(user=driver_user1, license_number='LIC-A')
        vehicle1 = Vehicle.objects.create(
            driver=driver1, vehicle_type='Van', license_plate='AA-1',
            max_weight_kg=1000, max_volume_m3=5,
        )

        driver_user2 = User.objects.create_user(username='driver_b', password='x', role='DRIVER')
        driver2 = Driver.objects.create(user=driver_user2, license_number='LIC-B')
        vehicle2 = Vehicle.objects.create(
            driver=driver2, vehicle_type='Van', license_plate='BB-1',
            max_weight_kg=1000, max_volume_m3=5,
        )

        self.offer1 = TransportOffer.objects.create(
            shipment=self.shipment, vehicle=vehicle1, offered_fare_xaf=10000, status='PENDING',
        )
        self.offer2 = TransportOffer.objects.create(
            shipment=self.shipment, vehicle=vehicle2, offered_fare_xaf=10000, status='PENDING',
        )

    def test_accepting_one_offer_rejects_the_others(self):
        """
        This is the 'first accepted offer wins' business rule — the most
        important invariant in the whole booking flow. If this breaks, a
        shipment could end up assigned to two drivers at once.
        """
        accept_transport_offer(self.offer1)

        self.offer1.refresh_from_db()
        self.offer2.refresh_from_db()
        self.shipment.refresh_from_db()

        self.assertEqual(self.offer1.status, 'ACCEPTED')
        self.assertEqual(self.offer2.status, 'REJECTED')
        self.assertEqual(self.shipment.status, 'MATCHED')

    def test_cannot_accept_an_already_handled_offer(self):
        accept_transport_offer(self.offer1)
        with self.assertRaises(ValueError):
            accept_transport_offer(self.offer1)
