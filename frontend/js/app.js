document.addEventListener('DOMContentLoaded', () => {
    setupAuthTabs();
    setupRoleToggle();
    setupLoginForm();
    setupRegisterForm();
});

function setupAuthTabs() {
    const tabs = document.querySelectorAll('#authTabs .nav-link');
    tabs.forEach(tab => {
        tab.addEventListener('click', (e) => {
            e.preventDefault();
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            const target = tab.dataset.tab;
            document.getElementById('loginForm').classList.toggle('d-none', target !== 'login');
            document.getElementById('registerForm').classList.toggle('d-none', target !== 'register');
        });
    });
}

function setupRoleToggle() {
    const roleSelect = document.getElementById('registerRole');
    roleSelect.addEventListener('change', () => {
        const isDriver = roleSelect.value === 'driver';
        document.getElementById('companyNameField').classList.toggle('d-none', isDriver);
        document.getElementById('licenseNumberField').classList.toggle('d-none', !isDriver);
    });
}

function setupLoginForm() {
    const form = document.getElementById('loginForm');
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const errorBox = document.getElementById('loginError');
        errorBox.classList.add('d-none');

        const username = document.getElementById('loginUsername').value;
        const password = document.getElementById('loginPassword').value;

        try {
            const user = await login(username, password);
            window.location.href = user.role === 'DRIVER' ? 'pages/driverDashboard.html' : 'pages/senderDashboard.html';
        } catch (err) {
            errorBox.textContent = err.message;
            errorBox.classList.remove('d-none');
        }
    });
}

function setupRegisterForm() {
    const form = document.getElementById('registerForm');

    if (form.dataset.bound === 'true') return; // prevents double-binding
    form.dataset.bound = 'true';

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const errorBox = document.getElementById('registerError');
        const successBox = document.getElementById('registerSuccess');

        errorBox.textContent = '';
        errorBox.classList.add('d-none');
        successBox.textContent = '';
        successBox.classList.add('d-none');

        const role = document.getElementById('registerRole').value;
        const userData = {
            username: document.getElementById('registerUsername').value,
            email: document.getElementById('registerEmail').value,
            password: document.getElementById('registerPassword').value,
        };

        try {
            if (role === 'customer') {
                const companyName = document.getElementById('registerCompanyName').value;
                await registerCustomer(userData, companyName);
            } else {
                const licenseNumber = document.getElementById('registerLicenseNumber').value;
                await registerDriver(userData, licenseNumber);
            }
            errorBox.classList.add('d-none');
            successBox.textContent = 'Account created! You can now log in.';
            successBox.classList.remove('d-none');
            form.reset();
        } catch (err) {
            successBox.classList.add('d-none');
            errorBox.textContent = err.message;
            errorBox.classList.remove('d-none');
        }
    });
}