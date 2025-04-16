"""
QuotestreamPY Service - Standalone market data service
Provides real-time and historical market data via a REST API and WebSocket
"""
import os
import json
import logging
import time
import random
import threading
import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO
import numpy as np
from typing import Dict, List, Optional, Any

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("quotestream")

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable cross-origin requests
socketio = SocketIO(app, cors_allowed_origins="*")

# Default port for the service
DEFAULT_PORT = int(os.getenv("QUOTESTREAM_PORT", 3000))

# Sample stock data
SAMPLE_STOCKS = {
    "AAPL": {"name": "Apple Inc.", "sector": "Technology"},
    "MSFT": {"name": "Microsoft Corporation", "sector": "Technology"},
    "AMZN": {"name": "Amazon.com Inc.", "sector": "Consumer Cyclical"},
    "GOOG": {"name": "Alphabet Inc.", "sector": "Communication Services"},
    "TSLA": {"name": "Tesla Inc.", "sector": "Consumer Cyclical"},
    "META": {"name": "Meta Platforms Inc.", "sector": "Communication Services"},
    "NVDA": {"name": "NVIDIA Corporation", "sector": "Technology"},
    "AMD": {"name": "Advanced Micro Devices Inc.", "sector": "Technology"},
    "INTC": {"name": "Intel Corporation", "sector": "Technology"},
    "SPY": {"name": "SPDR S&P 500 ETF Trust", "sector": "ETF"}
}

# In-memory data store
quotes = {}
depth_data = {}
trades = {}
options_data = {}
watchlist = list(SAMPLE_STOCKS.keys())[:5]  # Default watchlist with 5 stocks

# Service status
running = True
last_update = time.time()

# Generate realistic base price for each stock
base_prices = {
    "AAPL": 180.0,
    "MSFT": 330.0,
    "AMZN": 175.0,
    "GOOG": 160.0,
    "TSLA": 170.0,
    "META": 480.0,
    "NVDA": 850.0,
    "AMD": 155.0,
    "INTC": 35.0,
    "SPY": 510.0
}

# Market trend simulation
market_trend = 0.0  # -1.0 to 1.0, negative is bearish, positive is bullish
trend_change_time = time.time()

def update_market_trend():
    """Update the overall market trend periodically"""
    global market_trend, trend_change_time
    
    # Change market trend every 5-15 minutes
    now = time.time()
    if now - trend_change_time > random.randint(300, 900):
        # Gradual trend shift with some randomness
        market_trend = max(-1.0, min(1.0, market_trend + random.uniform(-0.3, 0.3)))
        trend_change_time = now
        logger.info(f"Market trend updated to {market_trend:.2f}")

def generate_quote(symbol):
    """Generate a simulated market quote for a symbol"""
    global base_prices
    
    if symbol not in base_prices:
        base_prices[symbol] = random.uniform(10, 500)
    
    base_price = base_prices[symbol]
    
    # Apply market trend influence
    trend_factor = 1.0 + (market_trend * random.uniform(0.0001, 0.001))
    
    # Apply individual stock movement
    stock_factor = 1.0 + random.uniform(-0.002, 0.002)
    
    # Calculate new price with a small random movement
    new_price = base_price * trend_factor * stock_factor
    
    # Update base price with some mean reversion
    base_prices[symbol] = base_price * 0.9995 + new_price * 0.0005
    
    # Create previous close
    prev_close = base_price * (1.0 + random.uniform(-0.02, 0.02))
    
    # Calculate change
    change = new_price - prev_close
    change_percent = (change / prev_close) * 100.0
    
    # Generate bid/ask spread
    spread = new_price * random.uniform(0.0005, 0.002)
    bid = new_price - (spread / 2)
    ask = new_price + (spread / 2)
    
    # Volume
    volume = int(random.uniform(10000, 10000000))
    
    # Time
    timestamp = datetime.datetime.now().isoformat()
    
    return {
        "symbol": symbol,
        "description": SAMPLE_STOCKS.get(symbol, {}).get("name", f"{symbol} Stock"),
        "last": round(new_price, 2),
        "bid": round(bid, 2),
        "ask": round(ask, 2),
        "bid_size": int(random.uniform(100, 2000)),
        "ask_size": int(random.uniform(100, 2000)),
        "volume": volume,
        "open": round(prev_close * (1.0 + random.uniform(-0.01, 0.01)), 2),
        "high": round(new_price * (1.0 + random.uniform(0.001, 0.02)), 2),
        "low": round(new_price * (1.0 - random.uniform(0.001, 0.02)), 2),
        "prev_close": round(prev_close, 2),
        "change": round(change, 2),
        "change_percent": round(change_percent, 2),
        "sector": SAMPLE_STOCKS.get(symbol, {}).get("sector", "Unknown"),
        "vwap": round(new_price * (1.0 + random.uniform(-0.005, 0.005)), 2),
        "timestamp": timestamp
    }

