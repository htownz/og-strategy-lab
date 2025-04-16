/**
 * Ticker Tape Component for OG Signal Bot
 * Lightweight real-time price ticker that replaces heavy chart visualizations
 * while maintaining data flow
 */

class TickerTape {
    constructor(containerId, options = {}) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        this.symbols = options.symbols || ['SPY', 'QQQ', 'AAPL', 'MSFT', 'NVDA'];
        this.updateInterval = options.updateInterval || 2000; // default: 2 seconds
        this.tickerData = {};
        this.socket = null;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.autoScrollEnabled = true;
        
        // Initialize UI
        this.initUI();
        
        // Connect to data source
        this.connect();
        
        // Set up controls
        this.setupControls();
    }
    
    initUI() {
        // Create container if it doesn't exist
        if (!this.container) {
            console.error(`Container with ID ${this.containerId} not found`);
            return;
        }
        
        // Create header
        const header = document.createElement('div');
        header.className = 'ticker-tape-header';
        header.innerHTML = `
            <div class="d-flex justify-content-between align-items-center mb-2">
                <h5 class="m-0">Live Market Data</h5>
                <div class="ticker-controls">
                    <small class="text-muted me-2">📉 Real-time chart paused. Live data continues.</small>
                    <button id="${this.containerId}-scroll-toggle" class="btn btn-sm btn-secondary">
                        <i class="fa fa-pause"></i> Pause
                    </button>
                </div>
            </div>
        `;
        this.container.appendChild(header);
        
        // Create ticker container
        const tickerContainer = document.createElement('div');
        tickerContainer.className = 'ticker-tape-container';
        tickerContainer.innerHTML = `
            <div id="${this.containerId}-tape" class="ticker-tape-scroll">
                <!-- Ticker items will be inserted here -->
            </div>
        `;
        this.container.appendChild(tickerContainer);
        
        // Create signal feed container
        const signalFeed = document.createElement('div');
        signalFeed.className = 'signal-feed mt-3';
        signalFeed.innerHTML = `
            <h5>Recent Signals</h5>
            <div id="${this.containerId}-signals" class="signal-feed-items">
                <!-- Signal items will be inserted here -->
            </div>
        `;
        this.container.appendChild(signalFeed);
        
        // Initialize the ticker tape with symbols
        const tapeElement = document.getElementById(`${this.containerId}-tape`);
        this.symbols.forEach(symbol => {
            const tickerItem = document.createElement('div');
            tickerItem.className = 'ticker-item';
            tickerItem.id = `ticker-${symbol}`;
            tickerItem.innerHTML = `
                <span class="symbol">${symbol}</span>
                <span class="price">---.--</span>
                <span class="change neutral">0.00%</span>
            `;
            tapeElement.appendChild(tickerItem);
            
            // Store initial data
            this.tickerData[symbol] = {
                price: null,
                prevPrice: null,
                change: null,
                changePercent: null,
                lastUpdate: null
            };
        });
    }
    
    connect() {
        // Use the existing SocketIO connection
        if (typeof io !== 'undefined') {
            console.log('Connecting to SocketIO for ticker data...');
            this.socket = io();
            
            this.socket.on('connect', () => {
                console.log('Connected to real-time data service');
                this.isConnected = true;
                this.reconnectAttempts = 0;
                
                // Request initial data
                this.socket.emit('get_ticker_data', { symbols: this.symbols });
            });
            
            this.socket.on('disconnect', () => {
                console.log('Disconnected from real-time data service');
                this.isConnected = false;
                
                // Auto reconnect
                if (this.reconnectAttempts < this.maxReconnectAttempts) {
                    this.reconnectAttempts++;
                    setTimeout(() => {
                        console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
                        this.socket.connect();
                    }, 2000 * this.reconnectAttempts); // Exponential backoff
                }
            });
            
            // Listen for ticker updates
            this.socket.on('ticker_update', (data) => {
                this.handleTickerUpdate(data);
            });
            
            // Listen for signal updates
            this.socket.on('new_signal', (data) => {
                this.handleSignalUpdate(data);
            });
            
            // Listen for chart status updates
            this.socket.on('chart_status', (data) => {
                if (data.status === 'enabled') {
                    // Show message about chart being re-enabled
                    this.showToast('Chart functionality restored', 'success');
                }
            });
            
            // Start simulated updates if we're in demo mode
            if (window.demoMode) {
                this.startDemoUpdates();
            }
        } else {
            console.error('SocketIO not available');
            // Fallback to demo updates
            this.startDemoUpdates();
        }
    }
    
    handleTickerUpdate(data) {
        if (!data || !data.symbol) return;
        
        const symbol = data.symbol;
        const tickerItem = document.getElementById(`ticker-${symbol}`);
        
        if (!tickerItem) return;
        
        // Update data store
        if (this.tickerData[symbol]) {
            this.tickerData[symbol].prevPrice = this.tickerData[symbol].price;
            this.tickerData[symbol].price = data.price;
            this.tickerData[symbol].change = data.change;
            this.tickerData[symbol].changePercent = data.changePercent;
            this.tickerData[symbol].lastUpdate = new Date();
        }
        
        // Update UI
        const priceElement = tickerItem.querySelector('.price');
        const changeElement = tickerItem.querySelector('.change');
        
        if (priceElement) {
            priceElement.textContent = data.price.toFixed(2);
            
            // Flash price change
            if (this.tickerData[symbol].prevPrice !== null) {
                if (data.price > this.tickerData[symbol].prevPrice) {
                    priceElement.classList.remove('price-down');
                    priceElement.classList.add('price-up');
                } else if (data.price < this.tickerData[symbol].prevPrice) {
                    priceElement.classList.remove('price-up');
                    priceElement.classList.add('price-down');
                }
                
                // Remove animation after a short delay
                setTimeout(() => {
                    priceElement.classList.remove('price-up', 'price-down');
                }, 1000);
            }
        }
        
        if (changeElement) {
            const changeText = `${data.changePercent >= 0 ? '+' : ''}${data.changePercent.toFixed(2)}%`;
            changeElement.textContent = changeText;
            
            // Update color
            changeElement.classList.remove('positive', 'negative', 'neutral');
            if (data.changePercent > 0) {
                changeElement.classList.add('positive');
            } else if (data.changePercent < 0) {
                changeElement.classList.add('negative');
            } else {
                changeElement.classList.add('neutral');
            }
        }
    }
    
    handleSignalUpdate(data) {
        if (!data || !data.symbol) return;
        
        const signalContainer = document.getElementById(`${this.containerId}-signals`);
        if (!signalContainer) return;
        
        // Create new signal entry
        const signalItem = document.createElement('div');
        signalItem.className = 'signal-item';
        signalItem.innerHTML = `
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <span class="symbol">${data.symbol}</span>
                    <span class="direction ${data.direction === 'UP' ? 'positive' : 'negative'}">
                        ${data.direction === 'UP' ? '▲ BUY' : '▼ SELL'}
                    </span>
                </div>
                <div>
                    <span class="price">$${data.price_at_signal?.toFixed(2) || '---.--'}</span>
                    <span class="time text-muted">${new Date(data.timestamp).toLocaleTimeString()}</span>
                </div>
            </div>
            <div class="signal-confidence">
                <div class="progress" style="height: 5px;">
                    <div class="progress-bar ${data.confidence >= 0.7 ? 'bg-success' : 'bg-warning'}" 
                         style="width: ${Math.round(data.confidence * 100)}%"></div>
                </div>
                <small class="text-muted">Confidence: ${Math.round(data.confidence * 100)}%</small>
            </div>
        `;
        
        // Add to the beginning of the container
        if (signalContainer.firstChild) {
            signalContainer.insertBefore(signalItem, signalContainer.firstChild);
        } else {
            signalContainer.appendChild(signalItem);
        }
        
        // Limit to 10 signals
        while (signalContainer.children.length > 10) {
            signalContainer.removeChild(signalContainer.lastChild);
        }
        
        // Highlight the symbol in the ticker tape
        this.highlightSymbol(data.symbol, data.direction);
    }
    
    highlightSymbol(symbol, direction) {
        const tickerItem = document.getElementById(`ticker-${symbol}`);
        if (!tickerItem) return;
        
        // Add highlighting class
        tickerItem.classList.add(direction === 'UP' ? 'highlight-buy' : 'highlight-sell');
        
        // Remove after 5 seconds
        setTimeout(() => {
            tickerItem.classList.remove('highlight-buy', 'highlight-sell');
        }, 5000);
    }
    
    setupControls() {
        const scrollToggle = document.getElementById(`${this.containerId}-scroll-toggle`);
        if (scrollToggle) {
            scrollToggle.addEventListener('click', () => {
                this.autoScrollEnabled = !this.autoScrollEnabled;
                
                // Update button text
                if (this.autoScrollEnabled) {
                    scrollToggle.innerHTML = '<i class="fa fa-pause"></i> Pause';
                } else {
                    scrollToggle.innerHTML = '<i class="fa fa-play"></i> Resume';
                }
                
                // Update scrolling behavior
                const tapeElement = document.getElementById(`${this.containerId}-tape`);
                if (tapeElement) {
                    tapeElement.style.animationPlayState = this.autoScrollEnabled ? 'running' : 'paused';
                }
            });
        }
    }
    
    startDemoUpdates() {
        // Only used in demo mode when no real data source is available
        console.log('Starting demo ticker updates...');
        
        setInterval(() => {
            this.symbols.forEach(symbol => {
                // Generate random price changes
                const currentPrice = this.tickerData[symbol].price || this.getInitialDemoPrice(symbol);
                const change = (Math.random() - 0.5) * 2; // Random change between -1 and 1
                const newPrice = Math.max(1, currentPrice + change);
                const prevClose = this.getPrevClosePrice(symbol);
                const dailyChange = newPrice - prevClose;
                const changePercent = (dailyChange / prevClose) * 100;
                
                // Send update
                this.handleTickerUpdate({
                    symbol: symbol,
                    price: newPrice,
                    change: dailyChange,
                    changePercent: changePercent
                });
            });
        }, this.updateInterval);
        
        // Generate occasional demo signals
        setInterval(() => {
            if (Math.random() > 0.8) { // 20% chance of signal
                const randomIndex = Math.floor(Math.random() * this.symbols.length);
                const symbol = this.symbols[randomIndex];
                const direction = Math.random() > 0.5 ? 'UP' : 'DOWN';
                const confidence = 0.5 + (Math.random() * 0.5); // 0.5 to 1.0
                
                this.handleSignalUpdate({
                    symbol: symbol,
                    direction: direction,
                    confidence: confidence,
                    price_at_signal: this.tickerData[symbol].price,
                    timestamp: new Date().toISOString()
                });
            }
        }, 30000); // Every 30 seconds
    }
    
    getInitialDemoPrice(symbol) {
        // Starting prices for demo mode
        const prices = {
            'SPY': 480 + (Math.random() * 10),
            'QQQ': 410 + (Math.random() * 10),
            'AAPL': 170 + (Math.random() * 5),
            'MSFT': 410 + (Math.random() * 10),
            'NVDA': 880 + (Math.random() * 20),
        };
        
        return prices[symbol] || 100 + (Math.random() * 10);
    }
    
    getPrevClosePrice(symbol) {
        // For demo purposes, returns a price slightly lower than current
        return (this.tickerData[symbol].price || this.getInitialDemoPrice(symbol)) * 0.995;
    }
    
    showToast(message, type = 'info') {
        // Simple toast notification
        const toast = document.createElement('div');
        toast.className = `toast show position-fixed bottom-0 end-0 m-3 bg-${type}`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="toast-header">
                <strong class="me-auto">OG Signal Bot</strong>
                <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        `;
        
        document.body.appendChild(toast);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 500);
        }, 5000);
    }
}

// Add CSS
(function() {
    const style = document.createElement('style');
    style.textContent = `
        .ticker-tape-container {
            width: 100%;
            height: 50px;
            overflow: hidden;
            background-color: var(--bs-dark);
            border-radius: 4px;
            position: relative;
        }
        
        .ticker-tape-scroll {
            display: flex;
            animation: ticker-scroll 20s linear infinite;
            padding: 10px 0;
        }
        
        .ticker-tape-scroll:hover {
            animation-play-state: paused;
        }
        
        @keyframes ticker-scroll {
            0% { transform: translateX(100%); }
            100% { transform: translateX(-100%); }
        }
        
        .ticker-item {
            display: flex;
            align-items: center;
            margin-right: 30px;
            white-space: nowrap;
            padding: 0 10px;
            border-radius: 3px;
            transition: background-color 0.3s ease;
        }
        
        .ticker-item .symbol {
            font-weight: bold;
            margin-right: 10px;
        }
        
        .ticker-item .price {
            margin-right: 10px;
            transition: color 0.3s;
        }
        
        .ticker-item .price.price-up {
            color: #28a745;
            animation: flash-green 1s;
        }
        
        .ticker-item .price.price-down {
            color: #dc3545;
            animation: flash-red 1s;
        }
        
        .ticker-item .change {
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 0.9em;
        }
        
        .ticker-item .change.positive {
            background-color: rgba(40, 167, 69, 0.2);
            color: #28a745;
        }
        
        .ticker-item .change.negative {
            background-color: rgba(220, 53, 69, 0.2);
            color: #dc3545;
        }
        
        .ticker-item .change.neutral {
            background-color: rgba(108, 117, 125, 0.2);
            color: #6c757d;
        }
        
        .highlight-buy {
            background-color: rgba(40, 167, 69, 0.1);
            animation: pulse-green 2s infinite;
        }
        
        .highlight-sell {
            background-color: rgba(220, 53, 69, 0.1);
            animation: pulse-red 2s infinite;
        }
        
        @keyframes flash-green {
            0% { color: #fff; }
            50% { color: #28a745; }
            100% { color: #fff; }
        }
        
        @keyframes flash-red {
            0% { color: #fff; }
            50% { color: #dc3545; }
            100% { color: #fff; }
        }
        
        @keyframes pulse-green {
            0% { background-color: rgba(40, 167, 69, 0.1); }
            50% { background-color: rgba(40, 167, 69, 0.3); }
            100% { background-color: rgba(40, 167, 69, 0.1); }
        }
        
        @keyframes pulse-red {
            0% { background-color: rgba(220, 53, 69, 0.1); }
            50% { background-color: rgba(220, 53, 69, 0.3); }
            100% { background-color: rgba(220, 53, 69, 0.1); }
        }
        
        .signal-feed {
            margin-top: 20px;
        }
        
        .signal-feed-items {
            max-height: 300px;
            overflow-y: auto;
        }
        
        .signal-item {
            padding: 10px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            margin-bottom: 5px;
        }
        
        .signal-item .symbol {
            font-weight: bold;
            margin-right: 10px;
        }
        
        .signal-item .direction {
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 0.9em;
        }
        
        .signal-item .direction.positive {
            background-color: rgba(40, 167, 69, 0.2);
            color: #28a745;
        }
        
        .signal-item .direction.negative {
            background-color: rgba(220, 53, 69, 0.2);
            color: #dc3545;
        }
        
        .signal-confidence {
            margin-top: 5px;
        }
    `;
    document.head.appendChild(style);
})();

// Expose to global scope
window.TickerTape = TickerTape;