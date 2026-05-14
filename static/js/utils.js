// static/js/utils.js

/**
 * MediPredict - Utility Functions
 * Common helper functions used throughout the application
 */

const MediPredictUtils = {
    // =========================================================================
    // DOM Manipulation Utilities
    // =========================================================================
    
    /**
     * Get element by selector
     */
    $(selector) {
        return document.querySelector(selector);
    },
    
    /**
     * Get all elements by selector
     */
    $$(selector) {
        return document.querySelectorAll(selector);
    },
    
    /**
     * Create element with attributes and children
     */
    createElement(tag, attributes = {}, children = []) {
        const element = document.createElement(tag);
        
        // Set attributes
        Object.entries(attributes).forEach(([key, value]) => {
            if (key === 'className') {
                element.className = value;
            } else if (key === 'textContent') {
                element.textContent = value;
            } else if (key === 'innerHTML') {
                element.innerHTML = value;
            } else if (key.startsWith('on') && typeof value === 'function') {
                element.addEventListener(key.substring(2).toLowerCase(), value);
            } else {
                element.setAttribute(key, value);
            }
        });
        
        // Append children
        children.forEach(child => {
            if (typeof child === 'string') {
                element.appendChild(document.createTextNode(child));
            } else if (child instanceof Node) {
                element.appendChild(child);
            }
        });
        
        return element;
    },
    
    /**
     * Remove element from DOM
     */
    removeElement(element) {
        if (element && element.parentNode) {
            element.parentNode.removeChild(element);
        }
    },
    
    /**
     * Toggle element visibility
     */
    toggleVisibility(element, show) {
        if (show === undefined) {
            show = element.style.display === 'none';
        }
        element.style.display = show ? '' : 'none';
        return show;
    },
    
    /**
     * Add/remove class with animation
     */
    toggleClass(element, className, force) {
        if (force === undefined) {
            element.classList.toggle(className);
        } else {
            element.classList.toggle(className, force);
        }
    },
    
    /**
     * Check if element is in viewport
     */
    isInViewport(element) {
        const rect = element.getBoundingClientRect();
        return (
            rect.top >= 0 &&
            rect.left >= 0 &&
            rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
            rect.right <= (window.innerWidth || document.documentElement.clientWidth)
        );
    },
    
    /**
     * Scroll element into view
     */
    scrollToElement(element, options = {}) {
        const defaultOptions = {
            behavior: 'smooth',
            block: 'start',
            inline: 'nearest'
        };
        
        element.scrollIntoView({ ...defaultOptions, ...options });
    },
    
    /**
     * Scroll to top of page
     */
    scrollToTop() {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    },
    
    // =========================================================================
    // String Utilities
    // =========================================================================
    
    /**
     * Capitalize first letter of string
     */
    capitalize(str) {
        return str.charAt(0).toUpperCase() + str.slice(1);
    },
    
    /**
     * Convert snake_case to Title Case
     */
    snakeToTitle(str) {
        return str
            .split('_')
            .map(word => this.capitalize(word))
            .join(' ');
    },
    
    /**
     * Convert camelCase to Title Case
     */
    camelToTitle(str) {
        return str
            .replace(/([A-Z])/g, ' $1')
            .replace(/^./, char => char.toUpperCase())
            .trim();
    },
    
    /**
     * Truncate string with ellipsis
     */
    truncate(str, maxLength = 100) {
        if (str.length <= maxLength) return str;
        return str.substring(0, maxLength - 3) + '...';
    },
    
    /**
     * Format number with commas
     */
    formatNumber(num) {
        return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    },
    
    /**
     * Format file size
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },
    
    /**
     * Generate random string
     */
    generateId(length = 8) {
        const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
        let result = '';
        for (let i = 0; i < length; i++) {
            result += chars.charAt(Math.floor(Math.random() * chars.length));
        }
        return result;
    },
    
    /**
     * Generate UUID v4
     */
    generateUUID() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0;
            const v = c === 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    },
    
    /**
     * Sanitize HTML string
     */
    sanitizeHTML(str) {
        const temp = document.createElement('div');
        temp.textContent = str;
        return temp.innerHTML;
    },
    
    /**
     * Escape regex special characters
     */
    escapeRegExp(str) {
        return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    },
    
    // =========================================================================
    // Date & Time Utilities
    // =========================================================================
    
    /**
     * Format date string
     */
    formatDate(date, format = 'YYYY-MM-DD') {
        const d = new Date(date);
        
        const pad = (num) => num.toString().padStart(2, '0');
        
        const replacements = {
            YYYY: d.getFullYear(),
            MM: pad(d.getMonth() + 1),
            DD: pad(d.getDate()),
            HH: pad(d.getHours()),
            mm: pad(d.getMinutes()),
            ss: pad(d.getSeconds())
        };
        
        return format.replace(/YYYY|MM|DD|HH|mm|ss/g, match => replacements[match]);
    },
    
    /**
     * Format relative time (e.g., "2 hours ago")
     */
    formatRelativeTime(date) {
        const now = new Date();
        const diffMs = now - new Date(date);
        const diffSec = Math.floor(diffMs / 1000);
        const diffMin = Math.floor(diffSec / 60);
        const diffHour = Math.floor(diffMin / 60);
        const diffDay = Math.floor(diffHour / 24);
        
        if (diffSec < 60) {
            return 'Just now';
        } else if (diffMin < 60) {
            return `${diffMin} minute${diffMin === 1 ? '' : 's'} ago`;
        } else if (diffHour < 24) {
            return `${diffHour} hour${diffHour === 1 ? '' : 's'} ago`;
        } else if (diffDay < 7) {
            return `${diffDay} day${diffDay === 1 ? '' : 's'} ago`;
        } else {
            return this.formatDate(date);
        }
    },
    
    /**
     * Get age from birth date
     */
    calculateAge(birthDate) {
        const today = new Date();
        const birth = new Date(birthDate);
        let age = today.getFullYear() - birth.getFullYear();
        const monthDiff = today.getMonth() - birth.getMonth();
        
        if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
            age--;
        }
        
        return age;
    },
    
    /**
     * Get timezone offset in hours
     */
    getTimezoneOffset() {
        const offset = new Date().getTimezoneOffset();
        const hours = Math.abs(Math.floor(offset / 60));
        const minutes = Math.abs(offset % 60);
        const sign = offset > 0 ? '-' : '+';
        
        return `${sign}${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;
    },
    
    /**
     * Parse duration string to milliseconds
     */
    parseDuration(duration) {
        const match = duration.match(/^(\d+)([smhdw])$/);
        if (!match) return 0;
        
        const value = parseInt(match[1]);
        const unit = match[2];
        
        const multipliers = {
            s: 1000,           // seconds
            m: 60 * 1000,      // minutes
            h: 3600 * 1000,    // hours
            d: 86400 * 1000,   // days
            w: 604800 * 1000   // weeks
        };
        
        return value * (multipliers[unit] || 0);
    },
    
    // =========================================================================
    // Number Utilities
    // =========================================================================
    
    /**
     * Clamp number between min and max
     */
    clamp(num, min, max) {
        return Math.min(Math.max(num, min), max);
    },
    
    /**
     * Round to specified decimal places
     */
    round(num, decimals = 2) {
        const factor = Math.pow(10, decimals);
        return Math.round((num + Number.EPSILON) * factor) / factor;
    },
    
    /**
     * Calculate percentage
     */
    percentage(value, total) {
        if (total === 0) return 0;
        return (value / total) * 100;
    },
    
    /**
     * Format percentage with symbol
     */
    formatPercentage(value, decimals = 1) {
        return `${this.round(value, decimals)}%`;
    },
    
    /**
     * Generate random number in range
     */
    random(min, max) {
        return Math.floor(Math.random() * (max - min + 1)) + min;
    },
    
    /**
     * Calculate average of numbers
     */
    average(numbers) {
        if (numbers.length === 0) return 0;
        const sum = numbers.reduce((a, b) => a + b, 0);
        return sum / numbers.length;
    },
    
    /**
     * Calculate standard deviation
     */
    standardDeviation(numbers) {
        if (numbers.length === 0) return 0;
        
        const avg = this.average(numbers);
        const squareDiffs = numbers.map(value => {
            const diff = value - avg;
            return diff * diff;
        });
        
        const avgSquareDiff = this.average(squareDiffs);
        return Math.sqrt(avgSquareDiff);
    },
    
    // =========================================================================
    // Array Utilities
    // =========================================================================
    
    /**
     * Remove duplicates from array
     */
    unique(array) {
        return [...new Set(array)];
    },
    
    /**
     * Shuffle array (Fisher-Yates algorithm)
     */
    shuffle(array) {
        const result = [...array];
        for (let i = result.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [result[i], result[j]] = [result[j], result[i]];
        }
        return result;
    },
    
    /**
     * Group array by key
     */
    groupBy(array, key) {
        return array.reduce((groups, item) => {
            const groupKey = item[key];
            if (!groups[groupKey]) {
                groups[groupKey] = [];
            }
            groups[groupKey].push(item);
            return groups;
        }, {});
    },
    
    /**
     * Sort array by key
     */
    sortBy(array, key, ascending = true) {
        return [...array].sort((a, b) => {
            const aVal = a[key];
            const bVal = b[key];
            
            if (aVal < bVal) return ascending ? -1 : 1;
            if (aVal > bVal) return ascending ? 1 : -1;
            return 0;
        });
    },
    
    /**
     * Chunk array into smaller arrays
     */
    chunk(array, size) {
        const chunks = [];
        for (let i = 0; i < array.length; i += size) {
            chunks.push(array.slice(i, i + size));
        }
        return chunks;
    },
    
    /**
     * Flatten nested array
     */
    flatten(array) {
        return array.reduce((flat, item) => {
            return flat.concat(Array.isArray(item) ? this.flatten(item) : item);
        }, []);
    },
    
    /**
     * Find object in array by property
     */
    findByProperty(array, property, value) {
        return array.find(item => item[property] === value);
    },
    
    /**
     * Remove item from array
     */
    removeFromArray(array, item) {
        const index = array.indexOf(item);
        if (index > -1) {
            array.splice(index, 1);
        }
        return array;
    },
    
    // =========================================================================
    // Object Utilities
    // =========================================================================
    
    /**
     * Deep clone object
     */
    deepClone(obj) {
        if (obj === null || typeof obj !== 'object') return obj;
        if (obj instanceof Date) return new Date(obj);
        if (obj instanceof Array) return obj.map(item => this.deepClone(item));
        
        const cloned = {};
        for (const key in obj) {
            if (obj.hasOwnProperty(key)) {
                cloned[key] = this.deepClone(obj[key]);
            }
        }
        return cloned;
    },
    
    /**
     * Merge objects deeply
     */
    deepMerge(target, source) {
        const output = this.deepClone(target);
        
        if (this.isObject(target) && this.isObject(source)) {
            Object.keys(source).forEach(key => {
                if (this.isObject(source[key])) {
                    if (!(key in target)) {
                        Object.assign(output, { [key]: source[key] });
                    } else {
                        output[key] = this.deepMerge(target[key], source[key]);
                    }
                } else {
                    Object.assign(output, { [key]: source[key] });
                }
            });
        }
        
        return output;
    },
    
    /**
     * Check if value is object
     */
    isObject(value) {
        return value && typeof value === 'object' && !Array.isArray(value);
    },
    
    /**
     * Check if object is empty
     */
    isEmptyObject(obj) {
        return Object.keys(obj).length === 0;
    },
    
    /**
     * Pick properties from object
     */
    pick(obj, keys) {
        return keys.reduce((result, key) => {
            if (obj.hasOwnProperty(key)) {
                result[key] = obj[key];
            }
            return result;
        }, {});
    },
    
    /**
     * Omit properties from object
     */
    omit(obj, keys) {
        const result = { ...obj };
        keys.forEach(key => delete result[key]);
        return result;
    },
    
    /**
     * Get nested property value
     */
    get(obj, path, defaultValue = undefined) {
        const keys = path.split('.');
        let result = obj;
        
        for (const key of keys) {
            result = result?.[key];
            if (result === undefined) return defaultValue;
        }
        
        return result;
    },
    
    /**
     * Set nested property value
     */
    set(obj, path, value) {
        const keys = path.split('.');
        let current = obj;
        
        for (let i = 0; i < keys.length - 1; i++) {
            const key = keys[i];
            if (!current[key] || typeof current[key] !== 'object') {
                current[key] = {};
            }
            current = current[key];
        }
        
        current[keys[keys.length - 1]] = value;
        return obj;
    },
    
    // =========================================================================
    // Function Utilities
    // =========================================================================
    
    /**
     * Debounce function
     */
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },
    
    /**
     * Throttle function
     */
    throttle(func, limit) {
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
    },
    
    /**
     * Memoize function
     */
    memoize(func) {
        const cache = new Map();
        return function(...args) {
            const key = JSON.stringify(args);
            if (cache.has(key)) {
                return cache.get(key);
            }
            const result = func.apply(this, args);
            cache.set(key, result);
            return result;
        };
    },
    
    /**
     * Retry function with exponential backoff
     */
    async retry(func, maxRetries = 3, delay = 1000) {
        for (let i = 0; i < maxRetries; i++) {
            try {
                return await func();
            } catch (error) {
                if (i === maxRetries - 1) throw error;
                await new Promise(resolve => setTimeout(resolve, delay * Math.pow(2, i)));
            }
        }
    },
    
    /**
     * Pipe functions together
     */
    pipe(...funcs) {
        return function(value) {
            return funcs.reduce((currentValue, func) => func(currentValue), value);
        };
    },
    
    /**
     * Compose functions together
     */
    compose(...funcs) {
        return function(value) {
            return funcs.reduceRight((currentValue, func) => func(currentValue), value);
        };
    },
    
    // =========================================================================
    // Validation Utilities
    // =========================================================================
    
    /**
     * Validate email address
     */
    isValidEmail(email) {
        const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return regex.test(email);
    },
    
    /**
     * Validate URL
     */
    isValidURL(url) {
        try {
            new URL(url);
            return true;
        } catch {
            return false;
        }
    },
    
    /**
     * Validate phone number (basic)
     */
    isValidPhone(phone) {
        const regex = /^[\+]?[1-9][\d]{0,15}$/;
        return regex.test(phone.replace(/[\s\-\(\)]/g, ''));
    },
    
    /**
     * Validate password strength
     */
    validatePassword(password) {
        const errors = [];
        
        if (password.length < 8) {
            errors.push('Password must be at least 8 characters long');
        }
        
        if (!/[A-Z]/.test(password)) {
            errors.push('Password must contain at least one uppercase letter');
        }
        
        if (!/[a-z]/.test(password)) {
            errors.push('Password must contain at least one lowercase letter');
        }
        
        if (!/\d/.test(password)) {
            errors.push('Password must contain at least one number');
        }
        
        if (!/[!@#$%^&*]/.test(password)) {
            errors.push('Password must contain at least one special character (!@#$%^&*)');
        }
        
        return {
            isValid: errors.length === 0,
            errors: errors
        };
    },
    
    /**
     * Validate form data
     */
    validateFormData(formData, rules) {
        const errors = {};
        
        Object.keys(rules).forEach(field => {
            const value = formData[field];
            const fieldRules = rules[field];
            
            if (fieldRules.required && !value) {
                errors[field] = fieldRules.requiredMessage || 'This field is required';
                return;
            }
            
            if (value) {
                if (fieldRules.email && !this.isValidEmail(value)) {
                    errors[field] = 'Please enter a valid email address';
                } else if (fieldRules.minLength && value.length < fieldRules.minLength) {
                    errors[field] = `Minimum length is ${fieldRules.minLength} characters`;
                } else if (fieldRules.maxLength && value.length > fieldRules.maxLength) {
                    errors[field] = `Maximum length is ${fieldRules.maxLength} characters`;
                } else if (fieldRules.pattern && !fieldRules.pattern.test(value)) {
                    errors[field] = fieldRules.patternMessage || 'Invalid format';
                } else if (fieldRules.match && value !== formData[fieldRules.match]) {
                    errors[field] = 'Values do not match';
                }
            }
        });
        
        return {
            isValid: Object.keys(errors).length === 0,
            errors: errors
        };
    },
    
    // =========================================================================
    // Browser Storage Utilities
    // =========================================================================
    
    /**
     * Set item in localStorage with expiration
     */
    setStorage(key, value, ttl = 3600) { // 1 hour default
        const item = {
            value: value,
            expires: Date.now() + (ttl * 1000)
        };
        localStorage.setItem(key, JSON.stringify(item));
    },
    
    /**
     * Get item from localStorage
     */
    getStorage(key) {
        const itemStr = localStorage.getItem(key);
        if (!itemStr) return null;
        
        const item = JSON.parse(itemStr);
        if (Date.now() > item.expires) {
            localStorage.removeItem(key);
            return null;
        }
        
        return item.value;
    },
    
    /**
     * Remove item from localStorage
     */
    removeStorage(key) {
        localStorage.removeItem(key);
    },
    
    /**
     * Clear all localStorage
     */
    clearStorage() {
        localStorage.clear();
    },
    
    /**
     * Check if storage is available
     */
    isStorageAvailable(type = 'localStorage') {
        let storage;
        try {
            storage = window[type];
            const x = '__storage_test__';
            storage.setItem(x, x);
            storage.removeItem(x);
            return true;
        } catch (e) {
            return e instanceof DOMException && (
                e.code === 22 ||
                e.code === 1014 ||
                e.name === 'QuotaExceededError' ||
                e.name === 'NS_ERROR_DOM_QUOTA_REACHED') &&
                storage && storage.length !== 0;
        }
    },
    
    // =========================================================================
    // Browser Utilities
    // =========================================================================
    
    /**
     * Get browser information
     */
    getBrowserInfo() {
        const ua = navigator.userAgent;
        let browser = 'Unknown';
        let version = '';
        
        if (ua.indexOf('Firefox') > -1) {
            browser = 'Firefox';
            version = ua.match(/Firefox\/([0-9.]+)/)[1];
        } else if (ua.indexOf('Chrome') > -1) {
            browser = 'Chrome';
            version = ua.match(/Chrome\/([0-9.]+)/)[1];
        } else if (ua.indexOf('Safari') > -1) {
            browser = 'Safari';
            version = ua.match(/Version\/([0-9.]+)/)[1];
        } else if (ua.indexOf('Edge') > -1) {
            browser = 'Edge';
            version = ua.match(/Edge\/([0-9.]+)/)[1];
        } else if (ua.indexOf('MSIE') > -1 || ua.indexOf('Trident/') > -1) {
            browser = 'IE';
            version = ua.match(/(MSIE |rv:)([0-9.]+)/)[2];
        }
        
        return {
            browser: browser,
            version: version,
            userAgent: ua,
            isMobile: /Mobi|Android/i.test(ua),
            isTablet: /Tablet|iPad/i.test(ua),
            isDesktop: !/Mobi|Android|Tablet|iPad/i.test(ua)
        };
    },
    
    /**
     * Get current URL parameters
     */
    getURLParams() {
        const params = new URLSearchParams(window.location.search);
        const result = {};
        
        for (const [key, value] of params) {
            result[key] = value;
        }
        
        return result;
    },
    
    /**
     * Update URL parameters without reload
     */
    updateURLParams(params) {
        const url = new URL(window.location);
        
        Object.entries(params).forEach(([key, value]) => {
            if (value === null || value === undefined) {
                url.searchParams.delete(key);
            } else {
                url.searchParams.set(key, value);
            }
        });
        
        window.history.pushState({}, '', url);
    },
    
    /**
     * Copy text to clipboard
     */
    async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            return true;
        } catch (error) {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = text;
            textArea.style.position = 'fixed';
            textArea.style.left = '-999999px';
            textArea.style.top = '-999999px';
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();
            
            try {
                document.execCommand('copy');
                document.body.removeChild(textArea);
                return true;
            } catch (err) {
                document.body.removeChild(textArea);
                return false;
            }
        }
    },
    
    /**
     * Download file
     */
    downloadFile(content, filename, type = 'text/plain') {
        const blob = new Blob([content], { type });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        
        a.href = url;
        a.download = filename;
        a.style.display = 'none';
        
        document.body.appendChild(a);
        a.click();
        
        setTimeout(() => {
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }, 100);
    },
    
    /**
     * Read file as text
     */
    readFileAsText(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result);
            reader.onerror = reject;
            reader.readAsText(file);
        });
    },
    
    /**
     * Read file as data URL
     */
    readFileAsDataURL(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result);
            reader.onerror = reject;
            reader.readAsDataURL(file);
        });
    },
    
    // =========================================================================
    // Medical Calculation Utilities
    // =========================================================================
    
    /**
     * Calculate BMI
     */
    calculateBMI(weight, height) {
        // height in cm, weight in kg
        const heightMeters = height / 100;
        return weight / (heightMeters * heightMeters);
    },
    
    /**
     * Get BMI category
     */
    getBMICategory(bmi) {
        if (bmi < 18.5) return { category: 'Underweight', risk: 'Low' };
        if (bmi < 25) return { category: 'Normal', risk: 'Low' };
        if (bmi < 30) return { category: 'Overweight', risk: 'Moderate' };
        if (bmi < 35) return { category: 'Obese I', risk: 'High' };
        if (bmi < 40) return { category: 'Obese II', risk: 'Very High' };
        return { category: 'Obese III', risk: 'Extremely High' };
    },
    
    /**
     * Calculate blood pressure category
     */
    getBloodPressureCategory(systolic, diastolic) {
        if (systolic < 120 && diastolic < 80) return 'Normal';
        if (systolic < 130 && diastolic < 80) return 'Elevated';
        if (systolic < 140 || diastolic < 90) return 'Hypertension Stage 1';
        if (systolic >= 140 || diastolic >= 90) return 'Hypertension Stage 2';
        if (systolic > 180 || diastolic > 120) return 'Hypertensive Crisis';
        return 'Unknown';
    },
    
    /**
     * Calculate heart rate category
     */
    getHeartRateCategory(heartRate, age) {
        const maxHeartRate = 220 - age;
        const targetZone = maxHeartRate * 0.5; // 50% of max
        
        if (heartRate < 60) return 'Bradycardia';
        if (heartRate < targetZone) return 'Below Target';
        if (heartRate <= maxHeartRate * 0.85) return 'Target Zone';
        return 'Above Target';
    },
    
    /**
     * Calculate eGFR (simplified)
     */
    calculateEGFR(creatinine, age, gender, race = 'non-black') {
        // CKD-EPI formula (simplified)
        let k = gender === 'female' ? 0.7 : 0.9;
        let a = gender === 'female' ? -0.329 : -0.411;
        
        const egfr = 141 * Math.min(creatinine/k, 1) ** a * 
                    Math.max(creatinine/k, 1) ** -1.209 * 
                    0.993 ** age;
        
        // Adjust for race
        if (race === 'black') {
            return egfr * 1.159;
        }
        
        return egfr;
    },
    
    /**
     * Get eGFR category
     */
    getEGFRCategory(egfr) {
        if (egfr >= 90) return { stage: 'G1', description: 'Normal' };
        if (egfr >= 60) return { stage: 'G2', description: 'Mild decrease' };
        if (egfr >= 45) return { stage: 'G3a', description: 'Mild to moderate' };
        if (egfr >= 30) return { stage: 'G3b', description: 'Moderate to severe' };
        if (egfr >= 15) return { stage: 'G4', description: 'Severe' };
        return { stage: 'G5', description: 'Kidney failure' };
    },
    
    /**
     * Calculate diabetes risk score
     */
    calculateDiabetesRisk(age, bmi, familyHistory, hypertension, physicalActivity) {
        let score = 0;
        
        // Age
        if (age >= 45) score += 1;
        if (age >= 65) score += 1;
        
        // BMI
        if (bmi >= 25) score += 1;
        if (bmi >= 30) score += 1;
        
        // Family history
        if (familyHistory) score += 1;
        
        // Hypertension
        if (hypertension) score += 1;
        
        // Physical activity
        if (!physicalActivity) score += 1;
        
        return {
            score: score,
            risk: score <= 2 ? 'Low' : score <= 4 ? 'Moderate' : 'High'
        };
    },
    
    // =========================================================================
    // Chart & Visualization Utilities
    // =========================================================================
    
    /**
     * Generate random color
     */
    generateColor(alpha = 1) {
        const r = Math.floor(Math.random() * 256);
        const g = Math.floor(Math.random() * 256);
        const b = Math.floor(Math.random() * 256);
        return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    },
    
    /**
     * Generate color palette
     */
    generateColorPalette(count) {
        const colors = [];
        const hueStep = 360 / count;
        
        for (let i = 0; i < count; i++) {
            const hue = i * hueStep;
            colors.push(`hsl(${hue}, 70%, 60%)`);
        }
        
        return colors;
    },
    
    /**
     * Format chart data
     */
    formatChartData(data, labels, datasets) {
        return {
            labels: labels,
            datasets: datasets.map((dataset, index) => ({
                label: dataset.label,
                data: dataset.data,
                backgroundColor: dataset.backgroundColor || this.generateColor(0.2),
                borderColor: dataset.borderColor || this.generateColor(1),
                borderWidth: dataset.borderWidth || 2,
                fill: dataset.fill || true,
                tension: dataset.tension || 0.4
            }))
        };
    },
    
    /**
     * Create gradient for charts
     */
    createChartGradient(ctx, color1, color2, direction = 'vertical') {
        const gradient = direction === 'vertical' 
            ? ctx.createLinearGradient(0, 0, 0, 400)
            : ctx.createLinearGradient(0, 0, 400, 0);
        
        gradient.addColorStop(0, color1);
        gradient.addColorStop(1, color2);
        
        return gradient;
    },
    
    // =========================================================================
    // Event Utilities
    // =========================================================================
    
    /**
     * Add event listener with cleanup
     */
    addEventListener(element, event, handler, options = {}) {
        element.addEventListener(event, handler, options);
        
        // Return cleanup function
        return () => {
            element.removeEventListener(event, handler, options);
        };
    },
    
    /**
     * Trigger custom event
     */
    triggerEvent(element, eventName, detail = {}) {
        const event = new CustomEvent(eventName, {
            detail: detail,
            bubbles: true,
            cancelable: true
        });
        element.dispatchEvent(event);
    },
    
    /**
     * Prevent default and stop propagation
     */
    stopEvent(event) {
        event.preventDefault();
        event.stopPropagation();
    },
    
    // =========================================================================
    // Performance Utilities
    // =========================================================================
    
    /**
     * Measure function execution time
     */
    measureTime(func, ...args) {
        const start = performance.now();
        const result = func(...args);
        const end = performance.now();
        
        return {
            result: result,
            time: end - start
        };
    },
    
    /**
     * Throttle based on frame rate
     */
    throttleAnimationFrame(func) {
        let ticking = false;
        return function(...args) {
            if (!ticking) {
                ticking = true;
                requestAnimationFrame(() => {
                    func(...args);
                    ticking = false;
                });
            }
        };
    },
    
    /**
     * Check if page is in background
     */
    isPageInBackground() {
        return document.hidden || document.visibilityState === 'hidden';
    },
    
    // =========================================================================
    // Security Utilities
    // =========================================================================
    
    /**
     * Sanitize user input
     */
    sanitizeInput(input) {
        if (typeof input !== 'string') return input;
        
        // Remove script tags
        input = input.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '');
        
        // Remove dangerous attributes
        input = input.replace(/\son\w+\s*=\s*("[^"]*"|'[^']*'|[^"'>\s]+)/gi, '');
        
        // Remove dangerous tags
        const dangerousTags = ['iframe', 'object', 'embed', 'base', 'meta', 'link'];
        dangerousTags.forEach(tag => {
            const regex = new RegExp(`<${tag}\\b[^>]*>.*?</${tag}>|<${tag}\\b[^>]*>`, 'gi');
            input = input.replace(regex, '');
        });
        
        return input.trim();
    },
    
    /**
     * Hash string (simple implementation)
     */
    hashString(str) {
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            const char = str.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash; // Convert to 32bit integer
        }
        return Math.abs(hash).toString(16);
    },
    
    /**
     * Generate CSRF token
     */
    generateCSRFToken() {
        return this.generateUUID();
    }
};

// Make utilities available globally
window.Utils = MediPredictUtils;

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MediPredictUtils;
}