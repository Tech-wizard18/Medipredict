// MEDIPREDICT - Main JavaScript File

document.addEventListener('DOMContentLoaded', function() {
    // Initialize all components
    initializeThemeToggle();
    initializeNotifications();
    initializeFormValidation();
    initializeRangeSliders();
    initializeTooltips();
    initializeMobileMenu();
    initializeSmoothScrolling();
    initializeChartComponents();
});

// Theme Management
function initializeThemeToggle() {
    const themeToggle = document.getElementById('themeToggle');
    const prefersDarkScheme = window.matchMedia('(prefers-color-scheme: dark)');
    
    // Check for saved theme preference
    const currentTheme = localStorage.getItem('theme') || 'light';
    if (currentTheme === 'dark') {
        document.body.classList.add('dark-theme');
    }
    
    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            document.body.classList.toggle('dark-theme');
            const theme = document.body.classList.contains('dark-theme') ? 'dark' : 'light';
            localStorage.setItem('theme', theme);
            updateThemeIcon(theme);
        });
        
        updateThemeIcon(currentTheme);
    }
    
    // Listen for system theme changes
    prefersDarkScheme.addListener((e) => {
        if (!localStorage.getItem('theme')) {
            document.body.classList.toggle('dark-theme', e.matches);
        }
    });
}

function updateThemeIcon(theme) {
    const themeToggle = document.getElementById('themeToggle');
    if (!themeToggle) return;
    
    const icon = themeToggle.querySelector('i');
    if (icon) {
        icon.className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
    }
}

// Notification System
function initializeNotifications() {
    const notificationBell = document.getElementById('notificationBell');
    const notificationPanel = document.getElementById('notificationPanel');
    
    if (notificationBell && notificationPanel) {
        notificationBell.addEventListener('click', (e) => {
            e.stopPropagation();
            notificationPanel.classList.toggle('show');
            markNotificationsAsRead();
        });
        
        // Close notification panel when clicking outside
        document.addEventListener('click', (e) => {
            if (!notificationPanel.contains(e.target) && !notificationBell.contains(e.target)) {
                notificationPanel.classList.remove('show');
            }
        });
    }
    
    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            fadeOut(alert);
        }, 5000);
    });
}

function markNotificationsAsRead() {
    // Send AJAX request to mark notifications as read
    fetch('/notifications/mark-as-read/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json',
        },
    }).then(response => {
        if (response.ok) {
            const badge = document.querySelector('.notification-badge');
            if (badge) badge.style.display = 'none';
        }
    });
}

// Form Validation
function initializeFormValidation() {
    const forms = document.querySelectorAll('.needs-validation');
    
    forms.forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            
            form.classList.add('was-validated');
            
            // Custom validation for password confirmation
            const password = form.querySelector('#password');
            const confirmPassword = form.querySelector('#confirmPassword');
            
            if (password && confirmPassword) {
                if (password.value !== confirmPassword.value) {
                    confirmPassword.setCustomValidity('Passwords do not match');
                } else {
                    confirmPassword.setCustomValidity('');
                }
            }
        }, false);
    });
}

// Range Sliders
function initializeRangeSliders() {
    const rangeSliders = document.querySelectorAll('input[type="range"]');
    
    rangeSliders.forEach(slider => {
        const valueDisplay = document.getElementById(slider.dataset.target);
        if (valueDisplay) {
            // Initial value
            valueDisplay.textContent = slider.value;
            
            // Update on input
            slider.addEventListener('input', () => {
                valueDisplay.textContent = slider.value;
                
                // Update background gradient for visual feedback
                const percentage = (slider.value - slider.min) / (slider.max - slider.min) * 100;
                slider.style.background = `linear-gradient(to right, var(--primary-color) 0%, var(--primary-color) ${percentage}%, var(--gray-300) ${percentage}%, var(--gray-300) 100%)`;
            });
        }
    });
}

// Tooltips
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(tooltipTriggerEl => {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Mobile Menu
function initializeMobileMenu() {
    const mobileMenuToggle = document.getElementById('mobileMenuToggle');
    const mobileMenu = document.getElementById('mobileMenu');
    
    if (mobileMenuToggle && mobileMenu) {
        mobileMenuToggle.addEventListener('click', () => {
            mobileMenu.classList.toggle('show');
        });
        
        // Close mobile menu when clicking outside
        document.addEventListener('click', (e) => {
            if (!mobileMenu.contains(e.target) && !mobileMenuToggle.contains(e.target)) {
                mobileMenu.classList.remove('show');
            }
        });
    }
}

// Smooth Scrolling
function initializeSmoothScrolling() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            
            const targetElement = document.querySelector(targetId);
            if (targetElement) {
                e.preventDefault();
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

// Chart Components
function initializeChartComponents() {
    // Initialize any chart-related components
    const chartContainers = document.querySelectorAll('[data-chart]');
    chartContainers.forEach(container => {
        const chartType = container.dataset.chart;
        switch(chartType) {
            case 'risk':
                initializeRiskChart(container);
                break;
            case 'health':
                initializeHealthChart(container);
                break;
            case 'predictions':
                initializePredictionsChart(container);
                break;
        }
    });
}

// Helper Functions
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function fadeOut(element) {
    element.style.opacity = 1;
    
    const fadeEffect = setInterval(() => {
        if (element.style.opacity > 0) {
            element.style.opacity -= 0.1;
        } else {
            clearInterval(fadeEffect);
            element.style.display = 'none';
        }
    }, 50);
}

function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) return;
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <div class="toast-content">
            <i class="fas ${getToastIcon(type)}"></i>
            <span>${message}</span>
        </div>
        <button class="toast-close" onclick="this.parentElement.remove()">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    toastContainer.appendChild(toast);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (toast.parentNode) {
            toast.remove();
        }
    }, 5000);
}

