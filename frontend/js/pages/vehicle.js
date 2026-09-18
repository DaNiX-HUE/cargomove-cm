document.addEventListener("DOMContentLoaded", function () {

    const vehicleForm = document.getElementById("vehicleForm");
    const vehicleMessage = document.getElementById("vehicleMessage");

    vehicleForm.addEventListener("submit", function (event) {

        event.preventDefault();

        const vehicle = {
            plateNumber: document.getElementById("plateNumber").value,
            vehicleType: document.getElementById("vehicleType").value,
            maxWeightCapacity: document.getElementById("maxWeightCapacity").value,
            maxVolumeCapacity: document.getElementById("maxVolumeCapacity").value,
            configuration: document.getElementById("configuration").value,
            status: document.getElementById("status").value
        };


        localStorage.setItem("registeredVehicle", JSON.stringify(vehicle));

        vehicleMessage.className = "alert alert-success";
        vehicleMessage.textContent =
            "Vehicle registered successfully!";

        vehicleForm.reset();

        console.log("Registered Vehicle:", vehicle);

    });

});