/**
 * Market Settings JavaScript
 * Handles interactions for the market settings page
 */

document.addEventListener('DOMContentLoaded', function() {
    // Toggle display of live trading warning when live trading mode is selected
    const liveTradingMode = document.getElementById('liveTradingMode');
    const paperTradingMode = document.getElementById('paperTradingMode');
    const liveTradingWarning = document.getElementById('liveTradingWarning');
    const tradingStatus = document.getElementById('tradingStatus');
    
    // Check if elements exist before adding event listeners
    if (liveTradingMode && paperTradingMode && liveTradingWarning && tradingStatus) {
        liveTradingMode.addEventListener('change', function() {
            if (this.checked) {
                liveTradingWarning.style.display = 'block';
                tradingStatus.className = 'badge bg-danger';
                tradingStatus.textContent = 'Live Trading';
            }
        });
        
        paperTradingMode.addEventListener('change', function() {
            if (this.checked) {
                liveTradingWarning.style.display = 'none';
                tradingStatus.className = 'badge bg-warning';
                tradingStatus.textContent = 'Paper Trading';
            }
        });
    } else {
        console.warn('Some trading mode elements are missing from the DOM');
    }
    
    // Circuit breaker toggle
    const enableCircuitBreaker = document.getElementById('enableCircuitBreaker');
    const circuitBreakerSettings = document.getElementById('circuitBreakerSettings');
    
    if (enableCircuitBreaker && circuitBreakerSettings) {
        enableCircuitBreaker.addEventListener('change', function() {
            circuitBreakerSettings.style.display = this.checked ? 'block' : 'none';
        });
    } else {
        console.warn('Circuit breaker elements are missing from the DOM');
    }
    
    // Form submission handlers
    const dataProviderForm = document.getElementById('dataProviderForm');
    if (dataProviderForm) {
        dataProviderForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const formData = {
            dataProvider: document.querySelector('input[name="dataProvider"]:checked').value,
            alpacaApiKey: document.getElementById('alpacaApiKey').value,
            alpacaApiSecret: document.getElementById('alpacaApiSecret').value,
            isPaperTrading: document.getElementById('isPaperTrading').checked,
            updateInterval: parseInt(document.getElementById('updateInterval').value),
            enableExtendedHours: document.getElementById('enableExtendedHours').checked
        };
        
        // Submit data to API endpoint
        fetch('/api/market/api-keys', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                alpaca_api_key: formData.alpacaApiKey,
                alpaca_secret_key: formData.alpacaApiSecret
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Also update settings
                return fetch('/api/settings/update', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        data_provider: formData.dataProvider,
                        update_interval_ms: formData.updateInterval,
                        extended_hours_enabled: formData.enableExtendedHours
                    })
                });
            } else {
                throw new Error(data.error || 'Failed to update API keys');
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showAlert('Data provider settings saved successfully!', 'success');
            } else {
                showAlert('Error saving settings: ' + data.error, 'danger');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('Failed to save settings. Please try again.', 'danger');
        });
    });
    } else {
        console.warn('Data provider form is missing from the DOM');
    }
    
    const tradingExecutionForm = document.getElementById('tradingExecutionForm');
    if (tradingExecutionForm) {
        tradingExecutionForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const formData = {
            tradingMode: document.querySelector('input[name="tradingMode"]:checked').value,
            defaultOrderType: document.getElementById('defaultOrderType').value,
            defaultTimeInForce: document.getElementById('defaultTimeInForce').value,
            enableCircuitBreaker: document.getElementById('enableCircuitBreaker').checked,
            maxConsecutiveLosses: parseInt(document.getElementById('maxConsecutiveLosses').value),
            maxDailyDrawdown: parseFloat(document.getElementById('maxDailyDrawdown').value)
        };
        
        // Update trading mode
        fetch('/api/market/trading-mode', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                paper_trading: formData.tradingMode === 'paper'
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Update circuit breaker
                return fetch('/api/market/circuit-breaker', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        enabled: formData.enableCircuitBreaker,
                        max_losses: formData.maxConsecutiveLosses,
                        max_drawdown: formData.maxDailyDrawdown
                    })
                });
            } else {
                throw new Error(data.error || 'Failed to update trading mode');
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Update default order settings
                return fetch('/api/settings/update', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        default_order_type: formData.defaultOrderType,
                        default_time_in_force: formData.defaultTimeInForce
                    })
                });
            } else {
                throw new Error(data.error || 'Failed to update circuit breaker');
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showAlert('Trading execution settings saved successfully!', 'success');
            } else {
                showAlert('Error saving settings: ' + data.error, 'danger');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('Failed to save settings. Please try again.', 'danger');
        });
    });
    } else {
        console.warn('Trading execution form is missing from the DOM');
    }
    
    // Watchlist save handler
    const saveWatchlist = document.getElementById('saveWatchlist');
    if (saveWatchlist) {
        saveWatchlist.addEventListener('click', function() {
        const watchlistSymbols = document.getElementById('watchlistSymbols').value;
        const symbols = watchlistSymbols.split(',').map(s => s.trim().toUpperCase()).filter(s => s !== '');
        
        fetch('/api/market/watchlist', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ symbols })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showAlert('Watchlist saved successfully!', 'success');
            } else {
                showAlert('Error saving watchlist: ' + data.error, 'danger');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('Failed to save watchlist. Please try again.', 'danger');
        });
    });
    } else {
        console.warn('Save watchlist button is missing from the DOM');
    }
    
    // Refresh status button
    const refreshStatus = document.getElementById('refreshStatus');
    if (refreshStatus) {
        refreshStatus.addEventListener('click', function() {
        loadMarketStatus();
    });
    
    // Reconnect services button
    const reconnectServices = document.getElementById('reconnectServices');
    if (reconnectServices) {
        reconnectServices.addEventListener('click', function() {
        fetch('/api/market/reconnect', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showAlert('Services reconnected successfully!', 'success');
                setTimeout(loadMarketStatus, 1000); // Refresh status after reconnect
            } else {
                showAlert('Error reconnecting services: ' + data.error, 'warning');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('Failed to reconnect services. Please try again.', 'danger');
        });
    });
    } else {
        console.warn('Reconnect services button is missing from the DOM');
    }
    
    // Preset watchlist buttons
    document.querySelectorAll('.preset-watchlist').forEach(button => {
        button.addEventListener('click', function() {
            const presetName = this.getAttribute('data-preset');
            let symbols = [];
            
            switch(presetName) {
                case 'tech':
                    symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'AMD', 'INTC', 'CSCO', 'ADBE'];
                    break;
                case 'etfs':
                    symbols = ['SPY', 'QQQ', 'IWM', 'DIA', 'XLF', 'XLE', 'XLK', 'XLV', 'XLU', 'XLI'];
                    break;
                case 'meme':
                    symbols = ['GME', 'AMC', 'BBBY', 'BB', 'NOK', 'PLTR', 'CLOV', 'WISH', 'SOFI', 'SNAP'];
                    break;
                case 'energy':
                    symbols = ['XOM', 'CVX', 'BP', 'SHEL', 'COP', 'EOG', 'SLB', 'PXD', 'OXY', 'MPC'];
                    break;
                case 'financial':
                    symbols = ['JPM', 'BAC', 'GS', 'MS', 'WFC', 'C', 'BLK', 'AXP', 'SCHW', 'V'];
                    break;
                default:
                    symbols = [];
            }
            
            document.getElementById('watchlistSymbols').value = symbols.join(', ');
        });
    });
    
    // Load initial data
    loadMarketStatus();
    loadTradingSettings();
    loadWatchlist();
    
    // Get API key hints (masked)
    fetch('/api/market/get-api-hints')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Display masked API keys where available
                if (data.alpaca_api_key_hint) {
                    document.getElementById('alpacaApiKey').placeholder = data.alpaca_api_key_hint;
                }
            }
        })
        .catch(error => {
            console.error('Error loading API hints:', error);
        });
});

