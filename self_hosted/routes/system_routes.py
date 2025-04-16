import logging
from flask import Blueprint, render_template, request, redirect, url_for, jsonify
import os

# Create blueprint for system routes
system_blueprint = Blueprint('system', __name__, url_prefix='/system')

logger = logging.getLogger(__name__)

@system_blueprint.route('/')
def system_status():
    """System status dashboard"""
    from app import discord_service, alpaca_service
    
    # Check service status
    services = {
        'discord': discord_service.enabled and discord_service.client_ready,
        'alpaca': alpaca_service.enabled
    }
    
    # Get Alpaca account info if available
    account_info = None
    if alpaca_service.enabled:
        account_info = alpaca_service.get_account_info()
    
    return render_template('system_status.html', 
                           services=services, 
                           account_info=account_info,
                           env_vars={
                               'DISCORD_ENABLED': os.environ.get('DISCORD_TOKEN') is not None,
                               'ALPACA_ENABLED': os.environ.get('ALPACA_API_KEY') is not None,
                               'AUTO_TRADE': os.environ.get('AUTO_TRADE', 'false')
                           })

@system_blueprint.route('/settings')
def system_settings():
    """System settings page"""
    # Get current settings
    settings = {
        'auto_trade': os.environ.get('AUTO_TRADE', 'false').lower() == 'true',
        'discord_notifications': os.environ.get('DISCORD_NOTIFICATIONS', 'true').lower() == 'true',
        'log_level': os.environ.get('LOG_LEVEL', 'INFO'),
        'signal_throttling': os.environ.get('SIGNAL_THROTTLING', 'false').lower() == 'true'
    }
    
    return render_template('system_settings.html', settings=settings)

@system_blueprint.route('/settings', methods=['POST'])
def update_system_settings():
    """Update system settings"""
    # This would update environment variables in a real implementation
    # For now, just log the changes
    
    auto_trade = 'true' if request.form.get('auto_trade') else 'false'
    discord_notifications = 'true' if request.form.get('discord_notifications') else 'false'
    log_level = request.form.get('log_level', 'INFO')
    signal_throttling = 'true' if request.form.get('signal_throttling') else 'false'
    
    logger.info(f"System settings updated: auto_trade={auto_trade}, "
                f"discord_notifications={discord_notifications}, "
                f"log_level={log_level}, signal_throttling={signal_throttling}")
    
    # In a real implementation, this would persist settings
    # For now, just return success message
    return redirect(url_for('system.system_settings'))

@system_blueprint.route('/logs')
def system_logs():
    """System logs page"""
    # In a real implementation, this would load logs from a file or database
    # For now, just show some sample logs
    logs = [
        {'timestamp': '2025-04-16 12:00:00', 'level': 'INFO', 'message': 'System started'},
        {'timestamp': '2025-04-16 12:01:00', 'level': 'INFO', 'message': 'Discord connection established'},
        {'timestamp': '2025-04-16 12:02:00', 'level': 'INFO', 'message': 'Alpaca API initialized'}
    ]
    
    return render_template('system_logs.html', logs=logs)

@system_blueprint.route('/test_discord')
def test_discord():
    """Test Discord notification"""
    from app import discord_service
    
    # Send test message
    success = discord_service.send_message('Test message from OG Signal Bot')
    
    return jsonify({
        'success': success,
        'message': 'Discord test message sent' if success else 'Failed to send Discord test message'
    })

@system_blueprint.route('/test_signal')
def test_signal():
    """Generate a test signal"""
    from app import signal_service, socketio
    
    # Create test signal
    signal_data = {
        'symbol': 'AAPL',
        'direction': 'BULLISH',
        'confidence': 0.75,
        'price_at_signal': 175.50,
        'indicators': {
            'strategy': 'OG Strategy',
            'timeframe': '1D',
            'technical_signals': {
                'ema_cloud': True,
                'ob_fvg': True,
                'volume': True,
                'price_action': True
            },
            'key_levels': {
                'entry': 175.50,
                'stop': 172.50,
                'target1': 178.50,
                'target2': 182.50
            },
            'setup_type': 'EMA + FVG + OB'
        }
    }
    
    # Process the signal
    result = signal_service.process_signal(signal_data)
    
    # Broadcast the signal to all connected clients
    socketio.emit('new_signal', result)
    
    return jsonify({
        'success': True,
        'message': 'Test signal generated',
        'signal': result
    })