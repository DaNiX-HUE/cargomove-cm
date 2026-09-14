from django.db import transaction
from rest_framework import generics, viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from .utils import create_offers_for_shipment, transition_shipment_status
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
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [permissions.IsAuthenticated]


class DriverViewSet(viewsets.ModelViewSet):
    queryset = Driver.objects.all()
    serializer_class = DriverSerializer
    permission_classes = [permissions.IsAuthenticated]


class VehicleViewSet(viewsets.ModelViewSet):
    serializer_class = VehicleSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.IsAuthenticated(), IsDriver()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        return Vehicle.objects.filter(driver__user=self.request.user)

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


class ShipmentViewSet(viewsets.ModelViewSet):
    serializer_class = ShipmentSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.IsAuthenticated(), IsCustomer()]
        return [permissions.IsAuthenticated()]

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


class TrackingHistoryViewSet(viewsets.ModelViewSet):
    queryset = TrackingHistory.objects.all()
    serializer_class = TrackingHistorySerializer
    permission_classes = [permissions.IsAuthenticated]


class RatingViewSet(viewsets.ModelViewSet):
    queryset = Rating.objects.all()
    serializer_class = RatingSerializer
    permission_classes = [permissions.IsAuthenticated]


class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)