function getShipmentIdFromUrl() {
    const params = new URLSearchParams(window.location.search);
    return params.get('id');
}

document.addEventListener('DOMContentLoaded', async () => {
    if (!isLoggedIn()) {
        window.location.href = '../index.html';
        return;
    }
    await enforceProfileComplete();

    const shipmentId = getShipmentIdFromUrl();
    if (!shipmentId) {
        document.getElementById('shipmentDetail').innerHTML =
            '<div class="alert alert-danger">No shipment specified.</div>';
        return;
    }

    await loadShipment(shipmentId);
});

async function loadShipment(id) {
    const container = document.getElementById('shipmentDetail');
    try {
        const shipment = await apiRequest(`/shipments/${id}/`);
        renderShipment(shipment);

        let isSender = false;
        try {
            const user = typeof getCurrentUser === 'function'
                ? getCurrentUser()
                : JSON.parse(localStorage.getItem('user') || 'null');
            isSender = user && user.role === 'SENDER';
        } catch (e) {
            isSender = false;
        }
        if (shipment.status === 'PENDING' && isSender) {
            await loadOffersForSender(id);
        }
        if (shipment.status === 'IN_TRANSIT') {
            loadTracking(id);
        }
        if (shipment.status === 'DELIVERED') {
            setupRatingForm(id);
        }
    } catch (err) {
        container.innerHTML = `<div class="alert alert-danger">${err.message}</div>`;
    }
}

function renderShipment(shipment) {
    const container = document.getElementById('shipmentDetail');
    const itemsHtml = shipment.items.map(i => `
        <li>${i.description} — qty ${i.quantity}, ${i.weight_kg} kg, ${i.calculated_volume_m3.toFixed(3)} m³</li>
    `).join('');

    container.innerHTML = `
        <div class="d-flex justify-content-between align-items-start mb-3">
            <h4 class="mb-0">${shipment.origin_city} → ${shipment.destination_city}</h4>
            <span class="status-badge status-${shipment.status}">${shipment.status}</span>
        </div>
        <div class="card">
            <div class="card-body">
                <p class="mb-1"><strong>Pickup date:</strong> ${shipment.pickup_date}</p>
                <p class="mb-1"><strong>Delivery type:</strong> ${shipment.delivery_type}</p>
                <p class="mb-1"><strong>Total weight:</strong> ${shipment.total_weight_kg} kg</p>
                <p class="mb-1"><strong>Total volume:</strong> ${shipment.total_volume_m3.toFixed(3)} m³</p>
                <p class="mb-1"><strong>Estimated price:</strong> ${shipment.estimated_price_xaf} XAF</p>
                <hr>
                <p class="mb-1"><strong>Items:</strong></p>
                <ul class="mb-0">${itemsHtml}</ul>
            </div>
        </div>
    `;
}

async function loadOffersForSender(shipmentId) {
    const section = document.getElementById('offersSection');
    const container = document.getElementById('offersForSenderList');
    try {
        const allOffers = await apiRequest('/offers/');
        const offers = allOffers.filter(o => o.shipment === parseInt(shipmentId));

        if (offers.length === 0) {
            section.classList.add('d-none');
            return;
        }

        offersById = {};
        offers.forEach(o => { offersById[o.id] = o; });
        section.classList.remove('d-none');
        container.innerHTML = offers.map(renderSenderOfferCard).join('');

        container.querySelectorAll('[data-approve-offer-id]').forEach(btn => {
            btn.addEventListener('click', () => handleSenderOfferAction(btn.dataset.approveOfferId, 'sender_approve', shipmentId));
        });
        container.querySelectorAll('[data-decline-offer-id]').forEach(btn => {
            btn.addEventListener('click', () => handleSenderOfferAction(btn.dataset.declineOfferId, 'sender_decline', shipmentId));
        });
        container.querySelectorAll('[data-driver-detail-id]').forEach(el => {
            el.addEventListener('click', () => showDriverModal(el.dataset.driverDetailId));
        });
    } catch (err) {
        console.error('Failed to load offers:', err.message);
    }
}

let offersById = {};