def generate_market_depth(symbol):
    """Generate simulated market depth data for a symbol"""
    if symbol not in quotes:
        quotes[symbol] = generate_quote(symbol)
    
    quote = quotes[symbol]
    last_price = quote["last"]
    
    bids = []
    asks = []
    
    # Generate bid levels
    for i in range(10):
        price_delta = (i + 1) * random.uniform(0.01, 0.05)
        price = round(last_price - price_delta, 2)
        size = int(random.uniform(100, 5000))
        bids.append({
            "price": price,
            "size": size,
            "exchange": random.choice(["NSDQ", "NYSE", "ARCA", "BATS"]),
            "timestamp": datetime.datetime.now().isoformat()
        })
    
    # Generate ask levels
    for i in range(10):
        price_delta = (i + 1) * random.uniform(0.01, 0.05)
        price = round(last_price + price_delta, 2)
        size = int(random.uniform(100, 5000))
        asks.append({
            "price": price,
            "size": size,
            "exchange": random.choice(["NSDQ", "NYSE", "ARCA", "BATS"]),
            "timestamp": datetime.datetime.now().isoformat()
        })
    
    return {
        "symbol": symbol,
        "bids": sorted(bids, key=lambda x: x["price"], reverse=True),
        "asks": sorted(asks, key=lambda x: x["price"]),
        "timestamp": datetime.datetime.now().isoformat()
    }

def generate_trade(symbol):
    """Generate a simulated trade for a symbol"""
    if symbol not in quotes:
        quotes[symbol] = generate_quote(symbol)
    
    quote = quotes[symbol]
    last_price = quote["last"]
    
    # Small variation around last price
    price = round(last_price * (1.0 + random.uniform(-0.001, 0.001)), 2)
    
    # Random size
    size = random.choice([100, 200, 300, 500, 1000, 2000])
    
    # Is this trade at bid, ask, or in between?
    if random.random() < 0.45:  # At bid
        price_change = -1
    elif random.random() < 0.9:  # At ask
        price_change = 1
    else:  # In between
        price_change = 0
    
    # Exchange
    exchange = random.choice(["NSDQ", "NYSE", "ARCA", "BATS"])
    
    # Conditions
    conditions = random.choice(["", "Regular", "Odd Lot", "Outside Regular Hours"])
    
    # Timestamp
    timestamp = datetime.datetime.now().isoformat()
    
    return {
        "symbol": symbol,
        "price": price,
        "size": size,
        "price_change": price_change,
        "exchange": exchange,
        "conditions": conditions,
        "timestamp": timestamp
    }

