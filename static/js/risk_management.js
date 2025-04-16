/**
 * Risk Management Configuration Panel
 * JavaScript to handle risk management functionality for OG Signal Bot
 */

document.addEventListener('DOMContentLoaded', function() {
    // Cache DOM elements
    const profilesTable = document.getElementById('risk-profiles-table');
    const newProfileForm = document.getElementById('new-profile-form');
    const editProfileForm = document.getElementById('edit-profile-form');
    const createDefaultProfileBtn = document.getElementById('create-default-profile');
    const positionSizingStrategySelect = document.getElementById('position-sizing-strategy');
    const customPositionSizingOptions = document.getElementById('custom-position-sizing-options');
    const confidenceWeightInput = document.getElementById('confidence-weight');
    const riskMetricsContainer = document.getElementById('risk-metrics-container');
    const saveRiskSettingsBtn = document.getElementById('save-risk-settings');

    // Setup tabbed interface for advanced settings
    setupTabbedInterface();
    
    // Initialize tooltips
    initializeTooltips();
    
    // Initialize charts
    initializeCharts();
    
    // Load risk metrics
    loadRiskMetrics();
    
    // Register form event handlers
    registerFormHandlers();
    
    // Register button event handlers
    registerButtonHandlers();
    
    // Setup risk heatmap
    setupRiskHeatmap();
    
    /**
     * Sets up tabbed interface for advanced risk settings
     */
    function setupTabbedInterface() {
        const tabs = document.querySelectorAll('.risk-tab');
        const tabContents = document.querySelectorAll('.risk-tab-content');
        
        tabs.forEach(tab => {
            tab.addEventListener('click', function(e) {
                e.preventDefault();
                
                // Remove active class from all tabs and contents
                tabs.forEach(t => t.classList.remove('active'));
                tabContents.forEach(c => c.classList.remove('show', 'active'));
                
                // Add active class to current tab
                this.classList.add('active');
                
                // Show corresponding content
                const targetId = this.getAttribute('data-bs-target');
                const targetContent = document.querySelector(targetId);
                if (targetContent) {
                    targetContent.classList.add('show', 'active');
                }
            });
        });
    }
    
    /**
     * Initialize tooltips for risk settings
     */
    function initializeTooltips() {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
    
    /**
     * Initialize charts for risk visualization
     */
    function initializeCharts() {
        // Win/Loss Ratio Chart
        if (document.getElementById('win-loss-chart')) {
            const winLossCtx = document.getElementById('win-loss-chart').getContext('2d');
            const winLossChart = new Chart(winLossCtx, {
                type: 'doughnut',
                data: {
                    labels: ['Wins', 'Losses', 'Breakeven'],
                    datasets: [{
                        data: [70, 25, 5],
                        backgroundColor: ['#198754', '#dc3545', '#ffc107'],
                        hoverOffset: 4
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                color: '#f8f9fa'
                            }
                        }
                    }
                }
            });
        }
        
        // Drawdown Chart
        if (document.getElementById('drawdown-chart')) {
            const drawdownCtx = document.getElementById('drawdown-chart').getContext('2d');
            const drawdownChart = new Chart(drawdownCtx, {
                type: 'line',
                data: {
                    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                    datasets: [{
                        label: 'Drawdown %',
                        data: [0, -2, -5, -3, -7, -4],
                        borderColor: '#dc3545',
                        backgroundColor: 'rgba(220, 53, 69, 0.1)',
                        tension: 0.4,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            grid: {
                                color: 'rgba(255, 255, 255, 0.1)'
                            },
                            ticks: {
                                color: '#f8f9fa'
                            }
                        },
                        x: {
                            grid: {
                                color: 'rgba(255, 255, 255, 0.1)'
                            },
                            ticks: {
                                color: '#f8f9fa'
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            labels: {
                                color: '#f8f9fa'
                            }
                        }
                    }
                }
            });
        }
    }
    
    /**
     * Load risk metrics from the server
     */
    function loadRiskMetrics() {
        fetch('/risk-management/api/metrics')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    updateRiskMetricsDisplay(data);
                } else {
                    console.error('Error loading risk metrics:', data.error);
                }
            })
            .catch(error => {
                console.error('Error:', error);
            });
    }
    
    /**
     * Update risk metrics display with data from the server
     */
    function updateRiskMetricsDisplay(data) {
        // Update dashboard values
        if (document.getElementById('current-drawdown')) {
            document.getElementById('current-drawdown').textContent = data.max_drawdown ? `${data.max_drawdown.toFixed(1)}%` : '0.0%';
        }
        
        if (document.getElementById('portfolio-heat')) {
            document.getElementById('portfolio-heat').textContent = data.portfolio_allocation ? `${data.portfolio_allocation.toFixed(1)}%` : '0.0%';
        }
        
        if (document.getElementById('win-rate')) {
            document.getElementById('win-rate').textContent = data.win_rate ? `${data.win_rate.toFixed(1)}%` : '0.0%';
        }
        
        if (document.getElementById('profit-factor')) {
            document.getElementById('profit-factor').textContent = data.profit_factor ? data.profit_factor.toFixed(2) : '0.00';
        }
        
        if (document.getElementById('avg-win-loss-ratio')) {
            const avgWin = data.avg_win || 0;
            const avgLoss = Math.abs(data.avg_loss || 1); // Avoid division by zero
            const ratio = avgWin / avgLoss;
            document.getElementById('avg-win-loss-ratio').textContent = ratio.toFixed(2);
        }
        
        if (document.getElementById('trading-status')) {
            // Update trading status based on risk limits
            const tradingStatus = document.getElementById('trading-status');
            if (data.trading_paused) {
                tradingStatus.textContent = 'Paused';
                tradingStatus.className = 'text-danger';
            } else if (data.trading_limited) {
                tradingStatus.textContent = 'Limited';
                tradingStatus.className = 'text-warning';
            } else {
                tradingStatus.textContent = 'Active';
                tradingStatus.className = 'text-success';
            }
        }
        
        // Update risk exposure chart if it exists
        if (data.strategy_allocation && document.getElementById('risk-exposure-container')) {
            updateRiskExposureChart(data.strategy_allocation);
        }
    }
    
    /**
     * Update the risk exposure progress bars
     */
    function updateRiskExposureChart(allocations) {
        const container = document.getElementById('risk-exposure-container');
        container.innerHTML = '';
        
        const colors = ['primary', 'success', 'info', 'warning', 'danger'];
        
        allocations.forEach((allocation, index) => {
            const color = colors[index % colors.length];
            const progressElement = document.createElement('div');
            progressElement.className = 'progress mb-2';
            progressElement.style.height = '20px';
            
            const progressBar = document.createElement('div');
            progressBar.className = `progress-bar bg-${color}`;
            progressBar.style.width = `${allocation.percentage}%`;
            progressBar.textContent = `${allocation.name} (${allocation.percentage}%)`;
            
            progressElement.appendChild(progressBar);
            container.appendChild(progressElement);
        });
    }
    
    /**
     * Register form handlers for new and edit profile forms
     */
    function registerFormHandlers() {
        // Handle new profile form submission
        if (newProfileForm) {
            newProfileForm.addEventListener('submit', function(e) {
                e.preventDefault();
                
                const formData = new FormData(this);
                const profileData = Object.fromEntries(formData.entries());
                
                // Convert checkbox values
                const checkboxes = this.querySelectorAll('input[type="checkbox"]');
                checkboxes.forEach(checkbox => {
                    profileData[checkbox.name] = checkbox.checked;
                });
                
                // Convert number inputs
                const numberInputs = this.querySelectorAll('input[type="number"]');
                numberInputs.forEach(input => {
                    profileData[input.name] = parseFloat(input.value);
                });
                
                submitProfile(profileData);
            });
        }
        
        // Handle edit profile form submission
        if (editProfileForm) {
            editProfileForm.addEventListener('submit', function(e) {
                e.preventDefault();
                
                const profileId = this.getAttribute('data-profile-id');
                const formData = new FormData(this);
                const profileData = Object.fromEntries(formData.entries());
                
                // Convert checkbox values
                const checkboxes = this.querySelectorAll('input[type="checkbox"]');
                checkboxes.forEach(checkbox => {
                    profileData[checkbox.name] = checkbox.checked;
                });
                
                // Convert number inputs
                const numberInputs = this.querySelectorAll('input[type="number"]');
                numberInputs.forEach(input => {
                    profileData[input.name] = parseFloat(input.value);
                });
                
                updateProfile(profileId, profileData);
            });
        }
        
        // Handle position sizing strategy change
        if (positionSizingStrategySelect) {
            positionSizingStrategySelect.addEventListener('change', function() {
                if (this.value === 'confidence_weighted') {
                    customPositionSizingOptions.classList.remove('d-none');
                } else {
                    customPositionSizingOptions.classList.add('d-none');
                }
            });
        }
    }
    
    /**
     * Register button event handlers
     */
    function registerButtonHandlers() {
        // Create default profile button
        if (createDefaultProfileBtn) {
            createDefaultProfileBtn.addEventListener('click', function() {
                fetch('/risk-management/api/profiles/default', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showAlert('success', 'Default risk profile created successfully');
                        location.reload();
                    } else {
                        showAlert('danger', data.error || 'Failed to create default profile');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    showAlert('danger', 'An error occurred while creating the default profile');
                });
            });
        }
        
        // Profile action buttons (activate, edit, delete)
        document.addEventListener('click', function(e) {
            // Activate button
            if (e.target.closest('.activate-profile')) {
                const button = e.target.closest('.activate-profile');
                const profileId = button.getAttribute('data-id');
                activateProfile(profileId);
            }
            
            // Edit button
            if (e.target.closest('.edit-profile')) {
                const button = e.target.closest('.edit-profile');
                const profileId = button.getAttribute('data-id');
                openEditProfileModal(profileId);
            }
            
            // Delete button
            if (e.target.closest('.delete-profile')) {
                const button = e.target.closest('.delete-profile');
                const profileId = button.getAttribute('data-id');
                
                if (confirm('Are you sure you want to delete this risk profile?')) {
                    deleteProfile(profileId);
                }
            }
        });
        
        // Save risk settings button
        if (saveRiskSettingsBtn) {
            saveRiskSettingsBtn.addEventListener('click', function() {
                // Get selected risk values
                const riskSettings = {
                    drawdown_pause_percent: parseFloat(document.getElementById('drawdown-pause').value || 7),
                    portfolio_allocation_limit: parseFloat(document.getElementById('portfolio-allocation-limit').value || 50),
                    position_sizing_strategy: document.getElementById('position-sizing-strategy').value,
                    confidence_weight: parseFloat(document.getElementById('confidence-weight').value || 0.3),
                    auto_hedging: document.getElementById('auto-hedging-checkbox').checked,
                    stop_loss_type: document.querySelector('input[name="stop-loss-type"]:checked').value
                };
                
                // Save risk settings to the server
                fetch('/risk-management/api/settings', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(riskSettings)
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showAlert('success', 'Risk settings saved successfully');
                    } else {
                        showAlert('danger', data.error || 'Failed to save risk settings');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    showAlert('danger', 'An error occurred while saving risk settings');
                });
            });
        }
    }
    
    /**
     * Submit a new profile to the server
     */
    function submitProfile(profileData) {
        fetch('/risk-management/api/profiles', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(profileData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showAlert('success', data.message || 'Profile created successfully');
                // Close modal and reload the page
                const modal = bootstrap.Modal.getInstance(document.getElementById('newProfileModal'));
                if (modal) {
                    modal.hide();
                }
                location.reload();
            } else {
                showAlert('danger', data.error || 'Failed to create profile');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('danger', 'An error occurred while creating the profile');
        });
    }
    
    /**
     * Update an existing profile
     */
    function updateProfile(profileId, profileData) {
        fetch(`/risk-management/api/profiles/${profileId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(profileData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showAlert('success', data.message || 'Profile updated successfully');
                // Close modal and reload the page
                const modal = bootstrap.Modal.getInstance(document.getElementById('editProfileModal'));
                if (modal) {
                    modal.hide();
                }
                location.reload();
            } else {
                showAlert('danger', data.error || 'Failed to update profile');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('danger', 'An error occurred while updating the profile');
        });
    }
    
    /**
     * Activate a profile
     */
    function activateProfile(profileId) {
        fetch(`/risk-management/api/profiles/${profileId}/activate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showAlert('success', data.message || 'Profile activated successfully');
                location.reload();
            } else {
                showAlert('danger', data.error || 'Failed to activate profile');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('danger', 'An error occurred while activating the profile');
        });
    }
    
    /**
     * Open edit profile modal with profile data
     */
    function openEditProfileModal(profileId) {
        fetch(`/risk-management/api/profiles/${profileId}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const profile = data.profile;
                    
                    // Set form action and profile ID
                    const form = document.getElementById('edit-profile-form');
                    form.setAttribute('data-profile-id', profile.id);
                    
                    // Set form values
                    form.querySelector('[name="name"]').value = profile.name;
                    form.querySelector('[name="description"]').value = profile.description;
                    form.querySelector('[name="max_position_size"]').value = profile.max_position_size;
                    form.querySelector('[name="max_positions"]').value = profile.max_positions;
                    form.querySelector('[name="max_daily_loss"]').value = profile.max_daily_loss;
                    form.querySelector('[name="max_position_loss"]').value = profile.max_position_loss;
                    form.querySelector('[name="stop_loss_percent"]').value = profile.stop_loss_percent;
                    form.querySelector('[name="take_profit_percent"]').value = profile.take_profit_percent;
                    form.querySelector('[name="max_daily_trades"]').value = profile.max_daily_trades;
                    form.querySelector('[name="auto_close_minutes"]').value = profile.auto_close_minutes;
                    form.querySelector('[name="min_strategy_confidence"]').value = profile.min_strategy_confidence;
                    form.querySelector('[name="is_active"]').checked = profile.is_active;
                    
                    // Set advanced fields if they exist
                    const dynamicSizingCheckbox = form.querySelector('[name="dynamic_sizing_enabled"]');
                    if (dynamicSizingCheckbox) {
                        dynamicSizingCheckbox.checked = profile.dynamic_sizing_enabled;
                    }
                    
                    const minContractsInput = form.querySelector('[name="min_contracts"]');
                    if (minContractsInput) {
                        minContractsInput.value = profile.min_contracts;
                    }
                    
                    const maxContractsInput = form.querySelector('[name="max_contracts"]');
                    if (maxContractsInput) {
                        maxContractsInput.value = profile.max_contracts;
                    }
                    
                    const confidenceWeightInput = form.querySelector('[name="confidence_weight"]');
                    if (confidenceWeightInput) {
                        confidenceWeightInput.value = profile.confidence_weight;
                    }
                    
                    // Open modal
                    const modal = new bootstrap.Modal(document.getElementById('editProfileModal'));
                    modal.show();
                } else {
                    showAlert('danger', data.error || 'Failed to load profile');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showAlert('danger', 'An error occurred while loading the profile');
            });
    }
    
    /**
     * Delete a profile
     */
    function deleteProfile(profileId) {
        fetch(`/risk-management/api/profiles/${profileId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showAlert('success', data.message || 'Profile deleted successfully');
                location.reload();
            } else {
                showAlert('danger', data.error || 'Failed to delete profile');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('danger', 'An error occurred while deleting the profile');
        });
    }
    
    /**
     * Setup risk heatmap visualization
     */
    function setupRiskHeatmap() {
        if (!document.getElementById('risk-heatmap')) return;
        
        // Create sample heatmap data
        const strategies = ['OG Strategy', 'EMA Cloud', 'Volume Analysis', 'Price Action'];
        const symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA'];
        
        // Generate a table for the heatmap
        const table = document.createElement('table');
        table.className = 'table table-dark table-bordered risk-heatmap-table';
        
        // Create header row with symbols
        const thead = document.createElement('thead');
        const headerRow = document.createElement('tr');
        headerRow.innerHTML = '<th></th>'; // Empty corner cell
        
        symbols.forEach(symbol => {
            const th = document.createElement('th');
            th.textContent = symbol;
            headerRow.appendChild(th);
        });
        
        thead.appendChild(headerRow);
        table.appendChild(thead);
        
        // Create body rows with strategies and risk values
        const tbody = document.createElement('tbody');
        
        strategies.forEach(strategy => {
            const row = document.createElement('tr');
            
            // Add strategy name as first cell
            const firstCell = document.createElement('td');
            firstCell.textContent = strategy;
            firstCell.className = 'strategy-name';
            row.appendChild(firstCell);
            
            // Add risk cells for each symbol
            symbols.forEach(symbol => {
                const td = document.createElement('td');
                const riskValue = Math.floor(Math.random() * 100); // Random value 0-100
                
                // Set color based on risk value
                let colorClass = 'bg-success';
                if (riskValue > 70) {
                    colorClass = 'bg-danger';
                } else if (riskValue > 40) {
                    colorClass = 'bg-warning';
                }
                
                td.className = colorClass;
                td.setAttribute('data-value', riskValue);
                td.textContent = riskValue;
                row.appendChild(td);
            });
            
            tbody.appendChild(row);
        });
        
        table.appendChild(tbody);
        document.getElementById('risk-heatmap').appendChild(table);
    }
    
    /**
     * Show alert message
     */
    function showAlert(type, message) {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.role = 'alert';
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        // Insert the alert at the top of the container
        const container = document.querySelector('.container');
        container.insertBefore(alertDiv, container.firstChild);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            alertDiv.classList.remove('show');
            setTimeout(() => alertDiv.remove(), 300);
        }, 5000);
    }
});