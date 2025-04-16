"""
AI Routes for OG Signal Bot

This module provides endpoints for AI-powered strategy analysis, market data enrichment,
and pattern recognition services.

Key features:
- AI-enhanced scanner for OG strategy patterns
- Market sentiment analysis
- Multi-timeframe trade opportunity identification
- Signal validation with confidence scoring
"""

import json
import logging
from flask import Blueprint, request, jsonify, render_template, current_app, session
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import threading

# Import internal services
from perplexity_service import get_perplexity_service
from ai_strategy_analyzer import get_ai_strategy_analyzer, initialize_ai_strategy_analyzer
from models import Signal, Trade
from market_data_service import get_market_data_service
from config import get_setting, update_setting
from logs_service import log_to_db
from og_strategy_matcher import get_strategy_matcher

# Set up logger
logger = logging.getLogger(__name__)

# Create blueprint
ai_bp = Blueprint('ai', __name__, url_prefix='/ai')

# Initialize services lazily
perplexity = None
ai_analyzer = None

def get_services():
    """Get services lazily to avoid app context issues"""
    global perplexity, ai_analyzer
    
    try:
        logger.info("Attempting to get Perplexity service")
        if perplexity is None:
            perplexity = get_perplexity_service()
            logger.info(f"Perplexity service initialized. Available: {perplexity.available}")
        
        logger.info("Attempting to get AI Strategy Analyzer")
        if ai_analyzer is None:
            ai_analyzer = get_ai_strategy_analyzer()
            logger.info("AI Strategy Analyzer initialized")
            
        return perplexity, ai_analyzer
    except Exception as e:
        error_msg = f"Failed to initialize AI services: {str(e)}"
        logger.error(error_msg)
        print(error_msg)
        
        # Create fallback instances if needed
        if perplexity is None:
            try:
                logger.warning("Creating fallback Perplexity service")
                perplexity = get_perplexity_service()
            except Exception as inner_e:
                logger.error(f"Failed to create fallback Perplexity service: {str(inner_e)}")
                # Create a minimal object with available=False to prevent crashes
                from types import SimpleNamespace
                perplexity = SimpleNamespace(available=False)
                
        if ai_analyzer is None:
            try:
                logger.warning("Creating fallback AI Strategy Analyzer")
                ai_analyzer = get_ai_strategy_analyzer()
            except Exception as inner_e:
                logger.error(f"Failed to create fallback AI Strategy Analyzer: {str(inner_e)}")
                # Create a minimal object to prevent crashes
                from types import SimpleNamespace
                ai_analyzer = SimpleNamespace(ai_validation_enabled=False)
                
        return perplexity, ai_analyzer

@ai_bp.route('/dashboard')
@login_required
def ai_dashboard():
    """AI Strategy Dashboard with real-time analysis and confidence metrics"""
    return render_template('ai_dashboard.html')
    
