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

        if (shipment.status === 'IN_TRANSIT') {
            await loadTracking(id);
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

async function loadTracking(shipmentId) {
    try {
        const allTracking = await apiRequest('/tracking/');
        const points = allTracking.filter(t => t.shipment === parseInt(shipmentId));

        if (points.length === 0) return;

        document.getElementById('trackingMapContainer').classList.remove('d-none');
        const map = L.map('trackingMap').setView([points[0].current_lat, points[0].current_lng], 10);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; OpenStreetMap contributors',
        }).addTo(map);

        const latlngs = points.map(p => [p.current_lat, p.current_lng]);
        L.polyline(latlngs, { color: '#D85A30' }).addTo(map);
        L.marker(latlngs[latlngs.length - 1]).addTo(map).bindPopup('Latest position').openPopup();
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