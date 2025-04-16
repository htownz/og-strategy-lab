/**
 * Risk Dashboard JavaScript
 * 
 * This file provides the client-side functionality for the risk dashboard,
 * connecting to the risk API endpoints and updating the UI with real-time
 * risk data.
 */

// Configuration
const API_ENDPOINTS = {
    all: '/risk/api/all',
    portfolio: '/risk/api/portfolio',
    positions: '/risk/api/positions',
    market: '/risk/api/market',
    alerts: '/risk/api/alerts',
    enhanced: '/risk/api/enhanced',
    positionSize: '/risk/api/position_size'
};

const REFRESH_INTERVAL = 60000; // 1 minute refresh interval
let refreshTimer = null;
let charts = {};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize dashboard
    initializeDashboard();
    
    // Set up refresh button
    document.getElementById('refresh-button')?.addEventListener('click', function() {
        this.disabled = true;
        this.innerHTML = '<i class="fa fa-spinner fa-spin me-1"></i> Refreshing...';
        
        refreshDashboard().finally(() => {
            setTimeout(() => {
                this.disabled = false;
                this.innerHTML = '<i class="fa fa-sync-alt me-1"></i> Refresh';
            }, 500);
        });
    });
    
    // Set up auto-refresh
    startAutoRefresh();
    
    // Set up position size calculator if available
    setupPositionSizeCalculator();
});

// Initialize the dashboard by loading data and setting up charts
function initializeDashboard() {
    console.log('Initializing risk dashboard...');
    
    // Initialize charts if they exist on the page
    if (typeof ApexCharts !== 'undefined') {
        initializeCharts();
    }
    
    // Load initial data
    refreshDashboard();
}

// Refresh all dashboard data
async function refreshDashboard() {
    try {
        const response = await fetch(API_ENDPOINTS.all);
        if (!response.ok) {
            throw new Error(`API response: ${response.status}`);
        }
        
        const data = await response.json();
        if (!data.success) {
            throw new Error('API returned unsuccessful response');
        }
        
        // Update the dashboard with the data
        updateDashboard(data.data);
        updateLastUpdated(data.timestamp);
        
        return true;
    } catch (error) {
        console.error('Error refreshing dashboard:', error);
        showErrorMessage('Failed to load risk data. Please try again later.');
        return false;
    }
}

// Update the dashboard with risk data
function updateDashboard(data) {
    // Update each section of the dashboard
    updateSummaryMetrics(data.portfolio);
    updatePositionRisks(data.positions);
    updateMarketIndicators(data.market);
    updateRiskAlerts(data.alerts);
    updateCharts(data.portfolio, data.positions, data.market);
}

// Format utilities
function formatPercent(value, decimals = 1) {
    if (value === null || value === undefined) return '--';
    return (value * 100).toFixed(decimals) + '%';
}

function formatNumber(value, decimals = 2) {
    if (value === null || value === undefined) return '--';
    return parseFloat(value).toFixed(decimals);
}

function formatCurrency(value, decimals = 0) {
    if (value === null || value === undefined) return '--';
    return '$' + parseFloat(value).toFixed(decimals).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

// Update UI timestamp
function updateLastUpdated(timestamp) {
    const element = document.getElementById('last-update-time');
    if (!element) return;
    
    if (!timestamp) {
        element.textContent = 'Never';
        return;
    }
    
    try {
        const date = new Date(timestamp);
        element.textContent = date.toLocaleTimeString();
    } catch (e) {
        element.textContent = timestamp;
    }
}

// Start auto-refresh timer
function startAutoRefresh() {
    if (refreshTimer) {
        clearInterval(refreshTimer);
    }
    
    refreshTimer = setInterval(() => {
        refreshDashboard();
    }, REFRESH_INTERVAL);
    
    console.log(`Auto-refresh started (interval: ${REFRESH_INTERVAL / 1000}s)`);
}

// Stop auto-refresh timer
function stopAutoRefresh() {
    if (refreshTimer) {
        clearInterval(refreshTimer);
        refreshTimer = null;
        console.log('Auto-refresh stopped');
    }
}

// Show error message
function showErrorMessage(message) {
    // Check if error container exists, if not create one
    let errorContainer = document.getElementById('error-container');
    if (!errorContainer) {
        errorContainer = document.createElement('div');
        errorContainer.id = 'error-container';
        errorContainer.className = 'alert alert-danger alert-dismissible fade show m-3';
        errorContainer.innerHTML = `
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            <div id="error-message"></div>
        `;
        document.body.insertBefore(errorContainer, document.body.firstChild);
    }
    
    // Set error message
    const errorMessage = document.getElementById('error-message');
    if (errorMessage) {
        errorMessage.textContent = message;
    }
    
    // Show the error container
    errorContainer.style.display = 'block';
}

// Position Size Calculator Setup
function setupPositionSizeCalculator() {
    const calculatorForm = document.getElementById('position-size-calculator');
    if (!calculatorForm) return;
    
    calculatorForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const symbol = document.getElementById('symbol-input').value.trim().toUpperCase();
        const confidence = parseFloat(document.getElementById('confidence-input').value);
        
        if (!symbol) {
            showErrorMessage('Please enter a valid symbol');
            return;
        }
        
        if (isNaN(confidence) || confidence < 0 || confidence > 1) {
            showErrorMessage('Confidence must be a number between 0 and 1');
            return;
        }
        
        // Show loading state
        const submitButton = calculatorForm.querySelector('button[type="submit"]');
        const originalButtonText = submitButton.innerHTML;
        submitButton.disabled = true;
        submitButton.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Calculating...';
        
        try {
            const response = await fetch(`${API_ENDPOINTS.positionSize}?symbol=${symbol}&confidence=${confidence}`);
            if (!response.ok) {
                throw new Error(`API response: ${response.status}`);
            }
            
            const data = await response.json();
            if (!data.success) {
                throw new Error(data.error || 'Failed to calculate position size');
            }
            
            // Update results
            updatePositionSizeResults(data.data);
            
        } catch (error) {
            console.error('Error calculating position size:', error);
            showErrorMessage('Failed to calculate position size. Please try again.');
        } finally {
            // Restore button state
            submitButton.disabled = false;
            submitButton.innerHTML = originalButtonText;
        }
    });
}

