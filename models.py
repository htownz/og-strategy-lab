from datetime import datetime
import json
from app import db

class Signal(db.Model):
    """Trading signal model"""
    
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(16), nullable=False)
    direction = db.Column(db.String(16), nullable=False)  # BULLISH or BEARISH
    confidence = db.Column(db.Float, nullable=False, default=0.5)
    price_at_signal = db.Column(db.Float, nullable=False)
    indicators = db.Column(db.Text, nullable=True)  # JSON string
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.now)
    
    def __repr__(self):
        return f"<Signal {self.id}: {self.symbol} {self.direction}>"
    
    def to_dict(self):
        """Convert signal to dictionary"""
        return {
            'id': self.id,
            'symbol': self.symbol,
            'direction': self.direction,
            'confidence': self.confidence,
            'price_at_signal': self.price_at_signal,
            'indicators': self.indicators,
            'timestamp': self.timestamp.isoformat()
        }
    
    def get_indicators(self):
        """Get indicators as Python dictionary"""
        if not self.indicators:
            return {}
        
        try:
            return json.loads(self.indicators)
        except:
            return {}


class Trade(db.Model):
    """Trade model for executed trades"""
    
    id = db.Column(db.Integer, primary_key=True)
    signal_id = db.Column(db.Integer, db.ForeignKey('signal.id'), nullable=True)
    symbol = db.Column(db.String(16), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    side = db.Column(db.String(8), nullable=False)  # buy or sell
    order_type = db.Column(db.String(16), nullable=False, default='market')
    price = db.Column(db.Float, nullable=True)  # Execution price
    status = db.Column(db.String(16), nullable=False, default='pending')
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.now)
    execution_time = db.Column(db.DateTime, nullable=True)  # When trade was executed
    external_id = db.Column(db.String(64), nullable=True)  # Alpaca order ID
    profit_loss = db.Column(db.Float, nullable=True)  # P&L
    
    signal = db.relationship('Signal', backref='trades')
    
    def __repr__(self):
        return f"<Trade {self.id}: {self.symbol} {self.side} {self.quantity}>"
    
    def to_dict(self):
        """Convert trade to dictionary"""
        return {
            'id': self.id,
            'signal_id': self.signal_id,
            'symbol': self.symbol,
            'quantity': self.quantity,
            'side': self.side,
            'order_type': self.order_type,
            'price': self.price,
            'status': self.status,
            'timestamp': self.timestamp.isoformat(),
            'execution_time': self.execution_time.isoformat() if self.execution_time else None,
            'external_id': self.external_id,
            'profit_loss': self.profit_loss
        }


class Settings(db.Model):
    """Settings model for system configuration"""
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), nullable=False, unique=True)
    value = db.Column(db.Text, nullable=True)
    
    def __repr__(self):
        return f"<Setting {self.key}: {self.value}>"