@ai_bp.route('/simple')
def ai_simple_dashboard():
    """Simple AI status page that doesn't require full dashboard to load"""
    try:
        # Get services with error handling
        perplexity, ai_analyzer = None, None
        
        try:
            perplexity = get_perplexity_service()
            perplexity_status = "Available" if perplexity.available else "Unavailable"
        except Exception as e:
            perplexity_status = f"Error: {str(e)}"
            
        try:
            ai_analyzer = get_ai_strategy_analyzer()
            analyzer_status = "Initialized"
        except Exception as e:
            analyzer_status = f"Error: {str(e)}"
        
        html = f"""
        <html>
        <head>
            <title>AI Services Simple Status</title>
            <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
            <style>
                body {{ padding: 20px; }}
                .status-card {{ padding: 15px; margin-bottom: 15px; border-radius: 5px; }}
                .status-ok {{ background-color: rgba(25, 135, 84, 0.2); }}
                .status-error {{ background-color: rgba(220, 53, 69, 0.2); }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1 class="mb-4">AI Services Simple Status</h1>
                
                <div class="status-card {{'status-ok' if 'Error' not in perplexity_status else 'status-error'}}">
                    <h3>Perplexity API</h3>
                    <p>Status: {perplexity_status}</p>
                </div>
                
                <div class="status-card {{'status-ok' if 'Error' not in analyzer_status else 'status-error'}}">
                    <h3>AI Strategy Analyzer</h3>
                    <p>Status: {analyzer_status}</p>
                </div>
                
                <a href="/dashboard" class="btn btn-primary">Back to Dashboard</a>
            </div>
        </body>
        </html>
        """
        return html
    except Exception as main_e:
        return f"""
        <html>
        <head>
            <title>AI Services Error</title>
            <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
            <style>
                body {{ padding: 20px; }}
                .error-card {{ padding: 15px; background-color: rgba(220, 53, 69, 0.2); border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1 class="mb-4">AI Services Error</h1>
                
                <div class="error-card">
                    <h3>Error Loading AI Services</h3>
                    <p>{str(main_e)}</p>
                </div>
                
                <a href="/dashboard" class="btn btn-primary">Back to Dashboard</a>
            </div>
        </body>
        </html>
        """

