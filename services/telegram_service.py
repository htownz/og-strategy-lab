import os
import logging
import requests
from datetime import datetime
from app import db
from models import SystemLog

# Get Telegram API credentials from environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

logger = logging.getLogger(__name__)

def send_telegram_message(message):
    """
    Send a message to the configured Telegram chat
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        log_message = "Telegram credentials not configured. Message not sent."
        logger.warning(log_message)
        
        # Log to database
        log_entry = SystemLog(
            level="WARNING",
            module="Telegram",
            message=log_message
        )
        db.session.add(log_entry)
        db.session.commit()
        return False
    
    try:
        api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        
        response = requests.post(api_url, data=payload)
        
        if response.status_code == 200:
            log_message = "Telegram message sent successfully"
            logger.info(log_message)
            
            # Log to database
            log_entry = SystemLog(
                level="INFO",
                module="Telegram",
                message=log_message
            )
            db.session.add(log_entry)
            db.session.commit()
            return True
        else:
            log_message = f"Failed to send Telegram message. Status code: {response.status_code}, Response: {response.text}"
            logger.error(log_message)
            
            # Log to database
            log_entry = SystemLog(
                level="ERROR",
                module="Telegram",
                message=log_message
            )
            db.session.add(log_entry)
            db.session.commit()
            return False
            
    except Exception as e:
        log_message = f"Error sending Telegram message: {str(e)}"
        logger.error(log_message)
        
        # Log to database
        log_entry = SystemLog(
            level="ERROR",
            module="Telegram",
            message=log_message
        )
        db.session.add(log_entry)
        db.session.commit()
        return False

def send_signal_alert(symbol, direction, confidence, price):
    """
    Send a formatted signal alert message
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    message = f"🔔 <b>SIGNAL ALERT</b>\n\n" \
             f"<b>Symbol:</b> {symbol}\n" \
             f"<b>Direction:</b> {'⬆️ BUY' if direction == 'UP' else '⬇️ SELL'}\n" \
             f"<b>Confidence:</b> {confidence:.2f}\n" \
             f"<b>Price:</b> ${price:.2f}\n" \
             f"<b>Time:</b> {timestamp}"
    
    return send_telegram_message(message)

def send_trade_execution_alert(contract, side, quantity, status):
    """
    Send a formatted trade execution message
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    message = f"🔄 <b>TRADE EXECUTED</b>\n\n" \
             f"<b>Contract:</b> {contract}\n" \
             f"<b>Action:</b> {'BUY' if side.lower() == 'buy' else 'SELL'}\n" \
             f"<b>Quantity:</b> {quantity}\n" \
             f"<b>Status:</b> {status}\n" \
             f"<b>Time:</b> {timestamp}"
    
    return send_telegram_message(message)
