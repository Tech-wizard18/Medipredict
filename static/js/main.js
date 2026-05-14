// static/js/main.js

/**
 * MediPredict - Main JavaScript File
 * Core functionality and initialization
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize all components
    initNavigation();
    initForms();
    initModals();
    initTooltips();
    initNotifications();
    initThemeSwitcher();
    initMobileMenu();
    
    // Global error handler
    window.addEventListener('error', handleGlobalError);
    
    // Performance monitoring
    initPerformanceMonitoring();
});

/**
 * Navigation initialization
 */
function initNavigation() {
    // Active link highlighting
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.nav-link, .sidebar-link');
    
    navLinks.forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
            link.setAttribute('aria-current', 'page');
        }
    });
    
    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            
            const targetElement = document.querySelector(targetId);
            if (targetElement) {
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

/**
 * Form initialization and validation
 */
function initForms() {
    // Auto-hide alerts after 5 seconds
    document.querySelectorAll('.alert').forEach(alert => {
        if (!alert.classList.contains('alert-permanent')) {
            setTimeout(() => {
                fadeOut(alert);
            }, 5000);
        }
    });
    
    // Form validation
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!validateForm(this)) {
                e.preventDefault();
                showFormErrors(this);
            }
        });
        
        // Real-time validation
        form.querySelectorAll('.form-control').forEach(input => {
            input.addEventListener('blur', function() {
                validateField(this);
            });
        });
    });
    
    // Character counters
    document.querySelectorAll('[data-maxlength]').forEach(input => {
        const maxLength = parseInt(input.dataset.maxlength);
        const counterId = input.id + '-counter';
        
        // Create counter element if it doesn't exist
        if (!document.getElementById(counterId)) {
            const counter = document.createElement('div');
            counter.id = counterId;
            counter.className = 'form-text text-end';
            input.parentNode.appendChild(counter);
        }
        
        input.addEventListener('input', function() {
            const counter = document.getElementById(counterId);
            const currentLength = this.value.length;
            counter.textContent = `${currentLength}/${maxLength}`;
            
            if (currentLength > maxLength) {
                counter.classList.add('text-danger');
            } else {
                counter.classList.remove('text-danger');
            }
        });
        
        // Trigger initial count
        input.dispatchEvent(new Event('input'));
    });
}

/**
 * Modal initialization
 */
function initModals() {
    // Modal triggers
    document.querySelectorAll('[data-toggle="modal"]').forEach(trigger => {
        trigger.addEventListener('click', function() {
            const modalId = this.dataset.target;
            const modal = document.querySelector(modalId);
            
            if (modal) {
                showModal(modal);
            }
        });
    });
    
    // Modal close buttons
    document.querySelectorAll('.modal .btn-close').forEach(button => {
        button.addEventListener('click', function() {
            const modal = this.closest('.modal');
            hideModal(modal);
        });
    });
    
    // Close modal on backdrop click
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', function(e) {
            if (e.target === this) {
                hideModal(this);
            }
        });
    });
    
    // Close modal on Escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            document.querySelectorAll('.modal.show').forEach(modal => {
                hideModal(modal);
            });
        }
    });
}

/**
 * Tooltip initialization
 */
function initTooltips() {
    const tooltipElements = document.querySelectorAll('[data-toggle="tooltip"]');
    
    tooltipElements.forEach(element => {
        element.addEventListener('mouseenter', function() {
            const tooltip = createTooltip(this);
            document.body.appendChild(tooltip);
            
            positionTooltip(this, tooltip);
            showTooltip(tooltip);
        });
        
        element.addEventListener('mouseleave', function() {
            const tooltip = document.querySelector('.tooltip');
            if (tooltip) {
                hideTooltip(tooltip);
            }
        });
    });
}

/**
 * Notification system
 */
function initNotifications() {
    // Toast notifications
    window.showToast = function(message, type = 'info', duration = 5000) {
        const toast = createToast(message, type);
        document.body.appendChild(toast);
        
        // Show toast
        setTimeout(() => {
            toast.classList.add('show');
        }, 100);
        
        // Auto-remove after duration
        setTimeout(() => {
            hideToast(toast);
        }, duration);
        
        // Close button
        toast.querySelector('.btn-close').addEventListener('click', () => {
            hideToast(toast);
        });
    };
    
    // Notification bell animation
    const notificationBell = document.querySelector('.notification-bell');
    if (notificationBell) {
        notificationBell.addEventListener('click', function() {
            this.classList.add('shake');
            setTimeout(() => {
                this.classList.remove('shake');
            }, 500);
        });
    }
}

/**
 * Theme switcher
 */
