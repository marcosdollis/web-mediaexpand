/**
 * MediaExpand - Custom JavaScript
 * Interactive functionality for the media management system
 */

// Global variables
let currentUser = null;
let csrfToken = null;

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Get CSRF token
    csrfToken = getCsrfToken();

    // Get current user info
    getCurrentUser();

    // Initialize components
    initializeTooltips();
    initializeAlerts();
    initializeForms();
    initializeModals();

    // Initialize page-specific functionality
    initializePageSpecific();
}

function getCsrfToken() {
    const token = document.querySelector('[name=csrfmiddlewaretoken]');
    return token ? token.value : null;
}

function getCurrentUser() {
    // Try to get user info from a global variable or API
    if (typeof userData !== 'undefined') {
        currentUser = userData;
        updateUserInterface();
    }
}

function updateUserInterface() {
    if (!currentUser) return;

    // Update user name in navbar
    const userNameElement = document.getElementById('user-name');
    if (userNameElement) {
        userNameElement.textContent = currentUser.first_name || currentUser.username;
    }

    // Update user role display
    const userRoleElement = document.getElementById('user-role');
    if (userRoleElement) {
        userRoleElement.textContent = getRoleDisplayName(currentUser.role);
    }

    // Show/hide menu items based on role
    updateNavigationVisibility();
}

function getRoleDisplayName(role) {
    const roleNames = {
        'OWNER': 'Proprietário',
        'FRANCHISEE': 'Franqueado',
        'CLIENT': 'Cliente'
    };
    return roleNames[role] || role;
}

function updateNavigationVisibility() {
    if (!currentUser) return;

    const role = currentUser.role;

    // Hide admin-only items for non-owners
    if (role !== 'OWNER') {
        document.querySelectorAll('.owner-only').forEach(el => el.style.display = 'none');
    }

    // Hide franchisee-only items for clients
    if (role === 'CLIENT') {
        document.querySelectorAll('.franchisee-only').forEach(el => el.style.display = 'none');
    }
}

function initializeTooltips() {
    // Initialize Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

function initializeAlerts() {
    // Auto-dismiss alerts after 5 seconds
    setTimeout(function() {
        document.querySelectorAll('.alert').forEach(function(alert) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);
}

function initializeForms() {
    // Add loading states to forms
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function(e) {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Processando...';
            }
        });
    });

    // Form validation
    document.querySelectorAll('.needs-validation').forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });
}

