// Confidence Dashboard - Visualizes the correlation between confidence scores and trade outcomes

// Chart objects
let correlationChart = null;
let winRateChart = null;
let roiChart = null;

// Current filter settings
let currentStrategyId = '';
let currentPeriod = 30;

// Auto-refresh configuration
const REFRESH_INTERVAL = 10000; // 10 seconds
let autoRefreshEnabled = true;
let refreshTimer = null;

// Socket connection for real-time updates
const socket = io();

// Initialize the dashboard on page load
document.addEventListener('DOMContentLoaded', function() {
    // Initialize charts
    initializeCharts();
    
    // Load initial data
    refreshDashboard();
    
    // Add auto-refresh toggle to the UI
    addAutoRefreshToggle();
    
    // Start auto-refresh timer
    startAutoRefresh();
    
    // Set up event listeners
    document.getElementById('strategySelect').addEventListener('change', function() {
        currentStrategyId = this.value;
        refreshDashboard();
    });
    
    document.getElementById('periodSelect').addEventListener('change', function() {
        currentPeriod = parseInt(this.value);
        refreshDashboard();
    });
    
    document.getElementById('exportBtn').addEventListener('click', exportCSV);
    
    // Add event listener for sample data generation
    document.getElementById('generateDataBtn').addEventListener('click', generateSampleData);
    
    // Set up Socket.IO event listeners for real-time updates
    socket.on('trade_update', function(data) {
        // Refresh the dashboard when a new trade is completed
        if (data.exit_price) {  // Only update for completed trades
            refreshDashboard();
        }
    });
    
    // Set up Socket.IO connection status
    socket.on('connect', function() {
        console.log('Connected to real-time updates');
        updateConnectionStatus(true);
    });
    
    socket.on('disconnect', function() {
        console.log('Disconnected from real-time updates');
        updateConnectionStatus(false);
    });
});

// Initialize all charts
function initializeCharts() {
    // Correlation scatter plot
    const correlationCtx = document.getElementById('correlationChart').getContext('2d');
    correlationChart = new Chart(correlationCtx, {
        type: 'scatter',
        data: {
            datasets: [{
                label: 'Trades',
                data: [],
                backgroundColor: 'rgba(54, 162, 235, 0.5)',
                borderColor: 'rgba(54, 162, 235, 1)',
                borderWidth: 1,
                pointRadius: 5,
                pointHoverRadius: 7
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Confidence Score'
                    },
                    min: 0,
                    max: 100
                },
                y: {
                    title: {
                        display: true,
                        text: 'ROI (%)'
                    }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const point = context.raw;
                            return `${point.symbol}: Confidence ${point.x}, ROI ${point.y.toFixed(2)}%`;
                        }
                    }
                },
                legend: {
                    display: false
                }
            }
        }
    });
    
    // Win rate by confidence tier
    const winRateCtx = document.getElementById('winRateChart').getContext('2d');
    winRateChart = new Chart(winRateCtx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Win Rate (%)',
                data: [],
                backgroundColor: [
                    'rgba(255, 59, 48, 0.7)',   // 0-59
                    'rgba(255, 149, 0, 0.7)',   // 60-69
                    'rgba(255, 204, 0, 0.7)',   // 70-79
                    'rgba(76, 217, 100, 0.7)',  // 80-89
                    'rgba(40, 167, 69, 0.7)'    // 90-100
                ],
                borderColor: [
                    'rgb(255, 59, 48)',
                    'rgb(255, 149, 0)',
                    'rgb(255, 204, 0)',
                    'rgb(76, 217, 100)',
                    'rgb(40, 167, 69)'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Win Rate (%)'
                    },
                    max: 100
                }
            },
            plugins: {
                title: {
                    display: true,
                    text: 'Win Rate by Confidence Tier'
                },
                legend: {
                    display: false
                }
            }
        }
    });
    
    // ROI by confidence tier
    const roiCtx = document.getElementById('roiChart').getContext('2d');
    roiChart = new Chart(roiCtx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Average ROI (%)',
                data: [],
                backgroundColor: [
                    'rgba(255, 59, 48, 0.7)',   // 0-59
                    'rgba(255, 149, 0, 0.7)',   // 60-69
                    'rgba(255, 204, 0, 0.7)',   // 70-79
                    'rgba(76, 217, 100, 0.7)',  // 80-89
                    'rgba(40, 167, 69, 0.7)'    // 90-100
                ],
                borderColor: [
                    'rgb(255, 59, 48)',
                    'rgb(255, 149, 0)',
                    'rgb(255, 204, 0)',
                    'rgb(76, 217, 100)',
                    'rgb(40, 167, 69)'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    title: {
                        display: true,
                        text: 'Average ROI (%)'
                    }
                }
            },
            plugins: {
                title: {
                    display: true,
                    text: 'ROI by Confidence Tier'
                },
                legend: {
                    display: false
                }
            }
        }
    });
}

