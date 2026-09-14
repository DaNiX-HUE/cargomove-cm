async function apiRequest(endpoint, method = 'GET', body = null) {
    const headers = {
        'Content-Type': 'application/json',
    };

    const token = getAccessToken();
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const options = {
        method,
        headers,
    };

    if (body) {
        options.body = JSON.stringify(body);
    }

    const response = await fetch(`${API_BASE_URL}${endpoint}`, options);

    if (response.status === 401) {
        clearAuth();
        window.location.href = 'index.html';
        throw new Error('Session expired. Please log in again.');
    }

    const data = await response.json().catch(() => null);

    if (!response.ok) {
        const message = data && data.detail ? data.detail : 'Something went wrong.';
        throw new Error(message);
    }

    return data;
}