/**
 * Load market status from API
 */
function loadMarketStatus() {
    fetch('/api/market/status')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            if (data) {
                updateMarketStatusTable(data);
            }
        })
        .catch(error => {
            console.error('Error loading market status:', error);
            showAlert('Failed to load market status. Please try again.', 'warning');
        });
}

/**
 * Update the market status table with current data
 */
function updateMarketStatusTable(statusData) {
    const table = document.getElementById('marketStatusTable').querySelector('tbody');
    
    // Clear existing rows
    table.innerHTML = '';
    
    // Update Alpaca API status
    const alpacaRow = document.createElement('tr');
    alpacaRow.innerHTML = `
        <td>Alpaca API</td>
        <td><span class="badge ${statusData.alpaca_connected ? 'bg-success' : 'bg-danger'}">${statusData.alpaca_connected ? 'Connected' : 'Disconnected'}</span></td>
        <td>${formatTimestamp(statusData.timestamp)}</td>
    `;
    table.appendChild(alpacaRow);
    
    // Update QuotestreamPY status
    const quotestreamRow = document.createElement('tr');
    quotestreamRow.innerHTML = `
        <td>QuotestreamPY</td>
        <td><span class="badge ${statusData.quotestream_connected ? 'bg-success' : statusData.quotestream_connecting ? 'bg-warning' : 'bg-danger'}">${statusData.quotestream_connected ? 'Connected' : statusData.quotestream_connecting ? 'Connecting...' : 'Disconnected'}</span></td>
        <td>${formatTimestamp(statusData.timestamp)}</td>
    `;
    table.appendChild(quotestreamRow);
    
    // Update Market Status
    const marketRow = document.createElement('tr');
    marketRow.innerHTML = `
        <td>Market Status</td>
        <td><span class="badge ${statusData.market_open ? 'bg-success' : 'bg-danger'}">${statusData.market_open ? 'Open' : 'Closed'}</span></td>
        <td>${formatTimestamp(statusData.timestamp)}</td>
    `;
    table.appendChild(marketRow);
    
    // Update Watchlist
    const watchlistRow = document.createElement('tr');
    watchlistRow.innerHTML = `
        <td>Watchlist</td>
        <td><span class="badge bg-info">${statusData.watchlist_count || 0} symbols</span></td>
        <td>${formatTimestamp(statusData.timestamp)}</td>
    `;
    table.appendChild(watchlistRow);
    
    // Update data provider status indicator
    const dataProviderStatus = document.getElementById('dataProviderStatus');
    if (statusData.alpaca_connected || statusData.quotestream_connected) {
        dataProviderStatus.className = 'badge bg-success';
        dataProviderStatus.textContent = 'Connected';
    } else if (statusData.alpaca_connecting || statusData.quotestream_connecting) {
        dataProviderStatus.className = 'badge bg-warning';
        dataProviderStatus.textContent = 'Connecting...';
    } else {
        dataProviderStatus.className = 'badge bg-danger';
        dataProviderStatus.textContent = 'Disconnected';
    }
}