// Refresh the dashboard with current filters
function refreshDashboard() {
    // Show loading indicators
    document.getElementById('correlationChartLoading').style.display = 'flex';
    document.getElementById('tierChartsLoading').style.display = 'flex';
    document.getElementById('strategyBreakdownLoading').style.display = 'flex';
    document.getElementById('tierBreakdownLoading').style.display = 'flex';
    
    // Build query parameters
    const queryParams = new URLSearchParams();
    if (currentStrategyId) {
        queryParams.append('strategy_id', currentStrategyId);
    }
    queryParams.append('days', currentPeriod);
    
    // Add a timestamp to prevent caching - ensures fresh data
    queryParams.append('t', Date.now());
    
    // Fetch data
    fetchConfidenceData(queryParams);
    
    // Update last updated timestamp
    updateLastUpdated();
}

// Fetch confidence data from API
function fetchConfidenceData(queryParams) {
    fetch(`/strategy-analytics/api/confidence-data?${queryParams.toString()}`)
        .then(response => response.json())
        .then(data => {
            // Update charts and metrics
            updateCorrelationChart(data);
            updateWinRateChart(data);
            updatePnLChart(data);
            updateStrategyTable(data);
            
            // Update summary metrics
            updateSummaryMetrics(data);
            
            // Update last updated timestamp
            updateLastUpdated();
            
            // Hide loading indicators
            document.getElementById('correlationChartLoading').style.display = 'none';
            document.getElementById('tierChartsLoading').style.display = 'none';
            document.getElementById('strategyBreakdownLoading').style.display = 'none';
            document.getElementById('tierBreakdownLoading').style.display = 'none';
        })
        .catch(error => {
            console.error('Error fetching confidence data:', error);
            
            // Hide loading indicators
            document.getElementById('correlationChartLoading').style.display = 'none';
            document.getElementById('tierChartsLoading').style.display = 'none';
            document.getElementById('strategyBreakdownLoading').style.display = 'none';
            document.getElementById('tierBreakdownLoading').style.display = 'none';
        });
}