function renderSenderOfferCard(offer) {
    const actionButtons = offer.status === 'PENDING'
        ? `<button class="btn btn-sm btn-primary" data-approve-offer-id="${offer.id}">Approve</button>
           <button class="btn btn-sm btn-outline-danger ms-1" data-decline-offer-id="${offer.id}">Decline</button>`
        : '';
    const ratingText = offer.driver_rating ? ` &middot; ★ ${offer.driver_rating.toFixed(1)}` : '';
    const avatarInner = offer.driver_profile_picture
        ? `<img src="${offer.driver_profile_picture}" alt="${offer.driver_username}" style="width:48px;height:48px;border-radius:50%;object-fit:cover;">`
        : `<div style="width:48px;height:48px;border-radius:50%;background:#D85A30;color:#fff;display:flex;align-items:center;justify-content:center;font-weight:600;">${(offer.driver_username || '?').charAt(0).toUpperCase()}</div>`;
    const avatarHtml = `<div data-driver-detail-id="${offer.id}" style="cursor:pointer;flex-shrink:0;" title="View driver details">${avatarInner}</div>`;
    return `
        <div class="card">
            <div class="card-body d-flex justify-content-between align-items-center">
                <div class="d-flex align-items-center gap-2">
                    ${avatarHtml}
                    <div>
                        <p class="mb-1 fw-medium" style="cursor:pointer;" data-driver-detail-id="${offer.id}">${offer.driver_username} — ${offer.vehicle_type} (${offer.vehicle_license_plate})</p>
                        <p class="mb-0 text-muted" style="font-size: 0.85rem;">
                            ${offer.driver_phone || 'No phone on file'} &middot; Fare: ${offer.offered_fare_xaf} XAF${ratingText}
                        </p>
                    </div>
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

function showDriverModal(offerId) {
    const offer = offersById[offerId];
    if (!offer) return;
    const avatarHtml = offer.driver_profile_picture
        ? `<img src="${offer.driver_profile_picture}" alt="${offer.driver_username}" style="width:88px;height:88px;border-radius:50%;object-fit:cover;">`
        : `<div style="width:88px;height:88px;border-radius:50%;background:#D85A30;color:#fff;display:flex;align-items:center;justify-content:center;font-weight:600;font-size:2rem;">${(offer.driver_username || '?').charAt(0).toUpperCase()}</div>`;
    const vehiclePhotoHtml = offer.vehicle_photo
        ? `<img src="${offer.vehicle_photo}" alt="${offer.vehicle_type}" style="width:100%;max-height:160px;object-fit:cover;border-radius:10px;margin-top:0.75rem;">`
        : '';
    document.getElementById('driverModalBody').innerHTML = `
        <div class="text-center mb-3">
            ${avatarHtml}
            <h5 class="mt-2 mb-0">${offer.driver_username}</h5>
            <p class="text-muted mb-0">${offer.driver_rating ? `★ ${offer.driver_rating.toFixed(1)} rating` : 'No ratings yet'}</p>
        </div>
        <ul class="list-unstyled mb-0">
            <li class="mb-2"><strong>Phone:</strong> ${offer.driver_phone || 'Not provided'}</li>
            <li class="mb-2"><strong>Vehicle:</strong> ${offer.vehicle_type}</li>
            <li class="mb-2"><strong>License plate:</strong> ${offer.vehicle_license_plate}</li>
            <li class="mb-2"><strong>Offered fare:</strong> ${offer.offered_fare_xaf} XAF</li>
        </ul>
        ${vehiclePhotoHtml}
    `;
    const modalEl = document.getElementById('driverInfoModal');
    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    modal.show();
}

async function handleSenderOfferAction(offerId, action, shipmentId) {
    try {
        await apiRequest(`/offers/${offerId}/${action}/`, 'POST');
        await loadShipment(shipmentId);
    } catch (err) {
        alert(err.message);
    }
}

/* ---------- Live tracking map (auto-refreshes every 20s while IN_TRANSIT) ---------- */

let trackingMap = null;
let trackingPolyline = null;
let trackingMarker = null;
let trackingIntervalId = null;

function loadTracking(shipmentId) {
    refreshTracking(shipmentId);
    if (trackingIntervalId) clearInterval(trackingIntervalId);
    trackingIntervalId = setInterval(function () {
        refreshTracking(shipmentId);
    }, 20000);
}

async function refreshTracking(shipmentId) {
    try {
        const allTracking = await apiRequest('/tracking/');
        const points = allTracking.filter(t => t.shipment === parseInt(shipmentId));

        if (points.length === 0) return;

        document.getElementById('trackingMapContainer').classList.remove('d-none');

        const latlngs = points.map(p => [p.current_lat, p.current_lng]);
        const latest = latlngs[latlngs.length - 1];

        if (!trackingMap) {
            trackingMap = L.map('trackingMap').setView(latest, 10);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '&copy; OpenStreetMap contributors',
            }).addTo(trackingMap);
            trackingPolyline = L.polyline(latlngs, { color: '#D85A30' }).addTo(trackingMap);
            trackingMarker = L.marker(latest).addTo(trackingMap).bindPopup('Latest position').openPopup();
        } else {
            trackingPolyline.setLatLngs(latlngs);
            trackingMarker.setLatLng(latest);
            trackingMap.panTo(latest);
        }
    } catch (err) {
        console.error('Tracking load failed:', err);
    }
}

function setupRatingForm(shipmentId) {
    document.getElementById('ratingSection').classList.remove('d-none');
    document.getElementById('ratingForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        try {
            await apiRequest('/ratings/', 'POST', {
                shipment: parseInt(shipmentId),
                stars: parseInt(document.getElementById('ratingStars').value),
                comment: document.getElementById('ratingComment').value,
            });
            alert('Thank you for your rating!');
            document.getElementById('ratingSection').classList.add('d-none');
        } catch (err) {
            alert(err.message);
        }
    });
}