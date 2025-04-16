/**
 * Strategy Templates for OG Signal Bot
 * 
 * This file contains pre-configured strategy templates that can be loaded
 * into the strategy builder.
 */

const StrategyTemplates = {
  /**
   * OG Strategy - Core Template
   * Based on Ripster EMA Cloud + Order Block + Fair Value Gap
   * 
   * This implements the core OG Strategy pattern with:
   * - EMA Cloud (9/21) for trend direction
   * - Order Block detection for support/resistance
   * - Fair Value Gap identification
   * - Volume confirmation
   * - RSI filter for avoiding overbought/oversold conditions
   */
  ogStrategy: {
    name: "OG Strategy Template",
    description: "Ripster EMA Cloud + OB + FVG with volume confirmation",
    components: [
      // Indicators
      {
        id: "ema_cloud_1",
        type: "indicator",
        category: "indicators",
        templateId: "ema_cloud",
        name: "EMA Cloud",
        x: 100,
        y: 100,
        properties: {
          fast_period: 9,
          slow_period: 21
        }
      },
      {
        id: "order_block_1",
        type: "indicator",
        category: "indicators",
        templateId: "order_block",
        name: "Order Block",
        x: 100,
        y: 200,
        properties: {
          lookback: 10,
          detection_method: "price_rejection"
        }
      },
      {
        id: "fvg_1",
        type: "indicator",
        category: "indicators",
        templateId: "fvg",
        name: "Fair Value Gap",
        x: 100,
        y: 300,
        properties: {
          min_gap: 0.5,
          lookback: 5
        }
      },
      {
        id: "volume_profile_1",
        type: "indicator",
        category: "indicators",
        templateId: "volume_profile",
        name: "Volume Profile",
        x: 100,
        y: 400,
        properties: {
          levels: 10,
          period: 20
        }
      },
      
      // Filters
      {
        id: "price_range_1",
        type: "filter",
        category: "filters",
        templateId: "price_range",
        name: "Price Range",
        x: 300,
        y: 100,
        properties: {
          min_price: 0,
          max_price: 1000
        }
      },
      {
        id: "liquidity_filter_1",
        type: "filter",
        category: "filters",
        templateId: "liquidity_filter",
        name: "Liquidity Filter",
        x: 300,
        y: 200,
        properties: {
          min_avg_volume: 500000,
          min_open_interest: 100
        }
      },
      
      // Conditions
      {
        id: "price_above_1",
        type: "condition",
        category: "conditions",
        templateId: "price_above",
        name: "Price Above EMA Cloud",
        x: 500,
        y: 100,
        properties: {
          buffer: 0
        }
      },
      {
        id: "volume_surge_1",
        type: "condition",
        category: "conditions",
        templateId: "volume_surge",
        name: "Volume Surge",
        x: 500,
        y: 200,
        properties: {
          threshold: 150,
          lookback: 5
        }
      },
      {
        id: "rsi_filter_1",
        type: "condition",
        category: "conditions",
        templateId: "rsi_overbought",
        name: "RSI Not Overbought",
        x: 500,
        y: 300,
        properties: {
          threshold: 70,
          period: 14
        }
      },
      
      // Actions
      {
        id: "alert_1",
        type: "action",
        category: "actions",
        templateId: "alert",
        name: "Send Alert",
        x: 700,
        y: 100,
        properties: {
          channels: "all"
        }
      },
      {
        id: "record_signal_1",
        type: "action",
        category: "actions",
        templateId: "record_signal",
        name: "Record Signal",
        x: 700,
        y: 200,
        properties: {
          log_level: "info"
        }
      },
      {
        id: "paper_trade_1",
        type: "action",
        category: "actions",
        templateId: "paper_trade",
        name: "Paper Trade",
        x: 700,
        y: 300,
        properties: {
          position_size: "confidence_based"
        }
      }
    ],
    connections: [
      // Connect EMA Cloud to Price Above condition
      { from: "ema_cloud_1", to: "price_above_1" },
      
      // Connect Order Block to Volume Surge (check for volume at order blocks)
      { from: "order_block_1", to: "volume_surge_1" },
      
      // Connect Price Above to Alert
      { from: "price_above_1", to: "alert_1" },
      
      // Connect Volume Surge to Alert
      { from: "volume_surge_1", to: "alert_1" },
      
      // Connect RSI Filter to Alert (only alert if not overbought)
      { from: "rsi_filter_1", to: "alert_1" },
      
      // Connect Alert to Record Signal
      { from: "alert_1", to: "record_signal_1" },
      
      // Connect Record Signal to Paper Trade
      { from: "record_signal_1", to: "paper_trade_1" },
      
      // Connect FVG to Paper Trade (use FVG for entry/exit)
      { from: "fvg_1", to: "paper_trade_1" }
    ]
  },
  
  /**
   * OG Strategy - Options Specific Template
   * Specialized for options trading with OG Strategy principles
   */
  ogOptionsStrategy: {
    name: "OG Options Strategy Template",
    description: "OG Strategy adapted for options trading with IV and Greeks filters",
    components: [
      // Core indicators same as OG Strategy
      {
        id: "ema_cloud_1",
        type: "indicator",
        category: "indicators",
        templateId: "ema_cloud",
        name: "EMA Cloud",
        x: 100,
        y: 100,
        properties: {
          fast_period: 9,
          slow_period: 21
        }
      },
      {
        id: "order_block_1",
        type: "indicator",
        category: "indicators",
        templateId: "order_block",
        name: "Order Block",
        x: 100,
        y: 200,
        properties: {
          lookback: 10,
          detection_method: "price_rejection"
        }
      },
      {
        id: "fvg_1",
        type: "indicator",
        category: "indicators",
        templateId: "fvg",
        name: "Fair Value Gap",
        x: 100,
        y: 300,
        properties: {
          min_gap: 0.5,
          lookback: 5
        }
      },
      
      // Options-specific filters
      {
        id: "iv_rank_filter",
        type: "filter",
        category: "filters",
        templateId: "price_range", // Reused component with different purpose
        name: "IV Rank Filter",
        x: 300,
        y: 100,
        properties: {
          min_price: 30, // Represents IV Rank min
          max_price: 100 // Represents IV Rank max
        }
      },
      {
        id: "liquidity_filter_1",
        type: "filter",
        category: "filters",
        templateId: "liquidity_filter",
        name: "Options Liquidity",
        x: 300,
        y: 200,
        properties: {
          min_avg_volume: 100, // Lower for options
          min_open_interest: 50 // Lower for options
        }
      },
      
      // Conditions
      {
        id: "price_above_1",
        type: "condition",
        category: "conditions",
        templateId: "price_above",
        name: "Price Above EMA Cloud",
        x: 500,
        y: 100,
        properties: {
          buffer: 0
        }
      },
      {
        id: "volume_surge_1",
        type: "condition",
        category: "conditions",
        templateId: "volume_surge",
        name: "Option Volume Surge",
        x: 500,
        y: 200,
        properties: {
          threshold: 200, // Higher for options to detect unusual activity
          lookback: 5
        }
      },
      
      // Actions
      {
        id: "alert_1",
        type: "action",
        category: "actions",
        templateId: "alert",
        name: "Send Alert",
        x: 700,
        y: 100,
        properties: {
          channels: "all"
        }
      },
      {
        id: "record_signal_1",
        type: "action",
        category: "actions",
        templateId: "record_signal",
        name: "Record Signal",
        x: 700,
        y: 200,
        properties: {
          log_level: "info"
        }
      },
      {
        id: "paper_trade_1",
        type: "action",
        category: "actions",
        templateId: "paper_trade",
        name: "Paper Trade",
        x: 700,
        y: 300,
        properties: {
          position_size: "confidence_based"
        }
      }
    ],
    connections: [
      // Connect EMA Cloud to Price Above condition
      { from: "ema_cloud_1", to: "price_above_1" },
      
      // Connect Order Block to Volume Surge
      { from: "order_block_1", to: "volume_surge_1" },
      
      // Connect Price Above to Alert
      { from: "price_above_1", to: "alert_1" },
      
      // Connect Volume Surge to Alert
      { from: "volume_surge_1", to: "alert_1" },
      
      // Connect Alert to Record Signal
      { from: "alert_1", to: "record_signal_1" },
      
      // Connect Record Signal to Paper Trade
      { from: "record_signal_1", to: "paper_trade_1" }
    ]
  }
};

