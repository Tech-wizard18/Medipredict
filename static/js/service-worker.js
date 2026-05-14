// static/js/service-worker.js

/**
 * MediPredict - Service Worker
 * Enables offline functionality and improves performance
 */

const CACHE_NAME = 'medipredict-v1.0.0';
const STATIC_CACHE_NAME = 'medipredict-static-v1.0.0';

// URLs to cache on install
const STATIC_URLS = [
    '/',
    '/static/css/base.css',
    '/static/css/components.css',
    '/static/css/layout.css',
    '/static/css/dashboard.css',
    '/static/css/forms.css',
    '/static/css/animations.css',
    '/static/js/main.js',
    '/static/js/charts.js',
    '/static/js/predictions.js',
    '/static/js/api.js',
    '/static/js/utils.js',
    '/static/images/logo.png',
    '/static/images/favicon.ico',
    '/manifest.json'
];

// API endpoints to cache
const API_CACHE_URLS = [
    '/api/v1/health/',
    '/api/v1/user/profile/',
    '/api/v1/user/predictions/',
    '/api/v1/notifications/'
];

// Install event - cache static assets
self.addEventListener('install', event => {
    console.log('[Service Worker] Installing...');
    
    event.waitUntil(
        Promise.all([
            // Cache static assets
            caches.open(STATIC_CACHE_NAME).then(cache => {
                console.log('[Service Worker] Caching static assets');
                return cache.addAll(STATIC_URLS);
            }),
            
            // Skip waiting to activate immediately
            self.skipWaiting()
        ])
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
    console.log('[Service Worker] Activating...');
    
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cacheName => {
                    // Delete old caches
                    if (cacheName !== CACHE_NAME && cacheName !== STATIC_CACHE_NAME) {
                        console.log('[Service Worker] Deleting old cache:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        }).then(() => {
            // Claim clients to control all open tabs
            return self.clients.claim();
        })
    );
});

// Fetch event - handle network requests
self.addEventListener('fetch', event => {
    // Skip non-GET requests
    if (event.request.method !== 'GET') return;
    
    // Skip browser extensions
    if (event.request.url.startsWith('chrome-extension://')) return;
    
    // Handle API requests differently
    if (event.request.url.includes('/api/')) {
        event.respondWith(handleApiRequest(event));
        return;
    }
    
    // Handle static assets
    event.respondWith(
        caches.match(event.request).then(response => {
            if (response) {
                // Return cached response
                return response;
            }
            
            // Fetch from network
            return fetch(event.request).then(response => {
                // Don't cache non-successful responses
                if (!response || response.status !== 200 || response.type !== 'basic') {
                    return response;
                }
                
                // Cache the response
                const responseToCache = response.clone();
                caches.open(STATIC_CACHE_NAME).then(cache => {
                    cache.put(event.request, responseToCache);
                });
                
                return response;
            }).catch(() => {
                // If offline and not cached, show offline page
                if (event.request.mode === 'navigate') {
                    return caches.match('/offline/');
                }
                return new Response('Network error', {
                    status: 408,
                    headers: { 'Content-Type': 'text/plain' }
                });
            });
        })
    );
});

// Handle API requests with caching strategy
async function handleApiRequest(event) {
    const request = event.request;
    const cache = await caches.open(CACHE_NAME);
    
    try {
        // Try network first
        const networkResponse = await fetch(request);
        
        // Cache successful responses
        if (networkResponse.ok) {
            // Clone response for caching
            const responseToCache = networkResponse.clone();
            
            // Only cache GET requests and specific endpoints
            if (request.method === 'GET' && shouldCacheAPI(request.url)) {
                cache.put(request, responseToCache);
            }
        }
        
        return networkResponse;
        
    } catch (error) {
        console.log('[Service Worker] Network failed, trying cache:', request.url);
        
        // Try cache if network fails
        const cachedResponse = await cache.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        
        // If no cache and offline, return offline response
        return new Response(
            JSON.stringify({
                error: 'You are offline',
                message: 'Please check your internet connection'
            }),
            {
                status: 503,
                headers: { 'Content-Type': 'application/json' }
            }
        );
    }
}

// Check if API endpoint should be cached
function shouldCacheAPI(url) {
    return API_CACHE_URLS.some(apiUrl => url.includes(apiUrl));
}

// Background sync for failed requests
self.addEventListener('sync', event => {
    console.log('[Service Worker] Background sync:', event.tag);
    
    if (event.tag === 'sync-predictions') {
        event.waitUntil(syncPredictions());
    }
});

// Sync predictions when back online
async function syncPredictions() {
    // Get pending predictions from IndexedDB
    const pendingPredictions = await getPendingPredictions();
    
    for (const prediction of pendingPredictions) {
        try {
            await sendPrediction(prediction);
            await removePendingPrediction(prediction.id);
        } catch (error) {
            console.error('[Service Worker] Failed to sync prediction:', error);
        }
    }
}

// IndexedDB for offline data storage
const DB_NAME = 'MediPredictDB';
const DB_VERSION = 1;
const STORE_NAME = 'pending_predictions';

// Open database
function openDatabase() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open(DB_NAME, DB_VERSION);
        
        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve(request.result);
        
        request.onupgradeneeded = event => {
            const db = event.target.result;
            if (!db.objectStoreNames.contains(STORE_NAME)) {
                db.createObjectStore(STORE_NAME, { keyPath: 'id' });
            }
        };
    });
}

