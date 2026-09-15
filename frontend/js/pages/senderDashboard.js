document.addEventListener('DOMContentLoaded', async () => {
    if (!isLoggedIn()) {
        window.location.href = '../index.html';
        return;
    }
    await loadShipments();
    document.getElementById('shipmentsList').addEventListener('click', handleCardClick);
});

async function loadShipments() {
    const container = document.getElementById('shipmentsList');

    try {
        const shipments = await apiRequest('/shipments/');

        if (shipments.length === 0) {
            container.innerHTML = '<p class="text-muted">No shipments yet. Create your first one!</p>';
            return;
        }

        container.innerHTML = shipments.map(renderShipmentCard).join('');
    } catch (err) {
        container.innerHTML = `<div class="alert alert-danger">${err.message}</div>`;
    }
}

function renderShipmentCard(shipment) {
    const cancellable = shipment.status === 'PENDING' || shipment.status === 'MATCHED';
    const cancelButton = cancellable
        ? `<button class="btn btn-sm btn-outline-danger ms-2" data-cancel-id="${shipment.id}">Cancel</button>`
        : '';

    return `
        <div class="card">
            <div class="card-body d-flex justify-content-between align-items-center">
                <div>
                    <p class="mb-1 fw-medium">${shipment.origin_city} → ${shipment.destination_city}</p>
                    <p class="mb-0 text-muted" style="font-size: 0.85rem;">
                        ${shipment.total_weight_kg} kg &middot; Pickup ${shipment.pickup_date}
                        ${shipment.estimated_price_xaf ? `&middot; ${shipment.estimated_price_xaf} XAF` : ''}
                    </p>
                </div>
                <div>
                    <span class="status-badge status-${shipment.status}">${shipment.status}</span>
                    ${cancelButton}
                </div>
            </div>
        </div>
    `;
}

async function handleCardClick(e) {
    const cancelId = e.target.dataset.cancelId;
    if (!cancelId) return;

    if (!confirm('Cancel this shipment?')) return;

    try {
        await apiRequest(`/shipments/${cancelId}/cancel/`, 'POST');
        await loadShipments();
    } catch (err) {
        alert(err.message);
    }
}