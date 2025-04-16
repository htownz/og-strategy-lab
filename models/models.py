from datetime import datetime
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import json

# We don't need to import BacktestResult here since it's defined in models_backtest.py
# and we set up the relationship there

class Signal(db.Model):
    __tablename__ = 'signal'
    
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(20), nullable=False)
    direction = db.Column(db.String(10), nullable=False)  # UP or DOWN
    confidence = db.Column(db.Float, nullable=False)
    price_at_signal = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    indicators = db.Column(db.JSON)  # Store indicators that triggered the signal
    executed = db.Column(db.Boolean, default=False)  # Whether a trade was executed for this signal
    strategy_id = db.Column(db.Integer, db.ForeignKey('strategy_profile.id'), nullable=True)  # Strategy that generated this signal
    strategy_name = db.Column(db.String(64), nullable=True)  # Strategy name for quick reference
    timeframe = db.Column(db.String(20), nullable=True)  # Trading timeframe (5m, 15m, 1h, 1D, etc.)
    
    # Relationships
    strategy = db.relationship('StrategyProfile', backref=db.backref('signals', lazy=True))
    
    def __repr__(self):
        return f"<Signal {self.symbol} {self.direction} at {self.timestamp} from {self.strategy_name or 'unknown'} strategy>"

class Trade(db.Model):
    __tablename__ = 'trade'
    
    id = db.Column(db.Integer, primary_key=True)
    signal_id = db.Column(db.Integer, db.ForeignKey('signal.id'), nullable=True)
    symbol = db.Column(db.String(20), nullable=False)
    direction = db.Column(db.String(10), nullable=False)  # BUY or SELL
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=True)  # May be null for market orders until filled
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), nullable=False, default="SUBMITTED")  # SUBMITTED, FILLED, PARTIAL, CANCELED, REJECTED
    alpaca_order_id = db.Column(db.String(50), nullable=True)
    
    # Pattern Day Trader tracking fields
    is_day_trade = db.Column(db.Boolean, default=False)  # Identifies this as a day trade
    timeframe = db.Column(db.String(20), default="1h")   # Trading timeframe (5m, 15m, 1h, 1D, etc.)
    trade_type = db.Column(db.String(20), default="day")  # 'day' or 'swing'
    
    # Trade outcome analysis fields
    outcome = db.Column(db.String(20), nullable=True)  # WIN, LOSS, BREAKEVEN, EXPIRED_WORTHLESS, PARTIAL, UNKNOWN
    last_profit_snapshot = db.Column(db.Float, nullable=True)  # To track when profit changes for re-labeling
    confidence = db.Column(db.Float, nullable=True)  # Strategy confidence score (0-100)
    profit = db.Column(db.Float, nullable=True)  # Profit/loss amount
    
    # Fields for proper profit/loss tracking
    entry_price = db.Column(db.Float, nullable=True)  # Entry price (may be different from 'price' field)
    exit_price = db.Column(db.Float, nullable=True)  # Exit price when closed
    entry_date = db.Column(db.DateTime, nullable=True)  # May differ from timestamp for pending orders
    exit_date = db.Column(db.DateTime, nullable=True)  # When the position was closed
    strategy_id = db.Column(db.Integer, db.ForeignKey('strategy_profile.id'), nullable=True)  # Which strategy generated this trade
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # User who executed this trade
    
    # Relationships
    signal = db.relationship('Signal', backref=db.backref('trades', lazy=True))
    strategy = db.relationship('StrategyProfile', backref='trades')
    user = db.relationship('User', backref='trades')
    
    def __repr__(self):
        return f"<Trade {self.symbol} {self.direction} {self.quantity} at {self.timestamp}>"