// Update the correlation scatter plot
function updateCorrelationChart(data) {
    // Prepare data points for scatter plot
    const scatterData = data.all_trades.map(trade => ({
        x: trade.confidence,
        y: trade.roi,
        symbol: trade.symbol
    }));
    
    // Update chart data
    correlationChart.data.datasets[0].data = scatterData;
    
    // Add trend line if there are enough data points
    if (scatterData.length > 1) {
        // Extract x and y values
        const x = scatterData.map(point => point.x);
        const y = scatterData.map(point => point.y);
        
        // Calculate linear regression
        const n = x.length;
        const xy = x.map((value, i) => value * y[i]).reduce((a, b) => a + b, 0);
        const x2 = x.map(value => value * value).reduce((a, b) => a + b, 0);
        const x_sum = x.reduce((a, b) => a + b, 0);
        const y_sum = y.reduce((a, b) => a + b, 0);
        
        const slope = (n * xy - x_sum * y_sum) / (n * x2 - x_sum * x_sum);
        const intercept = (y_sum - slope * x_sum) / n;
        
        // Create trend line dataset
        const trendLine = [
            { x: 0, y: intercept },
            { x: 100, y: slope * 100 + intercept }
        ];
        
        // Update or add trend line dataset
        if (correlationChart.data.datasets.length > 1) {
            correlationChart.data.datasets[1].data = trendLine;
        } else {
            correlationChart.data.datasets.push({
                type: 'line',
                label: 'Trend',
                data: trendLine,
                borderColor: 'rgba(255, 99, 132, 1)',
                borderWidth: 2,
                fill: false,
                pointRadius: 0
            });
        }
    } else if (correlationChart.data.datasets.length > 1) {
        // Remove trend line if not enough data points
        correlationChart.data.datasets.pop();
    }
    
    // Update chart
    correlationChart.update();
}

// Update the win rate chart
function updateWinRateChart(data) {
    // Sort tiers by confidence range (ascending)
    const sortedTiers = [...data.confidence_tiers].sort((a, b) => {
        return parseInt(a.tier.split('-')[0]) - parseInt(b.tier.split('-')[0]);
    });
    
    // Update chart data
    winRateChart.data.labels = sortedTiers.map(tier => tier.tier);
    winRateChart.data.datasets[0].data = sortedTiers.map(tier => tier.win_rate);
    
    // Update chart
    winRateChart.update();
}

// Update the ROI chart
function updatePnLChart(data) {
    // Sort tiers by confidence range (ascending)
    const sortedTiers = [...data.confidence_tiers].sort((a, b) => {
        return parseInt(a.tier.split('-')[0]) - parseInt(b.tier.split('-')[0]);
    });
    
    // Update chart data
    roiChart.data.labels = sortedTiers.map(tier => tier.tier);
    roiChart.data.datasets[0].data = sortedTiers.map(tier => tier.avg_roi);
    
    // Update chart
    roiChart.update();
}

