from django.db import transaction
from django.utils import timezone
from rest_framework import generics, viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from .utils import create_offers_for_shipment, transition_shipment_status, haversine_distance_km, estimate_shipment_price
from .pricing import calculate_price
from .permissions import IsCustomer, IsDriver
from .notifications import notify
from .models import (
    User, Customer, Driver, Vehicle, Shipment,
    CargoItem, TransportOffer, TrackingHistory, Rating, Notification
)
from .serializers import (
    UserSerializer, CustomerSerializer, DriverSerializer,
    VehicleSerializer, ShipmentSerializer, CargoItemSerializer,
    TransportOfferSerializer, TrackingHistorySerializer,
    RatingSerializer, NotificationSerializer,
)


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class UpdateProfilePhotosView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request):
        user = request.user
        for field in ['profile_picture', 'id_card_photo', 'selfie_with_id_photo']:
            if field in request.FILES:
                setattr(user, field, request.FILES[field])
        user.save()
        return Response(UserSerializer(user).data)


class ProfileStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        is_complete = bool(
            user.profile_picture and user.id_card_photo and user.selfie_with_id_photo
        )
        return Response({'profile_complete': is_complete})


class CustomerRegisterView(generics.CreateAPIView):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [permissions.AllowAny]


class DriverRegisterView(generics.CreateAPIView):
    queryset = Driver.objects.all()
    serializer_class = DriverSerializer
    permission_classes = [permissions.AllowAny]


# Login uses SimpleJWT's built-in view directly in urls.py — no custom code needed here.

