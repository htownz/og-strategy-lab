import os
import logging
from flask import Flask, render_template, jsonify, request
from datetime import datetime, timezone
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
import eventlet
from flask_socketio import SocketIO

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# Define SQLAlchemy base
class Base(DeclarativeBase):
    pass

# Initialize Flask extensions
db = SQLAlchemy(model_class=Base)
socketio = SocketIO()

# Create Flask application
app = Flask(__name__)

# Configure the app
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'dev-key-please-change')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions with app
db.init_app(app)
socketio.init_app(app, cors_allowed_origins="*", async_mode='eventlet')

# Import services and routes after app is created to avoid circular imports
from services import discord_service, alpaca_service, signal_service
from routes import api_routes, signal_routes, system_routes

# Register blueprints
app.register_blueprint(api_routes.api_bp)
app.register_blueprint(signal_routes.signal_bp)
app.register_blueprint(system_routes.system_bp)

# Create tables
with app.app_context():
    # Import models to ensure they're registered with SQLAlchemy
    from models.models import Signal, Trade, Settings
    
    # Create all tables
    db.create_all()
    
    # Initialize default settings if needed
    if not Settings.query.filter_by(key='trading_enabled').first():
        Settings(key='trading_enabled', value='false').save()
    
    if not Settings.query.filter_by(key='paper_trading').first():
        Settings(key='paper_trading', value='true').save()

# Socket.IO event handlers
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    client_id = request.sid
    logger.info(f"Client connected: {client_id}")
    return {'status': 'connected'}

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info(f"Client disconnected: {request.sid}")

@socketio.on('client_ready')
def handle_client_ready(data):
    """Handle client ready event"""
    logger.info(f"Client ready: {request.sid}")
    logger.debug(f"Client details: {data.get('client_info', {})}")
    
    # Send server ready event
    socketio.emit('server_ready', {
        'server_id': 'OG-Strategy-Lab-Server',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'server_status': 'healthy',
        'server_version': '1.0.0'
    }, to=request.sid)

@socketio.on('request_signals')
def handle_request_signals():
    """Handle request for signals"""
    signals = signal_service.get_recent_signals(limit=10)
    socketio.emit('signals', {'signals': signals}, to=request.sid)

@socketio.on('health_check')
def handle_health_check():
    """Handle health check request"""
    socketio.emit('health_response', {
        'status': 'healthy',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'server_uptime': 'Active'
    }, to=request.sid)

# Basic routes
@app.route('/')
def index():
    """Render home page"""
    return render_template('index.html')

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'env': app.config.get('FLASK_ENV', 'production')
    })

# Run the application
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)