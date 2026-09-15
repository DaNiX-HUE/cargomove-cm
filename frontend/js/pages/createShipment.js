let pickupMarker = null;
let dropoffMarker = null;
let map;
let itemCount = 0;

document.addEventListener('DOMContentLoaded', () => {
    if (!isLoggedIn()) {
        window.location.href = '../index.html';
        return;
    }
    initMap();
    addItemRow();
    document.getElementById('addItemBtn').addEventListener('click', addItemRow);
    document.getElementById('shipmentForm').addEventListener('submit', handleSubmit);
    document.getElementById('previewPriceBtn').addEventListener('click', previewPrice);
});

function initMap() {
    map = L.map('map').setView([3.848, 11.502], 7); // centered on Cameroon
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors',
    }).addTo(map);

    map.on('click', (e) => {
        if (!pickupMarker) {
            pickupMarker = L.marker(e.latlng, { title: 'Pickup' }).addTo(map);
            pickupMarker.bindPopup('Pickup point').openPopup();
        } else if (!dropoffMarker) {
            dropoffMarker = L.marker(e.latlng, { title: 'Drop-off' }).addTo(map);
            dropoffMarker.bindPopup('Drop-off point').openPopup();
        }
    });
}

function addItemRow() {
    itemCount++;
    const id = itemCount;
    const row = document.createElement('div');
    row.className = 'card mb-2';
    row.dataset.itemId = id;
    row.innerHTML = `
        <div class="card-body">
            <div class="row g-2">
                <div class="col-md-4">
                    <input type="text" class="form-control form-control-sm item-description" placeholder="Description" required>
                </div>
                <div class="col-md-2">
                    <input type="number" class="form-control form-control-sm item-quantity" placeholder="Qty" value="1" min="1" required>
                </div>
                <div class="col-md-2">
                    <input type="number" class="form-control form-control-sm item-weight" placeholder="Weight (kg)" required>
                </div>
                <div class="col-md-3">
                    <div class="d-flex gap-1">
                        <input type="number" class="form-control form-control-sm item-length" placeholder="L (cm)" required>
                        <input type="number" class="form-control form-control-sm item-width" placeholder="W (cm)" required>
                        <input type="number" class="form-control form-control-sm item-height" placeholder="H (cm)" required>
                    </div>
                </div>
                <div class="col-md-1">
                    <button type="button" class="btn btn-sm btn-outline-danger remove-item">×</button>
                </div>
            </div>
        </div>
    `;
    row.querySelector('.remove-item').addEventListener('click', () => row.remove());
    document.getElementById('itemsList').appendChild(row);
}

function collectItems() {
    const rows = document.querySelectorAll('#itemsList [data-item-id]');
    return Array.from(rows).map(row => ({
        description: row.querySelector('.item-description').value,
        quantity: parseInt(row.querySelector('.item-quantity').value),
        weight_kg: parseFloat(row.querySelector('.item-weight').value),
        length_cm: parseFloat(row.querySelector('.item-length').value),
        width_cm: parseFloat(row.querySelector('.item-width').value),
        height_cm: parseFloat(row.querySelector('.item-height').value),
    }));
}

async function handleSubmit(e) {
    e.preventDefault();
    const errorBox = document.getElementById('shipmentError');
    errorBox.classList.add('d-none');

    if (!pickupMarker || !dropoffMarker) {
        errorBox.textContent = 'Click the map to set both a pickup and a drop-off point.';
        errorBox.classList.remove('d-none');
        return;
    }

    const items = collectItems();
    if (items.length === 0) {
        errorBox.textContent = 'Add at least one cargo item.';
        errorBox.classList.remove('d-none');
        return;
    }

    const payload = {
        origin_city: document.getElementById('originCity').value,
        origin_lat: pickupMarker.getLatLng().lat,
        origin_lng: pickupMarker.getLatLng().lng,
        destination_city: document.getElementById('destinationCity').value,
        destination_lat: dropoffMarker.getLatLng().lat,
        destination_lng: dropoffMarker.getLatLng().lng,
        pickup_date: document.getElementById('pickupDate').value,
        delivery_type: document.getElementById('deliveryType').value,
        shared_load: document.getElementById('sharedLoad').checked,
        loading_assistance: document.getElementById('loadingAssistance').checked,
        special_handling: document.getElementById('specialHandling').checked,
        items: items,
    };

    try {
        await apiRequest('/shipments/', 'POST', payload);
        window.location.href = 'senderDashboard.html';
    } catch (err) {
        errorBox.textContent = err.message;
        errorBox.classList.remove('d-none');
    }
}

async function previewPrice() {
    const previewBox = document.getElementById('pricePreview');
    previewBox.textContent = 'Calculating...';

    if (!pickupMarker || !dropoffMarker) {
        previewBox.textContent = 'Set both map points first.';
        return;
    }

    const items = collectItems();
    if (items.length === 0) {
        previewBox.textContent = 'Add at least one item first.';
        return;
    }

    const totalWeight = items.reduce((sum, i) => sum + i.weight_kg * i.quantity, 0);
    const totalVolume = items.reduce(
        (sum, i) => sum + ((i.length_cm * i.width_cm * i.height_cm) / 1_000_000) * i.quantity,
        0
    );

    try {
        const result = await apiRequest('/shipments/estimate_price/', 'POST', {
            origin_lat: pickupMarker.getLatLng().lat,
            origin_lng: pickupMarker.getLatLng().lng,
            destination_lat: dropoffMarker.getLatLng().lat,
            destination_lng: dropoffMarker.getLatLng().lng,
            delivery_type: document.getElementById('deliveryType').value,
            total_weight_kg: totalWeight,
            total_volume_m3: totalVolume,
            shared_load: document.getElementById('sharedLoad').checked,
            loading_assistance: document.getElementById('loadingAssistance').checked,
            special_handling: document.getElementById('specialHandling').checked,
        });
        previewBox.textContent = `≈ ${result.estimated_price_xaf.toLocaleString()} XAF (${result.distance_km} km)`;
    } catch (err) {
        previewBox.textContent = err.message;
    }
}