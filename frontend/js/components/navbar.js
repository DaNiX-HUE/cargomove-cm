let notifPollInterval = null;

function renderNavbar() {
    const navLinks = document.getElementById('navLinks');
    if (!navLinks) return;

    const user = getCurrentUser();

    if (!user) {
     navLinks.innerHTML = `<li class="nav-item"><a class="nav-link" href="/index.html">Log in</a></li>`;
        return;
    }

    const initial = user.username.charAt(0).toUpperCase();
    const dashboardLink = user.role === 'DRIVER' ? '/pages/driverDashboard.html' : '/pages/senderDashboard.html';

    navLinks.innerHTML = `
        <li class="nav-item d-flex align-items-center">
            <div class="notif-bell-wrapper me-3">
                <button type="button" class="notif-bell-btn" id="notifBellBtn">
                    🔔
                    <span class="notif-badge d-none" id="notifBadge">0</span>
                </button>
                <div class="notif-dropdown d-none" id="notifDropdown">
                    <div class="notif-dropdown-header">Notifications</div>
                    <div id="notifList">
                        <p class="text-muted small p-3 mb-0">No notifications yet.</p>
                    </div>
                </div>
            </div>
            <span class="navbar-greeting me-2">Hi, ${user.username}</span>
            <a href="${dashboardLink}" class="user-avatar" title="${user.username}">${initial}</a>
            <a href="#" class="nav-link ms-3" id="logoutLink">Log out</a>
        </li>
    `;

    document.getElementById('logoutLink').addEventListener('click', (e) => {
        e.preventDefault();
        logout();
    });

    setupNotifications();
}

function setupNotifications() {
    const bellBtn = document.getElementById('notifBellBtn');
    const dropdown = document.getElementById('notifDropdown');

    bellBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        dropdown.classList.toggle('d-none');
    });

    document.addEventListener('click', (e) => {
        if (!dropdown.contains(e.target) && e.target !== bellBtn) {
            dropdown.classList.add('d-none');
        }
    });

    loadNotifications();

    if (notifPollInterval) clearInterval(notifPollInterval);
    notifPollInterval = setInterval(loadNotifications, 20000);
}

async function loadNotifications() {
    try {
        const notifications = await apiRequest('/notifications/');
        renderNotifications(notifications);
    } catch (err) {
        console.error('Failed to load notifications:', err.message);
    }
}

function renderNotifications(notifications) {
    const list = document.getElementById('notifList');
    const badge = document.getElementById('notifBadge');
    if (!list || !badge) return;

    const unreadCount = notifications.filter(n => !n.is_read).length;

    if (unreadCount > 0) {
        badge.textContent = unreadCount;
        badge.classList.remove('d-none');
    } else {
        badge.classList.add('d-none');
    }

    if (notifications.length === 0) {
        list.innerHTML = `<p class="text-muted small p-3 mb-0">No notifications yet.</p>`;
        return;
    }

    list.innerHTML = notifications.map(n => `
        <div class="notif-item ${n.is_read ? '' : 'unread'}" data-id="${n.id}">
            <div class="notif-item-title">${n.title}</div>
            <div class="notif-item-message">${n.message}</div>
            <div class="notif-item-time">${timeAgo(n.created_at)}</div>
        </div>
    `).join('');

    list.querySelectorAll('.notif-item.unread').forEach(item => {
        item.addEventListener('click', () => markNotificationRead(item.dataset.id));
    });
}

async function markNotificationRead(id) {
    try {
        await apiRequest(`/notifications/${id}/`, 'PATCH', { is_read: true });
        loadNotifications();
    } catch (err) {
        console.error('Failed to mark notification as read:', err.message);
    }
}

function timeAgo(isoString) {
    const seconds = Math.floor((new Date() - new Date(isoString)) / 1000);
    if (seconds < 60) return 'just now';
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
}

document.addEventListener('DOMContentLoaded', renderNavbar);