class TradeOutcome(db.Model):
    __tablename__ = 'trade_outcomes'
    
    id = db.Column(db.Integer, primary_key=True)
    trade_id = db.Column(db.Integer, db.ForeignKey('trade.id'))
    outcome = db.Column(db.String(20), nullable=False)  # WIN, LOSS, BREAKEVEN, EXPIRED_WORTHLESS, PARTIAL, UNKNOWN
    profit = db.Column(db.Float, nullable=True)
    profit_pct = db.Column(db.Float, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    trade = db.relationship('Trade', backref='outcomes')

class SystemLog(db.Model):
    __tablename__ = 'system_log'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    level = db.Column(db.String(20), nullable=False)  # INFO, WARNING, ERROR, DEBUG
    module = db.Column(db.String(50), nullable=False)
    message = db.Column(db.Text, nullable=False)
    
    def __repr__(self):
        return f"<SystemLog {self.level} {self.module} at {self.timestamp}>"

class Setting(db.Model):
    __tablename__ = 'setting'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value_str = db.Column(db.String(255), nullable=True)
    value_int = db.Column(db.Integer, nullable=True)
    value_float = db.Column(db.Float, nullable=True)
    value_bool = db.Column(db.Boolean, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Setting {self.key}>"

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime, default=None, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<User {self.username}>"
    
    def set_password(self, password):
        """Set password hash for the user"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against stored hash"""
        return check_password_hash(self.password_hash, password)
        
    @property
    def is_authenticated(self):
        """Required for Flask-Login, always return True for actual User instances"""
        return True
    
    @property
    def is_anonymous(self):
        """Required for Flask-Login, always return False for actual User instances"""
        return False
        
    def get_id(self):
        """Return the user ID as a unicode string"""
        return str(self.id)
        
    # Relationship with risk profiles
    risk_profiles = db.relationship('RiskProfile', backref='user', lazy='dynamic')


class RiskProfile(db.Model):
    """Risk management profile for trading"""
    __tablename__ = 'risk_profile'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Risk parameters
    max_position_size = db.Column(db.Float, default=1000.0)  # Max $ per position
    max_positions = db.Column(db.Integer, default=5)  # Max number of simultaneous positions
    max_daily_loss = db.Column(db.Float, default=500.0)  # Max loss per day ($)
    max_position_loss = db.Column(db.Float, default=150.0)  # Max loss per position ($)
    stop_loss_percent = db.Column(db.Float, default=25.0)  # Auto close at X% loss
    take_profit_percent = db.Column(db.Float, default=50.0)  # Auto close at X% profit
    max_daily_trades = db.Column(db.Integer, default=10)  # Max trades per day
    auto_close_minutes = db.Column(db.Integer, default=0)  # Auto close after X minutes (0 = off)
    min_strategy_confidence = db.Column(db.Float, default=70.0)  # Min strategy confidence score (0-100)
    
    # Position sizing guardrails
    dynamic_sizing_enabled = db.Column(db.Boolean, default=True)  # Enable dynamic position sizing
    min_contracts = db.Column(db.Integer, default=1)  # Minimum number of contracts per trade
    max_contracts = db.Column(db.Integer, default=5)  # Maximum number of contracts per trade
    k_multiplier = db.Column(db.Float, default=1.0)  # K multiplier for dynamic sizing formula
    confidence_weight = db.Column(db.Float, default=0.3)  # Weight given to confidence score in sizing
    base_quantity = db.Column(db.Integer, default=2)  # Base quantity for position sizing
    
    # Advanced risk controls
    enable_volatility_adjustment = db.Column(db.Boolean, default=False)  # Adjust position size based on volatility
    max_portfolio_allocation = db.Column(db.Float, default=50.0)  # Max % of portfolio in options
    drawdown_pause_percent = db.Column(db.Float, default=7.0)  # Pause trading after X% drawdown
    correlation_limit = db.Column(db.Float, default=0.0)  # Limit on correlated positions (0 = off)
    
    # Trading schedule
    trade_days = db.Column(db.String(32), default="1,2,3,4,5")  # Trading days (1=Monday, 7=Sunday)
    market_hours_only = db.Column(db.Boolean, default=True)  # Only trade during market hours
    
    # Pattern Day Trader Rule settings
    pdt_rule_enabled = db.Column(db.Boolean, default=True)  # Enable PDT rule tracking
    max_day_trades = db.Column(db.Integer, default=3)  # Max day trades in 5-day window (default 3 for PDT rule)
    swing_trade_only = db.Column(db.Boolean, default=False)  # Only show swing trades when enabled 
    preferred_timeframe = db.Column(db.String(20), default="1h")  # Preferred trading timeframe
    pdt_override = db.Column(db.Boolean, default=False)  # Override PDT rule (allow trading even if limit reached)
    
    def __repr__(self):
        return f"<RiskProfile {self.name} ({self.id})>"
    
    def to_dict(self):
        """Convert profile to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'max_position_size': self.max_position_size,
            'max_positions': self.max_positions,
            'max_daily_loss': self.max_daily_loss,
            'max_position_loss': self.max_position_loss,
            'stop_loss_percent': self.stop_loss_percent,
            'take_profit_percent': self.take_profit_percent,
            'max_daily_trades': self.max_daily_trades,
            'auto_close_minutes': self.auto_close_minutes,
            'min_strategy_confidence': self.min_strategy_confidence,
            'enable_volatility_adjustment': self.enable_volatility_adjustment,
            'max_portfolio_allocation': self.max_portfolio_allocation,
            'drawdown_pause_percent': self.drawdown_pause_percent,
            'correlation_limit': self.correlation_limit,
            'trade_days': self.trade_days,
            'market_hours_only': self.market_hours_only,
            'pdt_rule_enabled': self.pdt_rule_enabled,
            'max_day_trades': self.max_day_trades,
            'swing_trade_only': self.swing_trade_only,
            'preferred_timeframe': self.preferred_timeframe,
            'pdt_override': self.pdt_override
        }
        

class StrategyProfile(db.Model):
    """Trading strategy configuration profile"""
    __tablename__ = 'strategy_profile'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    description = db.Column(db.Text, nullable=True)
    type = db.Column(db.String(50), nullable=False, default="options")  # Type: options, equity, crypto
    strategy_type = db.Column(db.String(50), nullable=False, default="og_strategy")  # Type of strategy
    active = db.Column(db.Boolean, default=False)
    timeframe = db.Column(db.String(20), default="1d")  # Default timeframe
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    risk_profile_id = db.Column(db.Integer, db.ForeignKey('risk_profile.id'), nullable=True)
    
    # Strategy configuration stored as JSON
    config = db.Column(db.JSON, nullable=False, default=lambda: {
        "ema_periods": [9, 21, 72],
        "volume_threshold": 1.5,
        "min_conditions_required": 3,
        "use_ob_fvg": True,
        "use_volume": True,
        "use_ema_cloud": True,
        "timeframes": ["5m", "15m", "1h", "4h", "1D"]
    })
    
    # Strategy builder components and connections
    components = db.Column(db.JSON, nullable=False, default=list)  # List of component instances
    connections = db.Column(db.JSON, nullable=False, default=list)  # List of connections between components
    
    # Filter settings for this strategy
    min_confidence_score = db.Column(db.Float, default=70.0)  # Minimum confidence score (0-100)
    trade_direction = db.Column(db.String(20), default="both")  # calls, puts, or both
    
    # Alert settings
    send_alerts = db.Column(db.Boolean, default=True)  # Send alerts to Telegram, etc.
    send_to_paper_trader = db.Column(db.Boolean, default=True)  # Send signals to paper trading
    send_to_live_trader = db.Column(db.Boolean, default=False)  # Send signals to live trading
    
    # Relationships
    user = db.relationship('User', backref=db.backref('strategy_profiles', lazy='dynamic'))
    risk_profile = db.relationship('RiskProfile', backref=db.backref('strategy_profiles', lazy='dynamic'))
    
    # For backward compatibility
    @property
    def is_active(self):
        return self.active
    
    def __repr__(self):
        return f"<StrategyProfile {self.name} ({self.id})>"
    
    def to_dict(self):
        """Convert profile to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'type': self.type,
            'strategy_type': self.strategy_type,
            'active': self.active,
            'timeframe': self.timeframe,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'user_id': self.user_id,
            'risk_profile_id': self.risk_profile_id,
            'risk_profile_name': self.risk_profile.name if self.risk_profile else None,
            'config': self.config,
            'components': self.components,
            'connections': self.connections,
            'min_confidence_score': self.min_confidence_score,
            'trade_direction': self.trade_direction,
            'send_alerts': self.send_alerts,
            'send_to_paper_trader': self.send_to_paper_trader,
            'send_to_live_trader': self.send_to_live_trader
        }
    
    @classmethod
    def create_default_profile(cls, user_id, risk_profile_id=None):
        """Create a default strategy profile for a user"""
        # Check if user already has strategy profiles
        if cls.query.filter_by(user_id=user_id).count() > 0:
            return None
            
        # Create default profile
        profile = cls(
            name="OG Strategy",
            description="Default strategy using EMA Cloud, Order Blocks, FVG, and Volume",
            type="options",
            strategy_type="og_strategy",
            active=True,
            user_id=user_id,
            risk_profile_id=risk_profile_id,
            config={
                "ema_periods": [9, 21, 72],
                "volume_threshold": 1.5,
                "min_conditions_required": 3,
                "use_ob_fvg": True,
                "use_volume": True,
                "use_ema_cloud": True,
                "timeframes": ["5m", "15m", "1h", "4h", "1D"]
            },
            components=[],
            connections=[]
        )
        
        db.session.add(profile)
        db.session.commit()
        
        return profile


class ScanResult(db.Model):
    """Saved scan results from overnight ticker analysis"""
    __tablename__ = 'scan_results'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    timeframes = db.Column(db.String(100), nullable=True)  # Comma-separated timeframes
    multi_timeframe_mode = db.Column(db.Boolean, default=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    results = db.Column(db.JSON, nullable=False)  # Store the scan results
    ticker_list = db.Column(db.JSON, nullable=False)  # List of tickers scanned
    
    # Relationships
    user = db.relationship('User', backref=db.backref('scan_results', lazy='dynamic'))
    
    def __repr__(self):
        return f"<ScanResult {self.name} at {self.timestamp}>"
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'timeframes': self.timeframes,
            'multi_timeframe_mode': self.multi_timeframe_mode,
            'user_id': self.user_id,
            'results': self.results,
            'ticker_list': self.ticker_list,
            'num_tickers': len(self.ticker_list) if self.ticker_list else 0,
            'num_results': len(self.results) if self.results else 0
        }


class MarketNews(db.Model):
    """Market news and headlines"""
    __tablename__ = 'market_news'
    
    id = db.Column(db.Integer, primary_key=True)
    headline = db.Column(db.String(255), nullable=False)
    summary = db.Column(db.Text, nullable=True)
    source = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(255), nullable=True)
    related_tickers = db.Column(db.String(255), nullable=True)  # Comma-separated list of related tickers
    image_url = db.Column(db.String(255), nullable=True)
    published_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    category = db.Column(db.String(50), nullable=True)  # earnings, merger, general, etc.
    sentiment = db.Column(db.Float, nullable=True)  # sentiment score from -1 to 1
    
    def __repr__(self):
        return f"<MarketNews {self.headline[:30]}... from {self.source}>"
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'headline': self.headline,
            'summary': self.summary,
            'source': self.source,
            'url': self.url,
            'related_tickers': self.related_tickers.split(',') if self.related_tickers else [],
            'image_url': self.image_url,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'category': self.category,
            'sentiment': self.sentiment
        }


