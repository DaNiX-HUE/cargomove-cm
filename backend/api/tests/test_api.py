"""
Tests that go through the real HTTP layer (DRF's APIClient), exercising
serializers + views + permissions together, the way a real frontend
request would. Where a test needs a logged-in user, we use
force_authenticate() rather than doing a real JWT login — that's the
standard DRF shortcut for tests: it skips the login round-trip but still
exercises every permission check and the view logic exactly like a real
authenticated request would.
"""
from datetime import date

from rest_framework.test import APITestCase
from rest_framework import status

from api.models import User, Customer, Driver, Vehicle, Shipment, TransportOffer


class RegistrationTests(APITestCase):

    def test_customer_registration_creates_user_with_sender_role(self):
        response = self.client.post('/api/auth/register/customer/', {
            'user': {
                'username': 'newsender',
                'email': 'sender@example.com',
                'password': 'strongpass123',
            },
            'company_name': 'ACME Farms',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username='newsender')
        self.assertEqual(user.role, 'SENDER')
        # Password should be hashed, never stored in plain text
        self.assertNotEqual(user.password, 'strongpass123')
        self.assertTrue(user.check_password('strongpass123'))

    def test_driver_registration_creates_user_with_driver_role(self):
        response = self.client.post('/api/auth/register/driver/', {
            'user': {
                'username': 'newdriver',
                'email': 'driver@example.com',
                'password': 'strongpass123',
            },
            'license_number': 'LIC-999',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username='newdriver')
        self.assertEqual(user.role, 'DRIVER')


class ShipmentCreationTests(APITestCase):

    def setUp(self):
        self.sender_user = User.objects.create_user(
            username='sender', password='x', role='SENDER',
        )
        self.customer = Customer.objects.create(user=self.sender_user)

        self.driver_user = User.objects.create_user(
            username='driver', password='x', role='DRIVER',
        )
        driver = Driver.objects.create(user=self.driver_user, license_number='LIC-1')
        self.vehicle = Vehicle.objects.create(
            driver=driver, vehicle_type='Canter', license_plate='PLATE-1',
            max_weight_kg=5000, max_volume_m3=20,
            is_available=True, current_lat=3.848, current_lng=11.502,
        )

    def _shipment_payload(self):
        return {
            'origin_city': 'Yaounde', 'origin_lat': 3.848, 'origin_lng': 11.502,
            'destination_city': 'Douala', 'destination_lat': 4.0511, 'destination_lng': 9.7679,
            'pickup_date': str(date.today()),
            'delivery_type': 'ECONOMY',
            'items': [
                {
                    'description': 'Sacks of cocoa', 'quantity': 10,
                    'length_cm': 50, 'width_cm': 40, 'height_cm': 30, 'weight_kg': 20,
                },
            ],
        }

    def test_sender_can_create_shipment_and_it_gets_priced_and_matched(self):
        self.client.force_authenticate(user=self.sender_user)
        response = self.client.post('/api/shipments/', self._shipment_payload(), format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        shipment = Shipment.objects.get(id=response.data['id'])

        # sender auto-assigned from the logged-in user, not the client
        self.assertEqual(shipment.sender, self.customer)
        # weight/volume computed server-side from the items, never trusted from the client
        self.assertEqual(shipment.total_weight_kg, 200)  # 10 items x 20kg
        # a price should have been calculated automatically
        self.assertGreater(shipment.estimated_price_xaf, 0)
        # the nearby, available, capable vehicle should have gotten an auto-offer
        self.assertTrue(
            TransportOffer.objects.filter(shipment=shipment, vehicle=self.vehicle).exists()
        )

    def test_driver_cannot_create_a_shipment(self):
        """Shipment creation is sender-only — a driver posting here should get a clean 403, not a crash."""
        self.client.force_authenticate(user=self.driver_user)
        response = self.client.post('/api/shipments/', self._shipment_payload(), format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_user_cannot_create_a_shipment(self):
        response = self.client.post('/api/shipments/', self._shipment_payload(), format='json')
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))


class VehicleUpdateLocationTests(APITestCase):
    """
    Regression tests for the two real bugs hit earlier: the route not
    being registered (404), and the endpoint rejecting JSON bodies (415).
    """

    def setUp(self):
        self.driver_user = User.objects.create_user(
            username='driver', password='x', role='DRIVER',
        )
        driver = Driver.objects.create(user=self.driver_user, license_number='LIC-1')
        self.vehicle = Vehicle.objects.create(
            driver=driver, vehicle_type='Van', license_plate='PLATE-X',
            max_weight_kg=1000, max_volume_m3=5,
        )

    def test_update_location_accepts_json_body(self):
        self.client.force_authenticate(user=self.driver_user)
        response = self.client.post(
            f'/api/vehicles/{self.vehicle.id}/update_location/',
            {'current_lat': 4.05, 'current_lng': 9.70},
            format='json',  # this is what was failing with 415 before the fix
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.current_lat, 4.05)
        self.assertEqual(self.vehicle.current_lng, 9.70)

    def test_update_location_rejects_missing_coordinates(self):
        self.client.force_authenticate(user=self.driver_user)
        response = self.client.post(
            f'/api/vehicles/{self.vehicle.id}/update_location/', {}, format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_driver_cannot_update_location_of_another_drivers_vehicle(self):
        other_driver_user = User.objects.create_user(username='other', password='x', role='DRIVER')
        Driver.objects.create(user=other_driver_user, license_number='LIC-2')

        self.client.force_authenticate(user=other_driver_user)
        response = self.client.post(
            f'/api/vehicles/{self.vehicle.id}/update_location/',
            {'current_lat': 1, 'current_lng': 1}, format='json',
        )
        # get_queryset() filters vehicles by owning driver, so this should 404, not leak a 403
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class OfferAcceptTests(APITestCase):

    def setUp(self):
        sender_user = User.objects.create_user(username='sender', password='x', role='SENDER')
        self.customer = Customer.objects.create(user=sender_user)
        self.shipment = Shipment.objects.create(
            sender=self.customer,
            origin_city='A', origin_lat=0, origin_lng=0,
            destination_city='B', destination_lat=1, destination_lng=1,
            pickup_date=date.today(),
        )

        self.driver_user = User.objects.create_user(username='driver', password='x', role='DRIVER')
        driver = Driver.objects.create(user=self.driver_user, license_number='LIC-1')
        self.vehicle = Vehicle.objects.create(
            driver=driver, vehicle_type='Van', license_plate='PLATE-Y',
            max_weight_kg=1000, max_volume_m3=5,
        )
        self.offer = TransportOffer.objects.create(
            shipment=self.shipment, vehicle=self.vehicle,
            offered_fare_xaf=5000, status='PENDING',
        )

    def test_owning_driver_can_accept_offer(self):
        self.client.force_authenticate(user=self.driver_user)
        response = self.client.post(f'/api/offers/{self.offer.id}/accept/')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        self.offer.refresh_from_db()
        self.shipment.refresh_from_db()
        self.assertEqual(self.offer.status, 'ACCEPTED')
        self.assertEqual(self.shipment.status, 'MATCHED')

    def test_other_driver_cannot_accept_someone_elses_offer(self):
        other_driver_user = User.objects.create_user(username='other', password='x', role='DRIVER')
        Driver.objects.create(user=other_driver_user, license_number='LIC-2')

        self.client.force_authenticate(user=other_driver_user)
        response = self.client.post(f'/api/offers/{self.offer.id}/accept/')
        # get_queryset() on TransportOfferViewSet already scopes offers to the
        # requesting driver's own vehicles, so another driver's offer isn't
        # even visible to them — it 404s before the in-view ownership check
        # (offer.vehicle.driver.user != request.user) is ever reached.
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.offer.refresh_from_db()
        self.assertEqual(self.offer.status, 'PENDING')


class AdminDeletionGuardTests(APITestCase):
    """
    Covers the account-deletion feature: only staff can delete, and only
    when there's no shipment currently in progress.
    """

    def setUp(self):
        self.admin_user = User.objects.create_user(
            username='admin', password='x', role='', is_staff=True,
        )
        sender_user = User.objects.create_user(username='sender', password='x', role='SENDER')
        self.customer = Customer.objects.create(user=sender_user)

    def test_non_admin_cannot_delete_customer(self):
        non_admin = User.objects.create_user(username='regular', password='x', role='SENDER')
        self.client.force_authenticate(user=non_admin)
        response = self.client.delete(f'/api/customers/{self.customer.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Customer.objects.filter(id=self.customer.id).exists())

    def test_admin_can_delete_customer_with_no_active_shipment(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.delete(f'/api/customers/{self.customer.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Customer.objects.filter(id=self.customer.id).exists())

    def test_admin_cannot_delete_customer_with_active_shipment(self):
        Shipment.objects.create(
            sender=self.customer,
            origin_city='A', origin_lat=0, origin_lng=0,
            destination_city='B', destination_lat=1, destination_lng=1,
            pickup_date=date.today(),
            status='MATCHED',
        )
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.delete(f'/api/customers/{self.customer.id}/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(Customer.objects.filter(id=self.customer.id).exists())
