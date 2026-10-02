let adminData = {};

const ENTITY_CONFIG = {
    customers: {
        endpoint: "/customers/",
        label: function (item) { return item.username || item.company_name || ("Customer #" + item.id); },
        confirmNote: "This removes their profile and their entire shipment history.",
    },
    drivers: {
        endpoint: "/drivers/",
        label: function (item) { return item.username || ("Driver #" + item.id); },
        confirmNote: "This removes their profile, vehicle(s), and rating history.",
    },
    vehicles: {
        endpoint: "/vehicles/",
        label: function (item) { return (item.vehicle_type || "Vehicle") + " (" + (item.license_plate || item.id) + ")"; },
        confirmNote: "This removes the vehicle and its offer history.",
    },
    shipments: {
        endpoint: "/shipments/",
        label: function (item) { return (item.origin_city || "?") + " → " + (item.destination_city || "?") + " (#" + item.id + ")"; },
        confirmNote: "This removes the shipment and all its tracking/offer history.",
    },
};

document.addEventListener("DOMContentLoaded", async function () {

    if (!isLoggedIn()) {
        window.location.href = "../index.html";
        return;
    }

    const adminMessage = document.getElementById("adminMessage");

    try {
        const me = await apiRequest("/auth/me/");
        if (!me.is_staff) {
            adminMessage.className = "alert alert-danger";
            adminMessage.textContent = "You do not have permission to view this page.";
            return;
        }
    } catch (err) {
        window.location.href = "../index.html";
        return;
    }

    loadAdminDashboard();

    document.querySelectorAll(".stat-card").forEach(function (card) {
        card.addEventListener("click", function () {
            showDetails(card.dataset.type);
        });
    });

    document.getElementById("recordDeleteBtn").addEventListener("click", handleDeleteRecord);

});