class CustomerViewSet(viewsets.ModelViewSet):
    serializer_class = CustomerSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Customer.objects.all()
        return Customer.objects.filter(user=user)

    def destroy(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return Response(
                {'detail': 'Only admins can delete customer accounts.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        customer = self.get_object()

        has_active_shipment = Shipment.objects.filter(
            sender=customer, status__in=['PENDING', 'MATCHED', 'IN_TRANSIT'],
        ).exists()
        if has_active_shipment:
            return Response(
                {'detail': 'This customer has a shipment currently in progress and cannot be deleted until it is delivered or cancelled.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        customer.user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DriverViewSet(viewsets.ModelViewSet):
    serializer_class = DriverSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Driver.objects.all()
        return Driver.objects.filter(user=user)

    def destroy(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return Response(
                {'detail': 'Only admins can delete driver accounts.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        driver = self.get_object()

        # Business rule: can't delete a driver with a shipment currently in progress —
        # deleting their account would cascade-delete the TransportOffer and strand the shipment.
        has_active_shipment = TransportOffer.objects.filter(
            vehicle__driver=driver, status='ACCEPTED',
        ).exclude(shipment__status__in=['DELIVERED', 'CANCELLED']).exists()
        if has_active_shipment:
            return Response(
                {'detail': 'This driver has a shipment currently in progress and cannot be deleted until it is delivered or cancelled.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Delete the underlying User, not just the Driver row — this cascades to
        # Driver, their Vehicle(s), TransportOffers on those vehicles, Ratings, and Notifications.
        driver.user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class VehicleViewSet(viewsets.ModelViewSet):
    serializer_class = VehicleSerializer

    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.IsAuthenticated(), IsDriver()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Vehicle.objects.all()
        return Vehicle.objects.filter(driver__user=user)

    def perform_create(self, serializer):
        driver = Driver.objects.get(user=self.request.user)
        serializer.save(driver=driver)

    def destroy(self, request, *args, **kwargs):
        # Business rule: vehicle cannot be deleted if it is transporting cargo.
        vehicle = self.get_object()
        is_transporting = TransportOffer.objects.filter(
            vehicle=vehicle, status='ACCEPTED',
        ).exclude(shipment__status__in=['DELIVERED', 'CANCELLED']).exists()
        if is_transporting:
            return Response(
                {'detail': 'This vehicle is currently transporting cargo and cannot be deleted.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['post'])
    def update_location(self, request, pk=None):
        vehicle = self.get_object()
        try:
            lat = float(request.data['current_lat'])
            lng = float(request.data['current_lng'])
        except (KeyError, ValueError, TypeError):
            return Response(
                {'detail': 'current_lat and current_lng are required numbers.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        vehicle.current_lat = lat
        vehicle.current_lng = lng
        vehicle.last_location_update = timezone.now()
        vehicle.save(update_fields=['current_lat', 'current_lng', 'last_location_update'])

        # If this vehicle is actively carrying a shipment, log a tracking point for it
        # so the sender's live map has fresh data to show.
        active_offer = TransportOffer.objects.filter(
            vehicle=vehicle, status='ACCEPTED', shipment__status='IN_TRANSIT',
        ).select_related('shipment').first()
        if active_offer:
            TrackingHistory.objects.create(
                shipment=active_offer.shipment,
                current_lat=lat,
                current_lng=lng,
            )

        return Response(VehicleSerializer(vehicle).data)


class ShipmentViewSet(viewsets.ModelViewSet):
    serializer_class = ShipmentSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.IsAuthenticated(), IsCustomer()]
        if self.action in ('nearby', 'request_offer'):
            return [permissions.IsAuthenticated(), IsDriver()]
        return [permissions.IsAuthenticated()]

    def destroy(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return Response(
                {'detail': 'Only admins can delete shipments.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        shipment = self.get_object()

        if shipment.status in ('MATCHED', 'IN_TRANSIT'):
            return Response(
                {'detail': 'This shipment has an active driver assigned and cannot be deleted. Cancel it first.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return super().destroy(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        if user.role == 'SENDER':
            return Shipment.objects.filter(sender__user=user)
        return Shipment.objects.all()

    def perform_create(self, serializer):
        customer = Customer.objects.get(user=self.request.user)
        shipment = serializer.save(sender=customer)
        offers = create_offers_for_shipment(shipment)
        for offer in offers:
            notify(
                offer.vehicle.driver.user,
                'New shipment offer',
                f'A new shipment ({shipment.origin_city} → {shipment.destination_city}) matches your vehicle.',
            )

    @action(detail=True, methods=['post'])
    def start_transit(self, request, pk=None):
        shipment = self.get_object()
        try:
            transition_shipment_status(shipment, 'IN_TRANSIT')
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        notify(
            shipment.sender.user,
            'Your shipment is in transit',
            f'Your shipment #{shipment.id} ({shipment.origin_city} → {shipment.destination_city}) '
            f'is now on its way. Track its progress on the shipment page.',
        )

        return Response(ShipmentSerializer(shipment).data)

    @action(detail=True, methods=['post'])
    def mark_delivered(self, request, pk=None):
        shipment = self.get_object()
        try:
            transition_shipment_status(shipment, 'DELIVERED')
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ShipmentSerializer(shipment).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        shipment = self.get_object()
        try:
            transition_shipment_status(shipment, 'CANCELLED')
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ShipmentSerializer(shipment).data)

    @action(detail=False, methods=['post'])
    def estimate_price(self, request):
        data = request.data
        try:
            distance_km = haversine_distance_km(
                float(data['origin_lat']), float(data['origin_lng']),
                float(data['destination_lat']), float(data['destination_lng']),
            )
            price = calculate_price(
                distance=distance_km,
                delivery_type=data.get('delivery_type', 'ECONOMY'),
                weight=float(data.get('total_weight_kg', 0)),
                volume=float(data.get('total_volume_m3', 0)),
                shared_load=bool(data.get('shared_load', False)),
                loading_assistance=bool(data.get('loading_assistance', False)),
                special_handling=bool(data.get('special_handling', False)),
            )
        except (KeyError, ValueError, TypeError):
            return Response(
                {'detail': 'Missing or invalid fields for price estimate.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({'estimated_price_xaf': price, 'distance_km': round(distance_km, 2)})

    @action(detail=False, methods=['get'])
    def nearby(self, request):
        try:
            lat = float(request.query_params['lat'])
            lng = float(request.query_params['lng'])
        except (KeyError, ValueError, TypeError):
            return Response(
                {'detail': 'lat and lng query parameters are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        radius_km = float(request.query_params.get('radius_km', 100))

        results = []
        for shipment in Shipment.objects.filter(status='PENDING'):
            distance_km = haversine_distance_km(
                lat, lng, shipment.origin_lat, shipment.origin_lng,
            )
            if distance_km <= radius_km:
                data = ShipmentSerializer(shipment).data
                data['distance_km'] = round(distance_km, 2)
                results.append(data)

        results.sort(key=lambda s: s['distance_km'])
        return Response(results)

    @action(detail=True, methods=['post'])
    def request_offer(self, request, pk=None):
        shipment = self.get_object()
        if shipment.status != 'PENDING':
            return Response({'detail': 'This shipment is no longer available.'}, status=status.HTTP_400_BAD_REQUEST)

        vehicle = Vehicle.objects.filter(driver__user=request.user).first()
        if not vehicle:
            return Response({'detail': 'Register a vehicle before requesting shipments.'}, status=status.HTTP_400_BAD_REQUEST)

        if not shipment.estimated_price_xaf:
            estimate_shipment_price(shipment)

        offer, created = TransportOffer.objects.get_or_create(
            shipment=shipment, vehicle=vehicle,
            defaults={
                'offered_fare_xaf': shipment.estimated_price_xaf,
                'status': 'PENDING',
                'requested_by_driver': True,
            },
        )
        if not created and offer.status != 'PENDING':
            return Response(
                {'detail': f"You already have a '{offer.status}' offer on this shipment."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if created:
            notify(
                shipment.sender.user,
                'A driver wants to carry your shipment',
                f'{vehicle.driver.user.username} requested to carry shipment #{shipment.id} '
                f'({shipment.origin_city} → {shipment.destination_city}). Review it to approve or decline.',
            )

        return Response(
            TransportOfferSerializer(offer).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class TransportOfferViewSet(viewsets.ModelViewSet):
    serializer_class = TransportOfferSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'DRIVER':
            return TransportOffer.objects.filter(vehicle__driver__user=user)
        return TransportOffer.objects.filter(shipment__sender__user=user)

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        """
        Business rule: first accepted offer wins, all other pending
        offers on the same shipment expire automatically.
        """
        offer = self.get_object()

        if offer.vehicle.driver.user != request.user:
            return Response({'detail': 'This is not your offer.'}, status=status.HTTP_403_FORBIDDEN)
        if offer.status != 'PENDING':
            return Response({'detail': 'This offer is no longer available.'}, status=status.HTTP_400_BAD_REQUEST)
        if offer.requested_by_driver:
            return Response(
                {'detail': 'You requested this shipment — wait for the sender to approve it.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            shipment = Shipment.objects.select_for_update().get(pk=offer.shipment_id)
            if shipment.status != 'PENDING':
                return Response(
                    {'detail': 'This shipment already has an accepted driver.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            offer.status = 'ACCEPTED'
            offer.save(update_fields=['status'])

            TransportOffer.objects.filter(
                shipment=shipment, status='PENDING',
            ).exclude(pk=offer.pk).update(status='EXPIRED')

            shipment.status = 'MATCHED'
            shipment.save(update_fields=['status'])

            vehicle = offer.vehicle
            vehicle.is_available = False
            vehicle.save(update_fields=['is_available'])

        notify(
            shipment.sender.user,
            'Driver accepted your shipment',
            f'{vehicle.driver.user.username} accepted shipment #{shipment.id}.',
        )

        return Response(TransportOfferSerializer(offer).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        offer = self.get_object()

        if offer.vehicle.driver.user != request.user:
            return Response({'detail': 'This is not your offer.'}, status=status.HTTP_403_FORBIDDEN)
        if offer.status != 'PENDING':
            return Response({'detail': 'This offer was already handled.'}, status=status.HTTP_400_BAD_REQUEST)

        offer.status = 'REJECTED'
        offer.save(update_fields=['status'])

        notify(
            offer.shipment.sender.user,
            'Driver declined an offer',
            f'{offer.vehicle.driver.user.username} declined shipment #{offer.shipment_id}.',
        )

        return Response(TransportOfferSerializer(offer).data)

    @action(detail=True, methods=['post'])
    def sender_approve(self, request, pk=None):
        """
        Sender-side counterpart to accept(): approves a driver-requested offer.
        Same first-accepted-wins business rule as accept().
        """
        offer = self.get_object()

        if offer.shipment.sender.user != request.user:
            return Response({'detail': 'This is not your shipment.'}, status=status.HTTP_403_FORBIDDEN)
        if offer.status != 'PENDING':
            return Response({'detail': 'This offer is no longer available.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            shipment = Shipment.objects.select_for_update().get(pk=offer.shipment_id)
            if shipment.status != 'PENDING':
                return Response(
                    {'detail': 'This shipment already has an accepted driver.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            offer.status = 'ACCEPTED'
            offer.save(update_fields=['status'])

            TransportOffer.objects.filter(
                shipment=shipment, status='PENDING',
            ).exclude(pk=offer.pk).update(status='EXPIRED')

            shipment.status = 'MATCHED'
            shipment.save(update_fields=['status'])

            vehicle = offer.vehicle
            vehicle.is_available = False
            vehicle.save(update_fields=['is_available'])

        notify(
            vehicle.driver.user,
            'Your shipment request was approved',
            f'Your request to carry shipment #{shipment.id} was approved.',
        )

        return Response(TransportOfferSerializer(offer).data)

    @action(detail=True, methods=['post'])
    def sender_decline(self, request, pk=None):
        offer = self.get_object()

        if offer.shipment.sender.user != request.user:
            return Response({'detail': 'This is not your shipment.'}, status=status.HTTP_403_FORBIDDEN)
        if offer.status != 'PENDING':
            return Response({'detail': 'This offer was already handled.'}, status=status.HTTP_400_BAD_REQUEST)

        offer.status = 'REJECTED'
        offer.save(update_fields=['status'])

        notify(
            offer.vehicle.driver.user,
            'Your shipment request was declined',
            f'Your request to carry shipment #{offer.shipment_id} was declined.',
        )

        return Response(TransportOfferSerializer(offer).data)


class TrackingHistoryViewSet(viewsets.ModelViewSet):
    queryset = TrackingHistory.objects.all()
    serializer_class = TrackingHistorySerializer
    permission_classes = [permissions.IsAuthenticated]


class RatingViewSet(viewsets.ModelViewSet):
    queryset = Rating.objects.all()
    serializer_class = RatingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        shipment = serializer.validated_data['shipment']
        customer = shipment.sender
        accepted_offer = TransportOffer.objects.get(shipment=shipment, status='ACCEPTED')
        driver = accepted_offer.vehicle.driver
        serializer.save(customer=customer, driver=driver)


class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)