def generate_option_chain(symbol):
    """Generate a simulated options chain for a symbol"""
    if symbol not in quotes:
        quotes[symbol] = generate_quote(symbol)
    
    quote = quotes[symbol]
    underlying_price = quote["last"]
    
    chain = {
        "symbol": symbol,
        "underlying_price": underlying_price,
        "expirations": [],
        "strikes": [],
        "calls": [],
        "puts": []
    }
    
    # Generate expirations (weekly and monthly)
    today = datetime.date.today()
    
    # Next 4 weekly expirations (Fridays)
    for i in range(1, 5):
        days_until_friday = (4 - today.weekday()) % 7  # 4 = Friday
        friday = today + datetime.timedelta(days=days_until_friday + (i-1)*7)
        chain["expirations"].append(friday.strftime("%Y-%m-%d"))
    
    # Next 3 monthly expirations (3rd Friday of each month)
    for i in range(1, 4):
        # Find the first day of next month
        if today.month + i > 12:
            year = today.year + (today.month + i - 1) // 12
            month = (today.month + i - 1) % 12 + 1
        else:
            year = today.year
            month = today.month + i
        
        first_day = datetime.date(year, month, 1)
        
        # Find the third Friday
        days_until_friday = (4 - first_day.weekday()) % 7  # 4 = Friday
        third_friday = first_day + datetime.timedelta(days=days_until_friday + 14)  # +14 for third friday
        
        chain["expirations"].append(third_friday.strftime("%Y-%m-%d"))
    
    # Generate strikes (around current price)
    min_strike = underlying_price * 0.7
    max_strike = underlying_price * 1.3
    step = underlying_price * 0.025  # 2.5% increments
    
    strikes = []
    current_strike = min_strike
    while current_strike <= max_strike:
        strikes.append(round(current_strike, 2))
        current_strike += step
    
    chain["strikes"] = strikes
    
    # Generate option contracts
    for expiration in chain["expirations"]:
        for strike in chain["strikes"]:
            # Calculate days to expiration
            exp_date = datetime.datetime.strptime(expiration, "%Y-%m-%d").date()
            days_to_exp = (exp_date - today).days
            
            # Call option
            call_price = _calculate_option_price(underlying_price, strike, days_to_exp/365.0, 0.3, 0.02, "call")
            call_volume = int(random.uniform(10, 5000))
            call_open_interest = int(call_volume * random.uniform(1.0, 10.0))
            
            call = {
                "symbol": f"{symbol}{exp_date.strftime('%y%m%d')}C{int(strike*100):08d}",
                "underlying": symbol,
                "expiration": expiration,
                "strike": strike,
                "type": "call",
                "last": round(call_price, 2),
                "bid": round(call_price * 0.95, 2),
                "ask": round(call_price * 1.05, 2),
                "volume": call_volume,
                "open_interest": call_open_interest,
                "implied_volatility": round(random.uniform(0.2, 0.6), 2),
                "delta": round(random.uniform(0.1, 0.9), 2),
                "gamma": round(random.uniform(0.01, 0.2), 3),
                "theta": round(random.uniform(-0.1, -0.01), 3),
                "vega": round(random.uniform(0.01, 0.2), 3),
                "days_to_expiration": days_to_exp
            }
            
            # Put option
            put_price = _calculate_option_price(underlying_price, strike, days_to_exp/365.0, 0.3, 0.02, "put")
            put_volume = int(random.uniform(10, 5000))
            put_open_interest = int(put_volume * random.uniform(1.0, 10.0))
            
            put = {
                "symbol": f"{symbol}{exp_date.strftime('%y%m%d')}P{int(strike*100):08d}",
                "underlying": symbol,
                "expiration": expiration,
                "strike": strike,
                "type": "put",
                "last": round(put_price, 2),
                "bid": round(put_price * 0.95, 2),
                "ask": round(put_price * 1.05, 2),
                "volume": put_volume,
                "open_interest": put_open_interest,
                "implied_volatility": round(random.uniform(0.2, 0.6), 2),
                "delta": round(random.uniform(-0.9, -0.1), 2),
                "gamma": round(random.uniform(0.01, 0.2), 3),
                "theta": round(random.uniform(-0.1, -0.01), 3),
                "vega": round(random.uniform(0.01, 0.2), 3),
                "days_to_expiration": days_to_exp
            }
            
            chain["calls"].append(call)
            chain["puts"].append(put)
    
    return chain

