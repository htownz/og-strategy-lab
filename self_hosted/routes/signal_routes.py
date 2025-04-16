import logging
from flask import Blueprint, request, jsonify, render_template
from flask_socketio import emit

# Create blueprint for signal routes
signal_blueprint = Blueprint('signals', __name__, url_prefix='/signals')

logger = logging.getLogger(__name__)

@signal_blueprint.route('/')
def signals_page():
    """Signal dashboard page"""
    from app import signal_service
    
    # Get signals from service
    signals = signal_service.get_recent_signals()
    
    return render_template('signals.html', signals=signals)

@signal_blueprint.route('/<int:signal_id>')
def signal_detail(signal_id):
    """Signal detail page"""
    from app import signal_service
    
    # Get signals from service
    signals = signal_service.get_recent_signals()
    
    # Find signal by ID
    signal = next((s for s in signals if s['id'] == signal_id), None)
    
    if not signal:
        return render_template('error.html', error='Signal not found'), 404
    
    return render_template('signal_detail.html', signal=signal)

@signal_blueprint.route('/generate')
def generate_signal_form():
    """Form to generate a new signal"""
    return render_template('generate_signal.html')

@signal_blueprint.route('/generate', methods=['POST'])
def generate_signal():
    """Process form to generate a new signal"""
    from app import signal_service, socketio
    
    # Get signal data from form
    symbol = request.form.get('symbol', '').upper()
    direction = request.form.get('direction', '').upper()
    confidence = float(request.form.get('confidence', 0.5))
    price = float(request.form.get('price', 0))
    timeframe = request.form.get('timeframe', '1D')
    strategy = request.form.get('strategy', 'OG Strategy')
    setup_type = request.form.get('setup_type', 'EMA + FVG + OB')
    
    # Validate required fields
    if not symbol or not direction or confidence <= 0 or price <= 0:
        return render_template('generate_signal.html', error='Missing required fields'), 400
    
    # Create signal data
    signal_data = {
        'symbol': symbol,
        'direction': direction,
        'confidence': confidence,
        'price_at_signal': price,
        'indicators': {
            'strategy': strategy,
            'timeframe': timeframe,
            'technical_signals': {
                'ema_cloud': True,
                'ob_fvg': True,
                'volume': True,
                'price_action': True
            },
            'key_levels': {
                'entry': price,
                'stop': price * (1.01 if direction == 'BEARISH' else 0.99),
                'target1': price * (0.98 if direction == 'BEARISH' else 1.02),
                'target2': price * (0.96 if direction == 'BEARISH' else 1.04)
            },
            'setup_type': setup_type
        }
    }
    
    # Process the signal
    result = signal_service.process_signal(signal_data)
    
    # Broadcast the signal to all connected clients
    socketio.emit('new_signal', result)
    
    return render_template('signal_success.html', signal=result)