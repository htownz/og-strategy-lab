// Dashboard.js - Functionality for the OG Signal Bot Dashboard

// Socket.IO client
let socket;

document.addEventListener('DOMContentLoaded', function() {
    // Initialize system status check
    checkSystemStatus();
    
    // Initialize auto-trade toggle
    initAutoTradeToggle();
    
    // Initialize TradingView widget if present
    initTradingViewWidget();
    
    // Initialize Socket.IO connection
    initSocketConnection();
    
    // Initialize charts if present on page
    initCharts();
    
    // Set up refresh interval for data
    setInterval(refreshData, 60000); // Refresh data every minute
    
    // Set up page-specific initializations
    setupPageSpecificActions();
});

// System status check
function checkSystemStatus() {
    fetch('/api/system-status')
        .then(response => response.json())
        .then(data => {
            updateStatusIndicators(data);
        })
        .catch(error => {
            console.error('Error fetching system status:', error);
        });
}

// Update status indicators based on API response
function updateStatusIndicators(data) {
    const indicators = {
        'alpaca-status': data.alpaca_api,
        'strategy-status': data.strategy,
    };
    
    for (const [id, status] of Object.entries(indicators)) {
        const indicator = document.getElementById(id);
        if (indicator) {
            // Remove all existing status classes
            indicator.classList.remove('status-green', 'status-red', 'status-yellow', 'status-gray');
            
            // Add appropriate status class
            if (status === true) {
                indicator.classList.add('status-green');
            } else if (status === false) {
                indicator.classList.add('status-red');
            } else {
                indicator.classList.add('status-gray');
            }
        }
    }
    
    // Update error count if element exists
    const errorCountElement = document.getElementById('error-count');
    if (errorCountElement && data.error_count !== undefined) {
        errorCountElement.textContent = data.error_count;
        
        // Highlight if errors exist
        if (data.error_count > 0) {
            errorCountElement.classList.add('text-danger');
            errorCountElement.classList.remove('text-muted');
        } else {
            errorCountElement.classList.remove('text-danger');
            errorCountElement.classList.add('text-muted');
        }
    }
}

// Initialize auto-trade toggle button
function initAutoTradeToggle() {
    const autoTradeToggle = document.getElementById('auto-trade-toggle');
    if (autoTradeToggle) {
        autoTradeToggle.addEventListener('change', function() {
            toggleAutoTrading(this.checked);
        });
    }
}

// Toggle auto-trading via API
function toggleAutoTrading(enabled) {
    fetch('/api/toggle-trading', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ enabled: enabled })
    })
    .then(response => response.json())
    .then(data => {
        if (!data.success) {
            // If failed, revert the toggle
            document.getElementById('auto-trade-toggle').checked = !enabled;
            alert('Failed to toggle auto-trading. Please try again.');
        }
    })
    .catch(error => {
        console.error('Error toggling auto-trading:', error);
        // Revert the toggle on error
        document.getElementById('auto-trade-toggle').checked = !enabled;
        alert('Error toggling auto-trading. Please try again.');
    });
}

// Initialize charts using Chart.js
function initCharts() {
    // Signal history chart
    const signalChartElement = document.getElementById('signal-history-chart');
    if (signalChartElement) {
        // Data would typically come from an API
        const ctx = signalChartElement.getContext('2d');
        // Initialize with Chart.js configuration from chart-config.js
        if (typeof initSignalHistoryChart === 'function') {
            initSignalHistoryChart(ctx);
        }
    }
    
    // P&L chart
    const pnlChartElement = document.getElementById('pnl-chart');
    if (pnlChartElement) {
        const ctx = pnlChartElement.getContext('2d');
        // Initialize with Chart.js configuration from chart-config.js
        if (typeof initPnLChart === 'function') {
            initPnLChart(ctx);
        }
    }
}

// Refresh data on the dashboard
function refreshData() {
    // Refresh system status
    checkSystemStatus();
    
    // Refresh other dynamic data elements if needed
    const dataElements = document.querySelectorAll('[data-refresh="true"]');
    dataElements.forEach(element => {
        const refreshUrl = element.dataset.refreshUrl;
        if (refreshUrl) {
            fetch(refreshUrl)
                .then(response => response.json())
                .then(data => {
                    updateElement(element, data);
                })
                .catch(error => {
                    console.error(`Error refreshing element ${element.id}:`, error);
                });
        }
    });
}