// Update the strategy table
function updateStrategyTable(data) {
    // Strategy breakdown
    const strategyContainer = document.getElementById('strategyBreakdown');
    const strategies = data.strategies;
    
    if (strategies.length === 0) {
        strategyContainer.innerHTML = `
            <div class="text-center text-muted py-4">
                No strategy data available
            </div>
        `;
        return;
    }
    
    // Sort strategies by trade count (descending)
    strategies.sort((a, b) => b.trades.length - a.trades.length);
    
    // Build HTML for strategy cards
    let strategyHtml = '';
    
    for (const strategy of strategies) {
        const isActive = currentStrategyId === strategy.id ? 'active' : '';
        
        // Calculate ROI color
        const roiColor = strategy.avg_roi >= 0 ? 'text-success' : 'text-danger';
        
        // Format correlation strength
        const roiCorrelation = strategy.confidence_roi_correlation;
        const roiCorrelationStr = getCorrelationStrength(roiCorrelation);
        
        strategyHtml += `
            <div class="card strategy-card mb-2 ${isActive}" data-strategy-id="${strategy.id}" onclick="document.getElementById('strategySelect').value='${strategy.id}'; refreshDashboard();">
                <div class="card-body py-2">
                    <div class="d-flex justify-content-between align-items-center">
                        <h6 class="card-title mb-0">${strategy.name}</h6>
                        <span class="badge badge-pill badge-light">${strategy.trades.length} trades</span>
                    </div>
                    <div class="row mt-2">
                        <div class="col-4">
                            <small class="d-block text-muted">Win Rate</small>
                            <span class="font-weight-bold">${strategy.win_rate.toFixed(1)}%</span>
                        </div>
                        <div class="col-4">
                            <small class="d-block text-muted">Avg ROI</small>
                            <span class="font-weight-bold ${roiColor}">${strategy.avg_roi.toFixed(1)}%</span>
                        </div>
                        <div class="col-4">
                            <small class="d-block text-muted">Correlation</small>
                            <span class="font-weight-bold">${roiCorrelation.toFixed(2)}</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    strategyContainer.innerHTML = strategyHtml;
    
    // Confidence tier breakdown
    const tierTable = document.getElementById('tierBreakdownTable');
    const confidenceTiers = data.confidence_tiers;
    
    if (confidenceTiers.length === 0) {
        tierTable.innerHTML = `
            <tr>
                <td colspan="5" class="text-center text-muted">No data available</td>
            </tr>
        `;
        return;
    }
    
    // Sort tiers by confidence range (descending)
    confidenceTiers.sort((a, b) => {
        return parseInt(b.tier.split('-')[0]) - parseInt(a.tier.split('-')[0]);
    });
    
    // Build HTML for tier table
    let tierHtml = '';
    
    for (const tier of confidenceTiers) {
        // Calculate colors
        const winRateColor = tier.win_rate >= 50 ? 'text-success' : 'text-danger';
        const roiColor = tier.avg_roi >= 0 ? 'text-success' : 'text-danger';
        const pnlColor = tier.avg_pnl >= 0 ? 'text-success' : 'text-danger';
        
        // Format tier badge class
        const tierClass = tier.tier.replace('-', '-');
        
        tierHtml += `
            <tr>
                <td>
                    <span class="tier-badge tier-${tierClass}">${tier.tier}</span>
                </td>
                <td class="text-center">${tier.count}</td>
                <td class="${winRateColor}">${tier.win_rate.toFixed(1)}%</td>
                <td class="${roiColor}">${tier.avg_roi.toFixed(1)}%</td>
                <td class="${pnlColor}">$${tier.avg_pnl.toFixed(2)}</td>
            </tr>
        `;
    }
    
    tierTable.innerHTML = tierHtml;
}

// Update summary metrics at the top of the page
function updateSummaryMetrics(data) {
    // Calculate overall metrics from all trades
    const allTrades = data.all_trades;
    
    if (allTrades.length === 0) {
        document.getElementById('totalTradesValue').textContent = '0';
        document.getElementById('avgConfidenceValue').textContent = '0';
        document.getElementById('winRateValue').textContent = '0%';
        document.getElementById('avgRoiValue').textContent = '0%';
        document.getElementById('roiCorrelationValue').textContent = '0.00';
        document.getElementById('pnlCorrelationValue').textContent = '0.00';
        return;
    }
    
    // Total trades
    document.getElementById('totalTradesValue').textContent = allTrades.length;
    
    // Average confidence
    const avgConfidence = allTrades.reduce((sum, trade) => sum + trade.confidence, 0) / allTrades.length;
    document.getElementById('avgConfidenceValue').textContent = avgConfidence.toFixed(1);
    
    // Win rate
    const winningTrades = allTrades.filter(trade => trade.pnl > 0).length;
    const winRate = (winningTrades / allTrades.length) * 100;
    document.getElementById('winRateValue').textContent = `${winRate.toFixed(1)}%`;
    
    // Average ROI
    const avgRoi = allTrades.reduce((sum, trade) => sum + trade.roi, 0) / allTrades.length;
    document.getElementById('avgRoiValue').textContent = `${avgRoi.toFixed(1)}%`;
    
    // ROI correlation
    const roiCorrelation = data.overall_correlation.roi;
    document.getElementById('roiCorrelationValue').textContent = roiCorrelation.toFixed(2);
    
    // P&L correlation
    const pnlCorrelation = data.overall_correlation.pnl;
    document.getElementById('pnlCorrelationValue').textContent = pnlCorrelation.toFixed(2);
    
    // Set correlation strength badges
    const roiCorrelationStrength = getCorrelationStrength(roiCorrelation);
    const pnlCorrelationStrength = getCorrelationStrength(pnlCorrelation);
    
    const roiStrengthElement = document.getElementById('roiCorrelationStrength');
    const pnlStrengthElement = document.getElementById('pnlCorrelationStrength');
    
    // Update ROI correlation badge
    roiStrengthElement.textContent = roiCorrelationStrength;
    roiStrengthElement.className = 'badge';
    if (roiCorrelation > 0.5) {
        roiStrengthElement.classList.add('badge-success');
    } else if (roiCorrelation > 0.3) {
        roiStrengthElement.classList.add('badge-primary');
    } else if (roiCorrelation > 0.1) {
        roiStrengthElement.classList.add('badge-info');
    } else if (roiCorrelation > -0.1) {
        roiStrengthElement.classList.add('badge-secondary');
    } else {
        roiStrengthElement.classList.add('badge-danger');
    }
    
    // Update P&L correlation badge
    pnlStrengthElement.textContent = pnlCorrelationStrength;
    pnlStrengthElement.className = 'badge';
    if (pnlCorrelation > 0.5) {
        pnlStrengthElement.classList.add('badge-success');
    } else if (pnlCorrelation > 0.3) {
        pnlStrengthElement.classList.add('badge-primary');
    } else if (pnlCorrelation > 0.1) {
        pnlStrengthElement.classList.add('badge-info');
    } else if (pnlCorrelation > -0.1) {
        pnlStrengthElement.classList.add('badge-secondary');
    } else {
        pnlStrengthElement.classList.add('badge-danger');
    }
}

// Export data to CSV
function exportCSV() {
    // Build query parameters
    const queryParams = new URLSearchParams();
    if (currentStrategyId) {
        queryParams.append('strategy_id', currentStrategyId);
    }
    queryParams.append('days', currentPeriod);
    
    // Create download link
    const downloadUrl = `/strategy-analytics/api/export-confidence-data?${queryParams.toString()}`;
    
    // Create temporary link element and trigger download
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = 'confidence_data.csv';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// Get correlation strength description
function calculateCorrelation(x, y) {
    if (x.length !== y.length || x.length === 0) {
        return 0;
    }
    
    // Calculate means
    const xMean = x.reduce((sum, val) => sum + val, 0) / x.length;
    const yMean = y.reduce((sum, val) => sum + val, 0) / y.length;
    
    // Calculate numerator and denominators
    let numerator = 0;
    let xDenom = 0;
    let yDenom = 0;
    
    for (let i = 0; i < x.length; i++) {
        const xDiff = x[i] - xMean;
        const yDiff = y[i] - yMean;
        numerator += xDiff * yDiff;
        xDenom += xDiff * xDiff;
        yDenom += yDiff * yDiff;
    }
    
    // Calculate correlation
    if (xDenom === 0 || yDenom === 0) {
        return 0;
    }
    
    return numerator / Math.sqrt(xDenom * yDenom);
}

// Get correlation strength description
function getCorrelationStrength(correlation) {
    const absCorrelation = Math.abs(correlation);
    
    if (absCorrelation > 0.7) {
        return correlation > 0 ? 'Strong positive' : 'Strong negative';
    } else if (absCorrelation > 0.5) {
        return correlation > 0 ? 'Moderate positive' : 'Moderate negative';
    } else if (absCorrelation > 0.3) {
        return correlation > 0 ? 'Weak positive' : 'Weak negative';
    } else if (absCorrelation > 0.1) {
        return correlation > 0 ? 'Very weak positive' : 'Very weak negative';
    } else {
        return 'No correlation';
    }
}

// Format date for display
function formatDate(date) {
    const options = { year: 'numeric', month: 'short', day: 'numeric' };
    return new Date(date).toLocaleDateString(undefined, options);
}

// Function to generate sample data
function generateSampleData() {
    // Show the generation alert
    const alert = document.getElementById('dataGenerationAlert');
    const message = document.getElementById('dataGenerationMessage');
    message.textContent = 'Generating sample data with confidence-outcome correlation...';
    alert.style.display = 'block';
    
    // Disable generate button
    const generateBtn = document.getElementById('generateDataBtn');
    generateBtn.disabled = true;
    generateBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Generating...';
    
    // Make the API call
    fetch('/strategy-analytics/api/generate-sample-data?num_trades=100')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Show success message
                message.textContent = data.message;
                
                // Refresh the dashboard after a short delay
                setTimeout(() => {
                    refreshDashboard();
                    
                    // Re-enable the generate button
                    generateBtn.disabled = false;
                    generateBtn.innerHTML = '<i class="fas fa-chart-line"></i> Generate Sample Data';
                    
                    // Auto-hide the alert after 5 seconds
                    setTimeout(() => {
                        alert.style.display = 'none';
                    }, 5000);
                }, 1000);
            } else {
                // Show error message
                message.textContent = 'Error: ' + data.message;
                alert.classList.remove('alert-info');
                alert.classList.add('alert-danger');
                
                // Re-enable the generate button
                generateBtn.disabled = false;
                generateBtn.innerHTML = '<i class="fas fa-chart-line"></i> Generate Sample Data';
            }
        })
        .catch(error => {
            console.error('Error generating sample data:', error);
            
            // Show error message
            message.textContent = 'Error generating sample data. Check console for details.';
            alert.classList.remove('alert-info');
            alert.classList.add('alert-danger');
            
            // Re-enable the generate button
            generateBtn.disabled = false;
            generateBtn.innerHTML = '<i class="fas fa-chart-line"></i> Generate Sample Data';
        });
}

// Add auto-refresh toggle to the UI
function addAutoRefreshToggle() {
    // Create the toggle container
    const container = document.createElement('div');
    container.className = 'auto-refresh-container ml-3 d-inline-block';
    
    // Create the switch
    const toggleHTML = `
        <div class="custom-control custom-switch d-inline-block">
            <input type="checkbox" class="custom-control-input" id="autoRefreshToggle" ${autoRefreshEnabled ? 'checked' : ''}>
            <label class="custom-control-label" for="autoRefreshToggle">
                Auto-refresh
                <span id="connectionStatus" class="badge badge-pill badge-success ml-1" title="Connected to real-time updates">
                    <i class="fas fa-circle"></i>
                </span>
                <span id="lastUpdated" class="text-muted ml-2" style="font-size: 0.85em;"></span>
            </label>
        </div>
    `;
    
    container.innerHTML = toggleHTML;
    
    // Insert after the period select dropdown
    const periodSelect = document.getElementById('periodSelect');
    periodSelect.parentNode.insertBefore(container, periodSelect.nextSibling);
    
    // Add event listener
    document.getElementById('autoRefreshToggle').addEventListener('change', function() {
        autoRefreshEnabled = this.checked;
        
        if (autoRefreshEnabled) {
            startAutoRefresh();
        } else {
            stopAutoRefresh();
        }
    });
    
    // Update last updated timestamp
    updateLastUpdated();
}

// Start auto-refresh timer
function startAutoRefresh() {
    if (refreshTimer) {
        clearInterval(refreshTimer);
    }
    
    refreshTimer = setInterval(() => {
        if (autoRefreshEnabled) {
            refreshDashboard();
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

// Update last updated timestamp
function updateLastUpdated() {
    const element = document.getElementById('lastUpdated');
    if (element) {
        const now = new Date();
        const timeStr = now.toLocaleTimeString();
        element.textContent = `Updated: ${timeStr}`;
    }
}

// Update connection status indicator
function updateConnectionStatus(connected) {
    const status = document.getElementById('connectionStatus');
    if (status) {
        if (connected) {
            status.className = 'badge badge-pill badge-success ml-1';
            status.title = 'Connected to real-time updates';
        } else {
            status.className = 'badge badge-pill badge-danger ml-1';
            status.title = 'Disconnected from real-time updates';
        }
    }
}