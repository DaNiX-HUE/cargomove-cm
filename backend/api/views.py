from rest_framework import generics, viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.decorators import action
from .utils import create_offers_for_shipment, accept_transport_offer, transition_shipment_status
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
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Vehicle.objects.filter(driver__user=self.request.user)

    def perform_create(self, serializer):
        driver = Driver.objects.get(user=self.request.user)
        serializer.save(driver=driver)


from .utils import create_offers_for_shipment  # add this import at the top


class ShipmentViewSet(viewsets.ModelViewSet):
    serializer_class = ShipmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'SENDER':
            return Shipment.objects.filter(sender__user=user)
        return Shipment.objects.all()

    def perform_create(self, serializer):
        customer = Customer.objects.get(user=self.request.user)
        shipment = serializer.save(sender=customer)
        create_offers_for_shipment(shipment)

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
    queryset = TransportOffer.objects.all()
    serializer_class = TransportOfferSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        offer = self.get_object()
        try:
            accept_transport_offer(offer)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(TransportOfferSerializer(offer).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        offer = self.get_object()
        if offer.status != 'PENDING':
            return Response(
                {'detail': f"Offer is already '{offer.status}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        offer.status = 'REJECTED'
        offer.save()
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

