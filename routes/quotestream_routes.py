"""
QuotestreamPY API Routes - Integrates QuotestreamPY with OG Signal Bot
"""
import logging
import json
from flask import Blueprint, jsonify, request, render_template, current_app, redirect, url_for
from flask_login import login_required, current_user
from quotestream_integration import get_quotestream_integration

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Blueprint
quotestream_bp = Blueprint('quotestream', __name__, url_prefix='/quotestream')

# Default watchlist if none exists
DEFAULT_WATCHLIST = ['AAPL', 'MSFT', 'AMZN', 'GOOG', 'TSLA']

@quotestream_bp.route('/')
@login_required
def quotestream_dashboard():
    """Render QuotestreamPY dashboard"""
    return render_template('quotestream_dashboard.html')

@quotestream_bp.route('/api/status')
@login_required
def api_status():
    """Get QuotestreamPY API status"""
    quotestream = get_quotestream_integration()
    return jsonify({
        'connected': quotestream.connected,
        'api_base': quotestream.api_base
    })

@quotestream_bp.route('/api/watchlist', methods=['GET'])
@login_required
def get_watchlist():
    """Get watchlist symbols"""
    quotestream = get_quotestream_integration()
    watchlist = quotestream.get_watchlist()
    
    # Use default watchlist if empty
    if not watchlist:
        watchlist = DEFAULT_WATCHLIST
    
    return jsonify({
        'symbols': watchlist
    })

@quotestream_bp.route('/api/watchlist', methods=['POST'])
@login_required
def update_watchlist():
    """Add or remove symbols from watchlist"""
    data = request.json
    quotestream = get_quotestream_integration()
    
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400
    
    # Get current watchlist
    current_watchlist = quotestream.get_watchlist()
    if not current_watchlist:
        current_watchlist = DEFAULT_WATCHLIST
    
    if 'symbol' in data:
        # Add or remove a single symbol
        symbol = data['symbol'].upper()
        action = data.get('action', 'add')
        
        if action == 'add':
            if symbol not in current_watchlist:
                current_watchlist.append(symbol)
        elif action == 'remove':
            if symbol in current_watchlist:
                current_watchlist.remove(symbol)
    elif 'symbols' in data:
        # Replace entire watchlist
        current_watchlist = [s.upper() for s in data['symbols']]
    
    # Update watchlist in QuotestreamPY
    success = quotestream.update_watchlist(current_watchlist)
    
    if success:
        return jsonify({
            'success': True,
            'message': 'Watchlist updated successfully',
            'symbols': current_watchlist
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Failed to update watchlist'
        }), 500

@quotestream_bp.route('/api/quotes')
@login_required
def get_quotes():
    """Get quotes for specified symbols"""
    symbols = request.args.get('symbols', '')
    if not symbols:
        return jsonify({}), 400
    
    symbol_list = [s.strip().upper() for s in symbols.split(',')]
    quotestream = get_quotestream_integration()
    quotes = quotestream.get_quotes(symbol_list)
    
    return jsonify(quotes)

@quotestream_bp.route('/api/depth/<symbol>')
@login_required
def get_depth(symbol):
    """Get market depth for a symbol"""
    quotestream = get_quotestream_integration()
    depth = quotestream.get_market_depth(symbol.upper())
    
    return jsonify(depth)

@quotestream_bp.route('/api/trades/<symbol>')
@login_required
def get_trades(symbol):
    """Get recent trades for a symbol"""
    limit = request.args.get('limit', 20, type=int)
    quotestream = get_quotestream_integration()
    trades = quotestream.get_recent_trades(symbol.upper(), limit)
    
    return jsonify(trades)

@quotestream_bp.route('/api/options/<symbol>')
@login_required
def get_options(symbol):
    """Get options chain for an underlying symbol"""
    quotestream = get_quotestream_integration()
    options = quotestream.get_options_chain(symbol.upper())
    
    return jsonify(options)