class LearningPath(db.Model):
    """Personalized learning path for trading strategy education"""
    __tablename__ = 'learning_path'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    skill_level = db.Column(db.String(20), default="beginner")  # beginner, intermediate, advanced, expert
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    progress = db.Column(db.Float, default=0.0)  # Progress percentage (0-100)
    focus_areas = db.Column(db.JSON, default=list)  # List of focus areas (e.g., ["ema", "volume", "options_basics"])
    active_module = db.Column(db.Integer, nullable=True)  # Currently active module ID
    
    # Relationships
    user = db.relationship('User', backref=db.backref('learning_paths', lazy='dynamic'))
    modules = db.relationship('LearningModule', back_populates='learning_path', order_by='LearningModule.order')
    
    def __repr__(self):
        return f"<LearningPath {self.name} ({self.id})>"
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'description': self.description,
            'skill_level': self.skill_level,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'progress': self.progress,
            'focus_areas': self.focus_areas,
            'active_module': self.active_module,
            'modules': [module.to_dict() for module in self.modules]
        }
    
    def update_progress(self):
        """Update overall progress based on module completion"""
        if not self.modules:
            self.progress = 0.0
            return
        
        completed = sum(1 for module in self.modules if module.status == 'completed')
        self.progress = (completed / len(self.modules)) * 100
        db.session.commit()


