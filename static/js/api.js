// static/js/api.js

/**
 * MediPredict - API Communication Module
 * Handles all API requests and responses
 */

class MediPredictAPI {
    constructor() {
        this.baseURL = '/api/v1/';
        this.csrfToken = this.getCSRFToken();
        this.requestQueue = [];
        this.isProcessingQueue = false;
        
        this.setupInterceptors();
    }
    
    getCSRFToken() {
        // Try to get CSRF token from cookie
        const cookieValue = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1];
        
        // Try to get from meta tag
        if (!cookieValue) {
            const metaTag = document.querySelector('meta[name="csrf-token"]');
            if (metaTag) {
                return metaTag.getAttribute('content');
            }
        }
        
        // Try to get from input field
        if (!cookieValue) {
            const input = document.querySelector('[name="csrfmiddlewaretoken"]');
            if (input) {
                return input.value;
            }
        }
        
        return cookieValue || '';
    }
    
    setupInterceptors() {
        // Store original fetch
        const originalFetch = window.fetch;
        
        // Override fetch to add interceptors
        window.fetch = async (...args) => {
            const [resource, config = {}] = args;
            
            // Add CSRF token to headers if not present
            if (this.csrfToken && !config.headers?.['X-CSRFToken']) {
                config.headers = {
                    ...config.headers,
                    'X-CSRFToken': this.csrfToken
                };
            }
            
            // Add JSON content type for POST/PUT/PATCH requests with body
            if (config.body && !config.headers?.['Content-Type']) {
                if (typeof config.body === 'string' || config.body instanceof FormData) {
                    // Don't set Content-Type for FormData or strings
                } else {
                    config.headers = {
                        ...config.headers,
                        'Content-Type': 'application/json'
                    };
                }
            }
            
            try {
                const response = await originalFetch(resource, config);
                
                // Handle rate limiting
                if (response.status === 429) {
                    const retryAfter = response.headers.get('Retry-After');
                    this.handleRateLimit(resource, retryAfter);
                }
                
                // Handle authentication errors
                if (response.status === 401) {
                    this.handleUnauthorized();
                }
                
                // Handle forbidden errors
                if (response.status === 403) {
                    this.handleForbidden();
                }
                
                return response;
                
            } catch (error) {
                console.error('Fetch error:', error);
                throw error;
            }
        };
    }
    
    async request(endpoint, method = 'GET', data = null, options = {}) {
        const url = this.baseURL + endpoint;
        const config = {
            method: method,
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                ...options.headers
            },
            ...options
        };
        
        // Add CSRF token
        if (this.csrfToken) {
            config.headers['X-CSRFToken'] = this.csrfToken;
        }
        
        // Handle request data
        if (data) {
            if (data instanceof FormData) {
                config.body = data;
                // Don't set Content-Type for FormData, browser will set it
            } else {
                config.body = JSON.stringify(data);
                config.headers['Content-Type'] = 'application/json';
            }
        }
        
        try {
            const response = await fetch(url, config);
            
            // Check if response is JSON
            const contentType = response.headers.get('content-type');
            const isJson = contentType && contentType.includes('application/json');
            
            let responseData;
            if (isJson) {
                responseData = await response.json();
            } else {
                responseData = await response.text();
            }
            
            // Handle non-200 responses
            if (!response.ok) {
                const error = new Error(`HTTP ${response.status}: ${response.statusText}`);
                error.status = response.status;
                error.data = responseData;
                throw error;
            }
            
            return responseData;
            
        } catch (error) {
            console.error('API request failed:', error);
            
            // Show user-friendly error message
            this.showApiError(error);
            
            throw error;
        }
    }
    
    // Convenience methods
    async get(endpoint, params = {}, options = {}) {
        // Convert params to query string
        const queryString = new URLSearchParams(params).toString();
        const url = queryString ? `${endpoint}?${queryString}` : endpoint;
        
        return this.request(url, 'GET', null, options);
    }
    
    async post(endpoint, data = null, options = {}) {
        return this.request(endpoint, 'POST', data, options);
    }
    
    async put(endpoint, data = null, options = {}) {
        return this.request(endpoint, 'PUT', data, options);
    }
    
    async patch(endpoint, data = null, options = {}) {
        return this.request(endpoint, 'PATCH', data, options);
    }
    
    async delete(endpoint, options = {}) {
        return this.request(endpoint, 'DELETE', null, options);
    }
    
    // Prediction API methods
    async predict(diseaseType, parameters) {
        return this.post(`predict/${diseaseType}/`, parameters);
    }
    
    async getPredictionHistory(page = 1, limit = 10) {
        return this.get('user/predictions/', { page, limit });
    }
    
    async getPredictionDetail(predictionId) {
        return this.get(`user/predictions/${predictionId}/`);
    }
    
    async savePrediction(predictionData) {
        return this.post('predictions/save/', predictionData);
    }
    
    async deletePrediction(predictionId) {
        return this.delete(`predictions/${predictionId}/`);
    }
    
    // User API methods
    async getUserProfile() {
        return this.get('user/profile/');
    }
    
    async updateUserProfile(profileData) {
        return this.put('user/profile/', profileData);
    }
    
    async changePassword(currentPassword, newPassword) {
        return this.post('user/change-password/', {
            current_password: currentPassword,
            new_password: newPassword
        });
    }
    
    // Notifications API methods
    async getNotifications(unreadOnly = false) {
        return this.get('notifications/', { unread_only: unreadOnly });
    }
    
    async markNotificationAsRead(notificationId) {
        return this.post(`notifications/${notificationId}/read/`);
    }
    
    async markAllNotificationsAsRead() {
        return this.post('notifications/mark-all-read/');
    }
    
    async deleteNotification(notificationId) {
        return this.delete(`notifications/${notificationId}/`);
    }
    
    async getNotificationPreferences() {
        return this.get('notifications/preferences/');
    }
    
    async updateNotificationPreferences(preferences) {
        return this.put('notifications/preferences/', preferences);
    }
    
    // Statistics API methods
    async getPredictionStats(timeRange = '7d') {
        return this.get('stats/predictions/', { time_range: timeRange });
    }
    
    async getUserStats() {
        return this.get('stats/user/');
    }
    
    async getSystemStats() {
        return this.get('stats/system/');
    }
    
    // Health check
    async healthCheck() {
        try {
            const result = await this.get('health/');
            return result.status === 'ok';
        } catch (error) {
            return false;
        }
    }
    
    // File upload
    async uploadFile(file, endpoint = 'upload/', progressCallback = null) {
        const formData = new FormData();
        formData.append('file', file);
        
        const options = {};
        
        if (progressCallback) {
            options.onUploadProgress = progressCallback;
        }
        
        return this.post(endpoint, formData, options);
    }
    
    // Batch requests
    async batch(requests) {
        return this.post('batch/', { requests });
    }
    
    // WebSocket connection for real-time updates
    setupWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/notifications/`;
        
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.onWebSocketOpen();
        };
        
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleWebSocketMessage(data);
        };
        
        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.onWebSocketClose();
            
            // Attempt to reconnect after 5 seconds
            setTimeout(() => {
                this.setupWebSocket();
            }, 5000);
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.onWebSocketError(error);
        };
    }
    
    // WebSocket event handlers (to be overridden)
    onWebSocketOpen() {}
    onWebSocketClose() {}
    onWebSocketError(error) {}
    
    handleWebSocketMessage(data) {
        switch(data.type) {
            case 'notification':
                this.handleNewNotification(data.data);
                break;
            case 'prediction_complete':
                this.handlePredictionComplete(data.data);
                break;
            case 'system_alert':
                this.handleSystemAlert(data.data);
                break;
            default:
                console.warn('Unknown WebSocket message type:', data.type);
        }
    }
    
    handleNewNotification(notification) {
        // Show notification toast
        this.showNotificationToast(notification);
        
        // Update notification count
        this.updateNotificationCount();
    }
    
    handlePredictionComplete(prediction) {
        // Show prediction result
        if (window.PredictionSystem) {
            window.PredictionSystem.displayPredictionResult(prediction);
        }
    }
    
    handleSystemAlert(alert) {
        // Show system alert
        this.showAlert(alert.message, alert.level);
    }
    
    // Error handling
    showApiError(error) {
        let message = 'An error occurred. Please try again.';
        
        if (error.status === 400) {
            message = 'Invalid request. Please check your input.';
        } else if (error.status === 401) {
            message = 'Please log in to continue.';
            // Redirect to login page
            setTimeout(() => {
                window.location.href = '/login/?next=' + encodeURIComponent(window.location.pathname);
            }, 2000);
        } else if (error.status === 403) {
            message = 'You do not have permission to perform this action.';
        } else if (error.status === 404) {
            message = 'The requested resource was not found.';
        } else if (error.status === 429) {
            message = 'Too many requests. Please try again later.';
        } else if (error.status === 500) {
            message = 'Server error. Please try again later.';
        }
        
        // Show error to user
        this.showToast(message, 'danger');
    }
    
    handleRateLimit(resource, retryAfter) {
        const message = `Rate limit exceeded. Please try again in ${retryAfter || 'a few'} seconds.`;
        this.showToast(message, 'warning');
        
        // Add to queue for retry
        this.addToQueue(resource, retryAfter);
    }
    
    handleUnauthorized() {
        this.showToast('Your session has expired. Please log in again.', 'warning');
        
        setTimeout(() => {
            window.location.href = '/login/?next=' + encodeURIComponent(window.location.pathname);
        }, 3000);
    }
    
    handleForbidden() {
        this.showToast('You do not have permission to access this resource.', 'danger');
    }
    
    // Request queue for rate limiting
    addToQueue(resource, retryAfter) {
        const retryTime = retryAfter ? parseInt(retryAfter) * 1000 : 5000;
        const retryAt = Date.now() + retryTime;
        
        this.requestQueue.push({
            resource,
            retryAt,
            attempts: 0
        });
        
        if (!this.isProcessingQueue) {
            this.processQueue();
        }
    }
    
    async processQueue() {
        this.isProcessingQueue = true;
        
        while (this.requestQueue.length > 0) {
            const now = Date.now();
            const nextRequest = this.requestQueue[0];
            
            if (now >= nextRequest.retryAt) {
                const request = this.requestQueue.shift();
                
                try {
                    // Retry the request
                    await fetch(request.resource);
                    console.log('Retry successful for:', request.resource);
                } catch (error) {
                    console.error('Retry failed for:', request.resource, error);
                    
                    // Increment attempts and reschedule if less than 3 attempts
                    request.attempts++;
                    if (request.attempts < 3) {
                        request.retryAt = now + (5000 * Math.pow(2, request.attempts)); // Exponential backoff
                        this.requestQueue.push(request);
                    }
                }
            } else {
                // Wait before checking again
                await this.sleep(nextRequest.retryAt - now);
            }
        }
        
        this.isProcessingQueue = false;
    }
    
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    
    // UI helpers
    showToast(message, type = 'info', duration = 5000) {
        // Use existing toast system if available
        if (window.showToast) {
            window.showToast(message, type, duration);
            return;
        }
        
        // Fallback toast implementation
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <div class="toast-body">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.classList.add('show');
        }, 100);
        
        setTimeout(() => {
            this.hideToast(toast);
        }, duration);
        
        toast.querySelector('.btn-close').addEventListener('click', () => {
            this.hideToast(toast);
        });
    }
    
    hideToast(toast) {
        toast.classList.remove('show');
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }
    
    showNotificationToast(notification) {
        const toast = document.createElement('div');
        toast.className = 'toast notification-toast';
        toast.innerHTML = `
            <div class="toast-body">
                <div class="d-flex">
                    <div class="toast-icon">
                        <i class="fas fa-bell"></i>
                    </div>
                    <div class="toast-content">
                        <h6>${notification.title}</h6>
                        <p class="mb-0">${notification.message}</p>
                        <small class="text-muted">Just now</small>
                    </div>
                    <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
                </div>
            </div>
        `;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.classList.add('show');
        }, 100);
        
        // Auto-dismiss after 10 seconds
        setTimeout(() => {
            this.hideToast(toast);
        }, 10000);
        
        // Click to view notification
        toast.addEventListener('click', () => {
            window.location.href = notification.action_url || '/notifications/';
        });
        
        // Close button
        toast.querySelector('.btn-close').addEventListener('click', (e) => {
            e.stopPropagation();
            this.hideToast(toast);
        });
    }
    
    updateNotificationCount() {
        const countElement = document.querySelector('.notification-count');
        if (countElement) {
            const currentCount = parseInt(countElement.textContent) || 0;
            countElement.textContent = currentCount + 1;
            countElement.classList.remove('d-none');
        }
    }
    
    showAlert(message, level = 'info') {
        const alert = document.createElement('div');
        alert.className = `alert alert-${level} alert-dismissible fade show`;
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        // Add to page
        const container = document.querySelector('.alerts-container') || document.body;
        container.insertBefore(alert, container.firstChild);
        
        // Auto-dismiss after 10 seconds
        setTimeout(() => {
            this.hideAlert(alert);
        }, 10000);
    }
    
    hideAlert(alert) {
        alert.classList.remove('show');
        setTimeout(() => {
            if (alert.parentNode) {
                alert.parentNode.removeChild(alert);
            }
        }, 300);
    }
    
    // Cache management
    setCache(key, value, ttl = 300) { // 5 minutes default
        const item = {
            value: value,
            expires: Date.now() + (ttl * 1000)
        };
        localStorage.setItem(`medipredict_${key}`, JSON.stringify(item));
    }
    
    getCache(key) {
        const itemStr = localStorage.getItem(`medipredict_${key}`);
        if (!itemStr) return null;
        
        const item = JSON.parse(itemStr);
        if (Date.now() > item.expires) {
            localStorage.removeItem(`medipredict_${key}`);
            return null;
        }
        
        return item.value;
    }
    
    clearCache(key = null) {
        if (key) {
            localStorage.removeItem(`medipredict_${key}`);
        } else {
            // Clear all MediPredict cache
            Object.keys(localStorage).forEach(k => {
                if (k.startsWith('medipredict_')) {
                    localStorage.removeItem(k);
                }
            });
        }
    }
    
    // Offline support
    setupOfflineSupport() {
        // Cache critical API responses
        this.cacheCriticalEndpoints();
        
        // Handle offline/online events
        window.addEventListener('offline', () => {
            this.showToast('You are offline. Some features may not work.', 'warning');
        });
        
        window.addEventListener('online', () => {
            this.showToast('You are back online.', 'success');
            this.syncOfflineData();
        });
    }
    
    cacheCriticalEndpoints() {
        const criticalEndpoints = [
            'user/profile/',
            'user/predictions/',
            'notifications/'
        ];
        
        criticalEndpoints.forEach(endpoint => {
            this.get(endpoint).then(data => {
                this.setCache(endpoint, data, 300); // Cache for 5 minutes
            }).catch(() => {
                // Silently fail for cache population
            });
        });
    }
    
    async syncOfflineData() {
        // Check for pending operations in localStorage
        const pendingOps = this.getCache('pending_operations') || [];
        
        if (pendingOps.length > 0) {
            this.showToast(`Syncing ${pendingOps.length} pending operations...`, 'info');
            
            for (const op of pendingOps) {
                try {
                    await this.request(op.endpoint, op.method, op.data);
                    // Remove from pending ops
                    pendingOps.splice(pendingOps.indexOf(op), 1);
                } catch (error) {
                    console.error('Failed to sync operation:', op, error);
                }
            }
            
            this.setCache('pending_operations', pendingOps);
            this.showToast('Sync completed.', 'success');
        }
    }
    
    // Performance monitoring
    setupPerformanceMonitoring() {
        // Monitor API response times
        const originalRequest = this.request;
        
        this.request = async function(...args) {
            const startTime = performance.now();
            
            try {
                const result = await originalRequest.apply(this, args);
                const endTime = performance.now();
                const duration = endTime - startTime;
                
                // Log slow requests
                if (duration > 1000) { // 1 second
                    console.warn(`Slow API request: ${args[0]} took ${duration.toFixed(2)}ms`);
                }
                
                return result;
            } catch (error) {
                const endTime = performance.now();
                const duration = endTime - startTime;
                console.error(`API request failed after ${duration.toFixed(2)}ms:`, error);
                throw error;
            }
        }.bind(this);
    }
}

// Initialize API when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.API = new MediPredictAPI();
    
    // Setup offline support
    window.API.setupOfflineSupport();
    
    // Setup performance monitoring
    window.API.setupPerformanceMonitoring();
    
    // Setup WebSocket for real-time updates
    if (window.location.protocol !== 'file:') { // Don't setup WS for local file://
        window.API.setupWebSocket();
    }
});

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MediPredictAPI;
}