@quotestream_bp.route('/api/search')
@login_required
def search_symbols():
    """Search for symbols"""
    query = request.args.get('q', '').upper()
    if not query:
        return jsonify({'results': []}), 400
    
    # For now, return some filtered default results from our watchlist
    quotestream = get_quotestream_integration()
    watchlist = quotestream.get_watchlist()
    if not watchlist:
        watchlist = DEFAULT_WATCHLIST
    
    results = [
        {'symbol': symbol, 'description': f"{symbol} Stock"} 
        for symbol in watchlist if query in symbol
    ]
    
    # Add some common symbols if not in watchlist
    common_symbols = {
        'AAPL': 'Apple Inc.',
        'MSFT': 'Microsoft Corporation',
        'AMZN': 'Amazon.com Inc.',
        'GOOG': 'Alphabet Inc.',
        'TSLA': 'Tesla Inc.',
        'META': 'Meta Platforms Inc.',
        'NVDA': 'NVIDIA Corporation',
        'AMD': 'Advanced Micro Devices Inc.',
        'INTC': 'Intel Corporation'
    }
    
    for symbol, description in common_symbols.items():
        if query in symbol and symbol not in [r['symbol'] for r in results]:
            results.append({'symbol': symbol, 'description': description})
    
    return jsonify({'results': results[:10]})  # Limit to 10 results

