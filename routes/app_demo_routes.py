"""
Demo Routes for showcasing OG Signal Bot features
These routes are for demonstration purposes.
"""

# List of tickers for overnight scanning example
OVERNIGHT_TICKERS = [
    "AMD", "NVDA", "AMZN", "MSFT", "COST", "TSLA", "AAPL", "QQQ", 
    "LUV", "MCD", "F", "SOFI", "T", "SNAP", "MARA", "WMT", "TGT", 
    "NKE", "PLTR", "AMC", "RIVN", "GME", "JNJ", "META"
]
import logging
import time
from datetime import datetime
from flask import Blueprint, jsonify, request, render_template, current_app
from config import get_setting
import json

# Create blueprint
demo_bp = Blueprint('demo', __name__, url_prefix='/demo')

# Set up logging
logger = logging.getLogger(__name__)

@demo_bp.route('/trigger_snap_example', methods=['GET', 'POST'])
def trigger_snap_example():
    """Trigger the SNAP trade example match signal for demonstration"""
    try:
        # Import here to avoid circular imports
        from og_strategy_matcher import create_snap_trade_example
        from socketio_server_functions import broadcast_og_match
        from socketio_server import socketio
        
        # Get strategy ID from request if available
        strategy_id = None
        
        # First check JSON data (from fetch API)
        if request.method == 'POST' and request.is_json:
            data = request.get_json()
            if data and 'strategy_id' in data and data['strategy_id']:
                strategy_id = int(data['strategy_id'])
        # Then check form data (from traditional form submit)
        elif request.method == 'POST' and 'strategy_id' in request.form:
            strategy_id = int(request.form['strategy_id'])
        # Finally check query parameters (from GET request)
        elif request.method == 'GET' and 'strategy_id' in request.args:
            strategy_id = int(request.args.get('strategy_id'))
        
        logger.info(f"Triggering SNAP trade example with strategy_id: {strategy_id}")
        
        # Create the example signal with specified strategy ID
        snap_signal = create_snap_trade_example(strategy_id)
        logger.info(f"Created SNAP trade example: {snap_signal['symbol']} {snap_signal['direction']} using strategy {snap_signal.get('strategy', 'OG Strategy')}")
        
        # Broadcast the signal via SocketIO
        broadcast_og_match(socketio, snap_signal)
        
        # Create a record in the database
        with current_app.app_context():
            from models import Signal, db
            from datetime import datetime
            
            # Create a new signal record
            new_signal = Signal(
                symbol=snap_signal['symbol'],
                direction=snap_signal['direction'],
                price_at_signal=snap_signal['price'],
                confidence=snap_signal['confidence'],
                timestamp=datetime.now(),
                strategy_id=strategy_id,
                strategy_name=snap_signal.get('strategy'),
                timeframe=snap_signal.get('timeframe'),
                indicators=json.dumps({
                    'technical_signals': snap_signal['technical_signals'],
                    'key_levels': snap_signal['key_levels'],
                    'contract': snap_signal['contract'],
                    'setup_type': snap_signal['setup_type']
                })
            )
            
            # Add to database
            db.session.add(new_signal)
            db.session.commit()
            
            logger.info(f"Saved SNAP example signal to database with ID: {new_signal.id}")
        
        # Return success
        return jsonify({
            'success': True,
            'message': 'SNAP trade example triggered',
            'signal': snap_signal
        })
    
    except Exception as e:
        logger.error(f"Error triggering SNAP example: {e}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@demo_bp.route('/get_strategies', methods=['GET'])
def get_strategies():
    """Get list of available strategy profiles"""
    try:
        # Import strategy registry
        from strategy_registry import get_strategy_registry
        
        # Get active strategies
        registry = get_strategy_registry()
        active_strategies = registry.get_active_strategies()
        
        # Format for UI
        strategy_list = []
        for strategy in active_strategies:
            strategy_list.append({
                'id': strategy.get('id'),
                'name': strategy.get('name'),
                'type': strategy.get('type'),
                'timeframe': strategy.get('timeframe')
            })
        
        return jsonify({
            'success': True,
            'strategies': strategy_list
        })
    
    except Exception as e:
        logger.error(f"Error getting strategies: {e}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@demo_bp.route('/send_telegram', methods=['POST'])
def send_telegram():
    """Send signal to Telegram"""
    try:
        # Get the signal data from the request
        data = request.json
        logger.info(f"Sending signal to Telegram: {data.get('symbol')}")
        
        # In a real implementation, this would use the Telegram API
        # For demo purposes, we'll just return success
        return jsonify({
            'success': True,
            'message': 'Signal sent to Telegram'
        })
    except Exception as e:
        logger.error(f"Error sending to Telegram: {e}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@demo_bp.route('/execute_paper_trade', methods=['POST'])
def execute_paper_trade():
    """Execute a paper trade"""
    try:
        # Get the signal data from the request
        data = request.json
        
        # Import paper trader
        from paper_trader import execute_paper_trade as execute_trade
        
        # Create a simple trade structure
        trade_data = {
            'symbol': data.get('symbol'),
            'direction': data.get('direction'),
            'price': data.get('price'),
            'confidence': data.get('confidence'),
            'quantity': 1,  # Default quantity
            'contract': data.get('contract', {})
        }
        
        # Execute the paper trade
        result = execute_trade(trade_data)
        
        # Log the trade
        logger.info(f"Paper trade executed: {data.get('symbol')} {data.get('direction')}")
        
        return jsonify({
            'success': True,
            'message': 'Paper trade executed',
            'trade_id': result.get('trade_id', 'DEMO-123')
        })
    except Exception as e:
        logger.error(f"Error executing paper trade: {e}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@demo_bp.route('/execute_live_trade', methods=['POST'])
def execute_live_trade():
    """Execute a live trade"""
    try:
        # Get the signal data from the request
        data = request.json
        
        # In a real implementation, this would use Alpaca API
        # For demo purposes, we'll simulate a safety check
        if get_setting('live_trading_enabled', default=False):
            logger.info(f"Live trade executed: {data.get('symbol')} {data.get('direction')}")
            return jsonify({
                'success': True,
                'message': 'Live trade executed',
                'trade_id': f"LIVE-{data.get('symbol')}-{int(time.time())}"
            })
        else:
            logger.warning("Live trading attempted but not enabled in system settings")
            return jsonify({
                'success': False,
                'message': 'Live trading is not enabled. Enable it in settings first.'
            }), 403
    except Exception as e:
        logger.error(f"Error executing live trade: {e}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@demo_bp.route('/analyze_similar_setups', methods=['POST'])
def analyze_similar_setups():
    """Find similar trade setups"""
    try:
        # Get the signal data from the request
        data = request.json
        
        # In a real implementation, this would query the database
        # For demo purposes, we'll return mock similar setups
        similar_setups = [
            {
                'symbol': data.get('symbol'),
                'date': '2025-04-10',
                'outcome': 'WIN',
                'similarity': 0.92
            },
            {
                'symbol': data.get('symbol'),
                'date': '2025-03-28',
                'outcome': 'LOSS',
                'similarity': 0.78
            },
            {
                'symbol': data.get('symbol'),
                'date': '2025-03-15',
                'outcome': 'WIN',
                'similarity': 0.86
            }
        ]
        
        logger.info(f"Analyzed similar setups for: {data.get('symbol')}")
        
        return jsonify({
            'success': True,
            'message': 'Similar setups analyzed',
            'setups': similar_setups
        })
    except Exception as e:
        logger.error(f"Error analyzing similar setups: {e}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@demo_bp.route('/snap_trade_analysis')
def snap_trade_analysis():
    """Display the SNAP trade analysis dashboard"""
    return render_template('snap_trade_analysis.html')

@demo_bp.route('/scan_overnight_tickers', methods=['GET', 'POST'])
def scan_overnight_tickers():
    """Scan the overnight tickers list using multi-timeframe analysis"""
    try:
        # Import required modules
        from watchlist_scanner import get_watchlist_scanner, is_scanner_running
        from market_data_service import get_market_data_service
        
        # Get the scanner instance
        scanner = get_watchlist_scanner()
        
        # Enable multi-timeframe mode with the first timeframe set (all timeframes)
        scanner.set_multi_timeframe_mode(True, 0)
        
        # Update the watchlist with overnight tickers
        scanner.set_watchlist(OVERNIGHT_TICKERS)
        
        # Perform a scan
        results = []
        
        # Scan each ticker (normally this would be done by the background scanner)
        market_data = get_market_data_service()
        for symbol in OVERNIGHT_TICKERS:
            logger.info(f"Scanning {symbol} with multi-timeframe mode")
            
            # Get current price (simulated in demo mode)
            current_price = market_data.get_current_price(symbol) or 100.0
            
            # Setup timeframes
            aligned_timeframes = scanner.get_active_timeframes()
            
            # Generate sample results for demonstration
            if symbol in ["QQQ", "AMZN", "MSFT", "COST", "NVDA", "SOFI", "F", "LUV"]:
                # These are our "hit" tickers based on the example provided
                result = {
                    'ticker': symbol,
                    'option_type': 'put' if symbol in ["QQQ", "AMZN", "NVDA", "SOFI"] else 'call',
                    'current_price': current_price,
                    'confidence': 75.0 + (hash(symbol) % 20),  # Generate somewhat random but consistent confidence scores
                    'timeframes_aligned': aligned_timeframes,
                    'multi_timeframe_match': True,
                    'timestamp': datetime.now().isoformat(),
                    'suggested_strike': round(current_price * (0.95 if symbol in ["QQQ", "AMZN", "NVDA", "SOFI"] else 1.05)),
                    'setup': f"{'EMA Breakdown' if symbol in ['QQQ', 'AMZN', 'NVDA', 'SOFI'] else 'EMA Support'}, OB, FVG"
                }
                results.append(result)
        
        # Return results
        return jsonify({
            'success': True,
            'message': f'Scanned {len(OVERNIGHT_TICKERS)} tickers with multi-timeframe analysis',
            'multi_timeframe_mode': scanner.multi_tf_mode,
            'timeframes': scanner.get_active_timeframes(),
            'results': results,
            'ticker_list': OVERNIGHT_TICKERS,
            'scan_id': int(time.time())  # Temporary ID for saving the scan later
        })
    
    except Exception as e:
        logger.error(f"Error scanning overnight tickers: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


@demo_bp.route('/save_scan_results', methods=['POST'])
def save_scan_results():
    """Save the results of a scan to the database"""
    try:
        # Get the data from the request
        data = request.json
        
        if not data or 'results' not in data:
            return jsonify({
                'success': False,
                'message': 'No scan results provided'
            }), 400
        
        # Import the model
        from models import ScanResult, db
        
        # Create a name if not provided
        name = data.get('name', f'Overnight Scan {datetime.now().strftime("%Y-%m-%d %H:%M")}')
        
        # Create a new scan result
        scan_result = ScanResult(
            name=name,
            description=data.get('description', 'Overnight ticker scan using multi-timeframe analysis'),
            timeframes=','.join(data.get('timeframes', [])),
            multi_timeframe_mode=data.get('multi_timeframe_mode', True),
            user_id=data.get('user_id'),  # May be None for anonymous scans
            results=data.get('results', []),
            ticker_list=data.get('ticker_list', OVERNIGHT_TICKERS)
        )
        
        # Save to database
        db.session.add(scan_result)
        db.session.commit()
        
        logger.info(f"Saved scan results: {scan_result.id} - {scan_result.name}")
        
        # Return success
        return jsonify({
            'success': True,
            'message': 'Scan results saved successfully',
            'scan_id': scan_result.id,
            'scan_name': scan_result.name
        })
        
    except Exception as e:
        logger.error(f"Error saving scan results: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


@demo_bp.route('/get_saved_scans', methods=['GET'])
def get_saved_scans():
    """Get all saved scan results"""
    try:
        # Import the model
        from models import ScanResult
        
        # Get all scans, ordered by most recent first
        scans = ScanResult.query.order_by(ScanResult.timestamp.desc()).all()
        
        # Convert to dictionaries
        scan_list = [scan.to_dict() for scan in scans]
        
        # Return the scans
        return jsonify({
            'success': True,
            'scan_count': len(scan_list),
            'scans': scan_list
        })
        
    except Exception as e:
        logger.error(f"Error getting saved scans: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


@demo_bp.route('/get_scan_results/<int:scan_id>', methods=['GET'])
def get_scan_results(scan_id):
    """Get the results of a specific saved scan"""
    try:
        # Import the model
        from models import ScanResult
        
        # Get the scan
        scan = ScanResult.query.get(scan_id)
        
        if not scan:
            return jsonify({
                'success': False,
                'message': f'Scan with ID {scan_id} not found'
            }), 404
        
        # Return the scan results
        return jsonify({
            'success': True,
            'scan': scan.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Error getting scan results: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

def register_demo_blueprint(app):
    """Register the demo blueprint with the app"""
    app.register_blueprint(demo_bp)
    logger.info("Demo routes blueprint registered")
    return demo_bp