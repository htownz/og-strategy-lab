# signal_routes.py

from flask import Blueprint, request, jsonify, render_template
import logging
import json
from signal_service import get_signal_service
from models import Signal, db

logger = logging.getLogger(__name__)
signal_bp = Blueprint('signal', __name__)

@signal_bp.route('/list', methods=['GET'])
def list_signals():
    """Get list of signals"""
    try:
        # Get query parameters
        limit = int(request.args.get('limit', 20))
        symbol = request.args.get('symbol')
        direction = request.args.get('direction')
        signal_id = request.args.get('signal_id')
        
        # Get signals
        service = get_signal_service()
        signals = service.get_recent_signals(limit, symbol, direction, signal_id)
        
        return jsonify({
            'success': True,
            'signals': [signal.to_dict() for signal in signals]
        })
    except Exception as e:
        logger.error(f"Error listing signals: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error listing signals: {str(e)}"
        }), 500

@signal_bp.route('/generate', methods=['POST'])
def generate_signal():
    """Generate a signal manually"""
    try:
        data = request.json
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'Missing request body'
            }), 400
        
        # Extract signal parameters
        symbol = data.get('symbol')
        direction = data.get('direction')
        confidence = data.get('confidence', 0.5)
        price = data.get('price')
        indicators = data.get('indicators')
        
        # Validate required fields
        if not symbol or not direction or not price:
            return jsonify({
                'success': False,
                'message': 'Symbol, direction, and price are required'
            }), 400
        
        # Generate signal
        service = get_signal_service()
        signal = service.generate_signal(
            symbol=symbol,
            direction=direction,
            confidence=float(confidence),
            price=float(price),
            indicators=indicators
        )
        
        if signal:
            return jsonify({
                'success': True,
                'message': f"Signal generated for {symbol} {direction}",
                'signal': signal.to_dict()
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to generate signal'
            }), 500
            
    except Exception as e:
        logger.error(f"Error generating signal: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error generating signal: {str(e)}"
        }), 500

@signal_bp.route('/og-signal', methods=['POST'])
def generate_og_signal():
    """Generate an OG strategy signal"""
    try:
        data = request.json
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'Missing request body'
            }), 400
        
        # Extract parameters
        symbol = data.get('symbol')
        timeframe = data.get('timeframe', '1D')
        contract_type = data.get('contract_type')
        expiry = data.get('expiry')
        
        # Validate required fields
        if not symbol:
            return jsonify({
                'success': False,
                'message': 'Symbol is required'
            }), 400
        
        # Generate OG signal
        service = get_signal_service()
        signal = service.generate_og_signal(
            symbol=symbol,
            timeframe=timeframe,
            contract_type=contract_type,
            expiry=expiry
        )
        
        if signal:
            return jsonify({
                'success': True,
                'message': f"OG signal generated for {symbol}",
                'signal': signal.to_dict()
            })
        else:
            return jsonify({
                'success': False,
                'message': f"No OG pattern detected for {symbol}"
            })
            
    except Exception as e:
        logger.error(f"Error generating OG signal: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error generating OG signal: {str(e)}"
        }), 500

@signal_bp.route('/scan', methods=['POST'])
def scan_watchlist():
    """Scan a watchlist for OG strategy setups"""
    try:
        data = request.json
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'Missing request body'
            }), 400
        
        # Extract parameters
        symbols = data.get('symbols', [])
        timeframe = data.get('timeframe', '1D')
        
        # Validate required fields
        if not symbols or not isinstance(symbols, list):
            return jsonify({
                'success': False,
                'message': 'Symbols list is required'
            }), 400
        
        # Scan watchlist
        service = get_signal_service()
        results = service.scan_watchlist(symbols, timeframe)
        
        return jsonify({
            'success': True,
            'results': results
        })
            
    except Exception as e:
        logger.error(f"Error scanning watchlist: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error scanning watchlist: {str(e)}"
        }), 500

# Register the blueprint
def register_signal_blueprint(app):
    app.register_blueprint(signal_bp, url_prefix='/api/signals')
    
    # Add the signals page route
    @app.route('/signals')
    def signals_page():
        """Signals page"""
        return render_template('signals.html')
