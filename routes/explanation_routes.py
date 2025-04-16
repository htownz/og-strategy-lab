"""
Explanation Routes for OG Signal Bot

This module provides endpoints for AI-powered contextual explanations of trading strategies,
signals, and market patterns.
"""

import logging
import json
from flask import Blueprint, jsonify, request, render_template, current_app
from datetime import datetime

from strategy_explanation import get_strategy_explainer

logger = logging.getLogger(__name__)

# Initialize Blueprints
# API Blueprint for explanation endpoints
explanation_api_bp = Blueprint('explanation_api', __name__, url_prefix='/api/explanations')

# Web Blueprint for explanation UI pages
explanation_bp = Blueprint('explanation', __name__, url_prefix='/explanations')

@explanation_api_bp.route('/og_strategy', methods=['GET'])
def explain_og_strategy():
    """Get an explanation of the OG Strategy"""
    try:
        experience_level = request.args.get('level', 'beginner')
        if experience_level not in ['beginner', 'intermediate', 'advanced']:
            experience_level = 'beginner'
            
        explainer = get_strategy_explainer()
        result = explainer.explain_og_strategy(experience_level)
        
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
        logger.error(f"Error explaining OG strategy: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@explanation_api_bp.route('/signal/<int:signal_id>', methods=['GET'])
def explain_signal(signal_id):
    """Get an explanation for a specific signal"""
    try:
        from app import db
        from models import Signal
        
        detail_level = request.args.get('detail', 'medium')
        if detail_level not in ['brief', 'medium', 'detailed']:
            detail_level = 'medium'
        
        # Get the signal from the database
        signal = Signal.query.get(signal_id)
        if not signal:
            return jsonify({
                'success': False,
                'error': f'Signal with ID {signal_id} not found'
            }), 404
        
        # Convert signal to dictionary
        signal_data = {
            'id': signal.id,
            'symbol': signal.symbol,
            'direction': signal.direction,
            'confidence': signal.confidence,
            'price_at_signal': signal.price_at_signal,
            'indicators': signal.indicators,
            'timestamp': signal.timestamp.isoformat() if signal.timestamp else None
        }
        
        explainer = get_strategy_explainer()
        result = explainer.explain_signal(signal_data, detail_level)
        
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
        logger.error(f"Error explaining signal: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@explanation_api_bp.route('/answer_question', methods=['POST'])
def answer_question():
    """Answer a trading strategy question"""
    try:
        data = request.json
        
        if not data or 'question' not in data:
            return jsonify({
                'success': False,
                'error': 'Question is required'
            }), 400
        
        question = data.get('question')
        context = data.get('context', {})
        
        explainer = get_strategy_explainer()
        result = explainer.answer_strategy_question(question, context)
        
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
        logger.error(f"Error answering question: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@explanation_api_bp.route('/market_analysis', methods=['POST'])
def analyze_market():
    """Get AI analysis of current market conditions"""
    try:
        data = request.json
        
        if not data or 'market_data' not in data:
            return jsonify({
                'success': False,
                'error': 'Market data is required'
            }), 400
        
        market_data = data.get('market_data')
        ticker = data.get('ticker')
        
        explainer = get_strategy_explainer()
        result = explainer.analyze_market_conditions(market_data, ticker)
        
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
        logger.error(f"Error analyzing market: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@explanation_api_bp.route('/status', methods=['GET'])
def get_explainer_status():
    """Get status of strategy explainer service"""
    try:
        explainer = get_strategy_explainer()
        stats = explainer.get_stats()
        
        return jsonify({
            'success': True,
            'data': {
                'status': 'healthy' if stats.get('has_client') else 'limited',
                'stats': stats,
                'timestamp': datetime.now().isoformat()
            }
        })
    except Exception as e:
        logger.error(f"Error getting explainer status: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Web route for the explanation dashboard
@explanation_bp.route('/dashboard', methods=['GET'])
def explanation_dashboard():
    """Strategy Explanation Dashboard"""
    return render_template('explanations/dashboard.html')

@explanation_bp.route('/signal/<int:signal_id>', methods=['GET'])
def signal_explanation_page(signal_id):
    """Signal Explanation Page"""
    return render_template('explanations/signal.html', signal_id=signal_id)

@explanation_bp.route('/ask', methods=['GET'])
def ask_assistant_page():
    """Ask Trading Assistant Page"""
    return render_template('explanations/ask.html')

def register_explanation_blueprints(app):
    """Register the explanation blueprints"""
    # Register the web interface blueprint
    app.register_blueprint(explanation_bp)
    logger.info("Explanation web blueprint registered")
    
    # Register the API blueprint
    app.register_blueprint(explanation_api_bp)
    logger.info("Explanation API blueprint registered")
    
    # Initialize strategy explainer in a separate thread to avoid blocking app startup
    with app.app_context():
        try:
            # Just create the instance to initialize it
            explainer = get_strategy_explainer()
            logger.info("Strategy explainer initialized")
        except Exception as e:
            logger.error(f"Error initializing strategy explainer: {str(e)}")
    
    return explanation_bp