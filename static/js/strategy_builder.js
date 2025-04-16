/**
 * OG Signal Bot - Interactive Strategy Builder
 * 
 * This script implements a drag-and-drop interface for building
 * custom trading strategies using components from the strategy registry.
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize variables
    let components = {};
    let selectedComponent = null;
    let strategyData = {
        name: '',
        description: '',
        type: 'options',
        timeframe: '1d',
        components: [],
        connections: []
    };

    // Load components from the backend
    fetchComponents();

    // Initialize drag & drop
    initDragAndDrop();

    // Initialize event handlers
    initEventHandlers();

    /**
     * Fetch available components from the backend
     */
    function fetchComponents() {
        // Fetch components from the API endpoint
        fetch('/api/strategy-components')
            .then(response => response.json())
            .then(data => {
                if (data && Object.keys(data).length > 0) {
                    components = data;
                    renderComponentLists();
                } else {
                    console.warn('No components returned from server, using demo data');
                    useDemoComponents();
                }
            })
            .catch(error => {
                console.error('Error fetching components:', error);
                // Use demo data as fallback
                useDemoComponents();
            });
    }

    /**
     * Use demo components for testing
     */
    function useDemoComponents() {
        components = {
            indicators: [
                { id: 'ema', name: 'EMA', description: 'Exponential Moving Average', properties: { period: { type: 'number', default: 9 } } },
                { id: 'ema_cloud', name: 'EMA Cloud', description: 'EMA Cloud with two periods', properties: { fast_period: { type: 'number', default: 9 }, slow_period: { type: 'number', default: 21 } } },
                { id: 'order_block', name: 'Order Block', description: 'Support/Resistance order block detection', properties: { lookback: { type: 'number', default: 10 } } },
                { id: 'fvg', name: 'Fair Value Gap', description: 'Fair Value Gap detection', properties: { min_gap: { type: 'number', default: 0.5 } } },
                { id: 'volume_profile', name: 'Volume Profile', description: 'Volume profile analysis', properties: { levels: { type: 'number', default: 10 } } }
            ],
            filters: [
                { id: 'symbol_filter', name: 'Symbol Filter', description: 'Filter by ticker symbol', properties: { symbols: { type: 'string', default: 'SPY,QQQ,AAPL' } } },
                { id: 'price_range', name: 'Price Range', description: 'Filter by price range', properties: { min_price: { type: 'number', default: 0 }, max_price: { type: 'number', default: 1000 } } },
                { id: 'time_filter', name: 'Time Filter', description: 'Filter by market hours', properties: { market_hours_only: { type: 'boolean', default: true } } }
            ],
            conditions: [
                { id: 'price_above', name: 'Price Above', description: 'Check if price is above indicator', properties: { buffer: { type: 'number', default: 0 } } },
                { id: 'price_below', name: 'Price Below', description: 'Check if price is below indicator', properties: { buffer: { type: 'number', default: 0 } } },
                { id: 'crossover', name: 'Crossover', description: 'Detect when one line crosses over another', properties: { direction: { type: 'select', default: 'bullish', options: ['bullish', 'bearish', 'both'] } } },
                { id: 'volume_surge', name: 'Volume Surge', description: 'Detect unusual volume increase', properties: { threshold: { type: 'number', default: 200 } } }
            ],
            actions: [
                { id: 'alert', name: 'Alert', description: 'Send alert notification', properties: { channels: { type: 'select', default: 'all', options: ['telegram', 'email', 'ui', 'all'] } } },
                { id: 'paper_trade', name: 'Paper Trade', description: 'Execute paper trade', properties: { position_size: { type: 'select', default: 'fixed', options: ['fixed', 'risk_based', 'confidence_based'] } } },
                { id: 'live_trade', name: 'Live Trade', description: 'Execute a live trade', properties: { confirmation: { type: 'boolean', default: true }, position_size: { type: 'select', default: 'risk_based', options: ['fixed', 'risk_based', 'confidence_based'] } } }
            ]
        };
        
        renderComponentLists();
    }

    /**
     * Render component lists in the sidebar
     */
    function renderComponentLists() {
        renderComponentCategory('indicators', '.indicators-list');
        renderComponentCategory('filters', '.filters-list');
        renderComponentCategory('conditions', '.conditions-list');
        renderComponentCategory('actions', '.actions-list');
    }

    /**
     * Render a specific category of components
     */
    function renderComponentCategory(category, selector) {
        const container = document.querySelector(selector);
        if (!container) return;
        
        container.innerHTML = '';
        
        if (!components[category] || !components[category].length) {
            container.innerHTML = '<div class="text-muted text-center py-2">No components available</div>';
            return;
        }
        
        components[category].forEach(component => {
            const componentEl = document.createElement('div');
            componentEl.className = 'component-card mb-2 p-2 border rounded';
            componentEl.setAttribute('draggable', 'true');
            componentEl.setAttribute('data-component-id', component.id);
            componentEl.setAttribute('data-component-type', category);
            
            componentEl.innerHTML = `
                <div class="d-flex justify-content-between align-items-center">
                    <strong>${component.name}</strong>
                    <span class="badge bg-secondary">${category.slice(0, -1)}</span>
                </div>
                <small class="text-muted">${component.description || ''}</small>
            `;
            
            componentEl.addEventListener('dragstart', handleDragStart);
            container.appendChild(componentEl);
        });
    }

    /**
     * Initialize drag and drop functionality
     */
    function initDragAndDrop() {
        const canvas = document.getElementById('strategyCanvas');
        
        canvas.addEventListener('dragover', function(e) {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'copy';
        });
        
        canvas.addEventListener('drop', handleDrop);
    }

    /**
     * Handle the start of a drag operation
     */
    function handleDragStart(e) {
        const componentId = e.target.getAttribute('data-component-id');
        const componentType = e.target.getAttribute('data-component-type');
        
        e.dataTransfer.setData('application/json', JSON.stringify({
            id: componentId,
            type: componentType
        }));
        
        e.dataTransfer.effectAllowed = 'copy';
    }

    /**
     * Handle dropping a component onto the canvas
     */
    function handleDrop(e) {
        e.preventDefault();
        
        try {
            const data = JSON.parse(e.dataTransfer.getData('application/json'));
            
            if (!data || !data.id || !data.type) {
                console.error('Invalid drop data');
                return;
            }
            
            // Generate a unique instance ID for this component
            const instanceId = `${data.type}_${data.id}_${Date.now()}`;
            
            // Get component data from our components object
            const componentData = components[data.type].find(c => c.id === data.id);
            
            if (!componentData) {
                console.error('Component not found:', data.id, data.type);
                return;
            }
            
            // Create component on canvas
            addComponentToCanvas(instanceId, componentData, data.type, e.clientX, e.clientY);
            
            // Add to strategy data
            strategyData.components.push({
                id: instanceId,
                type: data.type,
                component: data.id,
                properties: getDefaultProperties(componentData),
                position: {
                    x: e.clientX - canvas.getBoundingClientRect().left,
                    y: e.clientY - canvas.getBoundingClientRect().top
                }
            });
            
            // Hide placeholder if this is the first component
            if (strategyData.components.length === 1) {
                document.querySelector('.canvas-placeholder').style.display = 'none';
            }
            
            // Update strategy output
            updateStrategyOutput();
        } catch (error) {
            console.error('Error handling drop:', error);
        }
    }

    /**
     * Add a component to the strategy canvas
     * @param {string} instanceId - Unique ID for this component instance
     * @param {object} componentData - Component data (from registry or template)
     * @param {string} componentType - Component type (indicators, filters, conditions, actions)
     * @param {number|string} clientX - X position or x coordinate
     * @param {number|string} clientY - Y position or y coordinate
     */
    function addComponentToCanvas(instanceId, componentData, componentType, clientX, clientY) {
        const canvas = document.getElementById('strategyCanvas');
        const canvasRect = canvas.getBoundingClientRect();
        
        // Get component template
        const template = document.querySelector('#componentTemplates .component-item').cloneNode(true);
        
        template.id = instanceId;
        template.setAttribute('data-instance-id', instanceId);
        template.setAttribute('data-component-id', componentData.id || componentData.templateId);
        template.setAttribute('data-component-type', componentType);
        
        // Handle positions from template (numbers) or drag operation (client coordinates)
        let posX, posY;
        
        if (typeof clientX === 'number' && typeof clientY === 'number') {
            // If they're regular numbers, treat as client coordinates from a drop event
            posX = clientX - canvasRect.left;
            posY = clientY - canvasRect.top;
        } else if (componentData.x !== undefined && componentData.y !== undefined) {
            // If component has x,y properties, use those directly (template case)
            posX = componentData.x;
            posY = componentData.y;
            
            // Also add to strategy data if this is from a template
            if (!strategyData.components.some(c => c.id === instanceId)) {
                strategyData.components.push({
                    id: instanceId,
                    type: componentType, 
                    component: componentData.templateId || componentData.id,
                    properties: componentData.properties || getDefaultProperties(componentData),
                    position: { x: posX, y: posY }
                });
            }
        } else {
            // Default fallback - center of canvas
            posX = canvas.clientWidth / 2;
            posY = canvas.clientHeight / 2;
        }
        
        // Set position
        template.style.position = 'absolute';
        template.style.left = posX + 'px';
        template.style.top = posY + 'px';
        
        // Style based on component type
        template.classList.add(`component-${componentType.slice(0, -1)}`);
        
        // Set title and content
        template.querySelector('.component-title').textContent = componentData.name;
        
        // Add a brief description
        const body = template.querySelector('.component-body');
        body.innerHTML = `<small class="text-muted">${componentData.description || ''}</small>`;
        
        // Set up event handlers
        template.addEventListener('click', (e) => {
            e.stopPropagation();
            selectComponent(instanceId);
        });
        
        template.querySelector('.component-config').addEventListener('click', (e) => {
            e.stopPropagation();
            openComponentConfig(instanceId);
        });
        
        template.querySelector('.component-remove').addEventListener('click', (e) => {
            e.stopPropagation();
            removeComponent(instanceId);
        });
        
        // Make draggable
        template.addEventListener('mousedown', startDragComponent);
        
        // Add to canvas
        canvas.appendChild(template);
        
        // Hide placeholder since we have components
        document.querySelector('.canvas-placeholder').style.display = 'none';
        
        return template;
    }

    /**
     * Make components draggable on the canvas
     */
    function startDragComponent(e) {
        e.stopPropagation();
        
        if (e.target.closest('.component-controls')) {
            return; // Don't drag if clicking controls
        }
        
        const component = e.currentTarget;
        const canvas = document.getElementById('strategyCanvas');
        
        // Initial positions
        const startX = e.clientX;
        const startY = e.clientY;
        const compLeft = parseInt(component.style.left || '0');
        const compTop = parseInt(component.style.top || '0');
        
        // Move function
        function moveComponent(moveEvent) {
            const newLeft = compLeft + (moveEvent.clientX - startX);
            const newTop = compTop + (moveEvent.clientY - startY);
            
            component.style.left = newLeft + 'px';
            component.style.top = newTop + 'px';
            
            // Update position in strategy data
            const instanceId = component.getAttribute('data-instance-id');
            const comp = strategyData.components.find(c => c.id === instanceId);
            if (comp) {
                comp.position = { x: newLeft, y: newTop };
            }
        }
        
        // End drag function
        function endDragComponent() {
            document.removeEventListener('mousemove', moveComponent);
            document.removeEventListener('mouseup', endDragComponent);
            
            // Update strategy output
            updateStrategyOutput();
        }
        
        // Add event listeners
        document.addEventListener('mousemove', moveComponent);
        document.addEventListener('mouseup', endDragComponent);
    }

    /**
     * Get default properties for a component
     */
    function getDefaultProperties(componentData) {
        const defaults = {};
        
        if (componentData.properties) {
            Object.keys(componentData.properties).forEach(prop => {
                defaults[prop] = componentData.properties[prop].default;
            });
        }
        
        return defaults;
    }

    /**
     * Select a component on the canvas
     */
    function selectComponent(instanceId) {
        // Deselect any currently selected component
        const selectedElements = document.querySelectorAll('.component-item.selected');
        selectedElements.forEach(el => el.classList.remove('selected'));
        
        // Select the new component
        const component = document.getElementById(instanceId);
        if (component) {
            component.classList.add('selected');
            selectedComponent = instanceId;
            
            // Show properties
            showComponentProperties(instanceId);
        }
    }

    /**
     * Show properties for the selected component
     */
    function showComponentProperties(instanceId) {
        const propertiesPanel = document.getElementById('propertiesPanel');
        const component = strategyData.components.find(c => c.id === instanceId);
        
        if (!component) {
            propertiesPanel.innerHTML = '<p class="text-muted">Select a component to edit its properties</p>';
            return;
        }
        
        // Find the component definition
        const componentDef = components[component.type].find(c => c.id === component.component);
        
        if (!componentDef || !componentDef.properties) {
            propertiesPanel.innerHTML = '<p class="text-muted">No editable properties for this component</p>';
            return;
        }
        
        // Build properties form
        let formHtml = `<form id="propertiesForm">
            <input type="hidden" id="propInstanceId" value="${instanceId}">
            <h6>${componentDef.name} Properties</h6>`;
        
        Object.keys(componentDef.properties).forEach(propName => {
            const prop = componentDef.properties[propName];
            const value = component.properties[propName];
            
            formHtml += buildPropertyInput(propName, prop, value);
        });
        
        formHtml += `<button type="button" class="btn btn-sm btn-primary mt-2" id="saveProperties">Apply Changes</button>
        </form>`;
        
        propertiesPanel.innerHTML = formHtml;
        
        // Add event listener to save button
        document.getElementById('saveProperties').addEventListener('click', saveProperties);
    }

    /**
     * Build an input control for a property
     */
    function buildPropertyInput(name, property, value) {
        const labelText = formatLabelText(name);
        
        switch (property.type) {
            case 'boolean':
                return `
                <div class="form-check mb-2">
                    <input class="form-check-input" type="checkbox" id="prop_${name}" ${value ? 'checked' : ''}>
                    <label class="form-check-label" for="prop_${name}">${labelText}</label>
                </div>`;
            
            case 'number':
                return `
                <div class="mb-2">
                    <label for="prop_${name}" class="form-label">${labelText}</label>
                    <input type="number" class="form-control form-control-sm" id="prop_${name}" value="${value}">
                </div>`;
            
            case 'select':
                let options = '';
                property.options.forEach(option => {
                    options += `<option value="${option}" ${value === option ? 'selected' : ''}>${formatLabelText(option)}</option>`;
                });
                
                return `
                <div class="mb-2">
                    <label for="prop_${name}" class="form-label">${labelText}</label>
                    <select class="form-select form-select-sm" id="prop_${name}">${options}</select>
                </div>`;
            
            case 'string':
            default:
                return `
                <div class="mb-2">
                    <label for="prop_${name}" class="form-label">${labelText}</label>
                    <input type="text" class="form-control form-control-sm" id="prop_${name}" value="${value}">
                </div>`;
        }
    }

    /**
     * Format a property name as a label
     */
    function formatLabelText(str) {
        return str
            .replace(/_/g, ' ')
            .replace(/\b\w/g, l => l.toUpperCase());
    }

    /**
     * Save properties from the properties panel
     */
    function saveProperties() {
        const instanceId = document.getElementById('propInstanceId').value;
        const component = strategyData.components.find(c => c.id === instanceId);
        
        if (!component) return;
        
        // Find component definition
        const componentDef = components[component.type].find(c => c.id === component.component);
        
        if (!componentDef || !componentDef.properties) return;
        
        // Update properties
        Object.keys(componentDef.properties).forEach(propName => {
            const prop = componentDef.properties[propName];
            const inputEl = document.getElementById(`prop_${propName}`);
            
            if (!inputEl) return;
            
            switch (prop.type) {
                case 'boolean':
                    component.properties[propName] = inputEl.checked;
                    break;
                    
                case 'number':
                    component.properties[propName] = parseFloat(inputEl.value);
                    break;
                    
                case 'select':
                case 'string':
                default:
                    component.properties[propName] = inputEl.value;
                    break;
            }
        });
        
        // Update strategy output
        updateStrategyOutput();
    }

    /**
     * Open component configuration modal
     */
    function openComponentConfig(instanceId) {
        const component = strategyData.components.find(c => c.id === instanceId);
        
        if (!component) return;
        
        // Find component definition
        const componentDef = components[component.type].find(c => c.id === component.component);
        
        if (!componentDef) return;
        
        // Set modal title
        const modalTitle = document.getElementById('configModalLabel');
        modalTitle.textContent = `Configure ${componentDef.name}`;
        
        // Build form content
        const formContainer = document.getElementById('componentConfigForm');
        
        if (!componentDef.properties || Object.keys(componentDef.properties).length === 0) {
            formContainer.innerHTML = '<p class="text-muted">This component has no configurable properties.</p>';
        } else {
            let formHtml = `<form id="configForm">
                <input type="hidden" id="configInstanceId" value="${instanceId}">`;
            
            Object.keys(componentDef.properties).forEach(propName => {
                const prop = componentDef.properties[propName];
                const value = component.properties[propName];
                
                formHtml += buildPropertyInput(propName, prop, value);
            });
            
            formHtml += '</form>';
            formContainer.innerHTML = formHtml;
        }
        
        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('componentConfigModal'));
        modal.show();
        
        // Setup save handler
        document.getElementById('saveComponentConfig').onclick = function() {
            saveComponentConfig();
            modal.hide();
        };
    }

    /**
     * Save component configuration from modal
     */
    function saveComponentConfig() {
        const instanceId = document.getElementById('configInstanceId').value;
        const component = strategyData.components.find(c => c.id === instanceId);
        
        if (!component) return;
        
        // Find component definition
        const componentDef = components[component.type].find(c => c.id === component.component);
        
        if (!componentDef || !componentDef.properties) return;
        
        // Update properties
        Object.keys(componentDef.properties).forEach(propName => {
            const prop = componentDef.properties[propName];
            const inputEl = document.getElementById(`prop_${propName}`);
            
            if (!inputEl) return;
            
            switch (prop.type) {
                case 'boolean':
                    component.properties[propName] = inputEl.checked;
                    break;
                    
                case 'number':
                    component.properties[propName] = parseFloat(inputEl.value);
                    break;
                    
                case 'select':
                case 'string':
                default:
                    component.properties[propName] = inputEl.value;
                    break;
            }
        });
        
        // Update strategy output
        updateStrategyOutput();
    }

    /**
     * Remove a component from the canvas
     */
    function removeComponent(instanceId) {
        // Remove from DOM
        const component = document.getElementById(instanceId);
        if (component) {
            component.remove();
        }
        
        // Remove from strategy data
        const index = strategyData.components.findIndex(c => c.id === instanceId);
        if (index !== -1) {
            strategyData.components.splice(index, 1);
        }
        
        // Remove any connections involving this component
        strategyData.connections = strategyData.connections.filter(connection => {
            return connection.from !== instanceId && connection.to !== instanceId;
        });
        
        // Reset properties panel if this was the selected component
        if (selectedComponent === instanceId) {
            selectedComponent = null;
            document.getElementById('propertiesPanel').innerHTML = 
                '<p class="text-muted">Select a component to edit its properties</p>';
        }
        
        // Show placeholder if no more components
        if (strategyData.components.length === 0) {
            document.querySelector('.canvas-placeholder').style.display = 'block';
        }
        
        // Update strategy output
        updateStrategyOutput();
    }

    /**
     * Initialize event handlers for UI controls
     */
    function initEventHandlers() {
        // Clear canvas button
        document.getElementById('clearCanvas').addEventListener('click', clearCanvas);
        
        // Validate strategy button
        document.getElementById('validateStrategy').addEventListener('click', validateStrategy);
        
        // Save strategy button
        document.getElementById('saveStrategy').addEventListener('click', saveStrategy);
        
        // Test strategy button
        document.getElementById('testStrategy').addEventListener('click', testStrategy);
        
        // Template select change
        document.getElementById('templateSelect').addEventListener('change', function(e) {
            // Just save the selection, don't load immediately
            console.log('Template selected:', e.target.value);
        });
        
        // Template load button
        document.getElementById('loadTemplate').addEventListener('click', loadSelectedTemplate);
        
        // Strategy form fields
        document.getElementById('strategyName').addEventListener('input', e => {
            strategyData.name = e.target.value;
            updateStrategyOutput();
        });
        
        document.getElementById('strategyDescription').addEventListener('input', e => {
            strategyData.description = e.target.value;
            updateStrategyOutput();
        });
        
        document.getElementById('strategyType').addEventListener('change', e => {
            strategyData.type = e.target.value;
            updateStrategyOutput();
        });
        
        document.getElementById('timeframe').addEventListener('change', e => {
            strategyData.timeframe = e.target.value;
            updateStrategyOutput();
        });
    }

    /**
     * Clear all components from the canvas
     * @param {boolean} skipConfirmation - If true, skips the confirmation dialog
     */
    function clearCanvas(skipConfirmation = false) {
        // Confirm unless skipConfirmation is true
        if (!skipConfirmation && !confirm('Are you sure you want to clear the strategy canvas? This cannot be undone.')) {
            return;
        }
        
        // Remove all components from the DOM
        const components = document.querySelectorAll('#strategyCanvas .component-item');
        components.forEach(comp => comp.remove());
        
        // Reset strategy data
        strategyData.components = [];
        strategyData.connections = [];
        
        // Reset properties panel
        selectedComponent = null;
        document.getElementById('propertiesPanel').innerHTML = 
            '<p class="text-muted">Select a component to edit its properties</p>';
        
        // Show placeholder
        document.querySelector('.canvas-placeholder').style.display = 'block';
        
        // Update strategy output
        updateStrategyOutput();
    }

    /**
     * Validate the current strategy
     */
    function validateStrategy() {
        // Check if there are any components
        if (strategyData.components.length === 0) {
            alert('Strategy is empty. Please add at least one component.');
            return false;
        }
        
        // Check if there is at least one action
        const hasAction = strategyData.components.some(comp => comp.type === 'actions');
        
        if (!hasAction) {
            alert('Strategy needs at least one action component (e.g., Alert or Trade).');
            return false;
        }
        
        // Check if strategy has a name
        if (!strategyData.name.trim()) {
            alert('Please give your strategy a name.');
            return false;
        }
        
        // All validations passed
        alert('Strategy is valid and ready to save!');
        return true;
    }

    /**
     * Save the current strategy
     */
    function saveStrategy() {
        // First validate the strategy
        if (!validateStrategy()) return;
        
        // Get additional form data
        strategyData.name = document.getElementById('strategyName').value;
        strategyData.description = document.getElementById('strategyDescription').value;
        strategyData.type = document.getElementById('strategyType').value;
        strategyData.timeframe = document.getElementById('timeframe').value;
        strategyData.active = document.getElementById('activateStrategy').checked;
        
        // In a real app, we would send this to the server
        console.log('Saving strategy:', strategyData);
        
        // Create a POST request to save the strategy
        fetch('/api/strategies', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(strategyData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Strategy saved successfully!');
                
                // If strategy should be activated, make a separate request
                if (strategyData.active && data.strategy_id) {
                    fetch(`/api/strategies/${data.strategy_id}/activate`, {
                        method: 'POST'
                    });
                }
            } else {
                alert(`Error saving strategy: ${data.error || 'Unknown error'}`);
            }
        })
        .catch(error => {
            console.error('Error saving strategy:', error);
            alert('Error saving strategy. See console for details.');
        });
    }

    /**
     * Test the current strategy
     */
    function testStrategy() {
        // First validate the strategy
        if (!validateStrategy()) return;
        
        alert('Test functionality would run the strategy against historical data. This feature is coming soon!');
        
        // In a real app, we would send the strategy to a test endpoint
    }

    /**
     * Load a strategy template
     */
    function loadTemplate(e) {
        const templateId = e.target.value;
        
        if (!templateId) return;
        
        // In a real app, we would fetch the template from the server
        // For this demo, we'll just use some hardcoded examples
        
        let template;
        
        switch (templateId) {
            case 'og_classic':
                template = {
                    name: 'OG Strategy - Classic',
                    description: 'Classic OG strategy looking for EMA cloud pattern with order blocks',
                    type: 'options',
                    timeframe: '1d',
                    components: [
                        // Demo components would be here
                    ]
                };
                break;
                
            case 'og_momentum':
                template = {
                    name: 'OG Strategy - Momentum',
                    description: 'OG momentum strategy looking for volume surges with EMA confirmation',
                    type: 'options',
                    timeframe: '1h',
                    components: [
                        // Demo components would be here
                    ]
                };
                break;
                
            case 'ema_crossover':
                template = {
                    name: 'EMA Crossover',
                    description: 'Simple EMA crossover strategy',
                    type: 'equity',
                    timeframe: '1d',
                    components: [
                        // Demo components would be here
                    ]
                };
                break;
                
            case 'custom':
                // Would load user's saved strategies
                alert('Loading custom strategies from your profile is coming soon!');
                e.target.value = '';
                return;
                
            default:
                alert('Unknown template');
                e.target.value = '';
                return;
        }
        
        // Confirm before loading template
        if (strategyData.components.length > 0) {
            if (!confirm('Loading a template will replace your current strategy. Continue?')) {
                e.target.value = '';
                return;
            }
        }
        
        // Clear canvas
        clearCanvas();
        
        // Set basic strategy properties
        strategyData.name = template.name;
        strategyData.description = template.description;
        strategyData.type = template.type;
        strategyData.timeframe = template.timeframe;
        
        // Update form fields
        document.getElementById('strategyName').value = template.name;
        document.getElementById('strategyDescription').value = template.description;
        document.getElementById('strategyType').value = template.type;
        document.getElementById('timeframe').value = template.timeframe;
        
        // In a real app, we would now load components onto the canvas
        alert('Template loaded! Component placement functionality coming soon.');
        
        // Reset select
        e.target.value = '';
        
        // Update strategy output
        updateStrategyOutput();
    }

    /**
     * Add a connection between two components
     * @param {string} fromId - ID of the source component
     * @param {string} toId - ID of the target component
     */
    function addConnection(fromId, toId) {
        // Check if components exist
        const fromComponent = document.getElementById(fromId);
        const toComponent = document.getElementById(toId);
        
        if (!fromComponent || !toComponent) {
            console.warn(`Cannot create connection: Component ${!fromComponent ? fromId : toId} not found`);
            return false;
        }
        
        // Add to strategyData connections
        strategyData.connections.push({ from: fromId, to: toId });
        
        // In a real implementation, we would draw a visual connection line between the components
        console.log(`Created connection from ${fromId} to ${toId}`);
        return true;
    }

    /**
     * Load the selected template from the dropdown
     */
    function loadSelectedTemplate() {
        const templateSelect = document.getElementById('templateSelect');
        const selectedTemplateId = templateSelect.value;
        
        if (!selectedTemplateId) {
            alert('Please select a template first');
            return;
        }
        
        // For custom templates (user saved)
        if (selectedTemplateId === 'custom') {
            alert('Custom strategies feature coming soon!');
            return;
        }
        
        // Check if we have this template in our StrategyTemplates object
        if (typeof StrategyTemplates !== 'undefined' && StrategyTemplates[selectedTemplateId]) {
            // Use the loadStrategyTemplate function from strategy_templates.js
            const loadedTemplate = loadStrategyTemplate(selectedTemplateId);
            
            if (loadedTemplate) {
                // Update form fields
                document.getElementById('strategyName').value = loadedTemplate.name;
                document.getElementById('strategyDescription').value = loadedTemplate.description;
                document.getElementById('strategyType').value = 'options'; // Default to options
                document.getElementById('timeframe').value = '1d';  // Default to daily
                
                // Update strategyData
                strategyData.name = loadedTemplate.name;
                strategyData.description = loadedTemplate.description;
                strategyData.type = 'options';
                strategyData.timeframe = '1d';
                
                // Reset the dropdown
                templateSelect.value = '';
                
                // Update strategy output
                updateStrategyOutput();
                
                console.log('Strategy template loaded successfully');
            }
        } else {
            console.error('Template not found or StrategyTemplates not defined');
            alert('Error loading template: Template not found');
        }
    }
    
    /**
     * Update the strategy output preview
     */
    function updateStrategyOutput() {
        const outputEl = document.getElementById('strategyOutput');
        
        // Get current strategy data with some sensitive cleanup
        const outputData = {
            ...strategyData,
            components: strategyData.components.map(c => ({
                ...c,
                id: c.id.split('_').slice(0, 2).join('_') // Simplify IDs for output
            }))
        };
        
        outputEl.textContent = JSON.stringify(outputData, null, 2);
    }
});