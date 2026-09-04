from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class User(AbstractUser):
    ROLE_CHOICES = [
        ('SENDER', 'Sender'),
        ('DRIVER', 'Driver'),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    phone_number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    profile_picture = models.ImageField(upload_to='profiles/', null=True, blank=True)
    id_card_photo = models.ImageField(upload_to='id_cards/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
    company_name = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return self.user.username


class Driver(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='driver_profile')
    license_number = models.CharField(max_length=50, unique=True)
    driving_license_photo = models.ImageField(upload_to='licenses/', null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    rating_average = models.FloatField(default=0.0)

    def __str__(self):
        return self.user.username


class Vehicle(models.Model):
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='vehicles')
    vehicle_type = models.CharField(max_length=50)  # e.g. Pick-up, Canter, Semi-Trailer
    license_plate = models.CharField(max_length=20, unique=True)
    max_weight_kg = models.FloatField()
    max_volume_m3 = models.FloatField()
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.vehicle_type} ({self.license_plate})"


class Shipment(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('MATCHED', 'Matched'),
        ('IN_TRANSIT', 'In Transit'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
    ]
    sender = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='shipments')
    origin_city = models.CharField(max_length=100)
    origin_lat = models.FloatField()
    origin_lng = models.FloatField()
    destination_city = models.CharField(max_length=100)
    destination_lat = models.FloatField()
    destination_lng = models.FloatField()
    pickup_date = models.DateField()
    total_weight_kg = models.FloatField(default=0.0)
    total_volume_m3 = models.FloatField(default=0.0)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Shipment #{self.id} ({self.origin_city} → {self.destination_city})"

class CargoItem(models.Model):
    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name='items')
    description = models.CharField(max_length=200)
    quantity = models.IntegerField(default=1)
    length_cm = models.FloatField()
    width_cm = models.FloatField()
    height_cm = models.FloatField()
    weight_kg = models.FloatField()
    calculated_volume_m3 = models.FloatField(default=0.0)

    def __str__(self):
        return f"{self.description} ({self.shipment_id})"


class TransportOffer(models.Model):
    OFFER_STATUS = [
        ('PENDING', 'Pending'),
        ('ACCEPTED', 'Accepted'),
        ('REJECTED', 'Rejected'),
    ]
    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name='offers')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='offers')
    offered_fare_xaf = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=OFFER_STATUS, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Offer #{self.id} — {self.status}"


class TrackingHistory(models.Model):
    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name='tracking_logs')
    current_lat = models.FloatField()
    current_lng = models.FloatField()
    checkpoint_name = models.CharField(max_length=150, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Tracking for shipment #{self.shipment_id} at {self.timestamp}"


class Rating(models.Model):
    shipment = models.OneToOneField(Shipment, on_delete=models.CASCADE, related_name='rating')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='received_ratings')
    stars = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.stars}★ for {self.driver}"


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=150)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} → {self.user}"