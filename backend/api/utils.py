import math


def haversine_distance_km(lat1, lng1, lat2, lng2):
    """
    Calculate the great-circle distance between two GPS points,
    in kilometers, accounting for the Earth's curvature.
    """
    R = 6371  # Earth's radius in km

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lng = math.radians(lng2 - lng1)

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c

from django.db.models import Sum
from .models import Vehicle, TransportOffer


def get_committed_capacity(vehicle):
    """
    How much weight/volume this vehicle is already committed to,
    based on ACCEPTED offers on shipments not yet delivered.
    """
    accepted_offers = TransportOffer.objects.filter(
        vehicle=vehicle,
        status='ACCEPTED',
    ).exclude(shipment__status__in=['DELIVERED', 'CANCELLED'])

    committed_weight = sum(o.shipment.total_weight_kg for o in accepted_offers)
    committed_volume = sum(o.shipment.total_volume_m3 for o in accepted_offers)
    return committed_weight, committed_volume


def find_matching_vehicles(shipment, max_distance_km=100, top_n=5):
    """
    Returns a ranked list of the best-fit vehicles for a given shipment.
    Each entry: {'vehicle': Vehicle, 'distance_km': float, 'score': float}
    """
    candidates = []

    available_vehicles = Vehicle.objects.filter(
        is_available=True,
        current_lat__isnull=False,
        current_lng__isnull=False,
    )

    for vehicle in available_vehicles:
        # Step 1: capacity check
        committed_weight, committed_volume = get_committed_capacity(vehicle)
        remaining_weight = vehicle.max_weight_kg - committed_weight
        remaining_volume = vehicle.max_volume_m3 - committed_volume

        if remaining_weight < shipment.total_weight_kg:
            continue
        if remaining_volume < shipment.total_volume_m3:
            continue

        # Step 2: distance check
        distance_km = haversine_distance_km(
            vehicle.current_lat, vehicle.current_lng,
            shipment.origin_lat, shipment.origin_lng,
        )
        if distance_km > max_distance_km:
            continue

        # Step 3: scoring — lower distance is better, more spare capacity is
        # better, higher driver rating is better. Weighted so distance
        # matters most, since a far-away vehicle is impractical regardless
        # of how good its other stats are.
        capacity_ratio = remaining_weight / vehicle.max_weight_kg
        score = (
            (max_distance_km - distance_km) * 2
            + capacity_ratio * 10
            + vehicle.driver.rating_average * 5
        )

        candidates.append({
            'vehicle': vehicle,
            'distance_km': round(distance_km, 2),
            'score': round(score, 2),
        })

    candidates.sort(key=lambda c: c['score'], reverse=True)
    return candidates[:top_n]


def create_offers_for_shipment(shipment):
    """
    Runs the matching algorithm and auto-creates PENDING TransportOffers
    for the top matching vehicles.
    """
    matches = find_matching_vehicles(shipment)
    created_offers = []

    for match in matches:
        offer, created = TransportOffer.objects.get_or_create(
            shipment=shipment,
            vehicle=match['vehicle'],
            defaults={'offered_fare_xaf': 0, 'status': 'PENDING'},
        )
        if created:
            created_offers.append(offer)

    return created_offers