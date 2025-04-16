"""
Ultra-Simplified Backtesting Routes for OG Signal Bot

This is a minimal version with no dependencies on models or other complex parts 
of the system to ensure we can get something working in the Replit environment.
"""

from flask import Blueprint, render_template, jsonify
from datetime import datetime

# Create blueprint with simpler prefix to reduce routing complexity
backtest_bp = Blueprint('backtest', __name__, url_prefix='/bt')

@backtest_bp.route('/')
def index():
    """Render backtesting dashboard"""
    try:
        # Use the standalone template without any dependencies
        return render_template('backtest/standalone.html')
    except Exception as e:
        return f"Error loading backtest dashboard: {str(e)}", 500
        
@backtest_bp.route('/simple')
def simple_index():
    """Render simple backtesting dashboard"""
    try:
        # For our simplified backtest UI with base.html dependency
        return render_template(
            'backtest/simple_index.html',
            timeframes=['5m', '15m', '1h', '4h', '1D'],
            default_symbols="AAPL,MSFT,AMZN,NVDA,QQQ"
        )
    except Exception as e:
        return f"Error loading simple backtest dashboard: {str(e)}", 500
        
@backtest_bp.route('/health')
def health():
    """Health check endpoint for backtest routes"""
    return jsonify({
        "status": "healthy", 
        "module": "backtest_routes", 
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "available_endpoints": ["/", "/health", "/api/test"]
    })

@backtest_bp.route('/api/test')
def api_test():
    """Simple test endpoint for backtest API"""
    return jsonify({
        "success": True,
        "message": "Backtest API is working", 
        "test_data": {
            "symbols": ["AAPL", "MSFT", "AMZN", "NVDA", "QQQ"],
            "timeframes": ["5m", "15m", "1h", "4h", "1D"]
        }
    })