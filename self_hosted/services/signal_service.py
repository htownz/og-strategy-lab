import os
import json
import logging
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class SignalService:
    """Service for handling trading signals"""
    
    def __init__(self, discord_service, alpaca_service):
        """
        Initialize the signal service
        
        Args:
            discord_service: Discord notification service
            alpaca_service: Alpaca trading service
        """
        self.discord_service = discord_service
        self.alpaca_service = alpaca_service
        
        # In-memory signal storage for demo (would use database in production)
        self.signals = []
        self.load_sample_signals()
    
    def load_sample_signals(self):
        """Load sample signals for testing"""
        sample_signal = {
            "id": 1,
            "symbol": "SNAP",
            "direction": "BEARISH",
            "confidence": 0.85,
            "price_at_signal": 7.8,
            "timestamp": datetime.now().isoformat(),
            "indicators": json.dumps({
                "strategy": "OG Strategy",
                "timeframe": "1H",
                "technical_signals": {
                    "ema_cloud": True,
                    "ob_fvg": True,
                    "volume": True,
                    "price_action": True
                },
                "key_levels": {
                    "entry": 7.8,
                    "stop": 8.0,
                    "target1": 7.65,
                    "target2": 7.5
                },
                "contract": {
                    "strike": 7.5,
                    "expiration": "2025-04-25",
                    "type": "PUT"
                },
                "setup_type": "EMA + FVG + OB"
            })
        }
        self.signals.append(sample_signal)
    
    def get_current_timestamp(self):
        """Get current timestamp in ISO format"""
        return datetime.now().isoformat()
    
    def get_recent_signals(self, limit=10):
        """
        Get recent signals
        
        Args:
            limit (int): Maximum number of signals to return
            
        Returns:
            list: List of recent signals
        """
        return self.signals[:limit]
    
    def process_signal(self, signal_data):
        """
        Process a new trading signal
        
        Args:
            signal_data (dict): Signal data including symbol, direction, confidence, etc.
            
        Returns:
            dict: Processed signal data with ID and timestamp
        """
        try:
            # Add ID and timestamp if not present
            if 'id' not in signal_data:
                signal_data['id'] = len(self.signals) + 1
            
            if 'timestamp' not in signal_data:
                signal_data['timestamp'] = self.get_current_timestamp()
            
            # Convert indicators to string if it's a dict
            if 'indicators' in signal_data and isinstance(signal_data['indicators'], dict):
                signal_data['indicators'] = json.dumps(signal_data['indicators'])
            
            # Add signal to in-memory storage
            self.signals.append(signal_data)
            
            # Send notification to Discord
            self.discord_service.send_signal_alert(signal_data)
            
            # Check if auto-trading is enabled
            auto_trade = os.environ.get('AUTO_TRADE', 'false').lower() == 'true'
            if auto_trade:
                self._execute_trade(signal_data)
            
            logger.info(f"Signal processed: {signal_data['symbol']} {signal_data['direction']}")
            
            return signal_data
        except Exception as e:
            logger.error(f"Error processing signal: {e}")
            return {"error": str(e)}
    
    def _execute_trade(self, signal):
        """
        Execute a trade based on signal data
        
        Args:
            signal (dict): Signal data
            
        Returns:
            dict: Trade execution result
        """
        try:
            # Extract trade details from signal
            symbol = signal['symbol']
            direction = signal['direction']
            side = 'sell' if direction == 'BEARISH' else 'buy'
            
            # Default to 1 share if not specified
            qty = signal.get('quantity', 1)
            
            # Get current price if not in signal
            price = signal.get('price_at_signal')
            if not price:
                price = self.alpaca_service.get_current_price(symbol)
            
            # Check if this is an options contract
            is_option = False
            if 'indicators' in signal:
                indicators = signal['indicators']
                if isinstance(indicators, str):
                    indicators = json.loads(indicators)
                
                if 'contract' in indicators:
                    is_option = True
                    # Options trading would require specific contract symbol
                    # This is just a placeholder
                    logger.info(f"Options trading not implemented yet: {indicators['contract']}")
                    return {"status": "skipped", "reason": "Options trading not implemented"}
            
            # Execute the trade if not options
            if not is_option:
                order_result = self.alpaca_service.place_order(
                    symbol=symbol,
                    qty=qty,
                    side=side,
                    order_type='market',
                    time_in_force='day'
                )
                
                logger.info(f"Trade executed: {symbol} {side} {qty} shares")
                return order_result
            
            return {"status": "skipped", "reason": "Unknown trade type"}
            
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            return {"error": str(e)}