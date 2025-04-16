# webhook_routes.py

from flask import Blueprint, request, jsonify
import logging
from discord_service import get_discord_service

logger = logging.getLogger(__name__)
webhook_bp = Blueprint('webhook', __name__)

@webhook_bp.route('/status', methods=['GET'])
def webhook_status():
    """Get Discord webhook status"""
    discord = get_discord_service()
    return jsonify({
        'enabled': discord.enabled,
        'webhook_configured': discord.webhook_url is not None
    })

@webhook_bp.route('/test', methods=['POST'])
def test_webhook():
    """Send a test message to Discord webhook"""
    discord = get_discord_service()
    if not discord.enabled:
        return jsonify({
            'success': False,
            'message': 'Discord webhook not configured'
        }), 400
        
    # Send test message
    success = discord.send_message(
        "This is a test message from OG Strategy Lab", 
        0x00ff00, 
        "Test Message"
    )
    
    if success:
        return jsonify({
            'success': True,
            'message': 'Test message sent successfully'
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Failed to send test message'
        }), 500

@webhook_bp.route('/configure', methods=['POST'])
def configure_webhook():
    """Configure Discord webhook URL"""
    data = request.json
    
    if not data or 'webhook_url' not in data:
        return jsonify({
            'success': False,
            'message': 'Missing webhook_url in request body'
        }), 400
        
    # This is just a temporary update for testing
    # In a real app, you'd store this in the database or environment
    import os
    os.environ['DISCORD_WEBHOOK_URL'] = data['webhook_url']
    
    # Reinitialize the service
    from discord_service import get_discord_service
    discord = get_discord_service()
    
    return jsonify({
        'success': True,
        'message': 'Webhook URL configured successfully',
        'enabled': discord.enabled
    })

# Register the blueprint
def register_webhook_blueprint(app):
    app.register_blueprint(webhook_bp, url_prefix='/api/webhook')
