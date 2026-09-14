const API_BASE_URL = 'http://127.0.0.1:8000/api';

const TOKEN_KEY = 'cargomove_access_token';
const REFRESH_KEY = 'cargomove_refresh_token';
const USER_KEY = 'cargomove_user';

function saveAuth(data, userInfo) {
    localStorage.setItem(TOKEN_KEY, data.access);
    localStorage.setItem(REFRESH_KEY, data.refresh);
    localStorage.setItem(USER_KEY, JSON.stringify(userInfo));
}

function getAccessToken() {
    return localStorage.getItem(TOKEN_KEY);
}

function getCurrentUser() {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
}

function clearAuth() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(USER_KEY);
}

function isLoggedIn() {
    return !!getAccessToken();
}