class LearningModule(db.Model):
    """Module within a learning path"""
    __tablename__ = 'learning_module'
    
    id = db.Column(db.Integer, primary_key=True)
    learning_path_id = db.Column(db.Integer, db.ForeignKey('learning_path.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    order = db.Column(db.Integer, nullable=False)  # Order within the learning path
    status = db.Column(db.String(20), default="not_started")  # not_started, in_progress, completed
    content_type = db.Column(db.String(20), default="text")  # text, video, interactive
    content = db.Column(db.Text, nullable=True)  # Can be text content or a URL
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    unlock_criteria = db.Column(db.JSON, nullable=True)  # Requirements to unlock this module
    
    # Relationships
    learning_path = db.relationship('LearningPath', back_populates='modules')
    activities = db.relationship('LearningActivity', back_populates='module', order_by='LearningActivity.order')
    
    def __repr__(self):
        return f"<LearningModule {self.title} ({self.id})>"
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'learning_path_id': self.learning_path_id,
            'title': self.title,
            'description': self.description,
            'order': self.order,
            'status': self.status,
            'content_type': self.content_type,
            'content': self.content,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'unlock_criteria': self.unlock_criteria,
            'activities': [activity.to_dict() for activity in self.activities]
        }
    
    def update_status(self):
        """Update status based on learning activities completion"""
        if not self.activities:
            return
        
        completed = sum(1 for activity in self.activities if activity.completed)
        if completed == 0:
            self.status = "not_started"
        elif completed == len(self.activities):
            self.status = "completed"
        else:
            self.status = "in_progress"
        
        db.session.commit()
        
        # Update learning path progress
        self.learning_path.update_progress()


class LearningActivity(db.Model):
    """Activity within a learning module"""
    __tablename__ = 'learning_activity'
    
    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey('learning_module.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    activity_type = db.Column(db.String(20), nullable=False)  # reading, quiz, exercise, analysis, practice
    order = db.Column(db.Integer, nullable=False)
    content = db.Column(db.Text, nullable=True)
    completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completion_data = db.Column(db.JSON, nullable=True)  # Store data related to completion (scores, answers, etc.)
    
    # Relationships
    module = db.relationship('LearningModule', back_populates='activities')
    
    def __repr__(self):
        return f"<LearningActivity {self.title} ({self.id})>"
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'module_id': self.module_id,
            'title': self.title,
            'description': self.description,
            'activity_type': self.activity_type,
            'order': self.order,
            'content': self.content,
            'completed': self.completed,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'completion_data': self.completion_data
        }
    
    def mark_completed(self, completion_data=None):
        """Mark activity as completed with optional completion data"""
        self.completed = True
        if completion_data:
            self.completion_data = completion_data
        self.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Update module status
        self.module.update_status()


class TradingCoach(db.Model):
    """AI-powered trading coach for personalized guidance"""
    __tablename__ = 'trading_coach'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(50), default="Coach")
    personality = db.Column(db.String(20), default="supportive")  # supportive, challenging, analytical, motivational
    focus_area = db.Column(db.String(50), default="og_strategy")  # Main area of coaching focus
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    coaching_history = db.Column(db.JSON, default=list)  # List of coaching interactions
    user_preferences = db.Column(db.JSON, nullable=True)  # User preferences for coaching
    
    # Relationships
    user = db.relationship('User', backref=db.backref('coach', uselist=False))
    coaching_sessions = db.relationship('CoachingSession', back_populates='coach', order_by='CoachingSession.created_at.desc()')
    
    def __repr__(self):
        return f"<TradingCoach {self.name} for User {self.user_id}>"
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'personality': self.personality,
            'focus_area': self.focus_area,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'coaching_history': self.coaching_history,
            'user_preferences': self.user_preferences
        }
    
    def get_recent_sessions(self, limit=5):
        """Get recent coaching sessions"""
        return self.coaching_sessions[:limit]
    
    def add_coaching_history(self, interaction):
        """Add an interaction to the coaching history"""
        if not self.coaching_history:
            self.coaching_history = []
        
        self.coaching_history.append({
            'timestamp': datetime.utcnow().isoformat(),
            'interaction': interaction
        })
        
        # Keep only the last 100 interactions
        if len(self.coaching_history) > 100:
            self.coaching_history = self.coaching_history[-100:]
            
        db.session.commit()