@quotestream_bp.route('/api/send-to-strategy', methods=['POST'])
@login_required
def send_to_strategy():
    """Send a symbol to OG Strategy Scanner"""
    data = request.json
    if not data or 'symbol' not in data:
        return jsonify({'success': False, 'message': 'No symbol provided'}), 400
    
    symbol = data['symbol'].upper()
    
    try:
        # Access OG Strategy Scanner from app context
        from app import og_scanner
        
        # Add symbol to scanner watchlist
        if og_scanner:
            from market_data_service import get_market_data_service
            market_data = get_market_data_service()
            
            # Get current watchlist
            current_watchlist = market_data.get_watchlist()
            
            # Add symbol if not already in watchlist
            if symbol not in current_watchlist:
                current_watchlist.append(symbol)
                market_data.set_watchlist(current_watchlist)
                
                # Log the addition
                logger.info(f"Added {symbol} to OG Strategy Scanner watchlist")
                
                return jsonify({
                    'success': True,
                    'message': f'Added {symbol} to OG Strategy Scanner'
                })
            else:
                return jsonify({
                    'success': True,
                    'message': f'{symbol} is already in the OG Strategy Scanner'
                })
        else:
            return jsonify({
                'success': False,
                'message': 'OG Strategy Scanner is not available'
            }), 500
            
    except ImportError as e:
        logger.error(f"Failed to import scanner module: {e}")
        return jsonify({
            'success': False,
            'message': 'OG Strategy Scanner module is not available'
        }), 500
    except Exception as e:
        logger.error(f"Error sending symbol to OG Strategy: {e}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@quotestream_bp.route('/api/volume-analysis/<symbol>')
@login_required
def get_volume_analysis(symbol):
    """Get volume analysis data for a symbol"""
    quotestream = get_quotestream_integration()
    analysis = quotestream.get_volume_analysis(symbol.upper())
    
    return jsonify(analysis)
    
@quotestream_bp.route('/api/historical/<symbol>')
@login_required
def get_historical_data(symbol):
    """Get historical price data for a symbol"""
    timeframe = request.args.get('timeframe', '1d')
    quotestream = get_quotestream_integration()
    
    try:
        # Try to connect to the QuotestreamPY API to get historical data
        # For now, generate sample data as the API doesn't have this endpoint yet
        import datetime
        import random
        
        symbol = symbol.upper()
        data = []
        now = datetime.datetime.now()
        
        # Get current price from quotes if available
        current_price = None
        quotes = quotestream.get_quotes([symbol])
        if symbol in quotes:
            current_price = quotes[symbol].get('last')
        
        # Use a reasonable default if not available
        if not current_price:
            current_price = 100.0
        
        # Determine timeframe settings
        days_back = 100
        time_increment = datetime.timedelta(days=1)
        
        if timeframe == '1min':
            days_back = 1
            time_increment = datetime.timedelta(minutes=1)
        elif timeframe == '5min':
            days_back = 1
            time_increment = datetime.timedelta(minutes=5)
        elif timeframe == '15min':
            days_back = 1
            time_increment = datetime.timedelta(minutes=15)
        elif timeframe == '1h':
            days_back = 7
            time_increment = datetime.timedelta(hours=1)
        elif timeframe == '1d':
            days_back = 100
            time_increment = datetime.timedelta(days=1)
        elif timeframe == '1w':
            days_back = 156
            time_increment = datetime.timedelta(weeks=1)
            
        # Generate a fixed number of data points to improve performance
        num_points = 100  # Limit to 100 data points
        price = current_price
        
        # Calculate time increments to generate fixed number of points
        total_time_range = datetime.timedelta(days=days_back)
        if timeframe == '1min':
            time_increment = datetime.timedelta(minutes=1)
        elif timeframe == '5min':
            time_increment = datetime.timedelta(minutes=5)
        elif timeframe == '15min':
            time_increment = datetime.timedelta(minutes=15)
        elif timeframe == '1h':
            time_increment = datetime.timedelta(hours=1)
        elif timeframe == '1w':
            time_increment = datetime.timedelta(weeks=1)
        else:  # default to 1d
            time_increment = datetime.timedelta(days=1)
        
        # Calculate actual number of increments to avoid generating too many points
        actual_increments = min(int(total_time_range / time_increment), num_points)
        
        # Generate data points
        for i in range(actual_increments):
            # Calculate the time for this point
            point_time = now - (total_time_range * (actual_increments - i) / actual_increments)
            
            # Add some randomness but maintain a trend
            price_change = (random.random() - 0.5) * 0.02  # -1% to +1% change
            price = price * (1 + price_change)
            
            # Generate OHLC data
            open_price = price
            high_price = price * (1 + random.random() * 0.01)  # Up to +1%
            low_price = price * (1 - random.random() * 0.01)   # Up to -1%
            close_price = price * (1 + (random.random() - 0.5) * 0.01)  # -0.5% to +0.5%
            
            # Ensure high is highest and low is lowest
            high_price = max(high_price, open_price, close_price)
            low_price = min(low_price, open_price, close_price)
            
            # Generate plausible volume
            base_volume = 1000000  # Base volume
            volume_multiplier = 1 + abs(price_change) * 10  # Higher volume on bigger moves
            volume = int(base_volume * volume_multiplier * random.uniform(0.8, 1.2))
            
            # Add data point
            data.append({
                'time': point_time.isoformat(),
                'open': round(open_price, 2),
                'high': round(high_price, 2),
                'low': round(low_price, 2),
                'close': round(close_price, 2),
                'volume': volume
            })
            
            price = close_price
            
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error generating historical data: {e}")
        return jsonify([]), 500

@quotestream_bp.route('/chart/<symbol>')
@login_required
def chart(symbol):
    """Display a chart for a symbol"""
    # Get market data for the chart from QuotestreamPY service
    quotestream = get_quotestream_integration()
    
    # Get additional symbols for comparison if needed
    comparison_symbols = request.args.get('comparison', '').split(',')
    comparison_symbols = [s.strip().upper() for s in comparison_symbols if s.strip()]
    
    # Get chart type and timeframe from request args, with defaults
    chart_type = request.args.get('type', 'candlestick')
    timeframe = request.args.get('timeframe', '1D')
    
    # Get any indicators requested
    indicators = request.args.get('indicators', 'ema,volume').split(',')
    indicators = [i.strip().lower() for i in indicators if i.strip()]
    
    return render_template(
        'quotestream_chart.html',
        symbol=symbol.upper(),
        comparison_symbols=comparison_symbols,
        chart_type=chart_type,
        timeframe=timeframe,
        indicators=indicators,
        page_title=f"{symbol.upper()} Chart"
    )

def register_quotestream_blueprint(app):
    """Register the QuotestreamPY blueprint with the Flask app"""
    app.register_blueprint(quotestream_bp)
    logger.info("QuotestreamPY blueprint registered")