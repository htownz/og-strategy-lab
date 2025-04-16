// QuotestreamPY Dashboard - Integrates real-time market data with OG Strategy Bot

// Global variables
let currentSymbol = null;
let watchlist = [];
let quotes = {};
let marketDepth = {};
let recentTrades = {};

// Auto-refresh configuration
const REFRESH_INTERVAL = 5000; // 5 seconds
let autoRefreshEnabled = true;
let refreshTimer = null;

// Socket connection for real-time updates
const socket = io();

// Initialize the dashboard on page load
document.addEventListener('DOMContentLoaded', function() {
    // Initial loading of data
    loadWatchlist();
    
    // Set up event listeners
    document.getElementById('refreshWatchlistBtn').addEventListener('click', loadWatchlist);
    document.getElementById('refreshQuoteBtn').addEventListener('click', function() {
        if (currentSymbol) {
            loadQuoteDetails(currentSymbol);
        }
    });
    
    document.getElementById('addToWatchlistBtn').addEventListener('click', addSymbolToWatchlist);
    document.getElementById('addToStrategyBtn').addEventListener('click', addSymbolToOGStrategy);
    document.getElementById('viewChartBtn').addEventListener('click', viewSymbolChart);
    
    document.getElementById('symbolSearch').addEventListener('input', handleSymbolSearch);
    document.getElementById('symbolSearch').addEventListener('focus', function() {
        document.getElementById('symbolSearchResults').style.display = 'block';
    });
    
    document.getElementById('symbolSearch').addEventListener('blur', function(e) {
        // Delay hiding to allow for click on results
        setTimeout(function() {
            document.getElementById('symbolSearchResults').style.display = 'none';
        }, 200);
    });
    
    // Auto-refresh toggle
    document.getElementById('autoRefreshToggle').addEventListener('change', function() {
        autoRefreshEnabled = this.checked;
        
        if (autoRefreshEnabled) {
            startAutoRefresh();
        } else {
            stopAutoRefresh();
        }
    });
    
    // Start auto-refresh
    startAutoRefresh();
    
    // Set up Socket.IO event listeners for real-time updates
    setupSocketListeners();
    
    // Initialize connection status
    updateConnectionStatus(socket.connected);
});

// Load watchlist from API
function loadWatchlist() {
    showLoading('watchlist');
    
    fetch('/quotestream/api/watchlist')
        .then(response => response.json())
        .then(data => {
            watchlist = data.symbols || [];
            updateWatchlistUI();
            
            if (watchlist.length > 0) {
                // Load quotes for all watchlist symbols
                loadQuotes(watchlist);
                
                // Select first symbol if none is selected
                if (!currentSymbol && watchlist.length > 0) {
                    selectSymbol(watchlist[0]);
                }
            }
            
            hideLoading('watchlist');
        })
        .catch(error => {
            console.error('Error loading watchlist:', error);
            showStatusMessage('Failed to load watchlist', 'danger');
            hideLoading('watchlist');
        });
}

// Update the watchlist UI
function updateWatchlistUI() {
    const container = document.getElementById('watchlistItems');
    
    if (watchlist.length === 0) {
        container.innerHTML = `
            <div class="text-center text-muted py-5">
                No symbols in watchlist
            </div>
        `;
        return;
    }
    
    let html = '';
    
    for (const symbol of watchlist) {
        const quote = quotes[symbol] || { last: 0, change: 0, change_percent: 0 };
        const changeClass = quote.change >= 0 ? 'text-success' : 'text-danger';
        const changeIcon = quote.change >= 0 ? 'fa-caret-up' : 'fa-caret-down';
        const isActive = symbol === currentSymbol ? 'active' : '';
        
        html += `
            <a href="#" class="list-group-item list-group-item-action d-flex justify-content-between align-items-center ${isActive}" data-symbol="${symbol}" onclick="selectSymbol('${symbol}'); return false;">
                <span class="font-weight-bold">${symbol}</span>
                <div>
                    <span class="mr-2">${formatPrice(quote.last)}</span>
                    <span class="quote-change ${changeClass}">
                        <i class="fas ${changeIcon}"></i> ${formatChange(quote.change)} (${formatPercent(quote.change_percent)})
                    </span>
                </div>
            </a>
        `;
    }
    
    container.innerHTML = html;
}

