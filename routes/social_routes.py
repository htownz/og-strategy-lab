"""
Social Sharing Routes for OG Strategy Lab

This module provides routes for the social sharing functionality, including
sharing signals, performance metrics, and strategy insights on social media.
"""

import json
import logging
from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from flask_login import login_required, current_user
from social_sharing import get_social_sharing_service, register_social_sharing_blueprint
from app import db
from models import Signal, Trade

# Setup logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create blueprints
social_routes = Blueprint('social_sharing_web', __name__, url_prefix='/social')
social_api = Blueprint('social_sharing_api', __name__, url_prefix='/social/api')

# Web UI Routes
@social_routes.route('/')
@login_required
def social_dashboard():
    """Main social sharing dashboard"""
    return redirect(url_for('social_sharing_web.share_signal_page'))

@social_routes.route('/signal')
@login_required
def share_signal_page():
    """Page for sharing trading signals"""
    # Get recent signals
    signals = db.session.query(Signal).order_by(Signal.timestamp.desc()).limit(20).all()
    
    return render_template('social/share_signal.html', 
                          signals=signals,
                          active_tab='signal')

@social_routes.route('/performance')
@login_required
def share_performance_page():
    """Page for sharing performance metrics"""
    return render_template('social/share_performance.html', 
                          active_tab='performance')

@social_routes.route('/strategy')
@login_required
def share_strategy_page():
    """Page for sharing strategy insights"""
    # Get strategies (in a real implementation, this would come from the database)
    strategies = [
        {'id': 1, 'name': 'OG Strategy'}
    ]
    
    return render_template('social/share_strategy.html', 
                          strategies=strategies,
                          active_tab='strategy')

@social_routes.route('/templates')
@login_required
def social_templates():
    """Page for customizing social sharing templates"""
    return render_template('social/templates.html', 
                          active_tab='templates')

# API Routes
@social_api.route('/signal/<int:signal_id>')
@login_required
def get_signal(signal_id):
    """Get signal details for sharing"""
    signal = db.session.query(Signal).get(signal_id)
    
    if not signal:
        return jsonify({'error': 'Signal not found'}), 404
    
    # Parse indicators JSON
    try:
        indicators = json.loads(signal.indicators)
    except:
        indicators = {}
    
    # Determine confidence level text
    confidence_level = "high"
    if signal.confidence < 0.7:
        confidence_level = "medium" if signal.confidence >= 0.4 else "low"
    
    return jsonify({
        'id': signal.id,
        'symbol': signal.symbol,
        'direction': signal.direction,
        'price': signal.price_at_signal,
        'confidence': signal.confidence,
        'confidence_level': confidence_level,
        'timestamp': signal.timestamp.strftime('%Y-%m-%d %H:%M'),
        'timeframe': indicators.get('timeframe', '1H') if indicators else '1H',
        'strategy': indicators.get('strategy', 'OG Strategy') if indicators else 'OG Strategy',
        'setup_type': indicators.get('setup_type', 'EMA + OB + FVG') if indicators else 'EMA + OB + FVG',
    })

@social_api.route('/performance/<period>')
@login_required
def get_performance(period):
    """Get performance metrics for sharing"""
    from datetime import datetime, timedelta
    import sqlalchemy as sa
    from sqlalchemy import func
    
    # Calculate date range based on period
    end_date = datetime.now()
    
    if period == 'all':
        start_date = datetime(2000, 1, 1)  # Effectively all time
    else:
        try:
            days = int(period)
            start_date = end_date - timedelta(days=days)
        except ValueError:
            # Default to 30 days if period is invalid
            start_date = end_date - timedelta(days=30)
    
    # Calculate trade stats
    trade_stats = db.session.query(
        func.count(Trade.id).label('total_trades'),
        func.sum(Trade.profit_loss).label('total_pl'),
        func.avg(Trade.profit_loss).label('avg_pl'),
        func.count(sa.case((Trade.profit_loss > 0, 1))).label('winning_trades'),
    ).filter(Trade.timestamp >= start_date).first()
    
    # Generate sample daily data for the chart
    # In a real implementation, this would be actual daily P&L data
    daily_data = []
    current_date = start_date
    cumulative_pl = 0
    
    while current_date <= end_date:
        # This is a placeholder - in a real implementation, would query actual daily P&L
        cumulative_pl += 0  # Sample data logic would go here
        
        daily_data.append({
            'date': current_date.strftime('%m/%d'),
            'pl': 0,  # Sample data
            'cumulative_pl': cumulative_pl
        })
        
        current_date += timedelta(days=1)
    
    # Calculate win rate
    if trade_stats.total_trades and trade_stats.total_trades > 0:
        win_rate = round((trade_stats.winning_trades / trade_stats.total_trades) * 100, 1)
    else:
        win_rate = 0
    
    # Format output
    result = {
        'id': 1,  # Use 1 as a default ID for performance sharing
        'win_rate': win_rate,
        'profit_loss': f"${trade_stats.total_pl:.2f}" if trade_stats.total_pl else "$0.00",
        'avg_profit_loss': f"${trade_stats.avg_pl:.2f}" if trade_stats.avg_pl else "$0.00",
        'num_trades': trade_stats.total_trades or 0,
        'period': period if period == 'all' else int(period),
        'timestamp': end_date.strftime('%Y-%m-%d'),
        'daily_data': daily_data
    }
    
    return jsonify(result)