function getToastIcon(type) {
    switch(type) {
        case 'success': return 'fa-check-circle';
        case 'error': return 'fa-exclamation-circle';
        case 'warning': return 'fa-exclamation-triangle';
        default: return 'fa-info-circle';
    }
}

// API Helper
async function apiRequest(url, method = 'GET', data = null) {
    const options = {
        method: method,
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json',
        },
    };
    
    if (data) {
        options.body = JSON.stringify(data);
    }
    
    try {
        const response = await fetch(url, options);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('API Request failed:', error);
        showToast('Request failed. Please try again.', 'error');
        throw error;
    }
}

// Prediction Functions
async function submitPrediction(formId, diseaseType) {
    const form = document.getElementById(formId);
    if (!form) return;
    
    const formData = new FormData(form);
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    
    // Show loading state
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="loading"></span> Processing...';
    
    try {
        const response = await apiRequest(`/api/predict/${diseaseType}/`, 'POST', Object.fromEntries(formData));
        
        if (response.success) {
            showResults(response);
        } else {
            showToast(response.error || 'Prediction failed', 'error');
        }
    } catch (error) {
        showToast('An error occurred. Please try again.', 'error');
    } finally {
        // Restore button state
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
    }
}

function showResults(data) {
    const resultsContainer = document.getElementById('resultsContainer');
    if (!resultsContainer) return;
    
    resultsContainer.innerHTML = `
        <div class="result-card fade-in">
            <h2>Prediction Results</h2>
            <div class="probability-meter">
                <div class="probability-circle" style="--percentage: ${data.probability * 100}%">
                    <div class="probability-text">${(data.probability * 100).toFixed(1)}%</div>
                </div>
            </div>
            <div class="result-badge ${data.result === 'positive' ? 'badge-positive' : 'badge-negative'}">
                ${data.result === 'positive' ? 'At Risk' : 'Low Risk'}
            </div>
            <p class="confidence">Confidence: ${(data.confidence * 100).toFixed(1)}%</p>
            ${data.recommendations ? `
                <div class="recommendations">
                    <h3>Recommendations</h3>
                    <p>${data.recommendations}</p>
                </div>
            ` : ''}
            <button class="btn btn-outline" onclick="savePrediction('${data.id}')">
                <i class="fas fa-save"></i> Save Results
            </button>
        </div>
    `;
    
    // Scroll to results
    resultsContainer.scrollIntoView({ behavior: 'smooth' });
}

async function savePrediction(predictionId) {
    try {
        await apiRequest(`/api/predictions/${predictionId}/save/`, 'POST');
        showToast('Prediction saved successfully!', 'success');
    } catch (error) {
        showToast('Failed to save prediction', 'error');
    }
}

// Export functionality
function exportReport(format = 'pdf') {
    const reportData = {
        date: new Date().toISOString(),
        user: document.querySelector('.user-profile h3')?.textContent || 'User',
        // Add more report data
    };
    
    switch(format) {
        case 'pdf':
            generatePDF(reportData);
            break;
        case 'csv':
            generateCSV(reportData);
            break;
        case 'json':
            generateJSON(reportData);
            break;
    }
}

function generatePDF(data) {
    showToast('PDF generation started...', 'info');
    // Implement PDF generation logic
}

// Event Listeners for Common Actions
document.addEventListener('click', function(e) {
    // Export buttons
    if (e.target.closest('[data-export]')) {
        const format = e.target.closest('[data-export]').dataset.export;
        exportReport(format);
    }
    
    // Print buttons
    if (e.target.closest('[data-print]')) {
        window.print();
    }
    
    // Copy to clipboard
    if (e.target.closest('[data-copy]')) {
        const text = e.target.closest('[data-copy]').dataset.copy;
        copyToClipboard(text);
    }
});

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast('Copied to clipboard!', 'success');
    }).catch(err => {
        console.error('Failed to copy:', err);
        showToast('Failed to copy', 'error');
    });
}

// Initialize when page loads
window.onload = function() {
    // Add any onload initialization here
};