// Load quotes for watchlist symbols
function loadQuotes(symbols) {
    if (symbols.length === 0) return;
    
    const symbolsParam = symbols.join(',');
    
    fetch(`/quotestream/api/quotes?symbols=${symbolsParam}`)
        .then(response => response.json())
        .then(data => {
            // Update quotes data
            quotes = data;
            
            // Update UI
            updateWatchlistUI();
            
            // Update current symbol details if needed
            if (currentSymbol && quotes[currentSymbol]) {
                updateQuoteDetailsUI(currentSymbol);
            }
            
            // Update last refreshed timestamp
            updateLastUpdated();
        })
        .catch(error => {
            console.error('Error loading quotes:', error);
            showStatusMessage('Failed to load quotes', 'danger');
        });
}

// Select a symbol to display details
function selectSymbol(symbol) {
    currentSymbol = symbol;
    
    // Update watchlist active item
    updateWatchlistUI();
    
    // Load detailed data for the symbol
    loadQuoteDetails(symbol);
}

// Load detailed data for a symbol
function loadQuoteDetails(symbol) {
    // Update the title
    document.getElementById('selectedSymbolTitle').textContent = `Quote Details: ${symbol}`;
    
    // Show loading indicators
    showLoading('quoteDetails');
    showLoading('marketDepth');
    showLoading('recentTrades');
    
    // Load quote details
    updateQuoteDetailsUI(symbol);
    
    // Load market depth data
    fetch(`/quotestream/api/depth/${symbol}`)
        .then(response => response.json())
        .then(data => {
            marketDepth[symbol] = data;
            updateMarketDepthUI(symbol);
            hideLoading('marketDepth');
        })
        .catch(error => {
            console.error(`Error loading market depth for ${symbol}:`, error);
            marketDepth[symbol] = { bids: [], asks: [] };
            updateMarketDepthUI(symbol);
            hideLoading('marketDepth');
        });
    
    // Load recent trades
    fetch(`/quotestream/api/trades/${symbol}`)
        .then(response => response.json())
        .then(data => {
            recentTrades[symbol] = data;
            updateRecentTradesUI(symbol);
            hideLoading('recentTrades');
        })
        .catch(error => {
            console.error(`Error loading recent trades for ${symbol}:`, error);
            recentTrades[symbol] = [];
            updateRecentTradesUI(symbol);
            hideLoading('recentTrades');
        });
    
    // Hide quote details loading
    hideLoading('quoteDetails');
}

// Update the quote details UI
function updateQuoteDetailsUI(symbol) {
    const container = document.getElementById('quoteDetails');
    const quote = quotes[symbol];
    
    if (!quote) {
        container.innerHTML = `
            <div class="col-12 text-center text-muted py-5">
                No data available for ${symbol}
            </div>
        `;
        return;
    }
    
    const changeClass = quote.change >= 0 ? 'text-success' : 'text-danger';
    const bgClass = quote.change >= 0 ? 'bg-up' : 'bg-down';
    
    container.innerHTML = `
        <div class="col-md-6">
            <div class="card quote-card ${bgClass} mb-3">
                <div class="card-body">
                    <h4 class="mb-0">${symbol}</h4>
                    <p class="text-muted mb-2">${quote.description || 'No description available'}</p>
                    <div class="d-flex justify-content-between align-items-end">
                        <div>
                            <h2 class="mb-0">${formatPrice(quote.last)}</h2>
                            <div class="quote-change ${changeClass}">
                                <i class="fas ${quote.change >= 0 ? 'fa-caret-up' : 'fa-caret-down'}"></i>
                                ${formatChange(quote.change)} (${formatPercent(quote.change_percent)})
                            </div>
                        </div>
                        <div class="text-right">
                            <div class="small text-muted">Volume</div>
                            <div>${formatVolume(quote.volume)}</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <div class="col-md-6">
            <div class="row">
                <div class="col-6">
                    <div class="card mb-3">
                        <div class="card-body py-2">
                            <div class="small text-muted">Open</div>
                            <div class="font-weight-bold">${formatPrice(quote.open)}</div>
                        </div>
                    </div>
                </div>
                <div class="col-6">
                    <div class="card mb-3">
                        <div class="card-body py-2">
                            <div class="small text-muted">Close</div>
                            <div class="font-weight-bold">${formatPrice(quote.prev_close)}</div>
                        </div>
                    </div>
                </div>
                <div class="col-6">
                    <div class="card mb-3">
                        <div class="card-body py-2">
                            <div class="small text-muted">High</div>
                            <div class="font-weight-bold">${formatPrice(quote.high)}</div>
                        </div>
                    </div>
                </div>
                <div class="col-6">
                    <div class="card mb-3">
                        <div class="card-body py-2">
                            <div class="small text-muted">Low</div>
                            <div class="font-weight-bold">${formatPrice(quote.low)}</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <div class="col-md-6">
            <div class="card mb-3">
                <div class="card-body p-0">
                    <table class="table table-sm mb-0">
                        <tbody>
                            <tr>
                                <td class="text-muted">Bid</td>
                                <td class="text-right font-weight-bold">${formatPrice(quote.bid)}</td>
                                <td class="text-right text-muted">${formatSize(quote.bid_size)}</td>
                            </tr>
                            <tr>
                                <td class="text-muted">Ask</td>
                                <td class="text-right font-weight-bold">${formatPrice(quote.ask)}</td>
                                <td class="text-right text-muted">${formatSize(quote.ask_size)}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        <div class="col-md-6">
            <div class="card mb-3">
                <div class="card-body p-0">
                    <table class="table table-sm mb-0">
                        <tbody>
                            <tr>
                                <td class="text-muted">VWAP</td>
                                <td class="text-right font-weight-bold">${formatPrice(quote.vwap || 0)}</td>
                            </tr>
                            <tr>
                                <td class="text-muted">Last Update</td>
                                <td class="text-right">${formatTime(quote.timestamp)}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    `;
}

