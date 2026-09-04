from rest_framework import serializers
from .models import (
    User, Customer, Driver, Vehicle, Shipment,
    CargoItem, TransportOffer, TrackingHistory, Rating, Notification
)


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'password', 'role',
            'phone_number', 'address', 'profile_picture', 'id_card_photo',
        ]

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class CustomerSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = Customer
        fields = ['id', 'user', 'company_name']

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user_data['role'] = 'SENDER'
        user = UserSerializer().create(user_data)
        return Customer.objects.create(user=user, **validated_data)


class DriverSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = Driver
        fields = [
            'id', 'user', 'license_number', 'driving_license_photo',
            'is_verified', 'rating_average',
        ]
        read_only_fields = ['is_verified', 'rating_average']

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user_data['role'] = 'DRIVER'
        user = UserSerializer().create(user_data)
        return Driver.objects.create(user=user, **validated_data)


class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = [
            'id', 'driver', 'vehicle_type', 'license_plate',
            'max_weight_kg', 'max_volume_m3', 'is_available',
        ]
        read_only_fields = ['driver']


class CargoItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CargoItem
        fields = [
            'id', 'shipment', 'description', 'quantity',
            'length_cm', 'width_cm', 'height_cm', 'weight_kg',
            'calculated_volume_m3',
        ]
        read_only_fields = ['shipment', 'calculated_volume_m3']

    def create(self, validated_data):
        item = CargoItem(**validated_data)
        item.calculated_volume_m3 = (
            item.length_cm * item.width_cm * item.height_cm
        ) / 1_000_000
        item.save()
        return item


class ShipmentSerializer(serializers.ModelSerializer):
    items = CargoItemSerializer(many=True)

    class Meta:
        model = Shipment
        fields = [
            'id', 'sender', 'origin_city', 'origin_lat', 'origin_lng',
            'destination_city', 'destination_lat', 'destination_lng',
            'pickup_date', 'total_weight_kg', 'total_volume_m3',
            'status', 'created_at', 'items',
        ]
        read_only_fields = ['sender', 'total_weight_kg', 'total_volume_m3', 'status']

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        shipment = Shipment.objects.create(**validated_data)

        total_weight = 0
        total_volume = 0
        for item_data in items_data:
            item = CargoItemSerializer().create({**item_data, 'shipment': shipment})
            total_weight += item.weight_kg * item.quantity
            total_volume += item.calculated_volume_m3 * item.quantity

        shipment.total_weight_kg = total_weight
        shipment.total_volume_m3 = total_volume
        shipment.save()
        return shipment

class TransportOfferSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransportOffer
        fields = ['id', 'shipment', 'vehicle', 'offered_fare_xaf', 'status', 'created_at']
        read_only_fields = ['status']


class TrackingHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TrackingHistory
        fields = ['id', 'shipment', 'current_lat', 'current_lng', 'checkpoint_name', 'timestamp']


class RatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rating
        fields = ['id', 'shipment', 'customer', 'driver', 'stars', 'comment', 'created_at']

    def validate_shipment(self, value):
        if value.status != 'DELIVERED':
            raise serializers.ValidationError(
                "You can only rate a shipment after it has been delivered."
            )
        return value


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'user', 'title', 'message', 'is_read', 'created_at']
        read_only_fields = ['user']