let myVehicle = null;
let trackingIntervalId = null;

const DEFAULT_LOCATION = { lat: 3.848, lng: 11.502 }; // Yaoundé — fallback when device location is unavailable

document.addEventListener('DOMContentLoaded', async () => {
    if (!isLoggedIn()) {
        window.location.href = '../index.html';
        return;
    }
    await enforceProfileComplete();
    await loadVehicle();
    await loadOffers();
    initNearbyShipments();
    document.getElementById('offersList').addEventListener('click', handleOfferAction);
});

async function loadVehicle() {
    const container = document.getElementById('vehicleSection');
    try {
        const vehicles = await apiRequest('/vehicles/');

        if (vehicles.length === 0) {
            myVehicle = null;
            container.innerHTML = `<div class="alert alert-warning">
                You haven't registered a vehicle yet. <a href="vehicle.html">Register one now</a>.
            </div>`;
            return;
        }

        const v = vehicles[0];
        myVehicle = v;
        container.innerHTML = `
            <div class="card">
                <div class="card-body d-flex justify-content-between align-items-center">
                    <div>
                        <p class="mb-1 fw-medium">${v.vehicle_type} — ${v.license_plate}</p>
                        <p class="mb-0 text-muted" style="font-size: 0.85rem;">
                            Capacity: ${v.max_weight_kg} kg / ${v.max_volume_m3} m³
                        </p>
                    </div>
                    <span class="status-badge ${v.is_available ? 'status-DELIVERED' : 'status-CANCELLED'}">
                        ${v.is_available ? 'Available' : 'Unavailable'}
                    </span>
                </div>
            </div>
        `;
    } catch (err) {
        myVehicle = null;
        container.innerHTML = `<div class="alert alert-danger">${err.message}</div>`;
    }
}

async function loadOffers() {
    const container = document.getElementById('offersList');
    const statsContainer = document.getElementById('statsCards');

    try {
        const offers = await apiRequest('/offers/');

        if (offers.length === 0) {
            statsContainer.innerHTML = '';
            container.innerHTML = '<p class="text-muted">No offers yet.</p>';
            stopLiveTracking();
            return;
        }

        const withShipments = await Promise.all(
            offers.map(async (offer) => {
                const shipment = await apiRequest(`/shipments/${offer.shipment}/`);
                return { offer, shipment };
            })
        );

        renderStats(withShipments, statsContainer);
        container.innerHTML = withShipments.map(renderOfferCard).join('');
        startLiveTrackingIfNeeded(withShipments);
    } catch (err) {
        container.innerHTML = `<div class="alert alert-danger">${err.message}</div>`;
    }
}

function renderStats(withShipments, container) {
    const total = withShipments.length;
    const pending = withShipments.filter(w => w.offer.status === 'PENDING').length;
    const delivered = withShipments.filter(w => w.shipment.status === 'DELIVERED').length;
    const earnings = withShipments
        .filter(w => w.offer.status === 'ACCEPTED' && w.shipment.status === 'DELIVERED')
        .reduce((sum, w) => sum + parseFloat(w.offer.offered_fare_xaf || 0), 0);

    container.innerHTML = `
        <div class="col-6 col-md-3">
            <div class="stat-card">
                <p class="stat-value">${total}</p>
                <p class="stat-label">Total offers</p>
            </div>
        </div>
        <div class="col-6 col-md-3">
            <div class="stat-card">
                <p class="stat-value">${pending}</p>
                <p class="stat-label">Awaiting response</p>
            </div>
        </div>
        <div class="col-6 col-md-3">
            <div class="stat-card">
                <p class="stat-value">${delivered}</p>
                <p class="stat-label">Completed</p>
            </div>
        </div>
        <div class="col-6 col-md-3">
            <div class="stat-card">
                <p class="stat-value">${earnings.toLocaleString()}</p>
                <p class="stat-label">XAF earned</p>
            </div>
        </div>
    `;
}

