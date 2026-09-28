async function registerCustomer(userData, companyName) {
    return apiRequest('/api/auth/register/customer/', 'POST', {
        user: userData,
        company_name: companyName,
    });
}

async function registerDriver(userData, licenseNumber) {
    return apiRequest('/api/auth/register/driver/', 'POST', {
        user: userData,
        license_number: licenseNumber,
    });
}

async function login(username, password) {
    const tokens = await apiRequest('/api/auth/login/', 'POST', { username, password });

    localStorage.setItem(TOKEN_KEY, tokens.access);
    localStorage.setItem(REFRESH_KEY, tokens.refresh);

    const me = await apiRequest('/api/auth/me/', 'GET');
    localStorage.setItem(USER_KEY, JSON.stringify(me));

    return me;
}

function logout() {
    clearAuth();
    window.location.href = 'index.html';
}
async function enforceProfileComplete() {
    try {
        const status = await apiRequest('/api/auth/profile-status/');
        if (!status.profile_complete) {
            const onProfilePage = window.location.pathname.includes('completeProfile.html');
            if (!onProfilePage) {
                window.location.href = 'completeProfile.html';
            }
        }
    } catch (err) {
        // If the check itself fails (e.g. expired session), apiRequest already
        // handles redirecting to login — nothing extra needed here.
    }
}