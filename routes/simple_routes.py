"""
Simple diagnostic routes for the OG Signal Bot application.
These routes are designed to be lightweight and have minimal dependencies.
"""

import os
import logging
import traceback
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request, current_app

logger = logging.getLogger(__name__)

# Create blueprint
simple_bp = Blueprint('simple', __name__)

@simple_bp.route('/simple')
def simple_route():
    """Simple diagnostic route with minimal dependencies"""
    logger.info("Simple route accessed")
    return jsonify({
        "status": "success",
        "message": "Simple diagnostic route is working",
        "timestamp": datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "auth_disabled": os.getenv("DISABLE_AUTH", "false").lower() == "true"
    })

@simple_bp.route('/simple/env')
def env_info():
    """Return environment information for debugging"""
    safe_env = {
        "DISABLE_AUTH": os.getenv("DISABLE_AUTH", "not set"),
        "FLASK_ENV": os.getenv("FLASK_ENV", "not set"),
        "FLASK_DEBUG": os.getenv("FLASK_DEBUG", "not set")
    }
    
    return jsonify({
        "status": "success",
        "environment": safe_env,
        "timestamp": datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    })

@simple_bp.route('/health-check')
def health_check():
    """Basic health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
        'server_uptime': 'Active'
    })

@simple_bp.route('/backtest-debug')
def backtest_debug():
    """Debug endpoint for backtest subsystem"""
    try:
        logger.info("Backtest debug endpoint called")
        
        # List all registered routes
        routes = []
        for rule in current_app.url_map.iter_rules():
            if 'backtest' in rule.endpoint:
                routes.append({
                    'endpoint': rule.endpoint,
                    'methods': [m for m in rule.methods if m not in ['HEAD', 'OPTIONS']],
                    'path': str(rule)
                })
        
        # Check if we can import the backtest modules
        import_status = {}
        try:
            import backtest_routes
            import_status['backtest_routes'] = 'success'
        except Exception as e:
            import_status['backtest_routes'] = f'error: {str(e)}'
            
        try:
            import strategy_backtester
            import_status['strategy_backtester'] = 'success'
        except Exception as e:
            import_status['strategy_backtester'] = f'error: {str(e)}'
        
        try:
            import models_backtest
            import_status['models_backtest'] = 'success'
        except Exception as e:
            import_status['models_backtest'] = f'error: {str(e)}'
        
        return jsonify({
            'status': 'success',
            'message': 'Backtest debug information',
            'timestamp': datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
            'backtest_routes': routes,
            'import_status': import_status,
            'request_info': {
                'path': request.path,
                'method': request.method,
                'remote_addr': request.remote_addr
            }
        })
    except Exception as e:
        logger.error(f"Error in backtest debug endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'Error in backtest debug: {str(e)}',
            'traceback': traceback.format_exc(),
            'timestamp': datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        }), 500

def register_simple_blueprint(app):
    """Register the simple blueprint with the app"""
    try:
        # Register with both URL prefixes for maximum accessibility during debugging
        app.register_blueprint(simple_bp, url_prefix='/api')
        # Also register the blueprint at the root path for direct access
        app.register_blueprint(simple_bp, url_prefix='/')
        logger.info("Simple diagnostic blueprint registered successfully")
        return True
    except Exception as e:
        logger.error(f"Error registering simple diagnostic blueprint: {str(e)}")
        return False