@ai_bp.route('/status')
@login_required
def ai_status():
    """Get the status of AI services and analytics"""
    try:
        # Get services
        perplexity, ai_analyzer = get_services()
        
        perplexity_status = {
            "available": perplexity.available,
            "api_configured": bool(perplexity.api_key),
            "cache_size": len(perplexity.cache)
        }
        
        ai_analyzer_status = ai_analyzer.get_stats()
        
        # Check if the background thread is running
        analyzer_thread_alive = (
            ai_analyzer.processing_thread is not None and 
            ai_analyzer.processing_thread.is_alive()
        )
        
        return jsonify({
            "status": "success",
            "ai_services": {
                "perplexity": perplexity_status,
                "ai_analyzer": {
                    **ai_analyzer_status,
                    "thread_running": analyzer_thread_alive
                }
            },
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting AI status: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@ai_bp.route('/market-sentiment')
@login_required
def market_sentiment():
    """Get AI-enhanced market sentiment analysis"""
    try:
        # Get services
        perplexity, ai_analyzer = get_services()
        
        # Get tickers to include in analysis (if specified)
        tickers = request.args.get('tickers', '')
        ticker_list = [t.strip() for t in tickers.split(',')] if tickers else None
        
        # Get sentiment from Perplexity if available
        if perplexity.available:
            sentiment = perplexity.get_market_sentiment(tickers=ticker_list)
            
            log_to_db(
                "Market sentiment analysis requested",
                level="INFO",
                module="AI Services"
            )
            
            return jsonify({
                "status": "success",
                "sentiment": sentiment
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Perplexity API not available"
            }), 503
    except Exception as e:
        logger.error(f"Error getting market sentiment: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@ai_bp.route('/watchlist-scan', methods=['POST'])
@login_required
def scan_watchlist():
    """Scan a watchlist for potential OG strategy setups using AI"""
    try:
        # Get services
        perplexity, ai_analyzer = get_services()
        
        data = request.get_json()
        watchlist = data.get('watchlist', [])
        timeframe = data.get('timeframe', '1D')
        
        if not watchlist:
            return jsonify({
                "status": "error",
                "message": "No tickers provided in watchlist"
            }), 400
        
        # Limit to reasonable batch size
        max_batch_size = 20
        if len(watchlist) > max_batch_size:
            watchlist = watchlist[:max_batch_size]
        
        # Forward to AI analyzer
        scan_result = ai_analyzer.find_potential_setups(watchlist, timeframe)
        
        log_to_db(
            f"AI scan completed for {len(watchlist)} tickers on {timeframe} timeframe",
            level="INFO",
            module="AI Scanner"
        )
        
        return jsonify({
            "status": "success",
            "result": scan_result,
            "scanned_tickers": watchlist,
            "timeframe": timeframe
        })
    except Exception as e:
        logger.error(f"Error scanning watchlist: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@ai_bp.route('/analyze/<ticker>')
@login_required
def analyze_ticker(ticker):
    """Get comprehensive AI analysis for a specific ticker"""
    try:
        # Get services
        perplexity, ai_analyzer = get_services()
        
        # Get optional timeframe parameter
        timeframe = request.args.get('timeframe', '1D')
        
        # Force uppercase for ticker
        ticker = ticker.upper()
        
        if perplexity.available:
            # Get from Perplexity
            analysis = perplexity.analyze_ticker(
                ticker=ticker,
                include_news=True,
                technical_analysis=True,
                og_pattern_focus=True
            )
            
            # Get OG parameters
            og_params = perplexity.extract_og_parameters(ticker)
            
            return jsonify({
                "status": "success",
                "ticker": ticker,
                "timeframe": timeframe,
                "analysis": analysis,
                "og_parameters": og_params,
                "timestamp": datetime.now().isoformat()
            })
        else:
            # Fall back to simpler analysis
            return jsonify({
                "status": "limited",
                "ticker": ticker,
                "message": "Perplexity API not available, using limited analysis",
                "og_parameters": ai_analyzer._get_default_parameters(ticker),
                "timestamp": datetime.now().isoformat()
            })
    except Exception as e:
        logger.error(f"Error analyzing ticker {ticker}: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@ai_bp.route('/validate-signal/<int:signal_id>')
@login_required
def validate_signal(signal_id):
    """Validate a specific signal using AI analysis"""
    try:
        # Get services
        perplexity, ai_analyzer = get_services()
        
        # Get the signal from the database
        signal = Signal.query.get(signal_id)
        
        if not signal:
            return jsonify({
                "status": "error",
                "message": f"Signal with ID {signal_id} not found"
            }), 404
            
        # Validate the signal using AI
        validation = ai_analyzer.validate_signal(signal)
        
        return jsonify({
            "status": "success",
            "signal_id": signal_id,
            "validation": validation,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error validating signal {signal_id}: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@ai_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def ai_settings():
    """Get or update AI service settings"""
    try:
        # Get services
        perplexity, ai_analyzer = get_services()
        
        if request.method == 'GET':
            # Get current settings
            settings = {
                "ai_validation_enabled": get_setting("ai_validation_enabled", True),
                "ai_confidence_threshold": get_setting("ai_confidence_threshold", 0.65),
                "ai_minimum_component_match": get_setting("ai_minimum_component_match", 3),
                "ai_multi_timeframe_confirmation": get_setting("ai_multi_timeframe_confirmation", True),
                "perplexity_api_configured": bool(perplexity.api_key),
                "perplexity_available": perplexity.available
            }
            
            return jsonify({
                "status": "success",
                "settings": settings
            })
        else:
            # Update settings
            data = request.get_json()
            
            # Process each setting
            for key, value in data.items():
                if key == "ai_validation_enabled":
                    update_setting("ai_validation_enabled", bool(value))
                    ai_analyzer.ai_validation_enabled = bool(value)
                    
                elif key == "ai_confidence_threshold":
                    # Ensure value is between 0 and 1
                    threshold = float(value)
                    threshold = max(0.0, min(1.0, threshold))
                    update_setting("ai_confidence_threshold", threshold)
                    ai_analyzer.confidence_threshold = threshold
                    
                elif key == "ai_minimum_component_match":
                    # Ensure value is between 1 and 4
                    min_match = int(value)
                    min_match = max(1, min(4, min_match))
                    update_setting("ai_minimum_component_match", min_match)
                    ai_analyzer.minimum_component_match = min_match
                    
                elif key == "ai_multi_timeframe_confirmation":
                    update_setting("ai_multi_timeframe_confirmation", bool(value))
                    ai_analyzer.multi_timeframe_confirmation = bool(value)
            
            log_to_db(
                f"AI settings updated: {json.dumps(data)}",
                level="INFO",
                module="AI Settings"
            )
            
            return jsonify({
                "status": "success",
                "message": "AI settings updated successfully"
            })
    except Exception as e:
        logger.error(f"Error with AI settings: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@ai_bp.route('/setup-perplexity-api', methods=['POST'])
@login_required
def setup_perplexity_api():
    """Set up Perplexity API with an API key"""
    try:
        # Get services
        perplexity, ai_analyzer = get_services()
        
        data = request.get_json()
        api_key = data.get('api_key')
        
        if not api_key:
            return jsonify({
                "status": "error",
                "message": "No API key provided"
            }), 400
            
        # Update environment variable (would be stored securely in production)
        import os
        os.environ['PERPLEXITY_API_KEY'] = api_key
        
        # Re-initialize the service with the new key
        # Note: We're creating a new instance rather than calling __init__ directly
        from perplexity_service import PerplexityService
        # Import and update the singleton in perplexity_service
        from perplexity_service import _perplexity_service_instance
        import sys
        # Update the module's global variable
        sys.modules['perplexity_service']._perplexity_service_instance = PerplexityService(api_key=api_key)
        
        log_to_db(
            "Perplexity API key configured",
            level="INFO",
            module="AI Settings"
        )
        
        return jsonify({
            "status": "success",
            "message": "Perplexity API configured successfully",
            "available": perplexity.available
        })
    except Exception as e:
        logger.error(f"Error setting up Perplexity API: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@ai_bp.route('/scan-overnight-watchlist', methods=['POST'])
@login_required
def scan_overnight_watchlist():
    """Scan the overnight watchlist for potential trade setups"""
    try:
        # Get services
        perplexity, ai_analyzer = get_services()
        
        data = request.get_json()
        watchlist = data.get('watchlist', [])
        
        if not watchlist:
            return jsonify({
                "status": "error",
                "message": "No tickers provided in watchlist"
            }), 400
        
        # Run scan on multiple timeframes for confluence
        results = {}
        timeframes = ['1D', '4H', '1H']
        
        for tf in timeframes:
            scan_result = ai_analyzer.find_potential_setups(watchlist, tf)
            results[tf] = scan_result
        
        log_to_db(
            f"Overnight watchlist scan completed for {len(watchlist)} tickers",
            level="INFO",
            module="AI Scanner"
        )
        
        return jsonify({
            "status": "success",
            "results": results,
            "scanned_tickers": watchlist,
            "timeframes": timeframes,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error scanning overnight watchlist: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

def register_ai_blueprint(app):
    """Register the AI blueprint with the app and initialize services"""
    try:
        # Register blueprint first
        logger.info("Attempting to register AI blueprint...")
        print("Attempting to register AI blueprint...")
        app.register_blueprint(ai_bp)
        logger.info("AI Service blueprint registered")
        print("AI Services blueprint registered successfully")
        
        # Initialize services with app context
        logger.info("Initializing AI services with app context...")
        print("Initializing AI services with app context...")
        with app.app_context():
            try:
                initialize_ai_strategy_analyzer()
                logger.info("AI Strategy Analyzer initialized successfully")
                print("AI Strategy Analyzer initialized successfully")
            except Exception as e:
                error_msg = f"Error initializing AI Strategy Analyzer: {str(e)}"
                logger.error(error_msg)
                print(error_msg)
                logger.error(f"Exception type: {type(e)}")
                print(f"Exception type: {type(e)}")
                import traceback
                tb = traceback.format_exc()
                logger.error(f"Traceback: {tb}")
                print(f"Traceback: {tb}")
            
        return ai_bp
    except Exception as e:
        error_msg = f"Critical error registering AI blueprint: {str(e)}"
        logger.error(error_msg)
        print(error_msg)
        logger.error(f"Exception type: {type(e)}")
        print(f"Exception type: {type(e)}")
        import traceback
        tb = traceback.format_exc()
        logger.error(f"Traceback: {tb}")
        print(f"Traceback: {tb}")
        return None