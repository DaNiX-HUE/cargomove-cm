document.addEventListener("DOMContentLoaded", function () {

    const vehicleForm = document.getElementById("vehicleForm");
    const vehicleMessage = document.getElementById("vehicleMessage");

    vehicleForm.addEventListener("submit", async function (event) {

        event.preventDefault();

        const formData = new FormData();

        formData.append(
            "license_plate",
            document.getElementById("plateNumber").value.trim()
        );

        formData.append(
            "vehicle_type",
            document.getElementById("vehicleType").value
        );

        formData.append(
            "max_weight_kg",
            document.getElementById("maxWeightCapacity").value
        );

        formData.append(
            "max_volume_m3",
            document.getElementById("maxVolumeCapacity").value
        );

        const photoInput = document.getElementById("vehiclePhoto");

        if (photoInput.files[0]) {
            formData.append(
                "vehicle_photo",
                photoInput.files[0]
            );
        }

        const submitButton = vehicleForm.querySelector(
            'button[type="submit"]'
        );

        submitButton.disabled = true;
        submitButton.textContent = "Registering...";

        vehicleMessage.className = "";
        vehicleMessage.textContent = "";

        try {

            const response = await apiMultipartRequest(
                "/api/vehicles/",
                formData
            );

            console.log("Vehicle registered successfully:", response);

            vehicleMessage.className = "alert alert-success";

            vehicleMessage.textContent =
                "Vehicle registered successfully! Redirecting...";

            setTimeout(function () {
                window.location.href = "driverDashboard.html";
            }, 1000);

        } catch (err) {

            console.error("Vehicle registration failed:", err);

            vehicleMessage.className = "alert alert-danger";

            vehicleMessage.textContent =
                err.message || "Failed to register vehicle.";

            submitButton.disabled = false;
            submitButton.textContent = "Register Vehicle";

        }

    });

});