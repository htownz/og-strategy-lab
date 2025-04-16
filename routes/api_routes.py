"""
API routes for Signal Health Dashboard and Signal Queue Monitor
"""
from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
import logging
import random

# Set up logging
logger = logging.getLogger(__name__)

# Create blueprint
monitoring_api = Blueprint('monitoring_api', __name__)

@monitoring_api.route('/api/throttling-metrics')
def get_throttling_metrics_api():
    """
    API endpoint to get current throttling metrics
    """
    try:
        from signal_throttler import get_throttling_metrics
        metrics = get_throttling_metrics()
        return jsonify(metrics)
    except Exception as e:
        logger.error(f"Error getting throttling metrics: {e}")
        return jsonify({
            'error': str(e)
        }), 500

@monitoring_api.route('/api/queue-metrics')
def get_queue_metrics_api():
    """
    API endpoint to get current queue metrics
    """
    try:
        from signal_queue_monitor import get_queue_metrics
        metrics = get_queue_metrics()
        return jsonify(metrics)
    except Exception as e:
        logger.error(f"Error getting queue metrics: {e}")
        return jsonify({
            'error': str(e)
        }), 500

@monitoring_api.route('/api/update-throttle-settings', methods=['POST'])
def update_throttle_settings():
    """
    API endpoint to update throttle settings
    """
    try:
        data = request.json
        from config import update_setting
        
        # Update settings
        update_setting('signal_throttle_active', data.get('throttle_active', True))
        update_setting('throttle_window_seconds', int(data.get('throttle_window', 30)))
        update_setting('confidence_cutoff', float(data.get('confidence_cutoff', 0.7)))
        update_setting('throttle_override', data.get('throttle_override', False))
        
        # Log the change
        from logs_service import log_to_db
        log_to_db(f"Throttle settings updated: {data}", level="INFO", module="Throttling")
        
        return jsonify({
            'success': True
        })
    except Exception as e:
        logger.error(f"Error updating throttle settings: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@monitoring_api.route('/api/activate-boost', methods=['POST'])
def activate_boost():
    """
    API endpoint to activate boost mode for a specified duration
    """
    try:
        data = request.json
        duration = int(data.get('duration', 30))  # Default to 30 seconds
        
        # Limit duration to maximum of 5 minutes
        if duration > 300:
            duration = 300
            
        # Calculate end time
        end_time = datetime.now() + timedelta(seconds=duration)
        
        from config import update_setting
        
        # Update settings
        update_setting('boost_mode_active', True)
        update_setting('boost_end_time', end_time.isoformat())
        
        # Log the change
        from logs_service import log_to_db
        log_to_db(f"Boost mode activated for {duration} seconds", level="INFO", module="Throttling")
        
        return jsonify({
            'success': True,
            'boost_end_time': end_time.isoformat(),
            'duration': duration
        })
    except Exception as e:
        logger.error(f"Error activating boost mode: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@monitoring_api.route('/api/cancel-boost', methods=['POST'])
def cancel_boost():
    """
    API endpoint to cancel boost mode
    """
    try:
        from config import update_setting
        
        # Update settings
        update_setting('boost_mode_active', False)
        update_setting('boost_end_time', '')
        
        # Log the change
        from logs_service import log_to_db
        log_to_db("Boost mode canceled", level="INFO", module="Throttling")
        
        return jsonify({
            'success': True
        })
    except Exception as e:
        logger.error(f"Error canceling boost mode: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@monitoring_api.route('/api/toggle-auto-healing', methods=['POST'])
def toggle_auto_healing():
    """
    API endpoint to toggle auto-healing
    """
    try:
        data = request.json
        enabled = data.get('enabled', True)
        
        from signal_queue_monitor import set_auto_healing
        set_auto_healing(enabled)
        
        # Log the change
        from logs_service import log_to_db
        log_to_db(f"Auto-healing {'enabled' if enabled else 'disabled'}", level="INFO", module="QueueMonitor")
        
        return jsonify({
            'success': True
        })
    except Exception as e:
        logger.error(f"Error toggling auto-healing: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@monitoring_api.route('/api/trigger-healing', methods=['POST'])
def trigger_healing():
    """
    API endpoint to trigger a manual healing action
    """
    try:
        from signal_queue_monitor import trigger_healing_action
        result = trigger_healing_action()
        
        # Log the action
        from logs_service import log_to_db
        log_to_db("Manual healing action triggered", level="INFO", module="QueueMonitor")
        
        return jsonify({
            'success': True,
            'result': result
        })
    except Exception as e:
        logger.error(f"Error triggering healing action: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@monitoring_api.route('/api/reset-queue', methods=['POST'])
def reset_queue():
    """
    API endpoint to reset the signal queue
    """
    try:
        from signal_queue_monitor import reset_queue as do_reset
        result = do_reset()
        
        # Log the action
        from logs_service import log_to_db
        log_to_db("Signal queue reset", level="WARNING", module="QueueMonitor")
        
        return jsonify({
            'success': True,
            'result': result
        })
    except Exception as e:
        logger.error(f"Error resetting queue: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@monitoring_api.route('/api/start-stress-test', methods=['POST'])
def start_stress_test():
    """
    API endpoint to start a stress test
    """
    try:
        data = request.json
        signal_count = int(data.get('signal_count', 100))
        signal_interval_ms = int(data.get('signal_interval_ms', 500))
        confidence_range = data.get('confidence_range', 'random')
        
        # Convert confidence range to min/max values
        if confidence_range == 'high':
            min_confidence = 0.7
            max_confidence = 1.0
        elif confidence_range == 'medium':
            min_confidence = 0.4
            max_confidence = 0.7
        elif confidence_range == 'low':
            min_confidence = 0.1
            max_confidence = 0.4
        else:  # random
            min_confidence = 0.1
            max_confidence = 1.0
        
        from signal_queue_monitor import start_stress_test as do_start_test
        result = do_start_test(signal_count, signal_interval_ms, min_confidence, max_confidence)
        
        # Log the action
        from logs_service import log_to_db
        log_to_db(f"Stress test started: {signal_count} signals at {signal_interval_ms}ms intervals", 
                 level="INFO", module="QueueMonitor")
        
        return jsonify({
            'success': True,
            'result': result
        })
    except Exception as e:
        logger.error(f"Error starting stress test: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@monitoring_api.route('/api/stop-stress-test', methods=['POST'])
def stop_stress_test():
    """
    API endpoint to stop a stress test
    """
    try:
        from signal_queue_monitor import stop_stress_test as do_stop_test
        result = do_stop_test()
        
        # Log the action
        from logs_service import log_to_db
        log_to_db("Stress test stopped", level="INFO", module="QueueMonitor")
        
        return jsonify({
            'success': True,
            'result': result
        })
    except Exception as e:
        logger.error(f"Error stopping stress test: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500