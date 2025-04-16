// Options Chain Analytics for OG Signal Bot
// This handles fetching and displaying options data with enhanced metrics
// Including: volume analysis, OG strategy pattern matching, and strike filtering

// Global state
let currentSymbol = 'SPY';
let currentExpiration = null;
let currentOptionsData = null;
let currentOptionType = 'all'; // 'call', 'put', or 'all'
let chartInstance = null;

// Initialize the options chain component
function initOptionsChain() {
    console.log("Initializing Options Chain Analytics...");
    
    // Set default symbol from URL or use default
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has('symbol')) {
        currentSymbol = urlParams.get('symbol').toUpperCase();
        document.getElementById('symbolInput').value = currentSymbol;
    }
    
    // Set up event listeners
    document.getElementById('symbolInput').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            fetchSymbolData();
        }
    });
    
    document.getElementById('searchButton').addEventListener('click', fetchSymbolData);
    document.getElementById('expirationSelector').addEventListener('change', handleExpirationChange);
    document.getElementById('optionTypeSelector').addEventListener('change', handleOptionTypeChange);
    
    // Initial data fetch
    fetchSymbolData();
}

// Fetch options data for the current symbol
function fetchSymbolData() {
    const symbolInput = document.getElementById('symbolInput');
    const symbol = symbolInput.value.trim().toUpperCase();
    
    if (!symbol) {
        showError("Please enter a valid symbol");
        return;
    }
    
    currentSymbol = symbol;
    updateBreadcrumb();
    
    // Update URL without reloading page
    const url = new URL(window.location);
    url.searchParams.set('symbol', symbol);
    window.history.pushState({}, '', url);
    
    // Show loading state
    document.getElementById('optionsLoading').classList.remove('d-none');
    document.getElementById('optionsTable').classList.add('d-none');
    document.getElementById('optionsError').classList.add('d-none');
    
    // Fetch options data from the API
    fetch(`/api/options/${symbol}?type=${currentOptionType}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`Error fetching options data: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            console.log("Options data received:", data);
            currentOptionsData = data;
            
            // Update expiration date selector
            updateExpirationSelector(data.expiration_date, data.all_expirations || []);
            
            // Render options data
            renderOptionsData(data);
            
            // Update price and headline
            updateSymbolInfo(data.symbol, data.current_price);
            
            // Show table, hide loading
            document.getElementById('optionsLoading').classList.add('d-none');
            document.getElementById('optionsTable').classList.remove('d-none');
        })
        .catch(error => {
            console.error("Error fetching options data:", error);
            showError(error.message);
            document.getElementById('optionsLoading').classList.add('d-none');
        });
}

// Show error message
function showError(message) {
    const errorElement = document.getElementById('optionsError');
    errorElement.textContent = message;
    errorElement.classList.remove('d-none');
    document.getElementById('optionsTable').classList.add('d-none');
}

// Update breadcrumb with current symbol
function updateBreadcrumb() {
    const symbolBreadcrumb = document.getElementById('symbolBreadcrumb');
    if (symbolBreadcrumb) {
        symbolBreadcrumb.textContent = currentSymbol;
    }
}

// Update symbol info display
function updateSymbolInfo(symbol, price) {
    const symbolTitle = document.getElementById('currentSymbol');
    const priceDisplay = document.getElementById('currentPrice');
    
    if (symbolTitle) symbolTitle.textContent = symbol;
    if (priceDisplay) priceDisplay.textContent = `$${price.toFixed(2)}`;
}

// Update expiration date selector
function updateExpirationSelector(currentExpiration, allExpirations) {
    const selector = document.getElementById('expirationSelector');
    
    // Clear existing options
    selector.innerHTML = '';
    
    // Add expiration dates
    if (allExpirations && allExpirations.length) {
        allExpirations.forEach(exp => {
            const option = document.createElement('option');
            option.value = exp;
            option.textContent = formatExpirationDate(exp);
            option.selected = exp === currentExpiration;
            selector.appendChild(option);
        });
    } else if (currentExpiration) {
        // If we only have the current expiration
        const option = document.createElement('option');
        option.value = currentExpiration;
        option.textContent = formatExpirationDate(currentExpiration);
        option.selected = true;
        selector.appendChild(option);
    }
}

// Format expiration date for display
function formatExpirationDate(dateStr) {
    if (!dateStr) return 'N/A';
    
    const date = new Date(dateStr);
    const month = date.toLocaleString('default', { month: 'short' });
    const day = date.getDate();
    const year = date.getFullYear();
    
    return `${month} ${day}, ${year}`;
}

