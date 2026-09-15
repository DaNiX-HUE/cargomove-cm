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
        let message = 'Something went wrong.';
        if (data) {
            message = data.detail ? data.detail : extractFirstError(data);
        }
        throw new Error(message);
    }

   function extractFirstError(obj, prefix = '') {
    for (const key in obj) {
        const value = obj[key];
        const label = prefix ? `${prefix}.${key}` : key;

        if (Array.isArray(value)) {
            return `${label}: ${value[0]}`;
        } else if (typeof value === 'object' && value !== null) {
            return extractFirstError(value, label);
        } else {
            return `${label}: ${value}`;
        }
    }
    return 'Something went wrong.';
}
    return data;
}