"""
Risk ML Routes for OG Signal Bot

This module provides endpoints for ML-powered risk forecasting and trade setup analysis.
"""

import logging
import json
from flask import Blueprint, jsonify, request, render_template, current_app
from datetime import datetime

from risk_forecasting_ml import (
    get_forecasting_engine,
    forecast_volatility,
    predict_market_regime,
    evaluate_trade_setup,
    train_forecasting_models,
    init_forecasting_engine
)

logger = logging.getLogger(__name__)

# Initialize Blueprints
# API Blueprint for ML endpoints
risk_ml_api_bp = Blueprint('risk_ml_api', __name__, url_prefix='/risk/api/ml')

# Web Blueprint for ML dashboard pages
risk_ml_bp = Blueprint('risk_ml', __name__, url_prefix='/risk')

# API endpoints
@risk_ml_api_bp.route('/volatility/<symbol>', methods=['GET'])
def get_volatility_forecast(symbol):
    """Get volatility forecast for a symbol"""
    try:
        result = forecast_volatility(symbol)
        
        if 'error' in result:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 400
        
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        logger.error(f"Error getting volatility forecast: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@risk_ml_api_bp.route('/market_regime', methods=['GET'])
def get_market_regime():
    """Get current market regime prediction"""
    try:
        result = predict_market_regime()
        
        if 'error' in result:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 400
        
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        logger.error(f"Error getting market regime: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@risk_ml_api_bp.route('/evaluate_setup', methods=['POST'])
def evaluate_trade_setup_endpoint():
    """Evaluate a potential trade setup"""
    try:
        data = request.json
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        result = evaluate_trade_setup(data)
        
        if 'error' in result:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 400
        
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        logger.error(f"Error evaluating trade setup: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@risk_ml_api_bp.route('/train', methods=['POST'])
def train_models_endpoint():
    """Train ML risk forecasting models"""
    try:
        result = train_forecasting_models()
        
        return jsonify({
            'success': result,
            'message': 'Models trained successfully' if result else 'Failed to train models'
        })
    except Exception as e:
        logger.error(f"Error training models: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@risk_ml_api_bp.route('/status', methods=['GET'])
def get_ml_status():
    """Get status of ML risk forecasting engine"""
    try:
        engine = get_forecasting_engine()
        
        # Get model training status
        volatility_model = engine.volatility_model
        regime_model = engine.regime_model
        setup_model = engine.setup_model
        
        status = {
            'volatility_model': {
                'trained': volatility_model.model is not None,
                'last_trained': volatility_model.last_trained.isoformat() if volatility_model.last_trained else None
            },
            'regime_model': {
                'trained': regime_model.model is not None,
                'last_trained': regime_model.last_trained.isoformat() if regime_model.last_trained else None
            },
            'setup_model': {
                'trained': setup_model.model is not None,
                'last_trained': setup_model.last_trained.isoformat() if setup_model.last_trained else None
            },
            'background_thread_running': engine.background_thread is not None and engine.background_thread.is_alive(),
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify({
            'success': True,
            'data': status
        })
    except Exception as e:
        logger.error(f"Error getting ML status: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Page routes for the risk ML dashboard
@risk_ml_bp.route('/dashboard', methods=['GET'])
def ml_forecasting_dashboard():
    """ML Risk Forecasting Dashboard"""
    return render_template('risk/ml_forecasting.html')

def register_risk_ml_blueprint(app):
    """Register the risk ML blueprints and initialize engine"""
    # Register the web interface blueprint
    app.register_blueprint(risk_ml_bp)
    logger.info("Risk ML web blueprint registered")
    
    # Register the API blueprint
    app.register_blueprint(risk_ml_api_bp)
    logger.info("Risk ML API blueprint registered")
    
    # Initialize ML engine in a separate thread to avoid blocking app startup
    with app.app_context():
        try:
            init_forecasting_engine()
            logger.info("Risk forecasting engine initialized")
        except Exception as e:
            logger.error(f"Error initializing risk forecasting engine: {str(e)}")
    
    return risk_ml_bp