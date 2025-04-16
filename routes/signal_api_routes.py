# signal_api_routes.py
# API routes for signals and trade events

from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
from models import Signal, Trade, db
from logs_service import log_to_db
from socketio_server import broadcast_signal, broadcast_trade

signal_api = Blueprint('signal_api', __name__)

@signal_api.route('/api/signal', methods=['POST'])
def create_signal():
    """
    Create a new trading signal from external systems
    
    Expected JSON format:
    {
        "ticker": "AAPL",
        "signal": "BULLISH",  # or "BEARISH"
        "entry": 176.50,
        "stop": 174.80,
        "target1": 179.00,
        "confidence": 3,  # 1-5 scale
        "setup": "Ripster EMA + FVG"
    }
    """
    data = request.json
    if not data:
        log_to_db("Invalid signal data received: no JSON content", level="ERROR", module="API")
        return jsonify({"error": "No data provided"}), 400
    
    # Validate required fields
    required_fields = ["ticker", "signal", "entry", "confidence"]
    for field in required_fields:
        if field not in data:
            log_to_db(f"Invalid signal data: missing {field}", level="ERROR", module="API")
            return jsonify({"error": f"Missing required field: {field}"}), 400
    
    # Convert signal direction to UP/DOWN for consistency with internal model
    signal_direction = "UP" if data.get("signal", "").upper() in ["BULLISH", "UP", "BUY", "LONG"] else "DOWN"
    
    # Convert confidence to float 0.0-1.0 from 1-5 scale
    confidence = min(max(float(data.get("confidence", 3)), 1), 5) / 5.0
    
    # Create indicators JSON
    indicators = {
        "entry": float(data.get("entry")),
        "stop": float(data.get("stop")) if "stop" in data else None,
        "target1": float(data.get("target1")) if "target1" in data else None,
        "target2": float(data.get("target2")) if "target2" in data else None,
        "setup": data.get("setup", "External Signal"),
        "notes": data.get("notes", "")
    }
    
    # Create new signal
    try:
        new_signal = Signal(
            symbol=data.get("ticker").upper(),
            direction=signal_direction,
            confidence=confidence,
            price_at_signal=float(data.get("entry")),
            indicators=indicators,
            executed=False
        )
        
        db.session.add(new_signal)
        db.session.commit()
        
        # Broadcast the new signal via Socket.IO
        signal_dict = {
            'id': new_signal.id,
            'symbol': new_signal.symbol,
            'direction': new_signal.direction,
            'confidence': new_signal.confidence,
            'price_at_signal': new_signal.price_at_signal,
            'timestamp': new_signal.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'executed': new_signal.executed,
            'indicators': new_signal.indicators
        }
        broadcast_signal(signal_dict)
        
        log_to_db(f"New signal created via API: {new_signal.symbol} {new_signal.direction}", 
                  level="INFO", module="API")
        
        return jsonify({
            "success": True,
            "message": f"Signal for {new_signal.symbol} created successfully",
            "signal_id": new_signal.id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        log_to_db(f"Error creating signal: {str(e)}", level="ERROR", module="API")
        return jsonify({"error": f"Failed to create signal: {str(e)}"}), 500

@signal_api.route('/api/signals', methods=['GET'])
def get_signals():
    """Get recent trading signals with optional filtering"""
    try:
        # Parse query parameters
        limit = min(int(request.args.get('limit', 50)), 500)  # Max 500 signals
        days = int(request.args.get('days', 7))  # Default to last 7 days
        symbol = request.args.get('symbol')  # Optional symbol filter
        direction = request.args.get('direction')  # Optional direction filter
        
        # Base query
        query = Signal.query
        
        # Apply filters
        if symbol:
            query = query.filter(Signal.symbol == symbol.upper())
        
        if direction:
            direction = direction.upper()
            if direction in ['UP', 'DOWN']:
                query = query.filter(Signal.direction == direction)
        
        # Time filter
        start_date = datetime.now() - timedelta(days=days)
        query = query.filter(Signal.timestamp >= start_date)
        
        # Get results
        signals = query.order_by(Signal.timestamp.desc()).limit(limit).all()
        
        # Format response
        response = []
        for signal in signals:
            signal_dict = {
                'id': signal.id,
                'symbol': signal.symbol,
                'direction': signal.direction,
                'confidence': signal.confidence,
                'price_at_signal': signal.price_at_signal,
                'timestamp': signal.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'executed': signal.executed
            }
            
            # Include indicators if they exist
            if signal.indicators:
                signal_dict['indicators'] = signal.indicators
                
            response.append(signal_dict)
            
        return jsonify({"signals": response, "count": len(response)})
        
    except Exception as e:
        log_to_db(f"Error retrieving signals: {str(e)}", level="ERROR", module="API")
        return jsonify({"error": f"Failed to retrieve signals: {str(e)}"}), 500

@signal_api.route('/api/trade-events', methods=['GET'])
def get_trade_events():
    """Get recent trade events with optional filtering"""
    try:
        # Parse query parameters
        limit = min(int(request.args.get('limit', 50)), 500)  # Max 500 trades
        days = int(request.args.get('days', 7))  # Default to last 7 days
        symbol = request.args.get('symbol')  # Optional symbol filter
        status = request.args.get('status')  # Optional status filter
        
        # Base query
        query = Trade.query
        
        # Apply filters
        if symbol:
            query = query.filter(Trade.symbol == symbol.upper())
        
        if status:
            status = status.upper()
            if status in ['SUBMITTED', 'FILLED', 'PARTIAL', 'CANCELED', 'REJECTED']:
                query = query.filter(Trade.status == status)
        
        # Time filter
        start_date = datetime.now() - timedelta(days=days)
        query = query.filter(Trade.timestamp >= start_date)
        
        # Get results
        trades = query.order_by(Trade.timestamp.desc()).limit(limit).all()
        
        # Format response
        response = []
        for trade in trades:
            trade_dict = {
                'id': trade.id,
                'symbol': trade.symbol,
                'direction': trade.direction,
                'quantity': trade.quantity,
                'price': trade.price,
                'status': trade.status,
                'timestamp': trade.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'alpaca_order_id': trade.alpaca_order_id
            }
            
            # Include signal info if exists
            if trade.signal:
                trade_dict['signal'] = {
                    'id': trade.signal.id,
                    'direction': trade.signal.direction,
                    'confidence': trade.signal.confidence
                }
                
            response.append(trade_dict)
            
        return jsonify({"trades": response, "count": len(response)})
        
    except Exception as e:
        log_to_db(f"Error retrieving trades: {str(e)}", level="ERROR", module="API")
        return jsonify({"error": f"Failed to retrieve trades: {str(e)}"}), 500