@social_api.route('/strategy/<int:strategy_id>')
@login_required
def get_strategy(strategy_id):
    """Get strategy details for sharing"""
    # In a real implementation, this would query the database for strategy details
    # For now, we'll return the OG Strategy as a fixed example
    
    if strategy_id != 1:
        return jsonify({'error': 'Strategy not found'}), 404
    
    # Calculate win rate from trades
    import sqlalchemy as sa
    from sqlalchemy import func
    
    # Get trades associated with this strategy
    trade_stats = db.session.query(
        func.count(Trade.id).label('total_trades'),
        func.count(sa.case((Trade.profit_loss > 0, 1))).label('winning_trades'),
    ).first()
    
    # Calculate win rate
    if trade_stats.total_trades and trade_stats.total_trades > 0:
        win_rate = round((trade_stats.winning_trades / trade_stats.total_trades) * 100, 1)
    else:
        win_rate = 62.5  # Default example value if no trades
    
    return jsonify({
        'id': 1,
        'name': 'OG Strategy',
        'description': 'The OG Strategy combines EMA Cloud, Order Blocks, and Fair Value Gaps for high-probability trading setups. It excels at identifying key reversal points in the market.',
        'win_rate': win_rate,
        'timeframes': '1H, 4H, 1D'
    })

@social_api.route('/share/<content_type>/<int:content_id>')
@login_required
def generate_share_links(content_type, content_id):
    """Generate sharing links for content"""
    service = get_social_sharing_service()
    
    # Get share links from the service
    links = service.generate_share_links(content_type, content_id)
    
    return jsonify({'links': links})

@social_api.route('/preview/<content_type>/<int:content_id>')
@login_required
def preview_share(content_type, content_id):
    """Get preview of content for sharing"""
    service = get_social_sharing_service()
    
    # Get content data
    content_data = service._get_content_data(content_type, content_id)
    
    if not content_data:
        return jsonify({'error': 'Content not found'}), 404
    
    # Format the content
    formatted_content = service._format_content(content_type, content_data)
    
    # Get social image if available
    image_data = service.generate_social_image(content_type, content_id)
    
    result = {
        'title': formatted_content.get('title', ''),
        'text': formatted_content.get('text', ''),
        'image': image_data
    }
    
    return jsonify(result)

@social_api.route('/templates')
@login_required
def get_templates():
    """Get current social sharing templates"""
    service = get_social_sharing_service()
    
    return jsonify({'templates': service.templates})

@social_api.route('/templates/<template_type>', methods=['POST'])
@login_required
def save_template(template_type):
    """Save a custom social sharing template"""
    service = get_social_sharing_service()
    template_data = request.get_json()
    
    success = service.save_custom_template(template_type, template_data)
    
    return jsonify({'success': success})

@social_api.route('/templates/reset', methods=['POST'])
@login_required
def reset_templates():
    """Reset templates to default"""
    service = get_social_sharing_service()
    
    # Reset the service by recreating it
    global _social_sharing_service
    _social_sharing_service = None
    
    # Get the new service instance with default templates
    service = get_social_sharing_service()
    
    return jsonify({'success': True})

@social_api.route('/track', methods=['POST'])
@login_required
def track_share():
    """Track when content is shared"""
    data = request.get_json()
    
    # In a real implementation, this would record the share event
    # For now, we just log it
    logger.info(f"Content shared: {data}")
    
    return jsonify({'success': True})


def register_blueprints(app):
    """Register social sharing blueprints with Flask app"""
    app.register_blueprint(social_routes)
    app.register_blueprint(social_api)
    
    # Register API endpoints from social_sharing.py
    register_social_sharing_blueprint(app)
    
    logger.info("Registered social sharing blueprints")