function renderNavbar() {
    const navLinks = document.getElementById('navLinks');
    if (!navLinks) return;

    const user = getCurrentUser();

    if (!user) {
        navLinks.innerHTML = `<li class="nav-item"><a class="nav-link" href="index.html">Log in</a></li>`;
        return;
    }

    const initial = user.username.charAt(0).toUpperCase();
    const dashboardLink = user.role === 'DRIVER' ? 'driverDashboard.html' : 'senderDashboard.html';

    navLinks.innerHTML = `
        <li class="nav-item d-flex align-items-center">
            <span class="navbar-greeting me-2">Hi, ${user.username}</span>
            <a href="${dashboardLink}" class="user-avatar" title="${user.username}">${initial}</a>
            <a href="#" class="nav-link ms-3" id="logoutLink">Log out</a>
        </li>
    `;

    document.getElementById('logoutLink').addEventListener('click', (e) => {
        e.preventDefault();
        logout();
    });
}

document.addEventListener('DOMContentLoaded', renderNavbar);