async function loadAdminDashboard() {

    const adminMessage = document.getElementById("adminMessage");

    try {

        const customers = await apiRequest("/customers/");
        const drivers = await apiRequest("/drivers/");
        const vehicles = await apiRequest("/vehicles/");
        const shipments = await apiRequest("/shipments/");

        adminData = { customers, drivers, vehicles, shipments };

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
        console.error("Admin dashboard failed:", err);
        adminMessage.className = "alert alert-danger";
        adminMessage.textContent =
            err.message || "Failed to load admin dashboard.";
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
        document.getElementById("shipmentTableBody");
    shipmentTableBody.innerHTML = "";

    const shipments =
        Array.isArray(data) ? data : data.results || [];

    if (shipments.length === 0) {

        shipmentTableBody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center text-muted">
                    No shipments found.
                </td>
            </tr>
        `;

        return;
    }

    shipments.forEach(function (shipment) {
        const row = document.createElement("tr");

        row.innerHTML = `
            <td>${shipment.id}</td>
            <td>${shipment.origin_city} → ${shipment.destination_city}</td>
            <td>${shipment.pickup_date}</td>
            <td>${shipment.status}</td>
            <td>${shipment.delivery_type}</td>
            <td>${shipment.estimated_price_xaf} XAF</td>
        `;

        shipmentTableBody.appendChild(row);
    });
}

/* ---------- Clickable details tables ---------- */

const HIDDEN_KEYS = [
    "password", "company", "company_name", "role",
    "is_active", "is_staff", "is_superuser",
    "last_login", "groups", "user_permissions"
];

const DOC_LABELS = {
    profile_picture: "Profile",
    id_card_photo: "ID card",
    selfie_with_id_photo: "Selfie + ID"
};

function toList(data) {
    return Array.isArray(data) ? data : (data && data.results) || [];
}

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
}

function isDocKey(key) {
    return /photo|picture|image/i.test(key);
}

function prettyHeader(key) {
    const text = key.replace(/_/g, " ");
    return text.charAt(0).toUpperCase() + text.slice(1);
}

function flattenRecord(item) {
    const flat = {};
    Object.keys(item).forEach(function (key) {
        const value = item[key];
        if (value && typeof value === "object" && !Array.isArray(value)) {
            Object.keys(value).forEach(function (innerKey) {
                if (innerKey !== "id") {
                    flat[innerKey] = value[innerKey];
                }
            });
        } else {
            flat[key] = value;
        }
    });
    return flat;
}

function formatCell(value) {
    if (value === null || value === undefined || value === "") return "-";
    if (typeof value === "boolean") return value ? "Yes" : "No";
    if (Array.isArray(value)) return value.join(", ") || "-";
    if (/^\d{4}-\d{2}-\d{2}T/.test(String(value))) {
        return new Date(value).toLocaleDateString();
    }
    return String(value);
}

function docLinks(row, docKeys) {
    const links = docKeys
        .filter(function (k) {
            return typeof row[k] === "string" && /^https?:\/\//.test(row[k]);
        })
        .map(function (k) {
            const label = DOC_LABELS[k] || prettyHeader(k);
            return '<a href="' + escapeHtml(row[k]) +
                '" target="_blank" rel="noopener">' + escapeHtml(label) + "</a>";
        });
    return links.length ? links.join(" · ") : "-";
}

function showDetails(type) {
    const items = toList(adminData[type]).map(flattenRecord);
    const card = document.getElementById("detailsCard");
    const title = document.getElementById("detailsTitle");
    const head = document.getElementById("detailsHead");
    const body = document.getElementById("detailsBody");

    title.textContent = type.charAt(0).toUpperCase() + type.slice(1);
    head.innerHTML = "";
    body.innerHTML = "";
    card.classList.remove("d-none");

    if (items.length === 0) {
        body.innerHTML =
            '<tr><td class="text-center text-muted">No ' + type + " found.</td></tr>";
        card.scrollIntoView({ behavior: "smooth" });
        return;
    }

    const allKeys = [];
    items.forEach(function (item) {
        Object.keys(item).forEach(function (k) {
            if (!allKeys.includes(k) && !HIDDEN_KEYS.includes(k)) {
                allKeys.push(k);
            }
        });
    });

    const docKeys = allKeys.filter(isDocKey);
    const textKeys = allKeys.filter(function (k) {
        return !isDocKey(k);
    });

    let headerHtml = textKeys.map(function (k) {
        return "<th>" + escapeHtml(prettyHeader(k)) + "</th>";
    }).join("");
    if (docKeys.length) headerHtml += "<th>Documents</th>";
    head.innerHTML = "<tr>" + headerHtml + "</tr>";

    items.forEach(function (item) {
        let cells = textKeys.map(function (k) {
            return "<td>" + escapeHtml(formatCell(item[k])) + "</td>";
        }).join("");
        if (docKeys.length) cells += "<td>" + docLinks(item, docKeys) + "</td>";

        const row = document.createElement("tr");
        row.innerHTML = cells;
        row.style.cursor = "pointer";
        row.title = "Click to view details";
        row.addEventListener("click", function () {
            showRecordDetail(type, item);
        });

        body.appendChild(row);
    });

    card.scrollIntoView({ behavior: "smooth" });
}

/* ---------- Record detail modal + delete (works for all 4 types) ---------- */

function showRecordDetail(type, item) {
    const config = ENTITY_CONFIG[type];
    const modalTitle = document.getElementById("recordDetailTitle");
    const modalBody = document.getElementById("recordDetailBody");

    const keys = Object.keys(item).filter(function (k) {
        return !HIDDEN_KEYS.includes(k);
    });
    const docKeys = keys.filter(isDocKey);
    const textKeys = keys.filter(function (k) {
        return !isDocKey(k);
    });

    modalTitle.textContent = config.label(item);

    let html = '<ul class="list-unstyled mb-0">';
    textKeys.forEach(function (k) {
        html += "<li class=\"mb-2\"><strong>" + escapeHtml(prettyHeader(k)) +
            ":</strong> " + escapeHtml(formatCell(item[k])) + "</li>";
    });
    if (docKeys.length) {
        html += "<li class=\"mb-2\"><strong>Documents:</strong> " + docLinks(item, docKeys) + "</li>";
    }
    html += "</ul>";
    modalBody.innerHTML = html;

    const deleteBtn = document.getElementById("recordDeleteBtn");
    deleteBtn.dataset.type = type;
    deleteBtn.dataset.id = item.id;
    deleteBtn.dataset.label = config.label(item);
    deleteBtn.dataset.note = config.confirmNote;

    bootstrap.Modal.getOrCreateInstance(document.getElementById("recordDetailModal")).show();
}

async function handleDeleteRecord(e) {
    const btn = e.currentTarget;
    const type = btn.dataset.type;
    const id = btn.dataset.id;
    const label = btn.dataset.label;
    const note = btn.dataset.note;

    if (!type || !id) return;

    const confirmed = confirm(
        "Permanently delete " + label + "? " + note + " This cannot be undone."
    );
    if (!confirmed) return;

    const originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = "Deleting...";

    try {
        await apiRequest(ENTITY_CONFIG[type].endpoint + id + "/", "DELETE");
        bootstrap.Modal.getOrCreateInstance(document.getElementById("recordDetailModal")).hide();
        await loadAdminDashboard();
        showDetails(type);
    } catch (err) {
        alert(err.message || "Failed to delete.");
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
}