def _calculate_option_price(spot, strike, time_to_exp, volatility, risk_free_rate, option_type):
    """Simplified Black-Scholes option pricing"""
    # This is a very simplified version of Black-Scholes
    # In a real scenario, use a proper options pricing library
    
    if time_to_exp < 0.01:  # Avoid calculation issues for near-expiry options
        time_to_exp = 0.01
    
    # Calculate d1 and d2
    d1 = (np.log(spot/strike) + (risk_free_rate + 0.5 * volatility**2) * time_to_exp) / (volatility * np.sqrt(time_to_exp))
    d2 = d1 - volatility * np.sqrt(time_to_exp)
    
    # Normal CDF approximation
    def norm_cdf(x):
        return 0.5 * (1 + np.tanh(np.sqrt(2/np.pi) * x * (0.044715 * x * x + 1)))
    
    if option_type.lower() == "call":
        price = spot * norm_cdf(d1) - strike * np.exp(-risk_free_rate * time_to_exp) * norm_cdf(d2)
    else:  # put
        price = strike * np.exp(-risk_free_rate * time_to_exp) * norm_cdf(-d2) - spot * norm_cdf(-d1)
    
    return max(0.01, price)  # Minimum price of 0.01

def generate_volume_analysis(symbol):
    """Generate simulated volume analysis data for a symbol"""
    if symbol not in quotes:
        quotes[symbol] = generate_quote(symbol)
    
    quote = quotes[symbol]
    
    # Daily VWAP
    vwap = quote.get("vwap", quote["last"])
    
    # Price levels with volume concentration
    levels = []
    
    # Add current price area
    levels.append({
        "price": round(quote["last"], 2),
        "volume": int(quote["volume"] * random.uniform(0.1, 0.3)),
        "type": "current"
    })
    
    # Add support levels (below current price)
    for i in range(random.randint(2, 4)):
        price = round(quote["last"] * (1 - random.uniform(0.02, 0.1) * (i+1)), 2)
        volume = int(quote["volume"] * random.uniform(0.05, 0.2))
        levels.append({
            "price": price,
            "volume": volume,
            "type": "support"
        })
    
    # Add resistance levels (above current price)
    for i in range(random.randint(2, 4)):
        price = round(quote["last"] * (1 + random.uniform(0.02, 0.1) * (i+1)), 2)
        volume = int(quote["volume"] * random.uniform(0.05, 0.2))
        levels.append({
            "price": price,
            "volume": volume,
            "type": "resistance"
        })
    
    # Sort by price
    levels.sort(key=lambda x: x["price"])
    
    return {
        "symbol": symbol,
        "vwap": vwap,
        "total_volume": quote["volume"],
        "levels": levels,
        "timestamp": datetime.datetime.now().isoformat()
    }

