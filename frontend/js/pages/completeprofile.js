document.addEventListener('DOMContentLoaded', () => {
    if (!isLoggedIn()) {
        window.location.href = '../index.html';
        return;
    }
    document.getElementById('profileForm').addEventListener('submit', handleSubmit);
});

async function handleSubmit(e) {
    e.preventDefault();
    const errorBox = document.getElementById('profileError');
    errorBox.classList.add('d-none');

    const formData = new FormData();
    formData.append('profile_picture', document.getElementById('selfieInput').files[0]);
    formData.append('id_card_photo', document.getElementById('idCardInput').files[0]);
    formData.append('selfie_with_id_photo', document.getElementById('selfieWithIdInput').files[0]);

    try {
        await apiUploadRequest('/auth/update-photos/', formData);
        const user = getCurrentUser();
        window.location.href = user.role === 'DRIVER' ? 'driverDashboard.html' : 'senderDashboard.html';
    } catch (err) {
        errorBox.textContent = err.message;
        errorBox.classList.remove('d-none');
    }
}