"""
Market API Routes
Provides API endpoints for market data and live trading functionality
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user

# Import market integration
from market_integration import get_market_integration
from config import get_setting, update_setting
from logs_service import log_to_db

logger = logging.getLogger(__name__)

# Create blueprint
market_bp = Blueprint('market', __name__, url_prefix='/api/market')

# Create a market integration instance with paper trading by default
# This will be updated based on user settings
market_integration = None

def init_market_integration():
    """Initialize market integration based on current settings"""
    global market_integration
    # Get trading mode from settings
    paper_trading = get_setting('paper_trading_mode', True)
    market_integration = get_market_integration(paper_trading=paper_trading)
    logger.info(f"Market integration initialized in {'paper' if paper_trading else 'live'} trading mode")
    return market_integration

# API Routes

@market_bp.route('/status')
@login_required
def get_market_status():
    """Get current status of market integration"""
    global market_integration
    if market_integration is None:
        market_integration = init_market_integration()
    
    return jsonify(market_integration.get_status())

@market_bp.route('/price/<symbol>')
@login_required
def get_price(symbol):
    """Get current price for a symbol"""
    global market_integration
    if market_integration is None:
        market_integration = init_market_integration()
    
    price = market_integration.get_current_price(symbol)
    
    if price is None:
        return jsonify({
            "success": False,
            "error": f"Could not get price for {symbol}"
        }), 404
    
    return jsonify({
        "success": True,
        "symbol": symbol,
        "price": price,
        "timestamp": datetime.now().isoformat()
    })

@market_bp.route('/bars/<symbol>')
@login_required
def get_bars(symbol):
    """Get price bars for a symbol"""
    global market_integration
    if market_integration is None:
        market_integration = init_market_integration()
    
    # Parse query parameters
    timeframe = request.args.get('timeframe', '1D')
    limit = int(request.args.get('limit', 100))
    
    bars = market_integration.get_bars(symbol, timeframe, limit)
    
    if bars is None:
        return jsonify({
            "success": False,
            "error": f"Could not get bars for {symbol}"
        }), 404
    
    return jsonify({
        "success": True,
        "symbol": symbol,
        "timeframe": timeframe,
        "bars": bars
    })

@market_bp.route('/options/<symbol>')
@login_required
def get_options(symbol):
    """Get options chain for a symbol"""
    global market_integration
    if market_integration is None:
        market_integration = init_market_integration()
    
    # Parse query parameters
    expiration = request.args.get('expiration')
    
    options = market_integration.get_options_chain(symbol, expiration)
    
    return jsonify({
        "success": True,
        "symbol": symbol,
        "options": options
    })

@market_bp.route('/news')
@login_required
def get_news():
    """Get market news"""
    global market_integration
    if market_integration is None:
        market_integration = init_market_integration()
    
    # Parse query parameters
    symbol = request.args.get('symbol')
    limit = int(request.args.get('limit', 5))
    
    news = market_integration.get_market_news(symbol, limit)
    
    return jsonify({
        "success": True,
        "symbol": symbol,
        "news": news
    })

@market_bp.route('/watchlist', methods=['GET', 'POST'])
@login_required
def watchlist():
    """Get or update watchlist"""
    global market_integration
    if market_integration is None:
        market_integration = init_market_integration()
    
    if request.method == 'GET':
        watchlist = market_integration.get_watchlist()
        return jsonify({
            "success": True,
            "watchlist": watchlist
        })
    
    elif request.method == 'POST':
        data = request.json
        if not data or 'symbols' not in data:
            return jsonify({
                "success": False,
                "error": "No symbols provided"
            }), 400
        
        symbols = data['symbols']
        market_integration.set_watchlist(symbols)
        
        return jsonify({
            "success": True,
            "message": f"Watchlist updated with {len(symbols)} symbols",
            "watchlist": symbols
        })

@market_bp.route('/market-status')
@login_required
def market_status():
    """Check if market is open"""
    global market_integration
    if market_integration is None:
        market_integration = init_market_integration()
    
    is_open = market_integration.is_market_open()
    
    return jsonify({
        "success": True,
        "is_open": is_open,
        "timestamp": datetime.now().isoformat()
    })

# Trading API Routes

@market_bp.route('/account')
@login_required
def get_account():
    """Get account information"""
    global market_integration
    if market_integration is None:
        market_integration = init_market_integration()
    
    account = market_integration.get_account_info()
    
    return jsonify(account)

@market_bp.route('/positions')
@login_required
def get_positions():
    """Get current positions"""
    global market_integration
    if market_integration is None:
        market_integration = init_market_integration()
    
    positions = market_integration.get_positions()
    
    return jsonify(positions)

@market_bp.route('/orders')
@login_required
def get_orders():
    """Get orders"""
    global market_integration
    if market_integration is None:
        market_integration = init_market_integration()
    
    # Parse query parameters
    status = request.args.get('status', 'all')
    limit = int(request.args.get('limit', 100))
    
    orders = market_integration.get_orders(status, limit)
    
    return jsonify(orders)

@market_bp.route('/order', methods=['POST'])
@login_required
def place_order():
    """Place an order"""
    global market_integration
    if market_integration is None:
        market_integration = init_market_integration()
    
    data = request.json
    if not data:
        return jsonify({
            "success": False,
            "error": "No order data provided"
        }), 400
    
    # Check required fields
    required_fields = ['symbol', 'qty', 'side']
    for field in required_fields:
        if field not in data:
            return jsonify({
                "success": False,
                "error": f"Missing required field: {field}"
            }), 400
    
    # Determine if this is a stock or option order
    is_option = 'option_type' in data or len(data['symbol']) > 15
    
    # Extract common parameters
    symbol = data['symbol']
    qty = int(data['qty'])
    side = data['side']
    order_type = data.get('order_type', 'market')
    time_in_force = data.get('time_in_force', 'day')
    limit_price = data.get('limit_price')
    
    try:
        # Handle order placement based on type
        if is_option:
            result = market_integration.place_option_order(
                symbol=symbol,
                qty=qty,
                side=side,
                order_type=order_type,
                time_in_force=time_in_force,
                limit_price=limit_price
            )
        else:
            # Additional parameters for stock orders
            stop_price = data.get('stop_price')
            extended_hours = data.get('extended_hours', False)
            
            result = market_integration.place_stock_order(
                symbol=symbol,
                qty=qty,
                side=side,
                order_type=order_type,
                time_in_force=time_in_force,
                limit_price=limit_price,
                stop_price=stop_price,
                extended_hours=extended_hours
            )
        
        return jsonify(result)
    
    except Exception as e:
        error_msg = f"Error placing order: {str(e)}"
        logger.error(error_msg)
        log_to_db(error_msg, level="ERROR", module="MarketAPI")
        
        return jsonify({
            "success": False,
            "error": error_msg
        }), 500

@market_bp.route('/order/<order_id>', methods=['DELETE'])
@login_required
def cancel_order(order_id):
    """Cancel an order"""
    global market_integration
    if market_integration is None:
        market_integration = init_market_integration()
    
    result = market_integration.cancel_order(order_id)
    
    return jsonify(result)

@market_bp.route('/position/<symbol>', methods=['DELETE'])
@login_required
def close_position(symbol):
    """Close a position"""
    global market_integration
    if market_integration is None:
        market_integration = init_market_integration()
    
    result = market_integration.close_position(symbol)
    
    return jsonify(result)

@market_bp.route('/positions', methods=['DELETE'])
@login_required
def close_all_positions():
    """Close all positions"""
    global market_integration
    if market_integration is None:
        market_integration = init_market_integration()
    
    result = market_integration.close_all_positions()
    
    return jsonify(result)

@market_bp.route('/orders', methods=['DELETE'])
@login_required
def cancel_all_orders():
    """Cancel all orders"""
    global market_integration
    if market_integration is None:
        market_integration = init_market_integration()
    
    result = market_integration.cancel_all_orders()
    
    return jsonify(result)

@market_bp.route('/circuit-breaker', methods=['POST'])
@login_required
def set_circuit_breaker():
    """Configure circuit breaker"""
    global market_integration
    if market_integration is None:
        market_integration = init_market_integration()
    
    data = request.json
    if not data or 'enabled' not in data:
        return jsonify({
            "success": False,
            "error": "Missing 'enabled' field"
        }), 400
    
    enabled = data['enabled']
    max_losses = int(data.get('max_losses', 3))
    max_drawdown = float(data.get('max_drawdown', 5.0))
    
    result = market_integration.set_circuit_breaker(enabled, max_losses, max_drawdown)
    
    return jsonify(result)

@market_bp.route('/execute-signal', methods=['POST'])
@login_required
def execute_signal():
    """Execute a trade based on an OG strategy signal"""
    global market_integration
    if market_integration is None:
        market_integration = init_market_integration()
    
    data = request.json
    if not data:
        return jsonify({
            "success": False,
            "error": "No signal data provided"
        }), 400
    
    result = market_integration.execute_og_signal(data)
    
    return jsonify(result)

@market_bp.route('/trading-mode', methods=['GET', 'POST'])
@login_required
def trading_mode():
    """Get or update trading mode (paper vs live)"""
    global market_integration
    
    if request.method == 'GET':
        paper_trading = get_setting('paper_trading_mode', True)
        
        return jsonify({
            "success": True,
            "paper_trading": paper_trading,
            "mode": "paper" if paper_trading else "live"
        })
    
    elif request.method == 'POST':
        data = request.json
        if not data or 'paper_trading' not in data:
            return jsonify({
                "success": False,
                "error": "Missing 'paper_trading' field"
            }), 400
        
        paper_trading = data['paper_trading']
        
        # Update setting
        update_setting('paper_trading_mode', paper_trading)
        
        # Re-initialize market integration with new mode
        market_integration = init_market_integration()
        
        log_to_db(
            f"Trading mode changed to {'paper' if paper_trading else 'live'} trading",
            level="INFO",
            module="MarketAPI"
        )
        
        return jsonify({
            "success": True,
            "message": f"Trading mode changed to {'paper' if paper_trading else 'live'} trading",
            "paper_trading": paper_trading,
            "mode": "paper" if paper_trading else "live"
        })

@market_bp.route('/api-keys', methods=['POST'])
@login_required
def update_api_keys():
    """Update market data and trading API keys"""
    data = request.json
    if not data:
        return jsonify({
            "success": False,
            "error": "No API key data provided"
        }), 400
    
    # Process Alpaca API keys
    if 'alpaca_api_key' in data and 'alpaca_secret_key' in data:
        alpaca_api_key = data['alpaca_api_key']
        alpaca_secret_key = data['alpaca_secret_key']
        
        # Update environment variables
        os.environ['ALPACA_API_KEY'] = alpaca_api_key
        os.environ['ALPACA_SECRET_KEY'] = alpaca_secret_key
        
        # Store in settings (securely in production)
        update_setting('alpaca_api_key', alpaca_api_key)
        update_setting('alpaca_secret_key', alpaca_secret_key)
    
    # Process Polygon.io API key
    if 'polygon_api_key' in data:
        polygon_api_key = data['polygon_api_key']
        
        # Update environment variable
        os.environ['POLYGON_API_KEY'] = polygon_api_key
        
        # Store in settings
        update_setting('polygon_api_key', polygon_api_key)
    
    # Process other API keys as needed
    if 'perplexity_api_key' in data:
        perplexity_api_key = data['perplexity_api_key']
        
        # Update environment variable
        os.environ['PERPLEXITY_API_KEY'] = perplexity_api_key
        
        # Store in settings
        update_setting('perplexity_api_key', perplexity_api_key)
    
    # Re-initialize market integration to use new keys
    global market_integration
    market_integration = init_market_integration()
    
    log_to_db("API keys updated and services reinitialized", level="INFO", module="MarketAPI")
    
    return jsonify({
        "success": True,
        "message": "API keys updated successfully"
    })

@market_bp.route('/get-api-hints')
@login_required
def get_api_hints():
    """Get masked API key hints for UI display"""
    # Get API keys from settings
    alpaca_api_key = get_setting('alpaca_api_key', '')
    polygon_api_key = get_setting('polygon_api_key', '')
    perplexity_api_key = get_setting('perplexity_api_key', '')
    
    # Create masked versions (show first 4 and last 4 chars only)
    def mask_key(key):
        if not key or len(key) < 8:
            return ''
        return key[:4] + '*' * (len(key) - 8) + key[-4:]
    
    return jsonify({
        "success": True,
        "alpaca_api_key_hint": mask_key(alpaca_api_key),
        "polygon_api_key_hint": mask_key(polygon_api_key),
        "perplexity_api_key_hint": mask_key(perplexity_api_key)
    })

@market_bp.route('/circuit-breaker-settings')
@login_required
def get_circuit_breaker_settings():
    """Get circuit breaker settings"""
    global market_integration
    if market_integration is None:
        market_integration = init_market_integration()
    
    # Get settings from market integration
    enabled = get_setting('circuit_breaker_enabled', True)
    max_losses = int(get_setting('circuit_breaker_max_losses', 3))
    max_drawdown = float(get_setting('circuit_breaker_max_drawdown', 5.0))
    
    return jsonify({
        "success": True,
        "enabled": enabled,
        "max_losses": max_losses,
        "max_drawdown": max_drawdown
    })

@market_bp.route('/reconnect', methods=['POST'])
@login_required
def reconnect_services():
    """Reconnect to market data and trading services"""
    global market_integration
    if market_integration is None:
        market_integration = init_market_integration()
    
    # Attempt to reconnect
    try:
        # Reconnect market data
        market_integration.market_data.reconnect()
        
        # Reconnect trade executor
        market_integration.trade_executor.reconnect()
        
        log_to_db("Market services reconnected manually", level="INFO", module="MarketAPI")
        
        return jsonify({
            "success": True,
            "message": "Successfully reconnected to market services"
        })
    except Exception as e:
        error_msg = f"Error reconnecting to market services: {str(e)}"
        logger.error(error_msg)
        log_to_db(error_msg, level="ERROR", module="MarketAPI")
        
        return jsonify({
            "success": False,
            "error": error_msg
        }), 500


# Register the blueprint with the app
def register_market_api_blueprint(app):
    app.register_blueprint(market_bp)
    logger.info("Market API blueprint registered")
    return "Market API blueprint registered successfully"