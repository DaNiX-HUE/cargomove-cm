document.addEventListener("DOMContentLoaded", function () {

    // Sample offer data for frontend testing

    const offer = {
        driverId: "DRV001",
        driverName: "John Driver",
        driverInitials: "JD",
        driverVerification: "Verified Driver",
        driverRating: 4.8,
        driverPhone: "+237 6XX XXX XXX",

        vehicleType: "Pickup Truck",
        plateNumber: "LT 123 AA",
        maxWeightCapacity: 1500,
        maxVolumeCapacity: 12,
        vehicleConfiguration: "Covered",

        shipmentId: "SHP001",
        deliveryOption: "Shared / Economy",
        pickupLocation: "Yaoundé",
        destination: "Douala",
        cargoCategory: "Furniture",
        cargoWeight: 500,

        estimatedPrice: 45000,
        estimatedPickupTime: "Today, 3:00 PM",
        offerStatus: "Pending"
    };


    function setText(elementId, value) {

        const element = document.getElementById(elementId);

        if (element) {
            element.textContent = value;
        }

    }



    setText("driverInitials", offer.driverInitials);

    setText("driverName", offer.driverName);

    setText("driverVerification", offer.driverVerification);

    setText("driverRating", offer.driverRating);

    setText("driverPhone", offer.driverPhone);

    setText("driverId", offer.driverId);




    setText("vehicleType", offer.vehicleType);

    setText("plateNumber", offer.plateNumber);

    setText("maxWeightCapacity", offer.maxWeightCapacity);

    setText("maxVolumeCapacity", offer.maxVolumeCapacity);

    setText("vehicleConfiguration", offer.vehicleConfiguration);




    setText("shipmentId", offer.shipmentId);

    setText("deliveryOption", offer.deliveryOption);

    setText("pickupLocation", offer.pickupLocation);

    setText("destination", offer.destination);

    setText("cargoCategory", offer.cargoCategory);

    setText("cargoWeight", offer.cargoWeight);


    setText(
        "estimatedPrice",
        offer.estimatedPrice.toLocaleString() + " FCFA"
    );

    setText("estimatedPickupTime", offer.estimatedPickupTime);

    setText("offerStatus", offer.offerStatus);



    const selectOfferButton =
        document.getElementById("selectOfferBtn");

    const offerMessage =
        document.getElementById("offerMessage");


    if (selectOfferButton) {

        selectOfferButton.addEventListener("click", function () {


            localStorage.setItem(
                "selectedOffer",
                JSON.stringify(offer)
            );


            if (offerMessage) {

                offerMessage.className = "alert alert-success";

                offerMessage.textContent =
                    "Offer selected successfully! Your request is ready for confirmation.";

            }

            selectOfferButton.textContent =
                "Offer Selected";

            selectOfferButton.disabled = true;

        });

    }

});