function renderOfferCard({ offer, shipment }) {
    let actionButtons = '';
    if (offer.status === 'PENDING' && !offer.requested_by_driver) {
        actionButtons = `
            <button class="btn btn-sm btn-primary" data-accept-id="${offer.id}">Accept</button>
            <button class="btn btn-sm btn-outline-danger ms-1" data-reject-id="${offer.id}">Reject</button>
        `;
    } else if (offer.status === 'PENDING' && offer.requested_by_driver) {
        actionButtons = `<span class="text-muted" style="font-size: 0.8rem;">Awaiting sender approval</span>`;
    } else if (offer.status === 'ACCEPTED' && shipment.status === 'MATCHED') {
        actionButtons = `<button class="btn btn-sm btn-primary" data-start-transit-id="${shipment.id}">Start Transit</button>`;
    } else if (offer.status === 'ACCEPTED' && shipment.status === 'IN_TRANSIT') {
        actionButtons = `<button class="btn btn-sm btn-primary" data-mark-delivered-id="${shipment.id}">Mark Delivered</button>`;
    }

    return `
        <div class="card">
            <div class="card-body d-flex justify-content-between align-items-center">
                <div>
                    <p class="mb-1 fw-medium"><a href="shipmentDetail.html?id=${shipment.id}" class="text-decoration-none text-dark">${shipment.origin_city} → ${shipment.destination_city}</a></p>
                    <p class="mb-0 text-muted" style="font-size: 0.85rem;">
                        ${shipment.total_weight_kg} kg &middot; Fare: ${offer.offered_fare_xaf} XAF
                    </p>
                </div>
                <div class="d-flex align-items-center gap-2">
                    <span class="status-badge status-${offer.status === 'ACCEPTED' ? 'MATCHED' : offer.status === 'EXPIRED' ? 'CANCELLED' : offer.status}">
                        ${offer.status}
                    </span>
                    ${actionButtons}
                </div>
            </div>
        </div>
    `;
}

async function handleOfferAction(e) {
    const acceptId = e.target.dataset.acceptId;
    const rejectId = e.target.dataset.rejectId;
    const startTransitId = e.target.dataset.startTransitId;
    const markDeliveredId = e.target.dataset.markDeliveredId;

    try {
        if (acceptId || rejectId) {
            const id = acceptId || rejectId;
            const action = acceptId ? 'accept' : 'reject';
            await apiRequest(`/offers/${id}/${action}/`, 'POST');
            await loadVehicle();
        } else if (startTransitId) {
            await apiRequest(`/shipments/${startTransitId}/start_transit/`, 'POST');
        } else if (markDeliveredId) {
            await apiRequest(`/shipments/${markDeliveredId}/mark_delivered/`, 'POST');
            await loadVehicle();
        } else {
            return;
        }
        await loadOffers();
    } catch (err) {
        alert(err.message);
    }
}

/* ---------- Live location tracking while a delivery is in progress ---------- */

function startLiveTrackingIfNeeded(withShipments) {
    const activeDelivery = withShipments.find(function (w) {
        return w.offer.status === 'ACCEPTED' && w.shipment.status === 'IN_TRANSIT';
    });

    if (activeDelivery && !trackingIntervalId) {
        sendLocationUpdate();
        trackingIntervalId = setInterval(sendLocationUpdate, 20000);
    } else if (!activeDelivery) {
        stopLiveTracking();
    }
}

function stopLiveTracking() {
    if (trackingIntervalId) {
        clearInterval(trackingIntervalId);
        trackingIntervalId = null;
    }
}