function initializeModals() {
    // Handle modal confirmations
    document.querySelectorAll('[data-confirm]').forEach(element => {
        element.addEventListener('click', function(e) {
            const message = this.getAttribute('data-confirm');
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });
}

function initializePageSpecific() {
    const currentPage = window.location.pathname;

    if (currentPage.includes('/dashboard/')) {
        initializeDashboard();
    } else if (currentPage.includes('/videos/')) {
        initializeVideoPage();
    } else if (currentPage.includes('/playlists/')) {
        initializePlaylistPage();
    } else if (currentPage.includes('/dispositivos/')) {
        initializeDevicePage();
    }
}

function initializeDashboard() {
    // Load dashboard statistics
    loadDashboardStats();

    // Initialize charts if Chart.js is available
    if (typeof Chart !== 'undefined') {
        initializeCharts();
    }
}

function loadDashboardStats() {
    // This would typically make an AJAX call to get stats
    // For now, we'll just animate the numbers
    document.querySelectorAll('.dashboard-card .card-title').forEach(counter => {
        animateCounter(counter);
    });
}

function animateCounter(element) {
    const target = parseInt(element.textContent.replace(/\D/g, ''));
    if (!target) return;

    let current = 0;
    const increment = target / 50;
    const timer = setInterval(() => {
        current += increment;
        if (current >= target) {
            current = target;
            clearInterval(timer);
        }
        element.textContent = Math.floor(current).toLocaleString();
    }, 30);
}

function initializeCharts() {
    // Example chart initialization
    const ctx = document.getElementById('usageChart');
    if (ctx) {
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun'],
                datasets: [{
                    label: 'Exibições',
                    data: [12, 19, 3, 5, 2, 3],
                    borderColor: '#0d6efd',
                    backgroundColor: 'rgba(13, 110, 253, 0.1)',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }
}

function initializeVideoPage() {
    // Video upload progress
    const videoInput = document.getElementById('id_video_file');
    if (videoInput) {
        videoInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                validateVideoFile(file);
            }
        });
    }

    // Video preview
    initializeVideoPreview();
}

function validateVideoFile(file) {
    const maxSize = 100 * 1024 * 1024; // 100MB
    const allowedTypes = ['video/mp4', 'video/avi', 'video/mov', 'video/wmv'];

    if (file.size > maxSize) {
        showAlert('Arquivo muito grande. Máximo: 100MB', 'danger');
        return false;
    }

    if (!allowedTypes.includes(file.type)) {
        showAlert('Tipo de arquivo não suportado. Use MP4, AVI, MOV ou WMV', 'danger');
        return false;
    }

    return true;
}

function initializeVideoPreview() {
    document.querySelectorAll('.video-preview').forEach(video => {
        video.addEventListener('loadeddata', function() {
            // Video loaded successfully
            this.style.display = 'block';
        });

        video.addEventListener('error', function() {
            // Video failed to load
            this.style.display = 'none';
            const fallback = this.nextElementSibling;
            if (fallback && fallback.classList.contains('video-fallback')) {
                fallback.style.display = 'block';
            }
        });
    });
}

function initializePlaylistPage() {
    // Drag and drop for playlist items
    initializeDragAndDrop();

    // Playlist preview
    initializePlaylistPreview();
}

function initializeDragAndDrop() {
    const playlistItems = document.querySelectorAll('.playlist-item');
    let draggedElement = null;

    playlistItems.forEach(item => {
        item.draggable = true;

        item.addEventListener('dragstart', function(e) {
            draggedElement = this;
            this.classList.add('dragging');
        });

        item.addEventListener('dragend', function(e) {
            this.classList.remove('dragging');
            draggedElement = null;
        });

        item.addEventListener('dragover', function(e) {
            e.preventDefault();
        });

        item.addEventListener('drop', function(e) {
            e.preventDefault();
            if (draggedElement && draggedElement !== this) {
                const allItems = Array.from(this.parentNode.children);
                const draggedIndex = allItems.indexOf(draggedElement);
                const droppedIndex = allItems.indexOf(this);

                if (draggedIndex < droppedIndex) {
                    this.parentNode.insertBefore(draggedElement, this.nextSibling);
                } else {
                    this.parentNode.insertBefore(draggedElement, this);
                }

                updatePlaylistOrder();
            }
        });
    });
}

function updatePlaylistOrder() {
    // Update the order of playlist items via AJAX
    const items = document.querySelectorAll('.playlist-item');
    const order = Array.from(items).map((item, index) => ({
        id: item.dataset.id,
        order: index + 1
    }));

    // Send order update to server
    fetch('/api/playlists/update-order/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({ order: order })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('Ordem da playlist atualizada!', 'success');
        }
    })
    .catch(error => {
        console.error('Error updating playlist order:', error);
        showAlert('Erro ao atualizar ordem da playlist', 'danger');
    });
}

function initializePlaylistPreview() {
    // Add click handlers for playlist preview
    document.querySelectorAll('.playlist-preview-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const playlistId = this.dataset.playlistId;
            openPlaylistPreview(playlistId);
        });
    });
}

function initializeDevicePage() {
    // Device status updates
    initializeDeviceStatus();

    // QR Code generation
    initializeQRCode();
}

function initializeDeviceStatus() {
    // Auto-refresh device status every 30 seconds
    setInterval(() => {
        document.querySelectorAll('.device-status').forEach(status => {
            const deviceId = status.dataset.deviceId;
            updateDeviceStatus(deviceId, status);
        });
    }, 30000);
}

function updateDeviceStatus(deviceId, statusElement) {
    fetch(`/api/dispositivos/${deviceId}/status/`)
        .then(response => response.json())
        .then(data => {
            statusElement.innerHTML = data.status_html;
            statusElement.className = `device-status status-${data.status}`;
        })
        .catch(error => {
            console.error('Error updating device status:', error);
        });
}

function initializeQRCode() {
    document.querySelectorAll('.generate-qr').forEach(btn => {
        btn.addEventListener('click', function() {
            const deviceId = this.dataset.deviceId;
            generateDeviceQR(deviceId);
        });
    });
}

function generateDeviceQR(deviceId) {
    // This would typically call an API to generate QR code
    // For now, just show a placeholder
    const qrContainer = document.getElementById(`qr-${deviceId}`);
    if (qrContainer) {
        qrContainer.innerHTML = '<div class="text-center"><i class="fas fa-qrcode fa-3x text-muted"></i><br><small>QR Code seria gerado aqui</small></div>';
    }
}

// Utility functions
function showAlert(message, type = 'info') {
    const alertContainer = document.getElementById('alert-container') || document.body;
    const alertHtml = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    alertContainer.insertAdjacentHTML('afterbegin', alertHtml);

    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        const alert = alertContainer.querySelector('.alert');
        if (alert) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }
    }, 5000);
}

function showLoading(button) {
    button.disabled = true;
    button.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Carregando...';
}

function hideLoading(button, originalText) {
    button.disabled = false;
    button.innerHTML = originalText;
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Export functions for global use
window.MediaExpand = {
    showAlert: showAlert,
    showLoading: showLoading,
    hideLoading: hideLoading,
    formatFileSize: formatFileSize,
    debounce: debounce
};