/**
 * Load trading settings
 */
function loadTradingSettings() {
    // Get trading mode
    fetch('/api/market/trading-mode')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            if (data && data.success) {
                // Get DOM elements
                const paperMode = document.getElementById('paperTradingMode');
                const liveMode = document.getElementById('liveTradingMode');
                const tradingStatus = document.getElementById('tradingStatus');
                const warning = document.getElementById('liveTradingWarning');
                
                // Check if elements exist before updating
                if (paperMode && liveMode && tradingStatus && warning) {
                    // Update radio buttons
                    if (data.paper_trading) {
                        paperMode.checked = true;
                        liveMode.checked = false;
                        tradingStatus.className = 'badge bg-warning';
                        tradingStatus.textContent = 'Paper Trading';
                        warning.style.display = 'none';
                    } else {
                        paperMode.checked = false;
                        liveMode.checked = true;
                        tradingStatus.className = 'badge bg-danger';
                        tradingStatus.textContent = 'Live Trading';
                        warning.style.display = 'block';
                    }
                }
            }
        })
        .catch(error => {
            console.error('Error loading trading mode:', error);
        });
    
    // Get circuit breaker settings
    fetch('/api/market/circuit-breaker-settings')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            if (data && data.success) {
                const enableCircuitBreaker = document.getElementById('enableCircuitBreaker');
                const maxConsecutiveLosses = document.getElementById('maxConsecutiveLosses');
                const maxDailyDrawdown = document.getElementById('maxDailyDrawdown');
                const circuitBreakerSettings = document.getElementById('circuitBreakerSettings');
                
                if (enableCircuitBreaker && circuitBreakerSettings) {
                    enableCircuitBreaker.checked = !!data.enabled;
                    
                    // Toggle circuit breaker settings visibility
                    circuitBreakerSettings.style.display = data.enabled ? 'block' : 'none';
                    
                    if (maxConsecutiveLosses && data.max_losses !== undefined) {
                        maxConsecutiveLosses.value = data.max_losses;
                    }
                    
                    if (maxDailyDrawdown && data.max_drawdown !== undefined) {
                        maxDailyDrawdown.value = data.max_drawdown;
                    }
                }
            }
        })
        .catch(error => {
            console.error('Error loading circuit breaker settings:', error);
        });
    
    // Get default order settings
    fetch('/api/settings/get', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            keys: ['default_order_type', 'default_time_in_force']
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        if (data && data.success && data.values) {
            const defaultOrderType = document.getElementById('defaultOrderType');
            const defaultTimeInForce = document.getElementById('defaultTimeInForce');
            
            // Update select elements if they exist
            if (defaultOrderType && data.values.default_order_type) {
                defaultOrderType.value = data.values.default_order_type;
            }
            
            if (defaultTimeInForce && data.values.default_time_in_force) {
                defaultTimeInForce.value = data.values.default_time_in_force;
            }
        }
    })
    .catch(error => {
        console.error('Error loading default order settings:', error);
    });
}

