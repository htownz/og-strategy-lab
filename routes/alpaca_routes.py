# alpaca_routes.py

from flask import Blueprint, request, jsonify
import os
import logging
from alpaca_service import get_alpaca_service

logger = logging.getLogger(__name__)
alpaca_bp = Blueprint('alpaca', __name__)

@alpaca_bp.route('/status', methods=['GET'])
def alpaca_status():
    """Get Alpaca API status"""
    alpaca = get_alpaca_service()
    
    return jsonify({
        'connected': alpaca.enabled,
        'paper_trading': alpaca.base_url == 'https://paper-api.alpaca.markets'
    })

@alpaca_bp.route('/configure', methods=['POST'])
def configure_alpaca():
    """Configure Alpaca API credentials"""
    data = request.json
    
    if not data:
        return jsonify({
            'success': False,
            'message': 'Missing request body'
        }), 400
        
    api_key = data.get('api_key')
    api_secret = data.get('api_secret')
    use_paper = data.get('use_paper', True)
    
    if not api_key or not api_secret:
        return jsonify({
            'success': False,
            'message': 'API key and secret are required'
        }), 400
        
    # Set environment variables
    os.environ['ALPACA_API_KEY'] = api_key
    os.environ['ALPACA_API_SECRET'] = api_secret
    
    if use_paper:
        os.environ['ALPACA_BASE_URL'] = 'https://paper-api.alpaca.markets'
    else:
        os.environ['ALPACA_BASE_URL'] = 'https://api.alpaca.markets'
    
    # Reinitialize the service
    from alpaca_service import get_alpaca_service
    alpaca = get_alpaca_service()
    
    # Test the connection
    if alpaca.enabled:
        account = alpaca.get_account()
        if account:
            return jsonify({
                'success': True,
                'message': 'Alpaca API configured successfully',
                'connected': True
            })
    
    return jsonify({
        'success': False,
        'message': 'Failed to connect to Alpaca API with provided credentials',
        'connected': False
    })

@alpaca_bp.route('/test', methods=['POST'])
def test_alpaca():
    """Test Alpaca API connection"""
    alpaca = get_alpaca_service()
    
    if not alpaca.enabled:
        return jsonify({
            'success': False,
            'message': 'Alpaca API not configured'
        }), 400
    
    account = alpaca.get_account()
    
    if account:
        return jsonify({
            'success': True,
            'message': 'Alpaca API connection successful',
            'account': account._raw
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Failed to connect to Alpaca API'
        })

@alpaca_bp.route('/account', methods=['GET'])
def get_account():
    """Get account information"""
    alpaca = get_alpaca_service()
    
    if not alpaca.enabled:
        return jsonify({
            'success': False,
            'message': 'Alpaca API not configured'
        })
    
    account = alpaca.get_account()
    
    if account:
        return jsonify({
            'success': True,
            'account': account._raw
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Failed to retrieve account information'
        })

@alpaca_bp.route('/market', methods=['GET'])
def get_market():
    """Get market status"""
    alpaca = get_alpaca_service()
    
    if not alpaca.enabled:
        return jsonify({
            'success': False,
            'message': 'Alpaca API not configured'
        })
    
    market_status = alpaca.get_market_status()
    
    return jsonify({
        'success': True,
        'market': market_status
    })

@alpaca_bp.route('/positions', methods=['GET'])
def get_positions():
    """Get current positions"""
    alpaca = get_alpaca_service()
    
    if not alpaca.enabled:
        return jsonify({
            'success': False,
            'message': 'Alpaca API not configured'
        })
    
    positions = alpaca.get_positions()
    
    return jsonify({
        'success': True,
        'positions': positions
    })

@alpaca_bp.route('/orders', methods=['GET'])
def get_orders():
    """Get orders"""
    alpaca = get_alpaca_service()
    
    if not alpaca.enabled:
        return jsonify({
            'success': False,
            'message': 'Alpaca API not configured'
        })
    
    status = request.args.get('status', 'all')
    limit = int(request.args.get('limit', 100))
    
    orders = alpaca.get_orders(status=status, limit=limit)
    
    return jsonify({
        'success': True,
        'orders': orders
    })

@alpaca_bp.route('/place-order', methods=['POST'])
def place_order():
    """Place an order"""
    data = request.json
    
    if not data:
        return jsonify({
            'success': False,
            'message': 'Missing request body'
        }), 400
    
    symbol = data.get('symbol')
    qty = data.get('qty')
    side = data.get('side')
    order_type = data.get('order_type', 'market')
    time_in_force = data.get('time_in_force', 'day')
    limit_price = data.get('limit_price')
    
    if not symbol or not qty or not side:
        return jsonify({
            'success': False,
            'message': 'Symbol, quantity, and side are required'
        }), 400
    
    alpaca = get_alpaca_service()
    
    if not alpaca.enabled:
        return jsonify({
            'success': False,
            'message': 'Alpaca API not configured'
        }), 400
    
    order = alpaca.place_order(
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
            'message': f'Order placed successfully',
            'order': order
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Failed to place order'
        })

# Register the blueprint
def register_alpaca_blueprint(app):
    app.register_blueprint(alpaca_bp, url_prefix='/api/alpaca')
    
    # Add the alpaca route
    @app.route('/alpaca')
    def alpaca_config():
        """Alpaca configuration page"""
        return render_template('alpaca.html')