// Update an element with refreshed data
function updateElement(element, data) {
    // This would depend on the type of element and data expected
    // For simplicity, we'll just handle text content updates
    if (element.dataset.refreshType === 'text') {
        element.textContent = data.value;
    } else if (element.dataset.refreshType === 'html') {
        element.innerHTML = data.value;
    }
    // Add more types as needed
}

// Setup page-specific actions
function setupPageSpecificActions() {
    // Test message button for settings page
    const testMessageBtn = document.getElementById('test-message-btn');
    if (testMessageBtn) {
        testMessageBtn.addEventListener('click', function() {
            sendTestMessage();
        });
    }
}

// Send test Telegram message
function sendTestMessage() {
    fetch('/api/send-test-message', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Test message sent successfully!');
        } else {
            alert('Failed to send test message: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error sending test message:', error);
        alert('Error sending test message. Please check the logs.');
    });
}

// Initialize TradingView widget
function initTradingViewWidget() {
    const container = document.getElementById('tradingview-widget-container');
    if (!container) return;
    
    let symbol = 'SPY';
    const symbolSelector = document.getElementById('tradingview-symbol');
    if (symbolSelector && symbolSelector.value) {
        symbol = symbolSelector.value;
    }
    
    new TradingView.widget({
        "width": "100%",
        "height": "100%",
        "symbol": symbol,
        "interval": "15",
        "timezone": "Etc/UTC",
        "theme": "dark",
        "style": "1",
        "locale": "en",
        "toolbar_bg": "#f1f3f6",
        "enable_publishing": false,
        "hide_side_toolbar": false,
        "allow_symbol_change": true,
        "container_id": "tradingview-widget-container",
        "studies": [
            "RSI@tv-basicstudies",
            "MAExp@tv-basicstudies",
            "VWAP@tv-basicstudies"
        ]
    });
    
    // Set up symbol change button
    const changeSymbolBtn = document.getElementById('change-symbol-btn');
    if (changeSymbolBtn && symbolSelector) {
        changeSymbolBtn.addEventListener('click', function() {
            // Reinitialize widget with new symbol
            container.innerHTML = '';
            initTradingViewWidget();
        });
    }
}

// Initialize Socket.IO connection
function initSocketConnection() {
    // Connect to Socket.IO server
    socket = io();
    
    // Connection events
    socket.on('connect', function() {
        console.log('Connected to Socket.IO server');
        
        // Show live indicator if it exists
        const liveIndicator = document.getElementById('live-signal-indicator');
        if (liveIndicator) {
            liveIndicator.style.display = 'inline-block';
        }
        
        // Request initial data
        socket.emit('load_signals');
        socket.emit('load_trades');
    });
    
    socket.on('disconnect', function() {
        console.log('Disconnected from Socket.IO server');
        
        // Hide live indicator
        const liveIndicator = document.getElementById('live-signal-indicator');
        if (liveIndicator) {
            liveIndicator.style.display = 'none';
        }
    });
    
    // Signal events
    socket.on('signal_history', function(data) {
        console.log('Received signal history:', data);
        updateSignalTable(data.signals);
    });
    
    socket.on('new_signal', function(data) {
        console.log('Received new signal:', data);
        
        // Flash notification
        showNotification(`New Signal: ${data.symbol} ${data.direction}`);
        
        // Add to signals table if exists
        prependToTable('recent-signals-table', createSignalRow(data));
    });
    
    // Trade events
    socket.on('trade_history', function(data) {
        console.log('Received trade history:', data);
        updateTradeTable(data.trades);
    });
    
    socket.on('new_trade', function(data) {
        console.log('Received new trade:', data);
        
        // Flash notification
        showNotification(`New Trade: ${data.symbol} ${data.direction}`);
        
        // Add to trades table if exists
        prependToTable('recent-trades-table', createTradeRow(data));
    });
    
    // System status events
    socket.on('system_status', function(data) {
        console.log('Received system status update:', data);
        updateStatusIndicators(data);
    });
    
    // Error handling
    socket.on('error', function(data) {
        console.error('Socket.IO error:', data);
    });
}