function sendLocationUpdate() {
    if (!myVehicle || !navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(
        function (position) {
            apiRequest(`/vehicles/${myVehicle.id}/update_location/`, 'POST', {
                current_lat: position.coords.latitude,
                current_lng: position.coords.longitude,
            }).catch(function (err) {
                console.error('Live location update failed:', err.message);
            });
        },
        function (error) {
            console.error('Geolocation error during live tracking:', error.message);
        }
    );
}

function initNearbyShipments() {
    const statusEl = document.getElementById('nearbyStatus');
    if (!myVehicle) {
        statusEl.textContent = 'Register a vehicle to see shipments near you.';
        return;
    }
    if (!navigator.geolocation) {
        loadNearbyWithLocation(DEFAULT_LOCATION.lat, DEFAULT_LOCATION.lng, false);
        return;
    }
    navigator.geolocation.getCurrentPosition(
        (position) => {
            loadNearbyWithLocation(position.coords.latitude, position.coords.longitude, true);
        },
        (error) => {
            console.error('Geolocation error:', error.message);
            loadNearbyWithLocation(DEFAULT_LOCATION.lat, DEFAULT_LOCATION.lng, false);
        }
    );
}

async function loadNearbyWithLocation(lat, lng, isRealLocation) {
    const statusEl = document.getElementById('nearbyStatus');
    try {
        await apiRequest(`/vehicles/${myVehicle.id}/update_location/`, 'POST', {
            current_lat: lat,
            current_lng: lng,
        });
    } catch (err) {
        console.error('Failed to update location:', err.message);
    }
    try {
        const nearby = await apiRequest(`/shipments/nearby/?lat=${lat}&lng=${lng}`);
        renderNearbyMap(lat, lng, nearby);
        renderNearbyList(nearby);
        const note = isRealLocation ? '' : ' (using a default location — device location is unavailable)';
        statusEl.textContent = nearby.length > 0
            ? `${nearby.length} shipment(s) within 100 km${note}.`
            : `No pending shipments within 100 km${note}.`;
    } catch (err) {
        statusEl.textContent = err.message;
    }
}

function renderNearbyMap(lat, lng, nearby) {
    const map = L.map('nearbyMap').setView([lat, lng], 8);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors',
    }).addTo(map);

    L.marker([lat, lng], { title: 'You' }).addTo(map).bindPopup('Your current location').openPopup();

    nearby.forEach((shipment) => {
        L.marker([shipment.origin_lat, shipment.origin_lng])
            .addTo(map)
            .bindPopup(`${shipment.origin_city} → ${shipment.destination_city}<br>${shipment.distance_km} km away`);
    });
}

function renderNearbyList(nearby) {
    const container = document.getElementById('nearbyList');
    if (nearby.length === 0) {
        container.innerHTML = '';
        return;
    }
    container.innerHTML = nearby.map(s => `
        <div class="card">
            <div class="card-body d-flex justify-content-between align-items-center">
                <div>
                    <p class="mb-1 fw-medium">
                        <a href="shipmentDetail.html?id=${s.id}" class="text-decoration-none text-dark">
                            ${s.origin_city} → ${s.destination_city}
                        </a>
                    </p>
                    <p class="mb-0 text-muted" style="font-size: 0.85rem;">
                        ${s.total_weight_kg} kg &middot; ${s.distance_km} km away
                    </p>
                </div>
                <button class="btn btn-sm btn-primary" data-request-shipment-id="${s.id}">
                    Request this shipment
                </button>
            </div>
        </div>
    `).join('');

    container.querySelectorAll('[data-request-shipment-id]').forEach(btn => {
        btn.addEventListener('click', handleRequestShipment);
    });
}

async function handleRequestShipment(e) {
    const shipmentId = e.target.dataset.requestShipmentId;
    e.target.disabled = true;
    e.target.textContent = 'Requesting...';
    try {
        await apiRequest(`/shipments/${shipmentId}/request_offer/`, 'POST');
        e.target.textContent = 'Requested — awaiting sender approval';
    } catch (err) {
        alert(err.message);
        e.target.disabled = false;
        e.target.textContent = 'Request this shipment';
    }
}