// Store prediction for offline sync
async function storePrediction(prediction) {
    const db = await openDatabase();
    const transaction = db.transaction([STORE_NAME], 'readwrite');
    const store = transaction.objectStore(STORE_NAME);
    
    return new Promise((resolve, reject) => {
        const request = store.add(prediction);
        request.onsuccess = () => resolve();
        request.onerror = () => reject(request.error);
    });
}

// Get pending predictions
async function getPendingPredictions() {
    const db = await openDatabase();
    const transaction = db.transaction([STORE_NAME], 'readonly');
    const store = transaction.objectStore(STORE_NAME);
    
    return new Promise((resolve, reject) => {
        const request = store.getAll();
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
    });
}

// Remove pending prediction
async function removePendingPrediction(id) {
    const db = await openDatabase();
    const transaction = db.transaction([STORE_NAME], 'readwrite');
    const store = transaction.objectStore(STORE_NAME);
    
    return new Promise((resolve, reject) => {
        const request = store.delete(id);
        request.onsuccess = () => resolve();
        request.onerror = () => reject(request.error);
    });
}

// Send prediction to server
async function sendPrediction(prediction) {
    const response = await fetch('/api/v1/predict/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': prediction.csrfToken
        },
        body: JSON.stringify(prediction.data)
    });
    
    if (!response.ok) {
        throw new Error('Failed to send prediction');
    }
    
    return response.json();
}

// Push notifications
self.addEventListener('push', event => {
    console.log('[Service Worker] Push received:', event);
    
    const data = event.data ? event.data.json() : {};
    const title = data.title || 'MediPredict';
    const options = {
        body: data.body || 'You have a new notification',
        icon: '/static/images/logo.png',
        badge: '/static/images/badge.png',
        vibrate: [200, 100, 200],
        data: {
            url: data.url || '/'
        },
        actions: [
            {
                action: 'view',
                title: 'View'
            },
            {
                action: 'dismiss',
                title: 'Dismiss'
            }
        ]
    };
    
    event.waitUntil(
        self.registration.showNotification(title, options)
    );
});

// Notification click handler
self.addEventListener('notificationclick', event => {
    console.log('[Service Worker] Notification click:', event);
    
    event.notification.close();
    
    if (event.action === 'dismiss') {
        return;
    }
    
    // Default action is 'view'
    event.waitUntil(
        clients.matchAll({
            type: 'window',
            includeUncontrolled: true
        }).then(clientList => {
            // Check if there's already a window open
            for (const client of clientList) {
                if (client.url === event.notification.data.url && 'focus' in client) {
                    return client.focus();
                }
            }
            
            // Open new window
            if (clients.openWindow) {
                return clients.openWindow(event.notification.data.url);
            }
        })
    );
});

// Message handler for communication with clients
self.addEventListener('message', event => {
    console.log('[Service Worker] Message received:', event.data);
    
    if (event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
    
    if (event.data.type === 'CACHE_ASSETS') {
        cacheAdditionalAssets(event.data.urls);
    }
});

// Cache additional assets on demand
async function cacheAdditionalAssets(urls) {
    const cache = await caches.open(STATIC_CACHE_NAME);
    return cache.addAll(urls);
}

// Periodic background sync (if supported)
if ('periodicSync' in self.registration) {
    self.addEventListener('periodicsync', event => {
        if (event.tag === 'update-cache') {
            console.log('[Service Worker] Periodic sync for cache update');
            event.waitUntil(updateCache());
        }
    });
}

// Update cache in background
async function updateCache() {
    const cache = await caches.open(STATIC_CACHE_NAME);
    
    for (const url of STATIC_URLS) {
        try {
            const response = await fetch(url);
            if (response.ok) {
                await cache.put(url, response);
            }
        } catch (error) {
            console.log('[Service Worker] Failed to update cache for:', url, error);
        }
    }
}

// Precache prediction forms
async function precachePredictionForms() {
    const forms = [
        '/predict/diabetes/',
        '/predict/heart/',
        '/predict/kidney/',
        '/predict/parkinson/',
        '/predict/breast-cancer/',
        '/predict/liver/'
    ];
    
    const cache = await caches.open(STATIC_CACHE_NAME);
    const requests = forms.map(form => new Request(form));
    
    return Promise.all(
        requests.map(request => 
            fetch(request).then(response => {
                if (response.ok) {
                    return cache.put(request, response);
                }
            }).catch(console.error)
        )
    );
}

// Health check
self.addEventListener('message', event => {
    if (event.data.type === 'HEALTH_CHECK') {
        event.ports[0].postMessage({
            status: 'healthy',
            cacheSize: 'unknown'
        });
    }
});
