import logging
from flask import Blueprint, request, jsonify
from flask_socketio import emit

# Create blueprint for API routes
api_blueprint = Blueprint('api', __name__, url_prefix='/api')

logger = logging.getLogger(__name__)

@api_blueprint.route('/health')
def health_check():
    """API health check endpoint"""
    from app import signal_service
    
    return jsonify({
        'status': 'healthy',
        'server_id': 'OG-Signal-Bot-API',
        'version': '1.0.0',
        'timestamp': signal_service.get_current_timestamp()
    })

@api_blueprint.route('/signals', methods=['GET'])
def get_signals():
    """Get all signals"""
    from app import signal_service
    
    # Get signals from service
    signals = signal_service.get_recent_signals()
    
    return jsonify({
        'signals': signals
    })

@api_blueprint.route('/signals', methods=['POST'])
def create_signal():
    """Create a new signal"""
    from app import signal_service, socketio
    
    # Get signal data from request
    signal_data = request.json
    
    if not signal_data or not isinstance(signal_data, dict):
        return jsonify({
            'error': 'Invalid signal data'
        }), 400
    
    # Required fields
    required_fields = ['symbol', 'direction', 'confidence']
    for field in required_fields:
        if field not in signal_data:
            return jsonify({
                'error': f'Missing required field: {field}'
            }), 400
    
    # Process the signal
    result = signal_service.process_signal(signal_data)
    
    # Broadcast the signal to all connected clients
    socketio.emit('new_signal', result)
    
    return jsonify(result)

@api_blueprint.route('/account')
def get_account():
    """Get trading account information"""
    from app import alpaca_service
    
    account_info = alpaca_service.get_account_info()
    
    return jsonify(account_info)

@api_blueprint.route('/positions')
def get_positions():
    """Get current positions"""
    from app import alpaca_service
    
    positions = alpaca_service.get_positions()
    
    return jsonify({
        'positions': positions
    })

@api_blueprint.route('/orders')
def get_orders():
    """Get orders"""
    from app import alpaca_service
    
    # Get query parameters
    status = request.args.get('status', 'all')
    limit = int(request.args.get('limit', 100))
    
    orders = alpaca_service.get_orders(status, limit)
    
    return jsonify({
        'orders': orders
    })

@api_blueprint.route('/price/<symbol>')
def get_price(symbol):
    """Get current price for a symbol"""
    from app import alpaca_service
    
    price = alpaca_service.get_current_price(symbol)
    
    if price is None:
        return jsonify({
            'error': f'Could not get price for {symbol}'
        }), 404
    
    return jsonify({
        'symbol': symbol,
        'price': price
    })

@api_blueprint.route('/bars/<symbol>')
def get_bars(symbol):
    """Get price bars for a symbol"""
    from app import alpaca_service
    
    # Get query parameters
    timeframe = request.args.get('timeframe', '1D')
    limit = int(request.args.get('limit', 100))
    
    bars = alpaca_service.get_bars(symbol, timeframe, limit)
    
    return jsonify({
        'symbol': symbol,
        'timeframe': timeframe,
        'bars': bars
    })