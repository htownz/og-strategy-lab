# alpaca_routes.py

from flask import Blueprint, jsonify, request, render_template
import logging
from alpaca_service import get_alpaca_service

logger = logging.getLogger(__name__)
alpaca_bp = Blueprint('alpaca', __name__)

@alpaca_bp.route('/status', methods=['GET'])
def get_status():
    """Get Alpaca API status"""
    try:
        service = get_alpaca_service()
        status = service.check_api_status()
        
        return jsonify({
            'success': True,
            'status': status
        })
    except Exception as e:
        logger.error(f"Error getting Alpaca status: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error getting Alpaca status: {str(e)}"
        }), 500

@alpaca_bp.route('/account', methods=['GET'])
def get_account():
    """Get account information from Alpaca"""
    try:
        service = get_alpaca_service()
        account = service.get_account()
        
        if account:
            return jsonify({
                'success': True,
                'account': account
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to get account information'
            }), 500
    except Exception as e:
        logger.error(f"Error getting account information: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error getting account information: {str(e)}"
        }), 500

@alpaca_bp.route('/market/status', methods=['GET'])
def get_market_status():
    """Get current market status from Alpaca"""
    try:
        service = get_alpaca_service()
        status = service.get_market_status()
        
        return jsonify({
            'success': True,
            'market': status
        })
    except Exception as e:
        logger.error(f"Error getting market status: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error getting market status: {str(e)}"
        }), 500

@alpaca_bp.route('/positions', methods=['GET'])
def get_positions():
    """Get current positions from Alpaca"""
    try:
        service = get_alpaca_service()
        positions = service.get_positions()
        
        if positions is not None:
            return jsonify({
                'success': True,
                'positions': positions
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to get positions'
            }), 500
    except Exception as e:
        logger.error(f"Error getting positions: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error getting positions: {str(e)}"
        }), 500

@alpaca_bp.route('/orders', methods=['GET'])
def get_orders():
    """Get orders from Alpaca"""
    try:
        service = get_alpaca_service()
        status = request.args.get('status', 'all')
        limit = int(request.args.get('limit', 100))
        
        orders = service.get_orders(status, limit)
        
        if orders is not None:
            return jsonify({
                'success': True,
                'orders': orders
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to get orders'
            }), 500
    except Exception as e:
        logger.error(f"Error getting orders: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error getting orders: {str(e)}"
        }), 500

@alpaca_bp.route('/order', methods=['POST'])
def place_order():
    """Place an order with Alpaca"""
    try:
        service = get_alpaca_service()
        data = request.json
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'Missing request body'
            }), 400
        
        # Extract order parameters
        symbol = data.get('symbol')
        qty = data.get('qty')
        side = data.get('side')
        order_type = data.get('order_type', 'market')
        time_in_force = data.get('time_in_force', 'day')
        limit_price = data.get('limit_price')
        
        # Validate required fields
        if not symbol or not qty or not side:
            return jsonify({
                'success': False,
                'message': 'Symbol, quantity, and side are required'
            }), 400
        
        # Place order
        order = service.place_order(
            symbol=symbol,
            qty=qty,
            side=side,
            order_type=order_type,
            time_in_force=time_in_force,
            limit_price=limit_price
        )
        
        if order:
            return jsonify({
                'success': True,
                'message': f"Order placed successfully for {qty} {symbol} ({side})",
                'order': order
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to place order'
            }), 500
            
    except Exception as e:
        logger.error(f"Error placing order: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error placing order: {str(e)}"
        }), 500

@alpaca_bp.route('/bars', methods=['GET'])
def get_bars():
    """Get price bars for a symbol"""
    try:
        service = get_alpaca_service()
        symbol = request.args.get('symbol')
        timeframe = request.args.get('timeframe', '1Day')
        limit = int(request.args.get('limit', 100))
        
        if not symbol:
            return jsonify({
                'success': False,
                'message': 'Symbol is required'
            }), 400
        
        bars = service.get_bars(symbol, timeframe, limit)
        
        if bars is not None:
            return jsonify({
                'success': True,
                'bars': bars
            })
        else:
            return jsonify({
                'success': False,
                'message': f"Failed to get bars for {symbol}"
            }), 500
    except Exception as e:
        logger.error(f"Error getting bars: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error getting bars: {str(e)}"
        }), 500

# Register the blueprint
def register_alpaca_blueprint(app):
    app.register_blueprint(alpaca_bp, url_prefix='/api/alpaca')
    
    # Add the Alpaca page route
    @app.route('/alpaca')
    def alpaca_page():
        """Alpaca settings and information page"""
        return render_template('alpaca.html')
