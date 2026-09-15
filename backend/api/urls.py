from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    CustomerRegisterView, DriverRegisterView,
    CustomerViewSet, DriverViewSet, VehicleViewSet, ShipmentViewSet,
    TransportOfferViewSet, TrackingHistoryViewSet, RatingViewSet, NotificationViewSet,
)
from .views import (
    CustomerRegisterView, DriverRegisterView, MeView,
    CustomerViewSet, DriverViewSet, VehicleViewSet, ShipmentViewSet,
    TransportOfferViewSet, TrackingHistoryViewSet, RatingViewSet, NotificationViewSet,
)

router = DefaultRouter()
router.register('customers', CustomerViewSet)
router.register('drivers', DriverViewSet)
router.register('vehicles', VehicleViewSet, basename='vehicle')
router.register('shipments', ShipmentViewSet, basename='shipment')
router.register('offers', TransportOfferViewSet, basename='offer')
router.register('tracking', TrackingHistoryViewSet)
router.register('ratings', RatingViewSet)
router.register('notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    path('auth/register/customer/', CustomerRegisterView.as_view(), name='register-customer'),
    path('auth/register/driver/', DriverRegisterView.as_view(), name='register-driver'),
    path('auth/login/', TokenObtainPairView.as_view(), name='token-obtain-pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('auth/me/', MeView.as_view(), name='me'),
    path('', include(router.urls)),

]