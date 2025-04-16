# discord_service.py

import os
import json
import logging
import requests
from datetime import datetime

logger = logging.getLogger(__name__)

class DiscordService:
    """
    Service for sending alerts and notifications to Discord
    """
    
    def __init__(self):
        """Initialize Discord service with webhook URL from environment"""
        self.webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
        self.enabled = self.webhook_url is not None and len(self.webhook_url) > 0
        
        if not self.enabled:
            logger.warning("Discord service disabled: No webhook URL configured")
    
    def send_message(self, message, color=0x00ff00, title=None):
        """
        Send a message to Discord
        
        Args:
            message: Message text to send
            color: Color for the message embed (hex integer)
            title: Optional title for the message
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            logger.warning("Attempted to send Discord message, but service is disabled")
            return False
        
        try:
            embed = {
                "description": message,
                "color": color,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if title:
                embed["title"] = title
                
            data = {
                "embeds": [embed]
            }
            
            response = requests.post(
                self.webhook_url,
                data=json.dumps(data),
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 204:
                logger.info(f"Successfully sent Discord message: {title}")
                return True
            else:
                logger.error(f"Failed to send Discord message: {response.status_code}, {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending Discord message: {str(e)}")
            return False
    
    def send_signal(self, signal):
        """
        Send a trading signal to Discord
        
        Args:
            signal: Signal object or dictionary with signal data
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False
            
        try:
            # Determine signal attributes
            if hasattr(signal, 'to_dict'):
                # This is a Signal object
                signal_data = signal.to_dict()
            else:
                # This is a dictionary
                signal_data = signal
                
            # Set color based on direction
            color = 0x00ff00  # Green for bullish
            if signal_data.get('direction', '').upper() == 'BEARISH':
                color = 0xff0000  # Red for bearish
                
            # Format the message
            title = f"🚨 New Signal: {signal_data.get('symbol')} {signal_data.get('direction')}"
            
            message = f"**Symbol**: {signal_data.get('symbol')}\n"
            message += f"**Direction**: {signal_data.get('direction')}\n"
            message += f"**Confidence**: {signal_data.get('confidence', 0) * 100:.1f}%\n"
            message += f"**Price**: ${signal_data.get('price_at_signal', 0):.2f}\n"
            
            # Add timestamp
            timestamp = signal_data.get('timestamp')
            if timestamp:
                message += f"**Time**: {timestamp}\n"
                
            # Add indicators if available
            indicators = signal_data.get('indicators')
            if indicators:
                if isinstance(indicators, str):
                    try:
                        indicators = json.loads(indicators)
                    except:
                        pass
                
                if isinstance(indicators, dict):
                    message += "\n**Indicators**:\n"
                    for key, value in indicators.items():
                        if isinstance(value, float):
                            message += f"• {key}: {value:.4f}\n"
                        else:
                            message += f"• {key}: {value}\n"
            
            return self.send_message(message, color, title)
            
        except Exception as e:
            logger.error(f"Error sending signal to Discord: {str(e)}")
            return False
            
    def send_trade(self, trade):
        """
        Send a trade execution message to Discord
        
        Args:
            trade: Trade object or dictionary with trade data
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False
            
        try:
            # Determine trade attributes
            if hasattr(trade, 'to_dict'):
                # This is a Trade object
                trade_data = trade.to_dict()
            else:
                # This is a dictionary
                trade_data = trade
                
            # Set color based on side
            color = 0x00ff00  # Green for buy
            if trade_data.get('side', '').lower() == 'sell':
                color = 0xff0000  # Red for sell
                
            # Format the message
            title = f"💰 Trade Executed: {trade_data.get('side').upper()} {trade_data.get('symbol')}"
            
            message = f"**Symbol**: {trade_data.get('symbol')}\n"
            message += f"**Side**: {trade_data.get('side').upper()}\n"
            message += f"**Quantity**: {trade_data.get('quantity')}\n"
            
            # Add price if available
            price = trade_data.get('price')
            if price:
                message += f"**Price**: ${price:.2f}\n"
                
            # Add status
            message += f"**Status**: {trade_data.get('status', 'unknown').upper()}\n"
            
            # Add execution time if available
            execution_time = trade_data.get('execution_time')
            if execution_time:
                message += f"**Executed**: {execution_time}\n"
                
            return self.send_message(message, color, title)
            
        except Exception as e:
            logger.error(f"Error sending trade to Discord: {str(e)}")
            return False
            
    def send_status_update(self, title, message, is_error=False):
        """
        Send a system status update to Discord
        
        Args:
            title: Status update title
            message: Status message
            is_error: Whether this is an error message
            
        Returns:
            True if successful, False otherwise
        """
        color = 0xff0000 if is_error else 0x0000ff
        return self.send_message(message, color, title)

# Singleton instance
discord_service = None

def get_discord_service():
    """Get singleton instance of DiscordService"""
    global discord_service
    
    if discord_service is None:
        discord_service = DiscordService()
        
    return discord_service