// Update the market depth UI
function updateMarketDepthUI(symbol) {
    const bidContainer = document.getElementById('bidLevels');
    const askContainer = document.getElementById('askLevels');
    const depth = marketDepth[symbol];
    
    if (!depth || (!depth.bids || !depth.asks)) {
        bidContainer.innerHTML = askContainer.innerHTML = `
            <tr>
                <td colspan="3" class="text-center text-muted">No market depth data available</td>
            </tr>
        `;
        return;
    }
    
    // Find max volume for scaling
    const allVolumes = [...depth.bids.map(b => b.size || 0), ...depth.asks.map(a => a.size || 0)];
    const maxVolume = Math.max(...allVolumes, 1);
    
    // Update bid levels
    if (depth.bids && depth.bids.length > 0) {
        let bidHtml = '';
        for (const bid of depth.bids.slice(0, 8)) {
            const volumePercent = (bid.size / maxVolume) * 100;
            bidHtml += `
                <tr class="bid-level">
                    <td class="font-weight-bold text-success">${formatPrice(bid.price)}</td>
                    <td>${formatSize(bid.size)}</td>
                    <td>
                        <div class="price-level-volume level-bid" style="width: ${volumePercent}%"></div>
                    </td>
                </tr>
            `;
        }
        bidContainer.innerHTML = bidHtml;
    } else {
        bidContainer.innerHTML = `
            <tr>
                <td colspan="3" class="text-center text-muted">No bid data available</td>
            </tr>
        `;
    }
    
    // Update ask levels
    if (depth.asks && depth.asks.length > 0) {
        let askHtml = '';
        for (const ask of depth.asks.slice(0, 8)) {
            const volumePercent = (ask.size / maxVolume) * 100;
            askHtml += `
                <tr class="ask-level">
                    <td class="font-weight-bold text-danger">${formatPrice(ask.price)}</td>
                    <td>${formatSize(ask.size)}</td>
                    <td>
                        <div class="price-level-volume level-ask" style="width: ${volumePercent}%"></div>
                    </td>
                </tr>
            `;
        }
        askContainer.innerHTML = askHtml;
    } else {
        askContainer.innerHTML = `
            <tr>
                <td colspan="3" class="text-center text-muted">No ask data available</td>
            </tr>
        `;
    }
}

// Update the recent trades UI
function updateRecentTradesUI(symbol) {
    const container = document.getElementById('recentTrades');
    const trades = recentTrades[symbol];
    
    if (!trades || trades.length === 0) {
        container.innerHTML = `
            <tr>
                <td colspan="5" class="text-center text-muted">No recent trades available</td>
            </tr>
        `;
        return;
    }
    
    let html = '';
    
    for (const trade of trades) {
        const priceClass = trade.price_change >= 0 ? 'text-success' : 'text-danger';
        html += `
            <tr>
                <td>${formatTime(trade.timestamp)}</td>
                <td class="${priceClass}">${formatPrice(trade.price)}</td>
                <td>${formatSize(trade.size)}</td>
                <td>${trade.exchange || '-'}</td>
                <td>${trade.conditions || '-'}</td>
            </tr>
        `;
    }
    
    container.innerHTML = html;
}