def update_data():
    """Update market data periodically"""
    global quotes, depth_data, trades, options_data, last_update, running
    
    logger.info("Starting market data update thread")
    
    # Initial data generation for all symbols to ensure data is available immediately
    for symbol in watchlist:
        quotes[symbol] = generate_quote(symbol)
        depth_data[symbol] = generate_market_depth(symbol)
        trades[symbol] = [generate_trade(symbol) for _ in range(10)]
        options_data[symbol] = generate_option_chain(symbol)
    
    logger.info(f"Initial data generated for {len(watchlist)} symbols")
    
    # Add some additional popular symbols
    additional_symbols = ["AAPL", "MSFT", "AMZN", "GOOG", "TSLA", "META", "NVDA"]
    for symbol in additional_symbols:
        if symbol not in watchlist:
            watchlist.append(symbol)
            quotes[symbol] = generate_quote(symbol)
            depth_data[symbol] = generate_market_depth(symbol)
            trades[symbol] = [generate_trade(symbol) for _ in range(10)]
            options_data[symbol] = generate_option_chain(symbol)
    
    update_counter = 0
    error_counter = 0
    
    while running:
        try:
            update_counter += 1
            
            # Update market trend
            update_market_trend()
            
            # Update quotes for watchlist symbols
            for symbol in watchlist:
                # Always update quotes for real-time data
                quotes[symbol] = generate_quote(symbol)
                
                # Update market depth more frequently (40% of the time instead of 20%)
                if random.random() < 0.4:
                    depth_data[symbol] = generate_market_depth(symbol)
                
                # Add new trade
                if symbol not in trades:
                    trades[symbol] = []
                
                new_trade = generate_trade(symbol)
                trades[symbol].insert(0, new_trade)
                
                # Limit to 50 most recent trades
                if len(trades[symbol]) > 50:
                    trades[symbol] = trades[symbol][:50]
                
                # Update options data more frequently (10% of the time instead of 5%)
                if random.random() < 0.1:
                    options_data[symbol] = generate_option_chain(symbol)
                
                # Always emit quote updates
                socketio.emit('quote_update', {
                    'symbol': symbol,
                    'quote': quotes[symbol]
                })
                
                # Emit depth update more frequently
                if random.random() < 0.2 and symbol in depth_data:
                    socketio.emit('depth_update', {
                        'symbol': symbol,
                        'depth': depth_data[symbol]
                    })
                
                # Emit trade update more frequently
                if random.random() < 0.5 and symbol in trades and trades[symbol]:
                    socketio.emit('trade_update', {
                        'symbol': symbol,
                        'trade': trades[symbol][0]
                    })
            
            # Every 100 updates, log a status message
            if update_counter % 100 == 0:
                logger.info(f"Data update cycle {update_counter}: {len(watchlist)} symbols, {len(quotes)} quotes")
            
            last_update = time.time()
            
            # Sleep for a consistent time to avoid CPU spikes
            # We'll use a fixed interval of 200ms which is 5 updates per second - fast enough for real-time
            time.sleep(0.2)
            
            # Reset error counter when successful
            error_counter = 0
            
        except Exception as e:
            error_counter += 1
            logger.error(f"Error in update thread: {e}")
            
            # If we get 5 consecutive errors, log a critical message but keep trying
            if error_counter >= 5:
                logger.critical(f"Multiple consecutive errors in update thread: {e}")
            
            # Wait a bit longer after an error
            time.sleep(1)

# API endpoints
@app.route('/api/status')
def api_status():
    """Get the service status"""
    return jsonify({
        "status": "running",
        "uptime": time.time() - last_update,
        "watchlist_symbols": len(watchlist),
        "market_trend": market_trend
    })

@app.route('/api/quotes')
def api_quotes():
    """Get quotes for specified symbols"""
    symbols = request.args.get('symbols', '')
    if not symbols:
        return jsonify({}), 400
    
    symbol_list = [s.strip().upper() for s in symbols.split(',')]
    result = {}
    
    for symbol in symbol_list:
        if symbol not in quotes:
            quotes[symbol] = generate_quote(symbol)
        result[symbol] = quotes[symbol]
    
    return jsonify(result)

@app.route('/api/depth/<symbol>')
def api_depth(symbol):
    """Get market depth for a symbol"""
    symbol = symbol.upper()
    
    if symbol not in depth_data:
        depth_data[symbol] = generate_market_depth(symbol)
    
    return jsonify(depth_data[symbol])

@app.route('/api/trades/<symbol>')
def api_trades(symbol):
    """Get recent trades for a symbol"""
    symbol = symbol.upper()
    limit = request.args.get('limit', 20, type=int)
    
    if symbol not in trades:
        trades[symbol] = [generate_trade(symbol) for _ in range(min(10, limit))]
    
    return jsonify(trades[symbol][:limit])