/**
 * Load watchlist
 */
function loadWatchlist() {
    fetch('/api/market/watchlist')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            if (data && data.success && data.watchlist && Array.isArray(data.watchlist)) {
                const watchlistSymbols = document.getElementById('watchlistSymbols');
                if (watchlistSymbols) {
                    watchlistSymbols.value = data.watchlist.join(', ');
                }
                
                // Update recently added badges
                const recentContainer = document.getElementById('recentSymbolsContainer');
                if (recentContainer) {
                    recentContainer.innerHTML = '';
                    
                    // Show max 5 recent symbols
                    const recentSymbols = data.watchlist.slice(0, 5);
                    recentSymbols.forEach(symbol => {
                        if (symbol) {
                            const badge = document.createElement('span');
                            badge.className = 'badge bg-secondary py-2 px-3 me-2 mb-2';
                            badge.textContent = symbol;
                            recentContainer.appendChild(badge);
                        }
                    });
                }
            }
        })
        .catch(error => {
            console.error('Error loading watchlist:', error);
        });
}

/**
 * Show alert message
 */
function showAlert(message, type = 'info') {
    const alertContainer = document.getElementById('alertContainer');
    
    // Create alert element
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.role = 'alert';
    
    // Add icon based on type
    let icon = 'info-circle';
    if (type === 'success') icon = 'check-circle';
    if (type === 'danger') icon = 'exclamation-circle';
    if (type === 'warning') icon = 'exclamation-triangle';
    
    alert.innerHTML = `
        <i class="fa fa-${icon} me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    // Add to container
    alertContainer.appendChild(alert);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        alert.classList.remove('show');
        setTimeout(() => alert.remove(), 300);
    }, 5000);
}

/**
 * Format timestamp for display
 */
function formatTimestamp(timestamp) {
    if (!timestamp) return 'Unknown';
    
    const now = new Date();
    const date = new Date(timestamp);
    const diffMs = now - date;
    const diffSec = Math.floor(diffMs / 1000);
    
    if (diffSec < 5) return 'Just now';
    if (diffSec < 60) return `${diffSec} sec ago`;
    if (diffSec < 3600) return `${Math.floor(diffSec / 60)} min ago`;
    if (diffSec < 86400) return `${Math.floor(diffSec / 3600)} hr ago`;
    
    return date.toLocaleString();
}