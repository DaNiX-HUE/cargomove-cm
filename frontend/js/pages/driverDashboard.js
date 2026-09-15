document.addEventListener('DOMContentLoaded', async () => {
    if (!isLoggedIn()) {
        window.location.href = '../index.html';
        return;
    }
    await loadVehicle();
    await loadOffers();
    document.getElementById('offersList').addEventListener('click', handleOfferAction);
});

async function loadVehicle() {
    const container = document.getElementById('vehicleSection');
    try {
        const vehicles = await apiRequest('/vehicles/');

        if (vehicles.length === 0) {
            container.innerHTML = `<div class="alert alert-warning">
                You haven't registered a vehicle yet. Vehicle management is coming soon — for now, ask an admin to add one for you.
            </div>`;
            return;
        }

        const v = vehicles[0];
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
        container.innerHTML = `<div class="alert alert-danger">${err.message}</div>`;
    }
}

async function loadOffers() {
    const container = document.getElementById('offersList');
    try {
        const offers = await apiRequest('/offers/');

        if (offers.length === 0) {
            container.innerHTML = '<p class="text-muted">No offers yet.</p>';
            return;
        }

        const withShipments = await Promise.all(
            offers.map(async (offer) => {
                const shipment = await apiRequest(`/shipments/${offer.shipment}/`);
                return { offer, shipment };
            })
        );

        container.innerHTML = withShipments.map(renderOfferCard).join('');
    } catch (err) {
        container.innerHTML = `<div class="alert alert-danger">${err.message}</div>`;
    }
}

function renderOfferCard({ offer, shipment }) {
    const actionButtons = offer.status === 'PENDING'
        ? `
            <button class="btn btn-sm btn-primary" data-accept-id="${offer.id}">Accept</button>
            <button class="btn btn-sm btn-outline-danger ms-1" data-reject-id="${offer.id}">Reject</button>
        `
        : '';

    return `
        <div class="card">
            <div class="card-body d-flex justify-content-between align-items-center">
                <div>
                    <p class="mb-1 fw-medium">${shipment.origin_city} → ${shipment.destination_city}</p>
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
    if (!acceptId && !rejectId) return;

    const id = acceptId || rejectId;
    const action = acceptId ? 'accept' : 'reject';

    try {
        await apiRequest(`/offers/${id}/${action}/`, 'POST');
        await loadVehicle();
        await loadOffers();
    } catch (err) {
        alert(err.message);
    }
}