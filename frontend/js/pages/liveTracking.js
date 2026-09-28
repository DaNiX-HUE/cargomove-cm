document.addEventListener("DOMContentLoaded", function () {

    const trackingForm = document.getElementById("trackingForm");
    const trackingMessage = document.getElementById("trackingMessage");
    const trackingResult = document.getElementById("trackingResult");

    trackingForm.addEventListener("submit", async function (event) {

        event.preventDefault();

        const shipmentId = document
            .getElementById("shipmentId")
            .value
            .trim();

        if (!shipmentId) {
            trackingMessage.className = "alert alert-danger";
            trackingMessage.textContent =
                "Please enter a shipment ID.";
            return;
        }

        const submitButton = trackingForm.querySelector(
            'button[type="submit"]'
        );

        submitButton.disabled = true;
        submitButton.textContent = "Tracking...";

        trackingMessage.className = "";
        trackingMessage.textContent = "";

        trackingResult.classList.add("d-none");

        try {

            const shipment = await apiRequest(
                `/api/shipments/${shipmentId}/`
            );

            console.log("Shipment found:", shipment);

            document.getElementById("displayShipmentId").textContent =
                shipment.id;

            document.getElementById("shipmentStatus").textContent =
                shipment.status;

            document.getElementById("pickupLocation").textContent =
                shipment.origin_city;

            document.getElementById("destination").textContent =
                shipment.destination_city;

            document.getElementById("pickupDate").textContent =
                shipment.pickup_date;

            document.getElementById("deliveryType").textContent =
                shipment.delivery_type;

            document.getElementById("totalWeight").textContent =
                shipment.total_weight_kg + " kg";

            document.getElementById("totalVolume").textContent =
                shipment.total_volume_m3 + " m³";

            document.getElementById("estimatedPrice").textContent =
                shipment.estimated_price_xaf + " XAF";

            trackingResult.classList.remove("d-none");

            trackingMessage.className = "alert alert-success";
            trackingMessage.textContent =
                "Shipment found successfully.";

        } catch (err) {

            console.error("Tracking failed:", err);

            trackingMessage.className = "alert alert-danger";
            trackingMessage.textContent =
                err.message || "Unable to find shipment.";

        }

        submitButton.disabled = false;
        submitButton.textContent = "Track Shipment";

    });

});