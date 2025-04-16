import os
import logging
from datetime import datetime, timezone
from flask import Flask, jsonify, render_template, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from webhook_routes import register_webhook_blueprint

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# Define SQLAlchemy base
class Base(DeclarativeBase):
    pass

# Initialize extensions
db = SQLAlchemy(model_class=Base)

# Create Flask application
app = Flask(__name__)

# Configure the app
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'dev-key-please-change')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Fix PostgreSQL URI if needed (handles Railway's postgres:// vs postgresql://)
if app.config['SQLALCHEMY_DATABASE_URI'] and app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://', 1)

# Initialize extensions with app
db.init_app(app)

# Import models
from models import Signal, Trade, Settings

# Create tables
@app.before_first_request
def create_tables():
    db.create_all()
    # Initialize default settings if needed
    with app.app_context():
        if not Settings.query.filter_by(key='trading_enabled').first():
            setting = Settings(key='trading_enabled', value='false')
            db.session.add(setting)
        
        if not Settings.query.filter_by(key='paper_trading').first():
            setting = Settings(key='paper_trading', value='true')
            db.session.add(setting)
            
        db.session.commit()
        logger.info("Database tables created and default settings initialized")

# Routes
@app.route('/')
def index():
    """Render the dashboard homepage"""
    return render_template('index.html')

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'env': app.config.get('FLASK_ENV', 'production'),
        'database': 'connected' if db_check() else 'disconnected'
    })

def db_check():
    """Check if database is connected"""
    try:
        # Execute a simple query
        db.session.execute('SELECT 1')
        return True
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        return False

@app.route('/signals')
def signals():
    """Get list of signals"""
    try:
        signals = Signal.query.order_by(Signal.timestamp.desc()).limit(10).all()
        return jsonify([signal.to_dict() for signal in signals])
    except Exception as e:
        logger.error(f"Error retrieving signals: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/settings')
def get_settings():
    """Get application settings"""
    try:
        settings = Settings.query.all()
        return jsonify({setting.key: setting.value for setting in settings})
    except Exception as e:
        logger.error(f"Error retrieving settings: {e}")
        return jsonify({'error': str(e)}), 500

register_webhook_blueprint(app)

@app.route('/discord')
def discord_config():
    """Discord configuration page"""
    return render_template('discord.html')
    
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