function initThemeSwitcher() {
    const themeToggle = document.querySelector('.theme-toggle');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)');
    
    if (themeToggle) {
        // Check saved theme or system preference
        const savedTheme = localStorage.getItem('theme');
        const systemTheme = prefersDark.matches ? 'dark' : 'light';
        const currentTheme = savedTheme || systemTheme;
        
        // Apply theme
        if (currentTheme === 'dark') {
            document.documentElement.setAttribute('data-theme', 'dark');
            themeToggle.checked = true;
        }
        
        // Toggle theme
        themeToggle.addEventListener('change', function() {
            if (this.checked) {
                document.documentElement.setAttribute('data-theme', 'dark');
                localStorage.setItem('theme', 'dark');
            } else {
                document.documentElement.removeAttribute('data-theme');
                localStorage.setItem('theme', 'light');
            }
        });
    }
    
    // Listen for system theme changes
    prefersDark.addEventListener('change', function(e) {
        if (!localStorage.getItem('theme')) {
            if (e.matches) {
                document.documentElement.setAttribute('data-theme', 'dark');
            } else {
                document.documentElement.removeAttribute('data-theme');
            }
        }
    });
}

/**
 * Mobile menu initialization
 */
function initMobileMenu() {
    const navbarToggler = document.querySelector('.navbar-toggler');
    const sidebarToggler = document.querySelector('.sidebar-toggler');
    const navbarNav = document.querySelector('.navbar-nav');
    const sidebar = document.querySelector('.sidebar');
    
    if (navbarToggler) {
        navbarToggler.addEventListener('click', function() {
            navbarNav.classList.toggle('show');
            this.classList.toggle('collapsed');
            
            // Animate hamburger icon
            const icon = this.querySelector('.navbar-toggler-icon');
            if (navbarNav.classList.contains('show')) {
                icon.style.backgroundColor = 'transparent';
                icon.style.transform = 'rotate(45deg)';
                icon.style.before = { transform: 'rotate(90deg)' };
            } else {
                icon.style.backgroundColor = '';
                icon.style.transform = '';
                icon.style.before = { transform: '' };
            }
        });
    }
    
    if (sidebarToggler) {
        sidebarToggler.addEventListener('click', function() {
            sidebar.classList.toggle('show');
        });
    }
    
    // Close mobile menu when clicking outside
    document.addEventListener('click', function(e) {
        if (navbarNav && navbarNav.classList.contains('show') && 
            !e.target.closest('.navbar-nav') && 
            !e.target.closest('.navbar-toggler')) {
            navbarNav.classList.remove('show');
        }
        
        if (sidebar && sidebar.classList.contains('show') && 
            !e.target.closest('.sidebar') && 
            !e.target.closest('.sidebar-toggler')) {
            sidebar.classList.remove('show');
        }
    });
}

/**
 * Performance monitoring
 */
function initPerformanceMonitoring() {
    // Log page load time
    window.addEventListener('load', function() {
        const perfData = window.performance.timing;
        const loadTime = perfData.loadEventEnd - perfData.navigationStart;
        
        if (loadTime > 3000) {
            console.warn(`Page load took ${loadTime}ms. Consider optimizing.`);
        }
    });
    
    // Monitor memory usage (if supported)
    if (performance.memory) {
        setInterval(() => {
            const usedMemory = performance.memory.usedJSHeapSize;
            const totalMemory = performance.memory.totalJSHeapSize;
            
            if (usedMemory / totalMemory > 0.8) {
                console.warn('High memory usage detected');
            }
        }, 60000);
    }
}

/**
 * Form validation helper
 */
function validateForm(form) {
    let isValid = true;
    
    form.querySelectorAll('.form-control').forEach(input => {
        if (!validateField(input)) {
            isValid = false;
        }
    });
    
    return isValid;
}

function validateField(input) {
    const value = input.value.trim();
    let isValid = true;
    let errorMessage = '';
    
    // Required validation
    if (input.hasAttribute('required') && !value) {
        isValid = false;
        errorMessage = 'This field is required';
    }
    
    // Email validation
    if (input.type === 'email' && value) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(value)) {
            isValid = false;
            errorMessage = 'Please enter a valid email address';
        }
    }
    
    // Password validation
    if (input.type === 'password' && value) {
        if (input.hasAttribute('data-minlength')) {
            const minLength = parseInt(input.dataset.minlength);
            if (value.length < minLength) {
                isValid = false;
                errorMessage = `Password must be at least ${minLength} characters`;
            }
        }
    }
    
    // Number range validation
    if (input.type === 'number' && value) {
        const min = parseFloat(input.getAttribute('min'));
        const max = parseFloat(input.getAttribute('max'));
        
        if (!isNaN(min) && parseFloat(value) < min) {
            isValid = false;
            errorMessage = `Value must be at least ${min}`;
        }
        
        if (!isNaN(max) && parseFloat(value) > max) {
            isValid = false;
            errorMessage = `Value must be at most ${max}`;
        }
    }
    
    // Custom pattern validation
    if (input.hasAttribute('pattern') && value) {
        const pattern = new RegExp(input.getAttribute('pattern'));
        if (!pattern.test(value)) {
            isValid = false;
            errorMessage = input.getAttribute('data-pattern-error') || 'Invalid format';
        }
    }
    
    // Update field state
    updateFieldState(input, isValid, errorMessage);
    
    return isValid;
}