// Add a symbol to the watchlist
function addSymbolToWatchlist() {
    const symbolInput = document.getElementById('symbolSearch');
    const symbol = symbolInput.value.trim().toUpperCase();
    
    if (!symbol) {
        showStatusMessage('Please enter a valid symbol', 'warning');
        return;
    }
    
    // Check if already in watchlist
    if (watchlist.includes(symbol)) {
        showStatusMessage(`${symbol} is already in your watchlist`, 'info');
        return;
    }
    
    // Add to watchlist
    fetch('/quotestream/api/watchlist', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            symbol: symbol,
            action: 'add'
        }),
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showStatusMessage(`Added ${symbol} to watchlist`, 'success');
                symbolInput.value = '';
                // Reload watchlist
                loadWatchlist();
            } else {
                showStatusMessage(data.message || 'Failed to add symbol', 'danger');
            }
        })
        .catch(error => {
            console.error('Error adding symbol to watchlist:', error);
            showStatusMessage('Failed to add symbol to watchlist', 'danger');
        });
}

// Add a symbol to OG Strategy for scanning
function addSymbolToOGStrategy() {
    if (!currentSymbol) {
        showStatusMessage('Please select a symbol first', 'warning');
        return;
    }
    
    fetch('/quotestream/api/send-to-strategy', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            symbol: currentSymbol
        }),
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showStatusMessage(`${currentSymbol} sent to OG Strategy Scanner`, 'success');
            } else {
                showStatusMessage(data.message || 'Failed to send to OG Strategy', 'danger');
            }
        })
        .catch(error => {
            console.error('Error sending to OG Strategy:', error);
            showStatusMessage('Failed to send to OG Strategy', 'danger');
        });
}

// Handle symbol search
function handleSymbolSearch() {
    const query = document.getElementById('symbolSearch').value.trim().toUpperCase();
    const resultsContainer = document.getElementById('symbolSearchResults');
    
    if (!query) {
        resultsContainer.style.display = 'none';
        return;
    }
    
    fetch(`/quotestream/api/search?q=${query}`)
        .then(response => response.json())
        .then(data => {
            if (data.results && data.results.length > 0) {
                let html = '';
                for (const result of data.results) {
                    html += `
                        <div class="symbol-search-item" onclick="selectSearchResult('${result.symbol}')">
                            <strong>${result.symbol}</strong> - ${result.description || ''}
                        </div>
                    `;
                }
                resultsContainer.innerHTML = html;
                resultsContainer.style.display = 'block';
            } else {
                resultsContainer.innerHTML = `
                    <div class="symbol-search-item">No results found</div>
                `;
                resultsContainer.style.display = 'block';
            }
        })
        .catch(error => {
            console.error('Error searching symbols:', error);
            resultsContainer.innerHTML = `
                <div class="symbol-search-item">Error searching symbols</div>
            `;
            resultsContainer.style.display = 'block';
        });
}

// Select a search result
function selectSearchResult(symbol) {
    document.getElementById('symbolSearch').value = symbol;
    document.getElementById('symbolSearchResults').style.display = 'none';
}

// Set up Socket.IO event listeners
function setupSocketListeners() {
    // Connection events
    socket.on('connect', function() {
        console.log('Connected to Socket.IO server');
        updateConnectionStatus(true);
        showStatusMessage('Connected to real-time updates', 'success');
    });
    
    socket.on('disconnect', function() {
        console.log('Disconnected from Socket.IO server');
        updateConnectionStatus(false);
        showStatusMessage('Disconnected from real-time updates', 'warning');
    });
    
    // Quote updates
    socket.on('quote_update', function(data) {
        console.log('Quote update received:', data);
        
        // Update quotes data
        if (data.symbol && data.quote) {
            quotes[data.symbol] = data.quote;
            
            // Update UI if needed
            updateWatchlistUI();
            
            if (data.symbol === currentSymbol) {
                updateQuoteDetailsUI(data.symbol);
            }
        }
    });
    
    // Market depth updates
    socket.on('depth_update', function(data) {
        if (data.symbol && data.depth) {
            marketDepth[data.symbol] = data.depth;
            
            if (data.symbol === currentSymbol) {
                updateMarketDepthUI(data.symbol);
            }
        }
    });
    
    // Trade updates
    socket.on('trade_update', function(data) {
        if (data.symbol && data.trade) {
            if (!recentTrades[data.symbol]) {
                recentTrades[data.symbol] = [];
            }
            
            // Add new trade to the beginning
            recentTrades[data.symbol].unshift(data.trade);
            
            // Limit to 20 trades
            if (recentTrades[data.symbol].length > 20) {
                recentTrades[data.symbol] = recentTrades[data.symbol].slice(0, 20);
            }
            
            if (data.symbol === currentSymbol) {
                updateRecentTradesUI(data.symbol);
            }
        }
    });
}

