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
from .pricing import calculate_price


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


def estimate_shipment_price(shipment):
    """
    Computes the shipment's estimated price via the Pricing Service and
    saves it on the shipment (estimated_price_xaf). Uses the straight-line
    origin -> destination distance, since the price should be consistent
    no matter which driver ends up taking the job.
    """
    distance_km = haversine_distance_km(
        shipment.origin_lat, shipment.origin_lng,
        shipment.destination_lat, shipment.destination_lng,
    )
    price = calculate_price(
        distance=distance_km,
        delivery_type=shipment.delivery_type,
        weight=shipment.total_weight_kg,
        volume=shipment.total_volume_m3,
        shared_load=shipment.shared_load,
        loading_assistance=shipment.loading_assistance,
        special_handling=shipment.special_handling,
    )
    shipment.estimated_price_xaf = price
    shipment.save(update_fields=['estimated_price_xaf'])
    return price


def create_offers_for_shipment(shipment):
    """
    Runs the matching algorithm and auto-creates PENDING TransportOffers
    for the top matching vehicles, priced via the Pricing Service.
    """
    if not shipment.estimated_price_xaf:
        estimate_shipment_price(shipment)

    matches = find_matching_vehicles(shipment)
    created_offers = []

    for match in matches:
        offer, created = TransportOffer.objects.get_or_create(
            shipment=shipment,
            vehicle=match['vehicle'],
            defaults={
                'offered_fare_xaf': shipment.estimated_price_xaf,
                'status': 'PENDING',
            },
        )
        if created:
            created_offers.append(offer)

    return created_offers


ALLOWED_SHIPMENT_TRANSITIONS = {
    'PENDING': ['MATCHED', 'CANCELLED'],
    'MATCHED': ['IN_TRANSIT', 'CANCELLED'],
    'IN_TRANSIT': ['DELIVERED'],
    'DELIVERED': [],
    'CANCELLED': [],
}


def transition_shipment_status(shipment, new_status):
    """
    Moves a Shipment to new_status only if the transition is legal.
    Raises ValueError with a clear message otherwise.
    """
    current = shipment.status
    allowed = ALLOWED_SHIPMENT_TRANSITIONS.get(current, [])

    if new_status not in allowed:
        raise ValueError(
            f"Cannot move shipment from '{current}' to '{new_status}'. "
            f"Allowed next steps: {allowed or 'none (final state)'}."
        )

    shipment.status = new_status
    shipment.save()
    return shipment


def accept_transport_offer(offer):
    """
    Accepts one offer, auto-rejects all other pending offers on the same
    shipment, and moves the shipment to MATCHED.
    """
    if offer.status != 'PENDING':
        raise ValueError(f"Offer is already '{offer.status}', cannot accept.")

    offer.status = 'ACCEPTED'
    offer.save()

    TransportOffer.objects.filter(
        shipment=offer.shipment,
        status='PENDING',
    ).exclude(id=offer.id).update(status='REJECTED')

    transition_shipment_status(offer.shipment, 'MATCHED')
    return offer