// Handle expiration date change
function handleExpirationChange(event) {
    const newExpiration = event.target.value;
    
    if (newExpiration !== currentExpiration) {
        currentExpiration = newExpiration;
        
        // Re-fetch data with the new expiration date
        fetch(`/api/options/${currentSymbol}?expiration=${currentExpiration}&type=${currentOptionType}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Error fetching options data: ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                currentOptionsData = data;
                renderOptionsData(data);
            })
            .catch(error => {
                console.error("Error fetching options data:", error);
                showError(error.message);
            });
    }
}

// Handle option type change (calls/puts/all)
function handleOptionTypeChange(event) {
    const newType = event.target.value;
    
    if (newType !== currentOptionType) {
        currentOptionType = newType;
        
        if (currentOptionsData) {
            // If we have data already, we can just re-render with the filtered data
            renderOptionsData(currentOptionsData);
        } else {
            // Otherwise fetch new data
            fetchSymbolData();
        }
    }
}

// Render options data in the table
function renderOptionsData(data) {
    const tableBody = document.getElementById('optionsTableBody');
    tableBody.innerHTML = '';
    
    // Determine which options to display based on the selected type
    let options = [];
    
    if (currentOptionType === 'call') {
        options = data.calls || [];
    } else if (currentOptionType === 'put') {
        options = data.puts || [];
    } else {
        // For 'all', display options sorted by strike price
        options = data.all_options || [...(data.calls || []), ...(data.puts || [])];
        options.sort((a, b) => a.strike - b.strike);
    }
    
    if (options.length === 0) {
        showError("No options data available for the selected criteria");
        return;
    }
    
    // Render each option row
    options.forEach(option => {
        const row = document.createElement('tr');
        
        // Highlight rows based on special conditions
        if (option.og_match) {
            row.classList.add('og-strategy-match');
        }
        
        if (option.is_whale) {
            row.classList.add('whale-activity');
        }
        
        // Add strike price cell (with ITM/OTM highlighting)
        const isITM = (option.option_type === 'call' && option.strike < data.current_price) || 
                      (option.option_type === 'put' && option.strike > data.current_price);
        
        row.innerHTML = `
            <td class="${isITM ? 'itm' : 'otm'}">${option.strike.toFixed(2)}</td>
            <td>${option.option_type.toUpperCase()}</td>
            <td>${option.bid.toFixed(2)} / ${option.ask.toFixed(2)}</td>
            <td>${option.last.toFixed(2)}</td>
            <td class="${option.volume > option.open_interest ? 'text-success fw-bold' : ''}">${option.volume}</td>
            <td>${option.open_interest}</td>
            <td>${(option.implied_volatility * 100).toFixed(1)}%</td>
            <td>${option.expiration}</td>
            <td>${option.is_whale ? '🐋' : ''}</td>
            <td>${option.og_match ? '✅' : ''}</td>
        `;
        
        tableBody.appendChild(row);
    });
    
    // Update summary statistics
    updateOptionsSummary(data, options);
}

// Update options summary statistics
function updateOptionsSummary(data, options) {
    const totalOptions = options.length;
    const whaleCount = options.filter(o => o.is_whale).length;
    const ogMatchCount = options.filter(o => o.og_match).length;
    
    document.getElementById('totalOptionsCount').textContent = totalOptions;
    document.getElementById('whaleActivityCount').textContent = whaleCount;
    document.getElementById('ogStrategyCount').textContent = ogMatchCount;
    
    // Calculate put/call ratio if we have both types
    if (data.calls && data.calls.length && data.puts && data.puts.length) {
        const putCallRatio = (data.puts.length / data.calls.length).toFixed(2);
        document.getElementById('putCallRatio').textContent = putCallRatio;
    }
    
    // Update or create price distribution chart
    createPriceDistributionChart(options, data.current_price);
}

// Create price distribution chart
function createPriceDistributionChart(options, currentPrice) {
    const chartCanvas = document.getElementById('optionsDistributionChart');
    
    if (!chartCanvas) return;
    
    // Destroy existing chart if it exists
    if (chartInstance) {
        chartInstance.destroy();
    }
    
    // Prepare data - group by strike price
    const callVolumes = {};
    const putVolumes = {};
    
    options.forEach(option => {
        const strike = option.strike.toFixed(2);
        
        if (option.option_type === 'call') {
            callVolumes[strike] = (callVolumes[strike] || 0) + option.volume;
        } else {
            putVolumes[strike] = (putVolumes[strike] || 0) + option.volume;
        }
    });
    
    // Get sorted unique strike prices
    const strikes = [...new Set(options.map(o => o.strike.toFixed(2)))].sort((a, b) => parseFloat(a) - parseFloat(b));
    
    // Prepare chart data
    const callData = strikes.map(strike => callVolumes[strike] || 0);
    const putData = strikes.map(strike => putVolumes[strike] || 0);
    
    // Create chart
    chartInstance = new Chart(chartCanvas, {
        type: 'bar',
        data: {
            labels: strikes,
            datasets: [
                {
                    label: 'Call Volume',
                    data: callData,
                    backgroundColor: 'rgba(75, 192, 192, 0.5)',
                    borderColor: 'rgba(75, 192, 192, 1)',
                    borderWidth: 1
                },
                {
                    label: 'Put Volume',
                    data: putData,
                    backgroundColor: 'rgba(255, 99, 132, 0.5)',
                    borderColor: 'rgba(255, 99, 132, 1)',
                    borderWidth: 1
                }
            ]
        },
        options: {
            responsive: true,
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Strike Price'
                    }
                },
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Volume'
                    }
                }
            },
            plugins: {
                annotation: {
                    annotations: {
                        line1: {
                            type: 'line',
                            yMin: 0,
                            yMax: Math.max(...callData, ...putData) * 1.1,
                            xMin: currentPrice,
                            xMax: currentPrice,
                            borderColor: 'rgb(255, 255, 0)',
                            borderWidth: 2,
                            label: {
                                content: 'Current Price',
                                enabled: true
                            }
                        }
                    }
                }
            }
        }
    });
}

// Document ready handler - called when the page is loaded
document.addEventListener('DOMContentLoaded', function() {
    initOptionsChain();
});