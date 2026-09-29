document.addEventListener("DOMContentLoaded", function () {

    loadAdminDashboard();

});

async function loadAdminDashboard() {

    const adminMessage = document.getElementById("adminMessage");

    try {

        const customers = await apiRequest(
            "/api/customers/"
        );
        const drivers = await apiRequest(
            "/api/drivers/"
        );
        const vehicles = await apiRequest(
            "/api/vehicles/"
        );
        const shipments = await apiRequest(
            "/api/shipments/"
        );

        document.getElementById("customerCount").textContent =
            getCount(customers);
        document.getElementById("driverCount").textContent =
            getCount(drivers);
        document.getElementById("vehicleCount").textContent =
            getCount(vehicles);
        document.getElementById("shipmentCount").textContent =
            getCount(shipments);

        displayShipments(shipments);

    } catch (err) {
        console.error(
            "Admin dashboard failed:",
            err
        );
        adminMessage.className =
            "alert alert-danger";
        adminMessage.textContent =
            err.message ||
            "Failed to load admin dashboard.";

    }

}

function getCount(data) {
    if (Array.isArray(data)) {
        return data.length;
    }

    if (data && Array.isArray(data.results)) {
        return data.results.length;
    }

    return 0;
}

function displayShipments(data) {
    const shipmentTableBody =
        document.getElementById(
            "shipmentTableBody"
        );
    shipmentTableBody.innerHTML = "";

    const shipments =
        Array.isArray(data)
            ? data
            : data.results || [];


    if (shipments.length === 0) {

        shipmentTableBody.innerHTML = `
            <tr>
                <td
                    colspan="6"
                    class="text-center text-muted"
                >
                    No shipments found.
                </td>
            </tr>
        `;

        return;
    }

    shipments.forEach(function (shipment) {
        const row =
            document.createElement("tr");

        row.innerHTML = `

            <td>
                ${shipment.id}
            </td>

            <td>
                ${shipment.origin_city}
                →
                ${shipment.destination_city}
            </td>

            <td>
                ${shipment.pickup_date}
            </td>

            <td>
                ${shipment.status}
            </td>

            <td>
                ${shipment.delivery_type}
            </td>

            <td>
                ${shipment.estimated_price_xaf} XAF
            </td>

        `;

        shipmentTableBody.appendChild(row);

    });

}