function updateFieldState(input, isValid, errorMessage) {
    const formGroup = input.closest('.form-group');
    
    if (formGroup) {
        // Remove existing error messages
        const existingError = formGroup.querySelector('.invalid-feedback');
        if (existingError) {
            existingError.remove();
        }
        
        // Update classes
        input.classList.remove('is-invalid', 'is-valid');
        
        if (!isValid) {
            input.classList.add('is-invalid');
            
            // Add error message
            const errorDiv = document.createElement('div');
            errorDiv.className = 'invalid-feedback';
            errorDiv.textContent = errorMessage;
            formGroup.appendChild(errorDiv);
        } else if (input.value.trim()) {
            input.classList.add('is-valid');
        }
    }
}

function showFormErrors(form) {
    // Scroll to first error
    const firstError = form.querySelector('.is-invalid');
    if (firstError) {
        firstError.scrollIntoView({
            behavior: 'smooth',
            block: 'center'
        });
        firstError.focus();
    }
}

/**
 * Modal helpers
 */
function showModal(modal) {
    modal.classList.add('show');
    modal.style.display = 'block';
    
    // Prevent body scrolling
    document.body.classList.add('modal-open');
    
    // Focus trap
    const focusableElements = modal.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
    const firstFocusable = focusableElements[0];
    const lastFocusable = focusableElements[focusableElements.length - 1];
    
    if (firstFocusable) firstFocusable.focus();
    
    modal.addEventListener('keydown', function(e) {
        if (e.key === 'Tab') {
            if (e.shiftKey) {
                if (document.activeElement === firstFocusable) {
                    e.preventDefault();
                    lastFocusable.focus();
                }
            } else {
                if (document.activeElement === lastFocusable) {
                    e.preventDefault();
                    firstFocusable.focus();
                }
            }
        }
    });
}

function hideModal(modal) {
    modal.classList.remove('show');
    modal.style.display = 'none';
    
    // Restore body scrolling
    document.body.classList.remove('modal-open');
}

/**
 * Tooltip helpers
 */
function createTooltip(element) {
    const tooltip = document.createElement('div');
    tooltip.className = 'tooltip';
    tooltip.textContent = element.getAttribute('title') || element.dataset.originalTitle;
    element.removeAttribute('title');
    
    return tooltip;
}

function positionTooltip(element, tooltip) {
    const rect = element.getBoundingClientRect();
    const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
    
    tooltip.style.position = 'absolute';
    tooltip.style.top = `${rect.top + scrollTop - tooltip.offsetHeight - 10}px`;
    tooltip.style.left = `${rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2)}px`;
}

function showTooltip(tooltip) {
    tooltip.style.opacity = '1';
}

function hideTooltip(tooltip) {
    tooltip.style.opacity = '0';
    setTimeout(() => {
        if (tooltip.parentNode) {
            tooltip.parentNode.removeChild(tooltip);
        }
    }, 300);
}

/**
 * Toast helpers
 */
function createToast(message, type) {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <div class="toast-body">
            ${message}
            <button type="button" class="btn-close" aria-label="Close"></button>
        </div>
    `;
    
    return toast;
}

function hideToast(toast) {
    toast.classList.remove('show');
    setTimeout(() => {
        if (toast.parentNode) {
            toast.parentNode.removeChild(toast);
        }
    }, 300);
}

/**
 * Animation helpers
 */
function fadeOut(element) {
    element.style.opacity = '1';
    
    const fadeEffect = setInterval(() => {
        if (!element.style.opacity) {
            element.style.opacity = '1';
        }
        if (parseFloat(element.style.opacity) > 0) {
            element.style.opacity = (parseFloat(element.style.opacity) - 0.1).toString();
        } else {
            clearInterval(fadeEffect);
            element.style.display = 'none';
        }
    }, 50);
}

/**
 * Global error handler
 */
function handleGlobalError(event) {
    console.error('Global error:', event.error);
    
    // Don't show error alerts in production
    if (window.location.hostname !== 'localhost' && !window.location.hostname.includes('127.0.0.1')) {
        return;
    }
    
    // Show error to user in development
    showToast(`Error: ${event.error.message}`, 'danger', 10000);
}

/**
 * Utility: Debounce function
 */
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

/**
 * Utility: Throttle function
 */
function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

/**
 * API helper functions
 */
window.MediPredictAPI = {
    // Base API URL
    baseURL: '/api/v1/',
    
    // Default headers
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
    },
    
    // Request method
    async request(endpoint, method = 'GET', data = null) {
        const url = this.baseURL + endpoint;
        const options = {
            method: method,
            headers: this.headers,
            credentials: 'same-origin'
        };
        
        if (data && method !== 'GET') {
            options.body = JSON.stringify(data);
        }
        
        try {
            const response = await fetch(url, options);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            }
            
            return await response.text();
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    },
    
    // Convenience methods
    get(endpoint) {
        return this.request(endpoint, 'GET');
    },
    
    post(endpoint, data) {
        return this.request(endpoint, 'POST', data);
    },
    
    put(endpoint, data) {
        return this.request(endpoint, 'PUT', data);
    },
    
    delete(endpoint) {
        return this.request(endpoint, 'DELETE');
    },
    
    // Health check
    async healthCheck() {
        try {
            const result = await this.get('health/');
            return result.status === 'ok';
        } catch (error) {
            return false;
        }
    }
};

// Expose API globally
window.API = window.MediPredictAPI;