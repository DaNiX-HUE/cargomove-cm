from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    User, Customer, Driver, Vehicle, Shipment,
    CargoItem, TransportOffer, TrackingHistory, Rating, Notification
)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'phone_number', 'is_staff')
    list_filter = ('role', 'is_staff', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('CargoMove Profile', {
            'fields': ('role', 'phone_number', 'address', 'profile_picture', 'id_card_photo')
        }),
    )


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ('user', 'license_number', 'is_verified', 'rating_average')
    list_filter = ('is_verified',)
    search_fields = ('license_number', 'user__username')


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('user', 'company_name')


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('license_plate', 'driver', 'vehicle_type', 'max_weight_kg', 'is_available')
    list_filter = ('vehicle_type', 'is_available')


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'sender', 'origin_city', 'destination_city', 'status', 'pickup_date')
    list_filter = ('status',)
    search_fields = ('origin_city', 'destination_city')


admin.site.register(CargoItem)
admin.site.register(TransportOffer)
admin.site.register(TrackingHistory)
admin.site.register(Rating)
admin.site.register(Notification)