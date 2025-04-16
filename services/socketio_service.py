# socketio_service.py

import os
import logging
import json
from datetime import datetime
from flask import request
from flask_socketio import SocketIO, emit, disconnect

logger = logging.getLogger(__name__)

# Initialize SocketIO
socketio = SocketIO()

class SocketIOService:
    """
    Service for managing Socket.IO real-time connections and events
    """
    
    def __init__(self, app=None):
        """Initialize Socket.IO service"""
        self.clients = {}
        self.app = app
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask app"""
        self.app = app
        
        # Configure Socket.IO
        socketio.init_app(
            app,
            cors_allowed_origins="*",
            async_mode="eventlet",
            logger=True,
            engineio_logger=True
        )
        
        # Register event handlers
        self._register_handlers()
        
        logger.info("Socket.IO service initialized")
    
    def _register_handlers(self):
        """Register Socket.IO event handlers"""
        
        @socketio.on('connect')
        def handle_connect():
            """Handle client connection"""
            client_id = request.sid
            self.clients[client_id] = {
                'connected_at': datetime.now().isoformat(),
                'client_info': {}
            }
            logger.info(f"Client connected: {client_id}")
            
            # Acknowledge connection
            emit('server_ready', {
                'server_id': 'OG-Strategy-Lab-Server',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'server_status': 'healthy',
                'server_version': '1.0.0'
            })
        
        @socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection"""
            client_id = request.sid
            if client_id in self.clients:
                del self.clients[client_id]
            logger.info(f"Client disconnected: {client_id}")
        
        @socketio.on('client_ready')
        def handle_client_ready(data):
            """Handle client ready event"""
            client_id = request.sid
            client_info = data.get('client_info', {})
            
            if client_id in self.clients:
                self.clients[client_id]['client_info'] = client_info
                logger.info(f"Client ready: {client_id}")
                logger.debug(f"Client details: {client_info}")
            
            # Send server ready response
            emit('server_ready', {
                'server_id': 'OG-Strategy-Lab-Server',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'server_status': 'healthy',
                'server_version': '1.0.0'
            })
        
        @socketio.on('request_signals')
        def handle_request_signals(data):
            """Handle request for signals"""
            limit = data.get('limit', 10)
            
            with self.app.app_context():
                from models import Signal
                signals = Signal.query.order_by(Signal.timestamp.desc()).limit(limit).all()
                
                emit('signals_update', {
                    'signals': [signal.to_dict() for signal in signals],
                    'timestamp': datetime.now().isoformat()
                })
        
        @socketio.on('request_market_status')
        def handle_market_status():
            """Handle request for market status"""
            from alpaca_service import get_alpaca_service
            
            alpaca = get_alpaca_service()
            market_status = alpaca.get_market_status()
            
            emit('market_status_update', {
                'market': market_status,
                'timestamp': datetime.now().isoformat()
            })
        
        @socketio.on('ping')
        def handle_ping():
            """Handle ping event"""
            emit('pong', {
                'timestamp': datetime.now().isoformat()
            })
        
        @socketio.on('health_check')
        def handle_health_check():
            """Handle health check request"""
            emit('health_response', {
                'status': 'healthy',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'server_uptime': 'Active'
            })
    
    def broadcast_signal(self, signal):
        """
        Broadcast a new signal to all connected clients
        
        Args:
            signal: Signal object or dictionary with signal data
        """
        try:
            # Convert to dictionary if needed
            if hasattr(signal, 'to_dict'):
                signal_data = signal.to_dict()
            else:
                signal_data = signal
            
            # Broadcast to all clients
            socketio.emit('new_signal', {
                'signal': signal_data,
                'timestamp': datetime.now().isoformat()
            })
            
            logger.info(f"Broadcasted new signal for {signal_data.get('symbol')}")
        except Exception as e:
            logger.error(f"Error broadcasting signal: {str(e)}")
    
    def broadcast_trade(self, trade):
        """
        Broadcast a new trade to all connected clients
        
        Args:
            trade: Trade object or dictionary with trade data
        """
        try:
            # Convert to dictionary if needed
            if hasattr(trade, 'to_dict'):
                trade_data = trade.to_dict()
            else:
                trade_data = trade
            
            # Broadcast to all clients
            socketio.emit('new_trade', {
                'trade': trade_data,
                'timestamp': datetime.now().isoformat()
            })
            
            logger.info(f"Broadcasted new trade for {trade_data.get('symbol')}")
        except Exception as e:
            logger.error(f"Error broadcasting trade: {str(e)}")
    
    def broadcast_market_update(self, data):
        """
        Broadcast a market update to all connected clients
        
        Args:
            data: Market data to broadcast
        """
        try:
            # Broadcast to all clients
            socketio.emit('market_update', {
                'data': data,
                'timestamp': datetime.now().isoformat()
            })
            
            logger.info(f"Broadcasted market update")
        except Exception as e:
            logger.error(f"Error broadcasting market update: {str(e)}")
    
    def broadcast_system_status(self, status, message=None):
        """
        Broadcast system status to all connected clients
        
        Args:
            status: Status code ('info', 'success', 'warning', 'error')
            message: Optional status message
        """
        try:
            # Broadcast to all clients
            socketio.emit('system_status', {
                'status': status,
                'message': message,
                'timestamp': datetime.now().isoformat()
            })
            
            logger.info(f"Broadcasted system status: {status}")
        except Exception as e:
            logger.error(f"Error broadcasting system status: {str(e)}")

# Singleton instance
socketio_service = None

def get_socketio_service():
    """Get singleton instance of SocketIOService"""
    global socketio_service
    
    if socketio_service is None:
        socketio_service = SocketIOService()
        
    return socketio_service