// Update Position Size Results
function updatePositionSizeResults(data) {
    const resultsContainer = document.getElementById('position-size-results');
    if (!resultsContainer) return;
    
    // Calculate position size
    const recommendedSize = formatCurrency(data.recommended_size);
    const maxSize = formatCurrency(data.max_size);
    const sharpeRatio = formatNumber(data.sharpe_ratio);
    const sectorExposure = formatPercent(data.sector_exposure);
    
    // Update results
    resultsContainer.innerHTML = `
        <div class="card mt-3">
            <div class="card-header bg-primary text-white">
                Position Size Recommendation
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-6">
                        <h5>Recommended Size</h5>
                        <div class="h3 mb-3">${recommendedSize}</div>
                        <p class="text-muted small">${data.reason}</p>
                    </div>
                    <div class="col-md-6">
                        <div class="mb-2">
                            <span class="text-muted">Maximum Size:</span>
                            <span class="float-end">${maxSize}</span>
                        </div>
                        <div class="mb-2">
                            <span class="text-muted">Sharpe Ratio:</span>
                            <span class="float-end">${sharpeRatio}</span>
                        </div>
                        <div class="mb-2">
                            <span class="text-muted">Win Rate:</span>
                            <span class="float-end">${formatPercent(data.win_rate)}</span>
                        </div>
                        <div class="mb-2">
                            <span class="text-muted">${data.sector} Exposure:</span>
                            <span class="float-end">${sectorExposure}</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Show results container
    resultsContainer.style.display = 'block';
    
    // Scroll to results
    resultsContainer.scrollIntoView({ behavior: 'smooth' });
}

// Chart Initialization (if ApexCharts is available)
function initializeCharts() {
    // Placeholder - Chart initialization code will go here
    // This will be different based on which page is loaded
    
    // Check for specific chart containers
    if (document.getElementById('portfolio-risk-gauge')) {
        // We're on the main dashboard
        initializeDashboardCharts();
    } else if (document.getElementById('portfolio-performance-chart')) {
        // We're on the portfolio page
        initializePortfolioCharts();
    } else if (document.getElementById('positions-risk-chart')) {
        // We're on the positions page
        initializePositionsCharts();
    }
}

// Specific implementations for different pages
function initializeDashboardCharts() {
    // Dashboard charts initialization
    console.log('Initializing dashboard charts...');
}

function initializePortfolioCharts() {
    // Portfolio charts initialization
    console.log('Initializing portfolio charts...');
}

function initializePositionsCharts() {
    // Positions charts initialization
    console.log('Initializing positions charts...');
}

// Dashboard update functions
function updateSummaryMetrics(portfolio) {
    // Update summary metrics in the dashboard
    // Implementation depends on the elements present in the current page
}

function updatePositionRisks(positions) {
    // Update position risks in the dashboard
    // Implementation depends on the elements present in the current page
}

function updateMarketIndicators(market) {
    // Update market indicators in the dashboard
    // Implementation depends on the elements present in the current page
}

function updateRiskAlerts(alerts) {
    // Update risk alerts in the dashboard
    // Implementation depends on the elements present in the current page
}

function updateCharts(portfolio, positions, market) {
    // Update charts in the dashboard
    // Implementation depends on the elements present in the current page
}