// Show a notification popup
function showNotification(message) {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = 'toast align-items-center text-white bg-primary border-0 show';
    notification.setAttribute('role', 'alert');
    notification.setAttribute('aria-live', 'assertive');
    notification.setAttribute('aria-atomic', 'true');
    notification.style.position = 'fixed';
    notification.style.top = '20px';
    notification.style.right = '20px';
    notification.style.zIndex = '9999';
    
    notification.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    // Add to document
    document.body.appendChild(notification);
    
    // Auto remove after 3 seconds
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

// Update signals table with new data
function updateSignalTable(signals) {
    const table = document.querySelector('table:has(th:contains("Symbol")):has(th:contains("Direction")):has(th:contains("Confidence"))');
    if (!table) return;
    
    const tbody = table.querySelector('tbody');
    if (!tbody) return;
    
    // Clear existing rows
    tbody.innerHTML = '';
    
    // Add new rows
    signals.forEach(signal => {
        tbody.appendChild(createSignalRow(signal));
    });
}

// Create a table row for a signal
function createSignalRow(signal) {
    const row = document.createElement('tr');
    
    // Format timestamp
    const timestamp = new Date(signal.timestamp);
    const formattedTime = timestamp.toLocaleString();
    
    // Direction class
    const directionClass = signal.direction === 'UP' ? 'text-success' : 'text-danger';
    
    row.innerHTML = `
        <td>${formattedTime}</td>
        <td>${signal.symbol}</td>
        <td class="${directionClass}">${signal.direction}</td>
        <td>
            <div class="progress confidence-meter">
                <div class="progress-bar bg-${signal.direction === 'UP' ? 'success' : 'danger'}" 
                     role="progressbar" 
                     style="width: ${signal.confidence * 100}%" 
                     aria-valuenow="${signal.confidence * 100}" 
                     aria-valuemin="0" 
                     aria-valuemax="100">
                </div>
            </div>
            ${signal.confidence.toFixed(2)}
        </td>
        <td>$${signal.price_at_signal.toFixed(2)}</td>
    `;
    
    return row;
}

// Update trades table with new data
function updateTradeTable(trades) {
    const table = document.querySelector('table:has(th:contains("Symbol")):has(th:contains("Action")):has(th:contains("Quantity"))');
    if (!table) return;
    
    const tbody = table.querySelector('tbody');
    if (!tbody) return;
    
    // Clear existing rows
    tbody.innerHTML = '';
    
    // Add new rows
    trades.forEach(trade => {
        tbody.appendChild(createTradeRow(trade));
    });
}

// Create a table row for a trade
function createTradeRow(trade) {
    const row = document.createElement('tr');
    
    // Format timestamp
    const timestamp = new Date(trade.timestamp);
    const formattedTime = timestamp.toLocaleString();
    
    // Direction class
    const directionClass = trade.direction === 'BUY' ? 'text-success' : 'text-danger';
    
    // Status class
    let statusClass = 'secondary';
    if (trade.status === 'FILLED') statusClass = 'success';
    else if (trade.status === 'SUBMITTED') statusClass = 'warning';
    else if (trade.status === 'REJECTED') statusClass = 'danger';
    
    row.innerHTML = `
        <td>${formattedTime}</td>
        <td>${trade.symbol}</td>
        <td class="${directionClass}">${trade.direction}</td>
        <td>${trade.quantity}</td>
        <td>
            <span class="badge bg-${statusClass}">
                ${trade.status}
            </span>
        </td>
    `;
    
    return row;
}

// Prepend a row to a table
function prependToTable(tableId, row) {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    const tbody = table.querySelector('tbody');
    if (!tbody) return;
    
    // Add row at the beginning
    if (tbody.firstChild) {
        tbody.insertBefore(row, tbody.firstChild);
    } else {
        tbody.appendChild(row);
    }
    
    // Remove last row if too many
    const maxRows = 10;
    const rows = tbody.querySelectorAll('tr');
    if (rows.length > maxRows) {
        tbody.removeChild(rows[rows.length - 1]);
    }
}