class CoachingSession(db.Model):
    """Individual coaching session between user and AI coach"""
    __tablename__ = 'coaching_session'
    
    id = db.Column(db.Integer, primary_key=True)
    coach_id = db.Column(db.Integer, db.ForeignKey('trading_coach.id'), nullable=False)
    title = db.Column(db.String(100), nullable=True)
    topic = db.Column(db.String(50), nullable=False)  # strategy_review, trade_analysis, skill_development, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    conversation = db.Column(db.JSON, default=list)  # List of messages in the conversation
    insights = db.Column(db.Text, nullable=True)  # AI-generated insights from the session
    action_items = db.Column(db.JSON, default=list)  # List of action items generated from the session
    status = db.Column(db.String(20), default="active")  # active, completed, archived
    
    # Relationships
    coach = db.relationship('TradingCoach', back_populates='coaching_sessions')
    
    def __repr__(self):
        return f"<CoachingSession {self.topic} ({self.id})>"
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'coach_id': self.coach_id,
            'title': self.title,
            'topic': self.topic,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'conversation': self.conversation,
            'insights': self.insights,
            'action_items': self.action_items,
            'status': self.status
        }
    
    def add_message(self, role, content):
        """Add a message to the conversation"""
        if not self.conversation:
            self.conversation = []
            
        self.conversation.append({
            'role': role,  # user or coach
            'content': content,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        self.updated_at = datetime.utcnow()
        db.session.commit()
        
    def generate_insights(self, insights_text):
        """Generate insights from the conversation"""
        self.insights = insights_text
        self.updated_at = datetime.utcnow()
        db.session.commit()
        
    def add_action_item(self, action_item):
        """Add an action item from the conversation"""
        if not self.action_items:
            self.action_items = []
            
        self.action_items.append({
            'description': action_item,
            'created_at': datetime.utcnow().isoformat(),
            'completed': False
        })
        
        self.updated_at = datetime.utcnow()
        db.session.commit()
        
    def complete_action_item(self, index):
        """Mark an action item as completed"""
        if not self.action_items or index >= len(self.action_items):
            return False
        
        self.action_items[index]['completed'] = True
        self.action_items[index]['completed_at'] = datetime.utcnow().isoformat()
        self.updated_at = datetime.utcnow()
        db.session.commit()
        return True
