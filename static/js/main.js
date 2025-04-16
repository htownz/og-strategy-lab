/**
 * OG Signal Bot - Main JavaScript
 * Handles global functionality used across pages
 * Enhanced with robust connection handling and retry logic
 */

document.addEventListener('DOMContentLoaded', function() {
    // Fix for transport errors - clean up any stale connections first
    if (localStorage.getItem('socketio_transport_error')) {
        localStorage.removeItem('socketio_transport_error');
        console.log('Cleared previous transport error state');
    }
    
    // Initialize SocketIO connection with enhanced reconnection parameters
    const socket = io({
        reconnection: true,
        reconnectionAttempts: 15,
        reconnectionDelay: 1000,
        reconnectionDelayMax: 30000,
        timeout: 60000,
        autoConnect: true,
        forceNew: true, // Force new connection to avoid stale connections
        transports: ['websocket', 'polling'] // Try WebSocket first, fallback to polling
    });
    
    // Store socket in window for other scripts to access
    window.socketIO = socket;
    
    // Track reconnection attempts for UI feedback
    let reconnectAttempts = 0;
    const maxReconnectAttempts = 15;
    let connectionHealthInterval = null;
    
    // Create connection status indicator element
    const createConnectionStatusIndicator = function() {
        // Check if indicator already exists
        if (document.getElementById('connection-status-indicator')) {
            return;
        }
        
        const statusIndicator = document.createElement('div');
        statusIndicator.id = 'connection-status-indicator';
        statusIndicator.className = 'connection-status disconnected';
        statusIndicator.innerHTML = '<span class="connection-dot"></span><span class="connection-text">Disconnected</span>';
        statusIndicator.style.position = 'fixed';
        statusIndicator.style.bottom = '10px';
        statusIndicator.style.right = '10px';
        statusIndicator.style.zIndex = '9999';
        statusIndicator.style.padding = '6px 12px';
        statusIndicator.style.borderRadius = '4px';
        statusIndicator.style.fontSize = '12px';
        statusIndicator.style.display = 'flex';
        statusIndicator.style.alignItems = 'center';
        statusIndicator.style.background = 'rgba(33, 37, 41, 0.8)';
        statusIndicator.style.color = '#fff';
        document.body.appendChild(statusIndicator);
        
        const styleElement = document.createElement('style');
        styleElement.textContent = `
            .connection-status.connected .connection-dot { background-color: #28a745; }
            .connection-status.connecting .connection-dot { background-color: #ffc107; }
            .connection-status.disconnected .connection-dot { background-color: #dc3545; }
            .connection-dot {
                display: inline-block;
                width: 8px;
                height: 8px;
                border-radius: 50%;
                margin-right: 6px;
            }
        `;
        document.head.appendChild(styleElement);
    };
    
    // Update connection status indicator
    const updateConnectionStatus = function(status, message) {
        const indicator = document.getElementById('connection-status-indicator');
        if (!indicator) return;
        
        indicator.className = `connection-status ${status}`;
        const textElement = indicator.querySelector('.connection-text');
        if (textElement) {
            textElement.textContent = message || status;
        }
    };
    
    // Start periodic connection health checks
    const startConnectionHealthChecks = function() {
        if (connectionHealthInterval) {
            clearInterval(connectionHealthInterval);
        }
        
        connectionHealthInterval = setInterval(function() {
            if (socket.connected) {
                // Send health check ping
                socket.emit('connection_health_check');
            }
        }, 30000); // Check every 30 seconds
    };
    
    // Socket connection events with enhanced handling
    socket.on('connect', function() {
        console.log('Connected to Socket.IO server');
        reconnectAttempts = 0;
        
        // Update connection status
        createConnectionStatusIndicator();
        updateConnectionStatus('connected', 'Connected');
        
        // Start health checks
        startConnectionHealthChecks();
        
        // Check system status after connecting
        if (typeof checkSystemStatus === 'function') {
            checkSystemStatus();
        }
        
        // Notify server of successful client connection
        socket.emit('client_ready', { 
            client_info: {
                userAgent: navigator.userAgent,
                timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                url: window.location.href
            }
        });
    });
    
    socket.on('connect_error', function(error) {
        console.log('Connection error:', error);
        reconnectAttempts++;
        
        // Update connection status
        createConnectionStatusIndicator();
        updateConnectionStatus('disconnected', `Connection error (attempt ${reconnectAttempts}/${maxReconnectAttempts})`);
        
        // Log error details to the server if possible
        if (socket.connected) {
            socket.emit('error', {
                type: 'connect_error',
                details: error.message || 'Unknown connection error'
            });
        }
    });
    
    socket.on('connect_timeout', function() {
        console.log('Connection timeout');
        
        // Update connection status
        createConnectionStatusIndicator();
        updateConnectionStatus('disconnected', 'Connection timeout');
    });
    
    socket.on('reconnect', function(attemptNumber) {
        console.log(`Reconnected after ${attemptNumber} attempts`);
        
        // Update connection status
        createConnectionStatusIndicator();
        updateConnectionStatus('connected', 'Reconnected');
        
        // Reload the page data if needed
        if (typeof reloadPageData === 'function') {
            reloadPageData();
        }
    });
    
    socket.on('reconnect_attempt', function(attemptNumber) {
        console.log(`Reconnection attempt: ${attemptNumber}`);
        
        // Update connection status
        createConnectionStatusIndicator();
        updateConnectionStatus('connecting', `Reconnecting (${attemptNumber}/${maxReconnectAttempts})`);
    });
    
    socket.on('reconnect_error', function(error) {
        console.log('Reconnection error:', error);
        
        // Update connection status
        createConnectionStatusIndicator();
        updateConnectionStatus('disconnected', 'Reconnection error');
    });
    
    socket.on('reconnect_failed', function() {
        console.log('Failed to reconnect after multiple attempts');
        
        // Update connection status with manual reconnect button
        createConnectionStatusIndicator();
        updateConnectionStatus('disconnected', 'Reconnection failed');
        
        const indicator = document.getElementById('connection-status-indicator');
        if (indicator) {
            // Add reconnect button
            const reconnectBtn = document.createElement('button');
            reconnectBtn.textContent = 'Reconnect';
            reconnectBtn.style.marginLeft = '8px';
            reconnectBtn.style.padding = '2px 6px';
            reconnectBtn.style.fontSize = '11px';
            reconnectBtn.style.border = 'none';
            reconnectBtn.style.borderRadius = '3px';
            reconnectBtn.style.background = '#6c757d';
            reconnectBtn.style.color = 'white';
            reconnectBtn.style.cursor = 'pointer';
            
            reconnectBtn.addEventListener('click', function() {
                // Try to reconnect manually
                socket.connect();
                updateConnectionStatus('connecting', 'Reconnecting...');
            });
            
            indicator.appendChild(reconnectBtn);
        }
        
        // Show browser notification if supported
        if ('Notification' in window) {
            if (Notification.permission === 'granted') {
                new Notification('Connection Lost', {
                    body: 'Connection to the server has been lost. Please refresh the page.',
                    icon: '/static/favicon.ico'
                });
            } else if (Notification.permission !== 'denied') {
                Notification.requestPermission();
            }
        }
    });
    
    socket.on('disconnect', function(reason) {
        console.log('Disconnected from Socket.IO server. Reason:', reason);
        
        // Update connection status
        createConnectionStatusIndicator();
        
        if (reason === 'io server disconnect') {
            // The server has forcefully disconnected the connection
            updateConnectionStatus('disconnected', 'Server disconnected');
            
            // Attempt to reconnect manually since server disconnect doesn't trigger auto reconnect
            setTimeout(function() {
                socket.connect();
            }, 5000);
        } else {
            updateConnectionStatus('disconnected', 'Disconnected');
        }
        
        // Clear health check interval
        if (connectionHealthInterval) {
            clearInterval(connectionHealthInterval);
            connectionHealthInterval = null;
        }
    });
    
    // Handle connection warnings (e.g., fallback to polling)
    socket.on('connection_warning', function(data) {
        console.warn('Connection warning:', data.message);
        
        // Show warning notification
        showConnectionWarning('Connection Warning', data.message);
    });
    
    /**
     * Show a connection warning notification
     */
    function showConnectionWarning(title, message) {
        // First try browser notifications
        if ('Notification' in window && Notification.permission === 'granted') {
            try {
                new Notification(title, {
                    body: message,
                    icon: '/static/favicon.ico'
                });
                return;
            } catch (e) {
                console.error('Failed to show browser notification:', e);
            }
        }
        
        // Fallback to toast notification if available
        if (typeof bootstrap !== 'undefined' && typeof bootstrap.Toast !== 'undefined') {
            // Create toast element
            const toastEl = document.createElement('div');
            toastEl.className = 'toast';
            toastEl.setAttribute('role', 'alert');
            toastEl.setAttribute('aria-live', 'assertive');
            toastEl.setAttribute('aria-atomic', 'true');
            toastEl.innerHTML = `
                <div class="toast-header bg-warning text-dark">
                    <strong class="me-auto">${title}</strong>
                    <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
                <div class="toast-body">${message}</div>
            `;
            
            // Add to document
            const toastContainer = document.getElementById('toast-container') || document.body;
            toastContainer.appendChild(toastEl);
            
            // Initialize and show
            const toast = new bootstrap.Toast(toastEl);
            toast.show();
            
            // Auto-remove after hiding
            toastEl.addEventListener('hidden.bs.toast', function() {
                toastEl.remove();
            });
        } else {
            // Basic alert as last resort
            console.warn(`${title}: ${message}`);
        }
    }
    
    // Handle server-sent connection status updates
    socket.on('connection_status', function(data) {
        console.log('Connection status update:', data);
        
        // Update connection quality indicator if provided
        if (data.connection_quality) {
            const indicator = document.getElementById('connection-status-indicator');
            if (indicator) {
                const textElement = indicator.querySelector('.connection-text');
                if (textElement) {
                    textElement.textContent = `Connected (${data.connection_quality})`;
                }
            }
        }
    });
    
    // Response to health check
    socket.on('connection_health_response', function(data) {
        console.log('Health check response:', data);
        // Could update UI with connection health metrics if needed
    });
    
    // Handle server ready response
    socket.on('server_ready', function(data) {
        console.log('Server ready response:', data);
        // Store transport error detection for troubleshooting
        if (data.server_status === 'healthy') {
            localStorage.removeItem('socketio_transport_error');
            // Update connection status with server info
            updateConnectionStatus('connected', `Connected (${data.server_version || '1.0'})`);
        }
    });
    
    // Listen for system status updates
    socket.on('system_status', function(data) {
        updateSystemStatus(data);
    });
    
    // Listen for signal updates
    socket.on('new_signal', function(data) {
        // Handle new signals
        if (typeof handleNewSignal === 'function') {
            handleNewSignal(data);
        }
        
        // Show notification if on a different page
        showSignalNotification(data);
    });
    
    // Listen for trade updates
    socket.on('trade_update', function(data) {
        if (typeof handleTradeUpdate === 'function') {
            handleTradeUpdate(data);
        }
    });
    
    // Listen for strategy matches
    socket.on('og_match', function(data) {
        if (typeof handleOGMatch === 'function') {
            handleOGMatch(data);
        }
    });
    
    // Get initial system status
    fetch('/api/system/status')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            if (data && typeof updateSystemStatus === 'function') {
                updateSystemStatus(data);
            }
        })
        .catch(error => {
            console.error('Error fetching system status:', error);
        });
    
    // Handle trading toggle button if present
    const toggleTradingBtn = document.getElementById('toggleTradingBtn');
    if (toggleTradingBtn) {
        toggleTradingBtn.addEventListener('click', function() {
            fetch('/api/system/toggle-trading', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                if (data && typeof updateSystemStatus === 'function') {
                    updateSystemStatus(data);
                }
            })
            .catch(error => {
                console.error('Error toggling trading:', error);
            });
        });
    }
    
    /**
     * Update the system status display
     */
    function updateSystemStatus(data) {
        const statusBar = document.getElementById('systemStatusBar');
        const indicator = document.getElementById('systemActiveIndicator');
        const message = document.getElementById('systemStatusMessage');
        const toggleBtn = document.getElementById('toggleTradingBtn');
        
        if (!statusBar || !indicator || !message) return;
        
        // Show status bar
        statusBar.classList.remove('d-none');
        
        // Update indicator and message
        if (data.trading_active) {
            indicator.className = 'badge bg-success me-2';
            indicator.textContent = 'Active';
            
            if (toggleBtn) {
                toggleBtn.className = 'btn btn-sm btn-outline-warning';
                toggleBtn.textContent = 'Pause Trading';
            }
        } else {
            indicator.className = 'badge bg-warning me-2';
            indicator.textContent = 'Paused';
            
            if (toggleBtn) {
                toggleBtn.className = 'btn btn-sm btn-outline-success';
                toggleBtn.textContent = 'Resume Trading';
            }
        }
        
        // Set status message
        if (data.message) {
            message.textContent = data.message;
        } else {
            message.textContent = data.trading_active ? 'System operational' : 'Trading paused';
        }
    }
    
    /**
     * Show browser notification for new signals
     */
    function showSignalNotification(data) {
        // Skip if notification permission not granted or data is invalid
        if (Notification.permission !== 'granted' || !data || !data.symbol || !data.direction) return;
        
        // Safely format price and confidence with fallbacks
        const price = data.price_at_signal ? `$${Number(data.price_at_signal).toFixed(2)}` : 'N/A';
        const confidence = data.confidence ? `${(Number(data.confidence) * 100).toFixed(1)}%` : 'N/A';
        
        const title = `New Signal: ${data.symbol} ${data.direction}`;
        const options = {
            body: `Price: ${price}\nConfidence: ${confidence}`,
            icon: '/static/img/favicon.png'
        };
        
        try {
            new Notification(title, options);
        } catch (error) {
            console.error('Error showing notification:', error);
        }
    }
    
    // Request notification permission if needed
    if ('Notification' in window && Notification.permission !== 'granted' && Notification.permission !== 'denied') {
        Notification.requestPermission();
    }
});