@app.route('/api/options/<symbol>')
def api_options(symbol):
    """Get options chain for a symbol"""
    symbol = symbol.upper()
    
    if symbol not in options_data:
        options_data[symbol] = generate_option_chain(symbol)
    
    # Filter by expiration if requested
    expiration = request.args.get('expiration')
    if expiration:
        filtered_calls = [c for c in options_data[symbol]["calls"] if c["expiration"] == expiration]
        filtered_puts = [p for p in options_data[symbol]["puts"] if p["expiration"] == expiration]
        
        result = {
            "symbol": symbol,
            "underlying_price": options_data[symbol]["underlying_price"],
            "expirations": options_data[symbol]["expirations"],
            "strikes": options_data[symbol]["strikes"],
            "calls": filtered_calls,
            "puts": filtered_puts
        }
        return jsonify(result)
    
    return jsonify(options_data[symbol])

@app.route('/api/watchlist', methods=['GET'])
def api_get_watchlist():
    """Get the current watchlist"""
    return jsonify({"symbols": watchlist})

@app.route('/api/watchlist', methods=['POST'])
def api_update_watchlist():
    """Update the watchlist"""
    data = request.json
    global watchlist
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    if 'symbol' in data:
        # Add or remove a symbol
        symbol = data['symbol'].upper()
        action = data.get('action', 'add')
        
        if action == 'add' and symbol not in watchlist:
            watchlist.append(symbol)
        elif action == 'remove' and symbol in watchlist:
            watchlist.remove(symbol)
            
    elif 'symbols' in data:
        # Replace entire watchlist
        watchlist = [s.upper() for s in data['symbols']]
    
    return jsonify({
        "success": True,
        "symbols": watchlist
    })

@app.route('/api/search')
def api_search():
    """Search for symbols"""
    query = request.args.get('q', '').upper()
    if not query:
        return jsonify({"results": []}), 400
    
    # Filter sample stocks by query
    results = []
    for symbol, data in SAMPLE_STOCKS.items():
        if query in symbol or query in data.get("name", "").upper():
            results.append({
                "symbol": symbol,
                "description": data.get("name", ""),
                "sector": data.get("sector", "Unknown")
            })
    
    return jsonify({"results": results})

@app.route('/api/analysis/volume/<symbol>')
def api_volume_analysis(symbol):
    """Get volume analysis for a symbol"""
    symbol = symbol.upper()
    
    return jsonify(generate_volume_analysis(symbol))

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info(f"Client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info(f"Client disconnected: {request.sid}")

@socketio.on('subscribe')
def handle_subscribe(data):
    """Handle subscription to a symbol"""
    if 'symbol' in data:
        symbol = data['symbol'].upper()
        logger.info(f"Client {request.sid} subscribed to {symbol}")
        
        # Add to watchlist if not present
        if symbol not in watchlist:
            watchlist.append(symbol)
            
        # Emit current data
        if symbol in quotes:
            socketio.emit('quote_update', {
                'symbol': symbol,
                'quote': quotes[symbol]
            }, room=request.sid)

def health_check():
    """Health check endpoint for monitoring"""
    return {"status": "running" if running else "stopped", 
            "uptime": time.time() - last_update,
            "watchlist_symbols": len(watchlist),
            "market_trend": market_trend}

def main():
    """Main function to start the service"""
    global running
    
    # Add health check endpoint
    app.route('/api/health', methods=['GET'])(lambda: jsonify(health_check()))
    
    # Start update thread
    update_thread = threading.Thread(target=update_data)
    update_thread.daemon = True
    update_thread.start()
    
    max_retries = 5
    retry_count = 0
    retry_delay = 10  # seconds
    
    while retry_count < max_retries:
        try:
            # Run the app
            port = DEFAULT_PORT
            logger.info(f"Starting QuotestreamPY service on port {port} (attempt {retry_count + 1}/{max_retries})")
            socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)
            break  # If we get here cleanly, break the loop
        except Exception as e:
            retry_count += 1
            logger.error(f"Service error: {e}")
            if retry_count < max_retries:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error("Maximum retries reached. Exiting.")
                running = False
        except KeyboardInterrupt:
            logger.info("Shutting down QuotestreamPY service")
            running = False
            break
    
    logger.info("QuotestreamPY service stopped")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        # Ensure we capture any top-level exceptions
        import traceback
        logger.critical(traceback.format_exc())