/**
 * Load a strategy template into the builder
 * @param {string} templateId - ID of the template to load
 */
function loadStrategyTemplate(templateId) {
  const template = StrategyTemplates[templateId];
  if (!template) {
    console.error(`Template not found: ${templateId}`);
    return null;
  }
  
  // Delegate to the strategy builder's canvas clear and update functions
  // This assumes the strategy builder has a global clearCanvas function
  if (typeof clearCanvas === 'function') {
    clearCanvas(true); // Pass true to skip confirmation
    
    // Now add the components to the canvas
    if (typeof addComponentToCanvas === 'function') {
      // Add each component to the canvas
      template.components.forEach(component => {
        addComponentToCanvas(
          component.id,
          component,
          component.category,
          component.x,
          component.y
        );
      });
      
      // Add connections if the functionality exists
      if (typeof addConnection === 'function') {
        template.connections.forEach(connection => {
          addConnection(connection.from, connection.to);
        });
      } else {
        console.warn('addConnection function not found, connections will need to be made manually');
      }
      
      // Update the strategy data object if it exists
      if (typeof strategyData !== 'undefined') {
        strategyData.name = template.name;
        strategyData.description = template.description;
        strategyData.components = template.components;
        strategyData.connections = template.connections;
        
        // Update the output if the function exists
        if (typeof updateStrategyOutput === 'function') {
          updateStrategyOutput();
        }
      }
    } else {
      console.error('addComponentToCanvas function not found, cannot add components to canvas');
    }
  } else {
    console.error('clearCanvas function not found. Make sure this script is loaded after strategy_builder.js');
    return null;
  }
  
  // Update strategy name field if it exists
  const nameField = document.getElementById('strategy-name');
  if (nameField) {
    nameField.value = template.name;
  }
  
  // Update strategy description field if it exists
  const descField = document.getElementById('strategy-description');
  if (descField) {
    descField.value = template.description;
  }
  
  console.log(`Loaded template: ${template.name}`);
  return template;
}