// Start auto-refresh timer
function startAutoRefresh() {
    if (refreshTimer) {
        clearInterval(refreshTimer);
    }
    
    refreshTimer = setInterval(() => {
        if (autoRefreshEnabled) {
            if (watchlist.length > 0) {
                loadQuotes(watchlist);
            }
            
            if (currentSymbol) {
                // Refresh market depth and recent trades every 10 seconds
                // (half as often as quotes)
                const now = new Date();
                if (now.getSeconds() % 10 === 0) {
                    fetch(`/quotestream/api/depth/${currentSymbol}`)
                        .then(response => response.json())
                        .then(data => {
                            marketDepth[currentSymbol] = data;
                            updateMarketDepthUI(currentSymbol);
                        });
                    
                    fetch(`/quotestream/api/trades/${currentSymbol}`)
                        .then(response => response.json())
                        .then(data => {
                            recentTrades[currentSymbol] = data;
                            updateRecentTradesUI(currentSymbol);
                        });
                }
            }
        }
    }, REFRESH_INTERVAL);
}

// Stop auto-refresh timer
function stopAutoRefresh() {
    if (refreshTimer) {
        clearInterval(refreshTimer);
        refreshTimer = null;
    }
}

// Update connection status indicator
function updateConnectionStatus(connected) {
    const status = document.getElementById('connectionStatus');
    const statusText = document.getElementById('connectionStatusText');
    
    if (status && statusText) {
        if (connected) {
            status.className = 'connection-status status-connected';
            status.title = 'Connected';
            statusText.textContent = 'Connected';
        } else {
            status.className = 'connection-status status-disconnected';
            status.title = 'Disconnected';
            statusText.textContent = 'Disconnected';
        }
    }
}

// Update last updated timestamp
function updateLastUpdated() {
    const element = document.getElementById('lastUpdated');
    if (element) {
        const now = new Date();
        const timeStr = now.toLocaleTimeString();
        element.textContent = `Last updated: ${timeStr}`;
    }
}

// Helper function to show loading indicator
function showLoading(section) {
    const element = document.getElementById(`${section}Loading`);
    if (element) {
        element.style.display = 'flex';
    }
}

// Helper function to hide loading indicator
function hideLoading(section) {
    const element = document.getElementById(`${section}Loading`);
    if (element) {
        element.style.display = 'none';
    }
}

// Show a status message alert
function showStatusMessage(message, type = 'info') {
    const alert = document.getElementById('statusAlert');
    const messageElement = document.getElementById('statusMessage');
    
    alert.className = `alert alert-${type} alert-dismissible fade show mb-4`;
    messageElement.textContent = message;
    alert.style.display = 'block';
    
    // Auto-hide after 5 seconds for success messages
    if (type === 'success') {
        setTimeout(() => {
            alert.style.display = 'none';
        }, 5000);
    }
}

// Format functions for display
function formatPrice(price) {
    if (price === undefined || price === null) return '-';
    return '$' + parseFloat(price).toFixed(2);
}

function formatChange(change) {
    if (change === undefined || change === null) return '-';
    return change >= 0 ? '+' + parseFloat(change).toFixed(2) : parseFloat(change).toFixed(2);
}

function formatPercent(percent) {
    if (percent === undefined || percent === null) return '-';
    return parseFloat(percent).toFixed(2) + '%';
}

function formatVolume(volume) {
    if (volume === undefined || volume === null) return '-';
    if (volume >= 1000000) {
        return (volume / 1000000).toFixed(2) + 'M';
    } else if (volume >= 1000) {
        return (volume / 1000).toFixed(1) + 'K';
    }
    return volume.toString();
}

function formatSize(size) {
    if (size === undefined || size === null) return '-';
    return size.toString();
}

function formatTime(timestamp) {
    if (!timestamp) return '-';
    const date = new Date(timestamp);
    return date.toLocaleTimeString();
}

// View symbol chart
function viewSymbolChart() {
    if (!currentSymbol) {
        showStatusMessage('Please select a symbol first', 'warning');
        return;
    }
    
    // Navigate to the chart page for the current symbol
    window.location.href = `/quotestream/chart/${currentSymbol}`;
}