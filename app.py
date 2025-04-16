import os
import logging
import io
import csv
from datetime import datetime, timedelta, time
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, make_response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_login import LoginManager, login_user, logout_user, current_user, login_required as flask_login_required
from flask_socketio import SocketIO, emit, join_room, leave_room
from functools import wraps

# Set up logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Flask app
class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///ogsignalbot.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

# Initialize LoginManager
login_manager = LoginManager(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'

# Custom login_required decorator that respects DISABLE_AUTH
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if auth is disabled for development
        if os.getenv("DISABLE_AUTH", "false").lower() == "true":
            return f(*args, **kwargs)
        # Otherwise use Flask-Login's login_required
        return flask_login_required(f)(*args, **kwargs)
    return decorated_function

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

# Import models and create tables
with app.app_context():
    from models import Signal, Trade, SystemLog, Setting, User
    db.create_all()
    
    # Initialize settings if not exists
    from config import init_settings
    init_settings()

# Import services
from strategy import SignalStrategy
from logs_service import get_latest_logs
from telegram_service import send_telegram_message
import alpaca_trade_executor as alpaca

# Create strategy instance
strategy = SignalStrategy()

# Initialize strategy within app context
with app.app_context():
    try:
        strategy.load_config()
        logger.info("Strategy initialized within app context")
    except Exception as e:
        logger.error(f"Failed to initialize strategy: {e}")

# Routes
@app.route('/health')
def health():
    """Health check endpoint for Autoscale deployment"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'server_uptime': 'Active'
    }), 200
    
@app.route('/test')
def test_route():
    """Simple test route that doesn't require authentication or database access"""
    return jsonify({
        "status": "success",
        "message": "Test route is working",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "auth_disabled": os.getenv("DISABLE_AUTH", "false").lower() == "true"
    })

@app.route('/')
def index():
    # Always return 200 for health checks first
    if request.headers.get('X-Forwarded-For') is None:
        return jsonify({'status': 'healthy'}), 200
        
    # Regular application flow
    disable_auth = os.getenv("DISABLE_AUTH", "false").lower() == "true"
    
    if disable_auth:
        flash("Authentication disabled for development", "info")
        
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Get account info
    account = alpaca.get_account_info()
    
    # Get recent signals
    signals = Signal.query.order_by(Signal.timestamp.desc()).limit(5).all()
    
    # Get recent trades
    trades = Trade.query.order_by(Trade.timestamp.desc()).limit(5).all()
    
    # Get system logs
    logs = get_latest_logs(10)
    
    # Get auto-trade setting
    auto_trade_setting = Setting.query.filter_by(key='auto_trade_enabled').first()
    auto_trade_enabled = auto_trade_setting.value_bool if auto_trade_setting else False
    
    # Get position data
    positions = alpaca.get_positions()
    
    return render_template('dashboard.html', 
                           account=account,
                           signals=signals, 
                           trades=trades, 
                           logs=logs,
                           auto_trade_enabled=auto_trade_enabled,
                           positions=positions)

@app.route('/signals')
@login_required
def signals():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Get filter parameters
    symbol_filter = request.args.get('symbol', '')
    direction_filter = request.args.get('direction', '')
    date_range = request.args.get('daterange', '')
    
    # Base query
    query = Signal.query
    
    # Apply filters
    if symbol_filter:
        query = query.filter(Signal.symbol.ilike(f'%{symbol_filter}%'))
    
    if direction_filter:
        query = query.filter(Signal.direction == direction_filter)
    
    if date_range:
        now = datetime.now()
        if date_range == 'today':
            start_date = datetime.combine(now.date(), time.min)
            query = query.filter(Signal.timestamp >= start_date)
        elif date_range == 'yesterday':
            yesterday = now.date() - timedelta(days=1)
            start_date = datetime.combine(yesterday, time.min)
            end_date = datetime.combine(yesterday, time.max)
            query = query.filter(Signal.timestamp.between(start_date, end_date))
        elif date_range == 'week':
            start_date = datetime.combine(now.date() - timedelta(days=now.weekday()), time.min)
            query = query.filter(Signal.timestamp >= start_date)
        elif date_range == 'month':
            start_date = datetime.combine(now.replace(day=1).date(), time.min)
            query = query.filter(Signal.timestamp >= start_date)
    
    # Paginate results
    signals = query.order_by(Signal.timestamp.desc()).paginate(page=page, per_page=per_page)
    
    # Get statistics for the dashboard
    # We'll use the same filters for the stats to maintain consistency
    stats_query = db.session.query(
        db.func.count(Signal.id),
        db.func.sum(db.case((Signal.executed == True, 1), else_=0)),
        db.func.sum(db.case((Signal.direction == 'UP', 1), else_=0)),
        db.func.sum(db.case((Signal.direction == 'DOWN', 1), else_=0))
    )
    
    # Apply the same filters as the main query
    if symbol_filter:
        stats_query = stats_query.filter(Signal.symbol.ilike(f'%{symbol_filter}%'))
    
    if direction_filter:
        stats_query = stats_query.filter(Signal.direction == direction_filter)
    
    if date_range:
        if date_range == 'today':
            start_date = datetime.combine(now.date(), time.min)
            stats_query = stats_query.filter(Signal.timestamp >= start_date)
        elif date_range == 'yesterday':
            yesterday = now.date() - timedelta(days=1)
            start_date = datetime.combine(yesterday, time.min)
            end_date = datetime.combine(yesterday, time.max)
            stats_query = stats_query.filter(Signal.timestamp.between(start_date, end_date))
        elif date_range == 'week':
            start_date = datetime.combine(now.date() - timedelta(days=now.weekday()), time.min)
            stats_query = stats_query.filter(Signal.timestamp >= start_date)
        elif date_range == 'month':
            start_date = datetime.combine(now.replace(day=1).date(), time.min)
            stats_query = stats_query.filter(Signal.timestamp >= start_date)
    
    # Execute the query and get the results
    total, executed, longs, shorts = stats_query.first()
    
    # Create a stats dictionary
    signals_stats = {
        'total': total or 0,
        'executed': executed or 0,
        'longs': longs or 0,
        'shorts': shorts or 0,
        'execution_rate': round((executed / total * 100) if total else 0, 1)
    }
    
    return render_template('signals.html', signals=signals, signals_stats=signals_stats)

@app.route('/trades')
@login_required
def trades():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Get filter parameters
    symbol_filter = request.args.get('symbol', '')
    direction_filter = request.args.get('direction', '')
    status_filter = request.args.get('status', '')
    date_range = request.args.get('daterange', '')
    
    # Base query
    query = Trade.query
    
    # Apply filters
    if symbol_filter:
        query = query.filter(Trade.symbol.ilike(f'%{symbol_filter}%'))
    
    if direction_filter:
        query = query.filter(Trade.direction == direction_filter)
    
    if status_filter:
        query = query.filter(Trade.status == status_filter)
    
    if date_range:
        now = datetime.now()
        if date_range == 'today':
            start_date = datetime.combine(now.date(), time.min)
            query = query.filter(Trade.timestamp >= start_date)
        elif date_range == 'yesterday':
            yesterday = now.date() - timedelta(days=1)
            start_date = datetime.combine(yesterday, time.min)
            end_date = datetime.combine(yesterday, time.max)
            query = query.filter(Trade.timestamp.between(start_date, end_date))
        elif date_range == 'week':
            start_date = datetime.combine(now.date() - timedelta(days=now.weekday()), time.min)
            query = query.filter(Trade.timestamp >= start_date)
        elif date_range == 'month':
            start_date = datetime.combine(now.replace(day=1).date(), time.min)
            query = query.filter(Trade.timestamp >= start_date)
    
    # Paginate results
    trades = query.order_by(Trade.timestamp.desc()).paginate(page=page, per_page=per_page)
    
    # Get Alpaca orders for additional info
    alpaca_orders = alpaca.get_orders()
    
    # Get statistics for the dashboard
    # We'll use the same filters for the stats to maintain consistency
    stats_query = db.session.query(
        db.func.count(Trade.id),
        db.func.sum(db.case((Trade.status == 'FILLED', 1), else_=0)),
        db.func.sum(db.case((Trade.direction == 'BUY', 1), else_=0)),
        db.func.sum(db.case((Trade.direction == 'SELL', 1), else_=0)),
        db.func.avg(Trade.price)
    )
    
    # Apply the same filters as the main query
    if symbol_filter:
        stats_query = stats_query.filter(Trade.symbol.ilike(f'%{symbol_filter}%'))
    
    if direction_filter:
        stats_query = stats_query.filter(Trade.direction == direction_filter)
    
    if status_filter:
        stats_query = stats_query.filter(Trade.status == status_filter)
    
    if date_range:
        if date_range == 'today':
            start_date = datetime.combine(now.date(), time.min)
            stats_query = stats_query.filter(Trade.timestamp >= start_date)
        elif date_range == 'yesterday':
            yesterday = now.date() - timedelta(days=1)
            start_date = datetime.combine(yesterday, time.min)
            end_date = datetime.combine(yesterday, time.max)
            stats_query = stats_query.filter(Trade.timestamp.between(start_date, end_date))
        elif date_range == 'week':
            start_date = datetime.combine(now.date() - timedelta(days=now.weekday()), time.min)
            stats_query = stats_query.filter(Trade.timestamp >= start_date)
        elif date_range == 'month':
            start_date = datetime.combine(now.replace(day=1).date(), time.min)
            stats_query = stats_query.filter(Trade.timestamp >= start_date)
    
    # Execute the query and get the results
    total, filled, buys, sells, avg_price = stats_query.first()
    
    # Create a stats dictionary
    trades_stats = {
        'total': total or 0,
        'filled': filled or 0,
        'buys': buys or 0,
        'sells': sells or 0,
        'fill_rate': round((filled / total * 100) if total else 0, 1),
        'avg_price': round(avg_price, 2) if avg_price else 0
    }
    
    return render_template('trades.html', trades=trades, alpaca_orders=alpaca_orders, trades_stats=trades_stats)

@app.route('/logs')
@login_required
def logs():
    page = request.args.get('page', 1, type=int)
    per_page = 50
    log_entries = SystemLog.query.order_by(SystemLog.timestamp.desc()).paginate(page=page, per_page=per_page)
    return render_template('logs.html', logs=log_entries)

@app.route('/market-settings')
@login_required
def market_settings():
    """Market data and trading settings page"""
    return render_template('market_settings.html')

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        # Update auto-trade setting
        auto_trade_enabled = 'auto_trade_enabled' in request.form
        
        setting = Setting.query.filter_by(key='auto_trade_enabled').first()
        if setting:
            setting.value_bool = auto_trade_enabled
        else:
            setting = Setting(key='auto_trade_enabled', value_bool=auto_trade_enabled)
            db.session.add(setting)
        
        # Update telegram notifications setting
        telegram_enabled = 'telegram_enabled' in request.form
        
        setting = Setting.query.filter_by(key='telegram_enabled').first()
        if setting:
            setting.value_bool = telegram_enabled
        else:
            setting = Setting(key='telegram_enabled', value_bool=telegram_enabled)
            db.session.add(setting)
        
        # Update evening brief setting
        evening_brief_enabled = 'evening_brief_enabled' in request.form
        
        setting = Setting.query.filter_by(key='evening_brief_enabled').first()
        if setting:
            setting.value_bool = evening_brief_enabled
        else:
            setting = Setting(key='evening_brief_enabled', value_bool=evening_brief_enabled)
            db.session.add(setting)
            
        db.session.commit()
        flash('Settings updated successfully', 'success')
        return redirect(url_for('settings'))
    
    # Get current settings
    auto_trade_setting = Setting.query.filter_by(key='auto_trade_enabled').first()
    auto_trade_enabled = auto_trade_setting.value_bool if auto_trade_setting else False
    
    telegram_setting = Setting.query.filter_by(key='telegram_enabled').first()
    telegram_enabled = telegram_setting.value_bool if telegram_setting else False
    
    evening_brief_setting = Setting.query.filter_by(key='evening_brief_enabled').first()
    evening_brief_enabled = evening_brief_setting.value_bool if evening_brief_setting else False
    
    return render_template('settings.html', 
                           auto_trade_enabled=auto_trade_enabled,
                           telegram_enabled=telegram_enabled,
                           evening_brief_enabled=evening_brief_enabled)

@app.route('/system')
@login_required
def system():
    # Get account info
    account = alpaca.get_account_info()
    
    # Get positions
    positions = alpaca.get_positions()
    
    # Get recent errors
    errors = SystemLog.query.filter_by(level='ERROR').order_by(SystemLog.timestamp.desc()).limit(10).all()
    
    # Get settings
    settings = Setting.query.all()
    
    return render_template('system.html', 
                           account=account,
                           positions=positions,
                           errors=errors,
                           settings=settings)

@app.route('/api/toggle-trading', methods=['POST'])
def toggle_trading():
    setting = Setting.query.filter_by(key='auto_trade_enabled').first()
    if setting:
        setting.value_bool = not setting.value_bool
        db.session.commit()
        return jsonify({'success': True, 'enabled': setting.value_bool})
    return jsonify({'success': False, 'error': 'Setting not found'}), 404

@app.route('/api/system-status')
def system_status():
    # Check if Alpaca API is working
    account = alpaca.get_account_info()
    alpaca_status = account is not None
    
    # Check if strategy is running
    strategy_status = strategy.is_running()
    
    # Count recent errors (last 24 hours)
    yesterday = datetime.now() - timedelta(days=1)
    error_count = SystemLog.query.filter(
        SystemLog.level == 'ERROR',
        SystemLog.timestamp >= yesterday
    ).count()
    
    return jsonify({
        'alpaca_api': alpaca_status,
        'strategy': strategy_status,
        'error_count': error_count
    })

@app.route('/api/send-test-message', methods=['POST'])
def send_test_message():
    try:
        send_telegram_message("Test message from OG Signal Bot Dashboard")
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/ticker')
def ticker_dashboard():
    """Lightweight ticker dashboard (fallback while chart system is improved)"""
    from config import get_setting
    
    # Get settings for UI display
    chart_enabled = get_setting('chart_enabled', False)
    chart_disable_reason = get_setting('chart_disable_reason', 'Optimizing for data reliability over visualization')
    update_interval = get_setting('update_interval_ms', 2000)
    
    # Get recent signals
    signals = Signal.query.order_by(Signal.timestamp.desc()).limit(10).all()
    
    # Get watchlist from settings or use default
    default_watchlist = ['SPY', 'QQQ', 'AAPL', 'MSFT', 'TSLA', 'NVDA', 'AMZN', 'META', 'GOOGL', 'AMD']
    watchlist_str = get_setting('watchlist', ','.join(default_watchlist))
    watchlist = [s.strip().upper() for s in watchlist_str.split(',') if s.strip()]
    
    # Get scanner status
    scanner_active = get_setting('scanner_active', True)
    scan_interval = get_setting('scan_interval_seconds', 15)
    
    # Get market status from market data service
    from market_data_service import get_market_data_service
    market_data = get_market_data_service()
    market_open = market_data.is_market_open()
    
    # Schedule real-time updates for these symbols
    from socketio_server import schedule_ticker_updates
    try:
        schedule_ticker_updates(watchlist, int(update_interval / 1000))
    except Exception as e:
        logger.error(f"Error scheduling ticker updates: {e}")
    
    # Get signal throttling status
    signal_throttle_active = get_setting('signal_throttle_active', True)
    throttle_window = get_setting('throttle_window_seconds', 30)
    confidence_cutoff = get_setting('confidence_cutoff', 0.7)
    
    return render_template('ticker_dashboard.html',
                          chart_enabled=chart_enabled,
                          chart_disable_reason=chart_disable_reason,
                          update_interval=update_interval,
                          signals=signals,
                          watchlist=watchlist,
                          scanner_active=scanner_active,
                          scan_interval=scan_interval,
                          market_open=market_open,
                          signal_throttle_active=signal_throttle_active,
                          throttle_window=throttle_window,
                          confidence_cutoff=confidence_cutoff,
                          page="ticker")

@app.route('/signal-health')
@login_required
def signal_health_dashboard():
    """Signal Health Dashboard for monitoring throttling metrics"""
    try:
        from signal_throttler import get_throttling_metrics
        from config import get_setting
        
        # Get throttling metrics
        metrics = get_throttling_metrics()
        
        # Get throttle settings
        throttle_active = get_setting('signal_throttle_active', True)
        throttle_window = get_setting('throttle_window_seconds', 30)
        confidence_cutoff = get_setting('confidence_cutoff', 0.7)
        throttle_override = get_setting('throttle_override', False)
        
        # Get boost mode status
        boost_mode_active = get_setting('boost_mode_active', False)
        boost_end_time = get_setting('boost_end_time', '')
        
        # Calculate remaining boost time
        boost_time_remaining = 0
        if boost_mode_active and boost_end_time:
            try:
                boost_end = datetime.fromisoformat(boost_end_time)
                now = datetime.now()
                if boost_end > now:
                    boost_time_remaining = int((boost_end - now).total_seconds())
                else:
                    # Boost mode expired
                    boost_mode_active = False
            except Exception:
                boost_mode_active = False
                
    except Exception as e:
        logger.error(f"Error getting throttling metrics: {e}")
        metrics = {
            'total_signals': 0,
            'allowed_count': 0,
            'throttled_count': 0,
            'throttle_rate': 0,
            'avg_latency_ms': 0,
            'active_throttles': [],
            'latency_samples': [0, 0, 0],
            'symbols': {}
        }
        throttle_active = True
        throttle_window = 30
        confidence_cutoff = 0.7
        throttle_override = False
        boost_mode_active = False
        boost_time_remaining = 0
        
    return render_template('signal_health.html',
                         metrics=metrics,
                         throttle_active=throttle_active,
                         throttle_window=throttle_window,
                         confidence_cutoff=confidence_cutoff,
                         throttle_override=throttle_override,
                         boost_mode_active=boost_mode_active,
                         boost_time_remaining=boost_time_remaining)

@app.route('/signal-queue')
@login_required
def signal_queue_monitor():
    """Signal Queue Monitor for viewing queue health and metrics"""
    try:
        from signal_queue_monitor import get_queue_metrics
        
        # Get queue metrics
        metrics = get_queue_metrics()
        
    except Exception as e:
        logger.error(f"Error getting queue metrics: {e}")
        metrics = {
            'total_processed': 0,
            'flushed': 0,
            'retried': 0,
            'active': 0,
            'avg_processing_time_ms': 0,
            'confidence_buckets': [0, 0, 0, 0, 0],
            'signal_rate_per_min': 0,
            'health_status': 'HEALTHY',
            'auto_healing_enabled': True, 
            'healing_actions_count': 0,
            'stress_test_active': False
        }
        
    return render_template('signal_queue.html', metrics=metrics)

@app.route('/options')
@login_required
def options():
    """Options analysis page"""
    from options_analyzer import get_current_price, get_options_chain
    
    # Default to SPY if no symbol provided
    symbol = request.args.get('symbol', 'SPY')
    
    # Get current price
    price = get_current_price(symbol)
    
    # Get recent options-related signals
    signals = Signal.query.filter(
        Signal.symbol == symbol,
        Signal.timestamp >= (datetime.now() - timedelta(days=7))
    ).order_by(Signal.timestamp.desc()).limit(5).all()
    
    # Get recent logs
    logs = get_latest_logs(limit=10)
    
    return render_template('options.html', 
                           symbol=symbol,
                           price=price,
                           signals=signals,
                           logs=logs)

@app.route('/api/options-chain')
def options_chain_api():
    """API endpoint for options chain data"""
    from options_analyzer import get_options_chain
    
    symbol = request.args.get('symbol', 'SPY')
    expiration = request.args.get('expiration')
    
    options_data = get_options_chain(symbol, expiration)
    return jsonify(options_data)

@app.route('/api/options/<symbol>')
def options_symbol_api(symbol):
    """API endpoint for options data with enhanced metrics
    
    This endpoint provides options data for a specific symbol with:
    - Volume/OI analysis to detect unusual activity
    - OG Strategy pattern matching markers
    - Enhanced price and Greek data
    - Support for filtering by expiration, strike range, etc.
    """
    # Get request parameters for filtering
    expiration_date = request.args.get('expiration', None)
    min_strike = request.args.get('min_strike')
    max_strike = request.args.get('max_strike')
    option_type = request.args.get('type', 'all')  # 'call', 'put', or 'all'
    
    try:
        # Convert min/max strike to float if provided
        min_strike_val = float(min_strike) if min_strike else None
        max_strike_val = float(max_strike) if max_strike else None
        
        # Get options chain data with current price included
        from options_analyzer import get_options_chain
        chain_data = get_options_chain(symbol, expiration_date)
        
        # Extract current price from the returned data
        current_price = chain_data.get('price')
        
        # Get calls and puts from chain data
        calls = chain_data.get('calls', [])
        puts = chain_data.get('puts', [])
        
        # Process calls with enhanced metrics
        processed_calls = []
        for option in calls:
            # Filter by strike range if specified
            if min_strike_val and option['strike'] < min_strike_val:
                continue
            if max_strike_val and option['strike'] > max_strike_val:
                continue
            
            # Add enhanced metrics
            option['option_type'] = 'call'  # Add type field for consistent processing
            option['is_whale'] = _detect_whale_activity(option)
            option['og_match'] = _check_og_strategy_match(symbol, option, current_price)
            
            processed_calls.append(option)
        
        # Process puts with enhanced metrics
        processed_puts = []
        for option in puts:
            # Filter by strike range if specified
            if min_strike_val and option['strike'] < min_strike_val:
                continue
            if max_strike_val and option['strike'] > max_strike_val:
                continue
            
            # Add enhanced metrics
            option['option_type'] = 'put'  # Add type field for consistent processing
            option['is_whale'] = _detect_whale_activity(option)
            option['og_match'] = _check_og_strategy_match(symbol, option, current_price)
            
            processed_puts.append(option)
        
        # Apply option type filter if requested
        if option_type.lower() == 'call':
            all_options = processed_calls
            processed_puts = []
        elif option_type.lower() == 'put':
            all_options = processed_puts
            processed_calls = []
        else:
            all_options = processed_calls + processed_puts
        
        # Sort all options by strike price
        all_options.sort(key=lambda x: x['strike'])
        
        # Prepare the response
        response = {
            'symbol': symbol,
            'current_price': current_price,
            'expiration_date': chain_data.get('expiration_date'),
            'calls': processed_calls,
            'puts': processed_puts,
            'all_options': all_options
        }
        
        return jsonify(response)
        
    except Exception as e:
        error_msg = f"Error processing options data for {symbol}: {str(e)}"
        log_to_db(error_msg, level="ERROR", module="Options")
        print(error_msg)  # For console debugging
        return jsonify({"error": error_msg}), 500
        
def _detect_whale_activity(option):
    """
    Detect unusual options activity that might indicate 'whale' trades
    
    A 'whale' is detected if:
    1. Volume > Open Interest (unusual activity)
    2. Volume > 500 contracts (significant size)
    3. Volume is 300% higher than 5-day average volume (if available)
    
    Returns: Boolean indicating whale detection
    """
    # Basic check: volume > open interest indicates unusual activity
    if option['volume'] > option['open_interest'] and option['volume'] > 500:
        return True
        
    # We'll implement more sophisticated checks when we have historical data
    return False
    
def _check_og_strategy_match(symbol, option, current_price):
    """
    Check if this option aligns with OG strategy pattern
    
    Returns: Boolean indicating if this option meets OG pattern criteria
    """
    # This will be expanded with actual OG strategy logic
    # For now, implement a simple check based on proximity to current price
    
    # For calls, check if strike is 2-5% above current price
    if option['option_type'].lower() == 'call':
        target_min = current_price * 1.02
        target_max = current_price * 1.05
        return target_min <= option['strike'] <= target_max
        
    # For puts, check if strike is 2-5% below current price
    elif option['option_type'].lower() == 'put':
        target_min = current_price * 0.95
        target_max = current_price * 0.98
        return target_min <= option['strike'] <= target_max
        
    return False

@app.route('/api/analyze-strategy', methods=['POST'])
def analyze_strategy_api():
    """API endpoint for options strategy analysis"""
    from options_analyzer import analyze_options_strategy
    
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    strategy = data.get('strategy')
    symbol = data.get('symbol')
    legs = data.get('legs', [])
    
    if not strategy or not symbol:
        return jsonify({"error": "Strategy and symbol are required"}), 400
    
    analysis = analyze_options_strategy(strategy, symbol, legs)
    return jsonify(analysis)

@app.template_filter('format_timestamp')
def format_timestamp(timestamp):
    if timestamp is None:
        return ""
    return timestamp.strftime('%Y-%m-%d %H:%M:%S')

# Initialize SocketIO integration
from socketio_server import init_socketio
socketio = init_socketio(app)

# Register simple diagnostic blueprint first
try:
    from simple_routes import simple_bp
    app.register_blueprint(simple_bp, url_prefix='/diag')
    print("Simple diagnostic blueprint registered successfully")
except Exception as e:
    print(f"Error registering simple diagnostic blueprint: {str(e)}")

# Register the signal API blueprint
from signal_api_routes import signal_api
app.register_blueprint(signal_api)

# Register the auth blueprint
from auth import auth
app.register_blueprint(auth, url_prefix='/auth')

# Register social sharing blueprint
from social_routes import register_blueprints as register_social_blueprints
register_social_blueprints(app)
logger.info("Social sharing blueprints registered")

# Risk management is already registered in risk_manager.py

# Import logs service
from logs_service import log_to_db

# Strategy configuration data store
# In production, this would be stored in the database
current_strategy_config = {
    "ema_periods": [9, 21, 72],
    "volume_threshold": 1.5,
    "min_conditions_required": 3,
    "enable_obfvg": True,
    "timeframe": "1h",
    "confirmation_timeframe": "higher",
    "cooldown_period": 60,
    "enable_higher_tf_filter": True,
    "enable_auto_trailing_stop": True,
    "last_updated": datetime.now().isoformat()
}

@app.route("/strategy-config")
@login_required
def strategy_config():
    """Strategy configuration page"""
    return render_template("strategy_config.html")
    
@app.route("/strategy-builder")
@login_required
def strategy_builder():
    """Interactive strategy builder with drag-and-drop components"""
    # Get all available strategy components
    from strategy_registry import get_available_components, get_active_strategies
    
    components = get_available_components()
    strategies = get_active_strategies()
    
    # Get user profiles for loading saved templates
    from models import StrategyProfile
    profiles = StrategyProfile.query.filter_by(user_id=current_user.id).all()
    
    return render_template('strategy_builder.html', 
                          components=components,
                          strategies=strategies,
                          profiles=profiles)

@app.route("/api/config/strategy", methods=["GET"])
def get_strategy_config():
    """API endpoint to get current strategy configuration"""
    return jsonify(current_strategy_config)
    
@app.route("/api/strategies", methods=["GET"])
@login_required
def get_strategies():
    """API endpoint to get all user's strategies"""
    from models import StrategyProfile
    
    # Get user's strategies
    strategies = StrategyProfile.query.filter_by(user_id=current_user.id).all()
    
    # Convert to JSON-serializable format
    result = []
    for strategy in strategies:
        result.append({
            "id": strategy.id,
            "name": strategy.name,
            "description": strategy.description,
            "type": strategy.type,
            "active": strategy.active,
            "created_at": strategy.created_at.isoformat() if strategy.created_at else None,
            "updated_at": strategy.updated_at.isoformat() if strategy.updated_at else None
        })
    
    return jsonify(result)

@app.route("/api/strategies/<int:strategy_id>", methods=["GET"])
@login_required
def get_strategy(strategy_id):
    """API endpoint to get a specific strategy"""
    from models import StrategyProfile
    
    # Get strategy
    strategy = StrategyProfile.query.filter_by(id=strategy_id, user_id=current_user.id).first()
    
    if not strategy:
        return jsonify({"error": "Strategy not found"}), 404
    
    # Convert to JSON-serializable format
    result = {
        "id": strategy.id,
        "name": strategy.name,
        "description": strategy.description,
        "type": strategy.type,
        "timeframe": strategy.timeframe,
        "active": strategy.active,
        "components": strategy.components,
        "connections": strategy.connections,
        "created_at": strategy.created_at.isoformat() if strategy.created_at else None,
        "updated_at": strategy.updated_at.isoformat() if strategy.updated_at else None
    }
    
    return jsonify(result)

@app.route("/api/strategies", methods=["POST"])
@login_required
def create_strategy():
    """API endpoint to create a new strategy"""
    from models import StrategyProfile
    
    data = request.json
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    # Validate required fields
    required_fields = ["name", "type"]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400
    
    # Create new strategy
    strategy = StrategyProfile(
        name=data["name"],
        description=data.get("description", ""),
        type=data["type"],
        timeframe=data.get("timeframe", "1d"),
        components=data.get("components", []),
        connections=data.get("connections", []),
        active=data.get("active", False),
        user_id=current_user.id
    )
    
    # Save to database
    db.session.add(strategy)
    db.session.commit()
    
    # Log action
    log_to_db(f"Strategy '{strategy.name}' created", level="INFO", module="Strategy")
    
    return jsonify({
        "success": True,
        "message": "Strategy created successfully",
        "strategy_id": strategy.id
    })

@app.route("/api/strategies/<int:strategy_id>", methods=["PUT"])
@login_required
def update_strategy(strategy_id):
    """API endpoint to update a strategy"""
    from models import StrategyProfile
    
    data = request.json
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    # Get strategy
    strategy = StrategyProfile.query.filter_by(id=strategy_id, user_id=current_user.id).first()
    
    if not strategy:
        return jsonify({"error": "Strategy not found"}), 404
    
    # Update fields
    if "name" in data:
        strategy.name = data["name"]
    if "description" in data:
        strategy.description = data["description"]
    if "type" in data:
        strategy.type = data["type"]
    if "timeframe" in data:
        strategy.timeframe = data["timeframe"]
    if "components" in data:
        strategy.components = data["components"]
    if "connections" in data:
        strategy.connections = data["connections"]
    if "active" in data:
        strategy.active = data["active"]
    
    # Update timestamp
    strategy.updated_at = datetime.now()
    
    # Save to database
    db.session.commit()
    
    # Log action
    log_to_db(f"Strategy '{strategy.name}' updated", level="INFO", module="Strategy")
    
    return jsonify({
        "success": True,
        "message": "Strategy updated successfully"
    })

@app.route("/api/strategies/<int:strategy_id>", methods=["DELETE"])
@login_required
def delete_strategy(strategy_id):
    """API endpoint to delete a strategy"""
    from models import StrategyProfile
    
    # Get strategy
    strategy = StrategyProfile.query.filter_by(id=strategy_id, user_id=current_user.id).first()
    
    if not strategy:
        return jsonify({"error": "Strategy not found"}), 404
    
    # Store name for logging
    name = strategy.name
    
    # Delete from database
    db.session.delete(strategy)
    db.session.commit()
    
    # Log action
    log_to_db(f"Strategy '{name}' deleted", level="INFO", module="Strategy")
    
    return jsonify({
        "success": True,
        "message": "Strategy deleted successfully"
    })

@app.route("/api/strategies/<int:strategy_id>/activate", methods=["POST"])
@login_required
def activate_strategy(strategy_id):
    """API endpoint to activate a strategy"""
    from strategy_registry import get_strategy_registry
    
    registry = get_strategy_registry()
    result = registry.activate_strategy(strategy_id)
    
    if result:
        log_to_db(f"Strategy {strategy_id} activated", level="INFO", module="Strategy")
        return jsonify({
            "success": True,
            "message": "Strategy activated successfully"
        })
    else:
        return jsonify({
            "success": False,
            "error": "Failed to activate strategy"
        }), 500

@app.route("/api/strategies/<int:strategy_id>/deactivate", methods=["POST"])
@login_required
def deactivate_strategy(strategy_id):
    """API endpoint to deactivate a strategy"""
    from strategy_registry import get_strategy_registry
    
    registry = get_strategy_registry()
    result = registry.deactivate_strategy(strategy_id)
    
    if result:
        log_to_db(f"Strategy {strategy_id} deactivated", level="INFO", module="Strategy")
        return jsonify({
            "success": True,
            "message": "Strategy deactivated successfully"
        })
    else:
        return jsonify({
            "success": False,
            "error": "Failed to deactivate strategy"
        }), 500

@app.route("/api/strategy-components", methods=["GET"])
@login_required
def get_strategy_components():
    """API endpoint to get all available strategy components"""
    from strategy_registry import get_available_components
    
    components = get_available_components()
    return jsonify(components)

@app.route("/api/config/strategy", methods=["POST"])
def save_strategy_config():
    """API endpoint to save strategy configuration"""
    global current_strategy_config
    data = request.json
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    # Validate required fields
    required_fields = ["ema_periods", "volume_threshold", "min_conditions_required"]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400
    
    # Update configuration
    current_strategy_config = data
    
    # In a real application, save to database here
    # For example:
    # for key, value in data.items():
    #     update_setting(key, value)
    
    log_to_db(f"Strategy configuration updated", level="INFO", module="Config")
    
    return jsonify({"message": "Configuration saved successfully!"}), 200

@app.route("/trade-log")
@login_required
def trade_log():
    """Trade log and performance analytics page"""
    return render_template("trade_log.html")


@app.route('/outcome-analysis')
@login_required
def outcome_analysis():
    """Trade outcome analysis page"""
    try:
        from trade_outcome_analyzer import analyze_trade_patterns, generate_trade_insights, get_next_best_decision, label_all_open_trades
        
        # Get current user ID
        user_id = current_user.id if current_user.is_authenticated else None
        
        # Label open trades first
        labeling_results = label_all_open_trades()
        
        # Get analysis data
        analysis = analyze_trade_patterns(user_id, days=30)
        
        # Get insights
        insights = generate_trade_insights(user_id)
        
        # Get next best decision
        next_decision = get_next_best_decision(user_id)
        
        # Get recent trades with outcomes
        recent_trades = Trade.query.filter(
            Trade.exit_date.isnot(None)
        ).order_by(Trade.exit_date.desc()).limit(50).all()
        
        return render_template(
            'trade_outcome_dashboard.html',
            analysis=analysis,
            insights=insights,
            next_decision=next_decision,
            recent_trades=recent_trades,
            labels_added=labeling_results.get('labels_added', 0)
        )
    except Exception as e:
        flash(f"Error loading trade outcome dashboard: {str(e)}", "danger")
        log_to_db(f"Error in outcome_analysis: {str(e)}", "ERROR", "TradeOutcomeAnalyzer")
        return render_template('error.html', error=str(e))

@app.route("/daily-analytics")
@login_required
def daily_analytics():
    """Daily analytics dashboard with performance metrics"""
    # Get today's date and start of month date for default timeframe
    today = datetime.now().date()
    start_of_month = today.replace(day=1)
    
    # Parse date range from query parameters if provided
    start_date_str = request.args.get('start_date', start_of_month.strftime('%Y-%m-%d'))
    end_date_str = request.args.get('end_date', today.strftime('%Y-%m-%d'))
    
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        # Default to month-to-date range if invalid dates provided
        start_date = start_of_month
        end_date = today
    
    # Get trades and signals in the selected date range
    trades = Trade.query.filter(
        Trade.timestamp >= datetime.combine(start_date, datetime.min.time()),
        Trade.timestamp <= datetime.combine(end_date, datetime.max.time())
    ).order_by(Trade.timestamp.asc()).all()
    
    signals = Signal.query.filter(
        Signal.timestamp >= datetime.combine(start_date, datetime.min.time()),
        Signal.timestamp <= datetime.combine(end_date, datetime.max.time())
    ).order_by(Signal.timestamp.asc()).all()
    
    # Calculate daily trade statistics
    daily_stats = {}
    for trade in trades:
        trade_date = trade.timestamp.date().strftime('%Y-%m-%d')
        
        if trade_date not in daily_stats:
            daily_stats[trade_date] = {
                'count': 0,
                'buys': 0,
                'sells': 0,
                'symbols': set()
            }
        
        daily_stats[trade_date]['count'] += 1
        
        if trade.direction.upper() in ['BUY', 'LONG']:
            daily_stats[trade_date]['buys'] += 1
        elif trade.direction.upper() in ['SELL', 'SHORT']:
            daily_stats[trade_date]['sells'] += 1
            
        daily_stats[trade_date]['symbols'].add(trade.symbol)
    
    # Convert daily stats to a format suitable for charts
    dates = []
    trade_counts = []
    buys = []
    sells = []
    
    # Ensure we have data for every day in the range, even days with no trades
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        dates.append(date_str)
        
        if date_str in daily_stats:
            trade_counts.append(daily_stats[date_str]['count'])
            buys.append(daily_stats[date_str]['buys'])
            sells.append(daily_stats[date_str]['sells'])
        else:
            trade_counts.append(0)
            buys.append(0)
            sells.append(0)
            
        current_date += timedelta(days=1)
    
    # Calculate overall statistics
    total_signals = len(signals)
    total_trades = len(trades)
    total_symbols = len(set(trade.symbol for trade in trades))
    execution_rate = (total_trades / total_signals) * 100 if total_signals > 0 else 0
    
    buy_trades = sum(1 for trade in trades if trade.direction.upper() in ['BUY', 'LONG'])
    sell_trades = sum(1 for trade in trades if trade.direction.upper() in ['SELL', 'SHORT'])
    
    # Calculate signals by direction
    bullish_signals = sum(1 for signal in signals if signal.direction.upper() in ['UP', 'BULLISH'])
    bearish_signals = sum(1 for signal in signals if signal.direction.upper() in ['DOWN', 'BEARISH'])
    
    # Get top symbols by trade count
    symbol_counts = {}
    for trade in trades:
        if trade.symbol not in symbol_counts:
            symbol_counts[trade.symbol] = 0
        symbol_counts[trade.symbol] += 1
    
    top_symbols = sorted(symbol_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    
    return render_template(
        "daily_analytics.html",
        start_date=start_date,
        end_date=end_date,
        total_signals=total_signals,
        total_trades=total_trades,
        total_symbols=total_symbols,
        execution_rate=execution_rate,
        buy_trades=buy_trades,
        sell_trades=sell_trades,
        bullish_signals=bullish_signals,
        bearish_signals=bearish_signals,
        top_symbols=top_symbols,
        dates=dates,
        buys=buys,
        sells=sells
    )

# OG Strategy Scanner routes
@app.route('/scanner')
@login_required
def og_scanner():
    """OG Strategy Scanner page"""
    # Get market data service to check if it's available
    try:
        from market_data_service import get_market_data_service
        market_data = get_market_data_service()
        market_status = market_data.is_market_open()
    except Exception as e:
        market_data = None
        market_status = False
        logger.error(f"Error initializing market data service: {str(e)}")
    
    # Get watchlist scanner to check if it's running
    try:
        from watchlist_scanner import get_watchlist_scanner, is_scanner_running
        scanner = get_watchlist_scanner()
        scanner_status = is_scanner_running()
        watchlist = scanner.get_watchlist()
    except Exception as e:
        scanner_status = False
        watchlist = ['SPY', 'QQQ', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'AMD', 'NVDA']
        logger.error(f"Error checking scanner status: {str(e)}")
    
    # Get recent logs
    logs = get_latest_logs(limit=10)
    
    return render_template('scanner.html',
                          market_status=market_status,
                          scanner_status=scanner_status,
                          watchlist=watchlist,
                          logs=logs)


@app.route('/api/scanner/status')
def scanner_status_api():
    """API endpoint to get the current scanner status"""
    try:
        from watchlist_scanner import get_watchlist_scanner, is_scanner_running
        scanner = get_watchlist_scanner()
        
        status = {
            'running': is_scanner_running(),
            'watchlist': scanner.get_watchlist(),
            'last_scan': scanner.last_scan.isoformat() if scanner.last_scan > datetime.min else None,
            'multi_tf_mode': scanner.multi_tf_mode,
            'preferred_timeframe': scanner.preferred_timeframe,
            'swing_trade_only': scanner.swing_trade_only
        }
        
        # Add available timeframe sets
        status['timeframe_sets'] = scanner.multi_tf_sets
        
        # Get active timeframe set index if in multi-timeframe mode
        if hasattr(scanner, 'active_tf_set_index'):
            status['active_tf_set_index'] = scanner.active_tf_set_index
        
        # Get market status
        try:
            from market_data_service import get_market_data_service
            market_data = get_market_data_service()
            status['market_open'] = market_data.is_market_open()
        except Exception as e:
            status['market_open'] = False
            status['market_error'] = str(e)
        
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/scanner/toggle', methods=['POST'])
@login_required
def toggle_scanner_api():
    """API endpoint to start or stop the scanner"""
    try:
        from watchlist_scanner import get_watchlist_scanner, start_scanner, stop_scanner, is_scanner_running
        
        # Check current status
        current_status = is_scanner_running()
        
        if current_status:
            # Stop the scanner
            success = stop_scanner()
            new_status = False
            action = 'stopped'
        else:
            # Start the scanner
            success = start_scanner()
            new_status = True
            action = 'started'
        
        if success:
            log_to_db(f"Scanner {action} by user", level="INFO", module="Scanner")
            return jsonify({'success': True, 'running': new_status, 'action': action})
        else:
            return jsonify({'success': False, 'error': f"Failed to {action} scanner"}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/scanner/watchlist', methods=['GET', 'POST'])
@login_required
def scanner_watchlist_api():
    """API endpoint to get or update the scanner watchlist"""
    from watchlist_scanner import get_watchlist_scanner
    scanner = get_watchlist_scanner()
    
    if request.method == 'GET':
        # Return current watchlist
        return jsonify({'watchlist': scanner.get_watchlist()})
    else:
        # Update watchlist
        data = request.json
        if not data or 'watchlist' not in data:
            return jsonify({'error': 'No watchlist provided'}), 400
        
        # Validate symbols
        symbols = data['watchlist']
        if not isinstance(symbols, list):
            return jsonify({'error': 'Watchlist must be a list of symbols'}), 400
        
        # Update watchlist
        success = scanner.set_watchlist(symbols)
        
        if success:
            log_to_db(f"Scanner watchlist updated with {len(symbols)} symbols", level="INFO", module="Scanner")
            return jsonify({'success': True, 'watchlist': scanner.get_watchlist()})
        else:
            return jsonify({'success': False, 'error': 'Failed to update watchlist'}), 500


@app.route('/api/scanner/multi-timeframe', methods=['POST'])
@login_required
def set_scanner_multi_timeframe():
    """API endpoint to toggle multi-timeframe mode and configure settings"""
    try:
        from watchlist_scanner import get_watchlist_scanner
        scanner = get_watchlist_scanner()
        
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        # Check if we're enabling or disabling multi-timeframe mode
        enabled = data.get('enabled', False)
        
        # Get timeframe set index if provided
        tf_set_index = data.get('timeframe_set_index', 0)
        
        # Apply the setting
        success = scanner.set_multi_timeframe_mode(enabled, tf_set_index)
        
        if success:
            mode_str = "enabled" if enabled else "disabled"
            log_to_db(f"Multi-timeframe mode {mode_str} by user", level="INFO", module="Scanner")
            
            # Return updated scanner status
            return jsonify({
                'success': True, 
                'multi_tf_mode': scanner.multi_tf_mode,
                'active_tf_set_index': getattr(scanner, 'active_tf_set_index', 0) if enabled else None,
                'timeframe_sets': scanner.multi_tf_sets
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to update multi-timeframe mode'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/og-strategy/match', methods=['POST'])
def check_og_match_api():
    """API endpoint to check if an option matches the OG strategy criteria"""
    try:
        from og_strategy_matcher import check_option_og_match
        
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Get required parameters
        symbol = data.get('symbol')
        option_type = data.get('option_type')
        strike = data.get('strike')
        current_price = data.get('current_price')
        
        if not symbol or not option_type or not strike or not current_price:
            return jsonify({'error': 'Missing required parameters'}), 400
        
        # Convert strike and price to float if needed
        if isinstance(strike, str):
            strike = float(strike)
        if isinstance(current_price, str):
            current_price = float(current_price)
        
        # Check for OG strategy match
        is_match, match_details = check_option_og_match(symbol, option_type, strike, current_price)
        
        # Return result
        return jsonify({
            'symbol': symbol,
            'option_type': option_type,
            'strike': strike,
            'current_price': current_price,
            'is_match': is_match,
            'match_details': match_details
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Paper trading routes
@app.route('/paper-trading')
@login_required
def paper_trading():
    """Paper trading dashboard"""
    from paper_trader import get_portfolio_status
    portfolio = get_portfolio_status()
    return render_template('paper_trading.html', portfolio=portfolio)


@app.route('/api/paper-trading/status')
@login_required
def paper_trading_status():
    """API endpoint to get paper trading status"""
    from paper_trader import get_portfolio_status
    return jsonify(get_portfolio_status())


@app.route('/api/paper-trading/trade', methods=['POST'])
@login_required
def execute_paper_trade():
    """API endpoint to execute a paper trade based on a strategy match"""
    try:
        from paper_trader import execute_paper_trade as paper_execute_trade
        
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Execute the paper trade with the provided data
        result = paper_execute_trade(data)
        if result and result.get('success'):
            return jsonify(result)
        else:
            error_msg = result.get('error', 'Failed to execute paper trade')
            return jsonify({'error': error_msg}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/paper-trading/close', methods=['POST'])
@login_required
def close_paper_position():
    """API endpoint to close a paper trading position"""
    try:
        from paper_trader import close_position
        
        data = request.json
        if not data or 'position_key' not in data:
            return jsonify({'error': 'No position key provided'}), 400
        
        # Optional exit price
        exit_price = data.get('exit_price')
        if exit_price and isinstance(exit_price, str):
            exit_price = float(exit_price)
        
        result = close_position(data['position_key'], exit_price)
        if result and result.get('success'):
            return jsonify(result)
        else:
            return jsonify({'error': result.get('error', 'Failed to close position')}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/paper-trading/update', methods=['POST'])
@login_required
def update_paper_positions():
    """API endpoint to update all paper trading positions"""
    try:
        from paper_trader import update_positions, save_account_state
        
        result = update_positions()
        save_account_state()  # Save after updating
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Initialize the OG Strategy Scanner at startup - with proper app context handling
og_strategy_scanner = None  # Global instance
def init_og_strategy_scanner():
    """Initialize the OG Strategy Scanner with proper app context"""
    global og_strategy_scanner
    try:
        with app.app_context():
            from watchlist_scanner import get_watchlist_scanner, start_scanner
            
            # Don't start immediately for now - let user control via UI
            og_strategy_scanner = get_watchlist_scanner()
            logger.info("OG Strategy Scanner initialized with application context")
            return og_strategy_scanner
    except Exception as e:
        logger.error(f"Error initializing OG Strategy Scanner: {str(e)}")
        return None

# Defer initialization to a later point when app context is fully available

# Additional Paper Trading API routes
@app.route('/api/paper-trading/reset', methods=['POST'])
@login_required
def reset_paper_portfolio():
    """API endpoint to reset the paper trading portfolio"""
    try:
        from paper_trader import reset_portfolio, save_account_state
        
        result = reset_portfolio()
        save_account_state()
        
        if result:
            log_to_db("Paper trading portfolio reset to initial state", level="INFO", module="PaperTrader")
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to reset portfolio'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/paper-trading/logs', methods=['GET'])
@login_required
def get_paper_trading_logs():
    """API endpoint to get paper trading logs"""
    try:
        limit = request.args.get('limit', 20, type=int)
        logs = get_logs_by_level(module="PaperTrader", limit=limit)
        return jsonify({'logs': logs})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/paper-trading/auto-close-settings', methods=['POST'])
@login_required
def update_auto_close_settings():
    """API endpoint to update auto-close settings for paper trading"""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Update settings in the database
        minutes = data.get('minutes', 0)
        update_setting('paper_auto_close_minutes', str(minutes))
        
        # Enable/disable auto-close
        enable = minutes > 0
        update_setting('paper_auto_close_enabled', 'true' if enable else 'false')
        
        log_to_db(f"Auto-close settings updated: {minutes} minutes", level="INFO", module="PaperTrader")
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/paper-trading/export', methods=['GET'])
@login_required
def export_paper_trading():
    """API endpoint to export paper trading history to CSV"""
    try:
        from paper_trader import export_to_csv
        
        # Generate the CSV data
        csv_data = export_to_csv()
        
        # Create a response with the CSV data
        response = make_response(csv_data)
        response.headers["Content-Disposition"] = "attachment; filename=paper_trade_history.csv"
        response.headers["Content-Type"] = "text/csv"
        
        return response
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Added routes for getting logs by module
@app.route('/api/logs')
@login_required
def get_logs_api():
    """API endpoint to get logs with optional filtering"""
    module = request.args.get('module', None)
    level = request.args.get('level', None)
    limit = request.args.get('limit', 50, type=int)
    
    if module:
        logs = get_logs_by_level(module=module, limit=limit)
    elif level:
        logs = get_logs_by_level(level=level, limit=limit)
    else:
        logs = get_latest_logs(limit=limit)
    
    # Convert datetime objects to ISO format strings
    for log in logs:
        log['timestamp'] = log['timestamp'].isoformat()
    
    return jsonify({'logs': logs})

# SocketIO event handlers for real-time updates
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info(f"Client connected: {request.sid}")
    
    # Send trade alerts to the client - simplified for now
    try:
        # Get recent signals from the database directly
        recent_signals = Signal.query.order_by(Signal.timestamp.desc()).limit(10).all()
        
        # Convert to list of dictionaries for JSON serialization
        signals_list = []
        for signal in recent_signals:
            signals_list.append({
                'id': signal.id,
                'symbol': signal.symbol,
                'direction': signal.direction,
                'confidence': signal.confidence,
                'price_at_signal': signal.price_at_signal,
                'timestamp': signal.timestamp.isoformat(),
                'indicators': signal.indicators
            })
            
        socketio.emit('signals', {'signals': signals_list}, to=request.sid)
    except Exception as e:
        logger.error(f"Error sending signals to client: {str(e)}")


@socketio.on('disconnect')
def handle_disconnect(sid=None):
    """Handle client disconnection"""
    disconnect_id = sid if sid else request.sid
    logger.info(f"Client disconnected: {disconnect_id}")


@socketio.on('request_og_matches')
def handle_og_matches_request(data):
    """Handle request for OG strategy matches"""
    try:
        # Get recent signals from the database
        recent_signals = Signal.query.order_by(Signal.timestamp.desc()).limit(10).all()
        
        # Convert to list of dictionaries for JSON serialization
        matches_list = []
        for signal in recent_signals:
            # Extract OG-related information
            matches_list.append({
                'id': signal.id,
                'ticker': signal.symbol,
                'option_type': signal.indicators.get('option_type', 'call') if signal.indicators else 'call',
                'strike': signal.indicators.get('strike', 0) if signal.indicators else 0,
                'current_price': signal.price_at_signal,
                'confidence': signal.confidence,
                'timestamp': signal.timestamp.isoformat(),
                'setup': signal.indicators.get('setup', 'OG Strategy') if signal.indicators else 'OG Strategy'
            })
            
        socketio.emit('og_matches', {'matches': matches_list}, to=request.sid)
    except Exception as e:
        logger.error(f"Error handling OG matches request: {str(e)}")


# Function to broadcast new OG strategy matches to connected clients
def broadcast_og_match(match_data):
    """Broadcast an OG strategy match to all connected clients"""
    socketio.emit('trade_alert', match_data)
    logger.debug(f"Broadcast OG match: {match_data['ticker']} {match_data['strike']} {match_data['option_type']}")
    
    # Check if auto-trading is enabled and handle paper trading
    process_paper_trade(match_data)


# Function to process a paper trade for an OG strategy match
def process_paper_trade(match_data):
    """Process a paper trade for an OG strategy match"""
    # Check if auto-trading is enabled in settings
    auto_trading_enabled = get_setting('paper_auto_trading', 'false') == 'true'
    
    if auto_trading_enabled:
        try:
            from paper_trader import simulate_og_trade, save_account_state
            
            # Get minimum confidence setting
            min_confidence = int(get_setting('paper_min_confidence', '3'))
            
            # Check if match meets minimum confidence
            if match_data.get('confidence', 0) >= min_confidence:
                # Execute the paper trade
                result = simulate_og_trade(match_data)
                
                # Save the account state
                save_account_state()
                
                # Log the result
                if result and result.get('success'):
                    log_to_db(f"Auto paper trade executed for {match_data['ticker']} {match_data['strike']} {match_data['option_type']}", 
                            level="INFO", module="PaperTrader")
                    
                    # Check if auto-close is enabled
                    auto_close_enabled = get_setting('paper_auto_close_enabled', 'false') == 'true'
                    if auto_close_enabled:
                        auto_close_minutes = int(get_setting('paper_auto_close_minutes', '20'))
                        
                        # Schedule auto-close using a background task
                        socketio.start_background_task(
                            schedule_auto_close,
                            position_key=result['position'],
                            minutes=auto_close_minutes
                        )
                else:
                    log_to_db(f"Auto paper trade failed for {match_data['ticker']}", 
                            level="WARNING", module="PaperTrader")
            else:
                log_to_db(f"Skipped paper trade for {match_data['ticker']} - confidence {match_data.get('confidence', 0)} below minimum {min_confidence}", 
                        level="INFO", module="PaperTrader")
                
        except Exception as e:
            log_to_db(f"Error in auto paper trading: {str(e)}", 
                    level="ERROR", module="PaperTrader")


# Function to schedule auto-close of a paper trade position
def schedule_auto_close(position_key, minutes):
    """Schedule auto-close of a paper trade position after specified minutes"""
    try:
        # Sleep for the specified minutes
        socketio.sleep(minutes * 60)
        
        # Import functions here to avoid circular imports
        from paper_trader import close_position, save_account_state
        
        # Close the position
        result = close_position(position_key)
        
        # Save the account state
        save_account_state()
        
        # Log the result
        if result and result.get('success'):
            log_to_db(f"Auto-closed paper trade position {position_key} after {minutes} minutes. PnL: ${result.get('pnl', 0)}", 
                    level="INFO", module="PaperTrader")
            
            # Broadcast portfolio update
            socketio.emit('portfolio_update')
        else:
            log_to_db(f"Failed to auto-close paper trade position {position_key}",
                    level="WARNING", module="PaperTrader")
    except Exception as e:
        log_to_db(f"Error auto-closing paper trade position: {str(e)}",
                level="ERROR", module="PaperTrader")

# Note: The risk_manager blueprint is registered in risk_manager.py to avoid circular imports

# Register the risk ML routes
try:
    from risk_ml_routes import register_risk_ml_blueprint
    register_risk_ml_blueprint(app)
    print("Risk ML forecasting blueprint registered successfully")
except Exception as e:
    print(f"Risk ML forecasting blueprint registration error: {str(e)}")

# Register the strategy tuning blueprint
from strategy_autotuner import autotuner_bp, register_autotuner_blueprint
register_autotuner_blueprint(app)

# Register the strategy analytics blueprint
try:
    from strategy_analytics import strategy_analytics_bp
    if not any(bp.name == 'strategy_analytics' for bp in app.blueprints.values()):
        app.register_blueprint(strategy_analytics_bp)
except ImportError:
    print("Strategy analytics blueprint not available")

# Register the safety net blueprint
try:
    from safety_net import safety_net_bp, register_safety_net_blueprint
    register_safety_net_blueprint(app)
except ImportError:
    print("Safety net blueprint not available")
    
# Register the trade outcome analyzer blueprint
try:
    from trade_outcome_analyzer import trade_outcome_bp, register_trade_outcome_blueprint
    register_trade_outcome_blueprint(app)
    print("Trade outcome analyzer blueprint registered successfully")
except Exception as e:
    print(f"Trade outcome analyzer blueprint not available: {str(e)}")

# Register the QuotestreamPY integration blueprint
try:
    from quotestream_routes import register_quotestream_blueprint
    register_quotestream_blueprint(app)
    print("QuotestreamPY integration blueprint registered successfully")
except Exception as e:
    print(f"QuotestreamPY integration blueprint not available: {str(e)}")

# Register the demo blueprint for SNAP example
try:
    from app_demo_routes import register_demo_blueprint
    register_demo_blueprint(app)
    print("Demo routes for OG signals blueprint registered successfully")
    
    # Register Strategy Coach routes
    from strategy_coach_routes import register_strategy_coach_blueprint
    register_strategy_coach_blueprint(app)
    print("Strategy coach blueprint registered successfully")
    
    # Register Market API routes
    from market_api_routes import register_market_api_blueprint
    register_market_api_blueprint(app)
    print("Market API blueprint registered successfully")
    
    # Register AI Services and Analysis routes
    try:
        with app.app_context():
            from ai_routes import register_ai_blueprint
            register_ai_blueprint(app)
            print("AI Services blueprint registered successfully")
    except Exception as e:
        print(f"AI Services blueprint registration error: {str(e)}")
        
    # Register Strategy Explanation and AI Assistant routes
    try:
        with app.app_context():
            from explanation_routes import register_explanation_blueprints
            register_explanation_blueprints(app)
            print("Strategy Explanation blueprints registered successfully")
    except Exception as e:
        print(f"Strategy Explanation blueprint registration error: {str(e)}")
except Exception as e:
    print(f"Blueprint registration error: {str(e)}")
    
# Note: OG Strategy Matcher will be initialized lazily when accessed
# to prevent application context errors

# Initialize components that need application context
with app.app_context():
    try:
        # Initialize OG Strategy Scanner
        og_strategy_scanner = init_og_strategy_scanner()
        if og_strategy_scanner:
            logger.info("OG Strategy Scanner successfully initialized within app context")
        else:
            logger.warning("OG Strategy Scanner initialization returned None")
    except Exception as e:
        logger.error(f"Error initializing OG Strategy Scanner: {str(e)}")

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=True, log_output=True)

