# alpaca_service.py

import os
import logging
import time
from datetime import datetime, timedelta
import pandas as pd
import alpaca_trade_api as tradeapi

logger = logging.getLogger(__name__)

class AlpacaService:
    """
    Service for interacting with Alpaca API to get market data and execute trades
    """
    
    def __init__(self):
        """Initialize Alpaca API client with API keys from environment"""
        self.api_key = os.environ.get('ALPACA_API_KEY')
        self.api_secret = os.environ.get('ALPACA_API_SECRET')
        self.base_url = os.environ.get('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')
        
        self.enabled = (self.api_key is not None and self.api_secret is not None)
        
        if not self.enabled:
            logger.warning("Alpaca service disabled: Missing API credentials")
            self.api = None
        else:
            try:
                self.api = tradeapi.REST(
                    self.api_key,
                    self.api_secret,
                    self.base_url,
                    api_version='v2'
                )
                logger.info(f"Alpaca API initialized, connected to {self.base_url}")
            except Exception as e:
                logger.error(f"Failed to initialize Alpaca API: {str(e)}")
                self.api = None
                self.enabled = False
    
    def get_account(self):
        """Get account information"""
        if not self.enabled:
            return None
        
        try:
            return self.api.get_account()
        except Exception as e:
            logger.error(f"Error getting account information: {str(e)}")
            return None
    
    def get_current_price(self, symbol):
        """Get current price for a symbol"""
        if not self.enabled:
            return None
        
        try:
            # Get the latest trade
            last_trade = self.api.get_latest_trade(symbol)
            return last_trade.price
        except Exception as e:
            logger.error(f"Error getting current price for {symbol}: {str(e)}")
            return None
    
    def get_bars(self, symbol, timeframe='1D', limit=100):
        """
        Get historical bars for a symbol
        
        Args:
            symbol: Asset symbol
            timeframe: Bar timeframe (1Min, 5Min, 15Min, 1H, 1D)
            limit: Maximum number of bars to return
            
        Returns:
            DataFrame with bar data or None on error
        """
        if not self.enabled:
            return None
        
        try:
            bars = self.api.get_bars(symbol, timeframe, limit=limit)
            return pd.DataFrame([bar._raw for bar in bars])
        except Exception as e:
            logger.error(f"Error getting bars for {symbol}: {str(e)}")
            return None
    
    def get_positions(self):
        """Get current positions"""
        if not self.enabled:
            return []
        
        try:
            positions = self.api.list_positions()
            return [position._raw for position in positions]
        except Exception as e:
            logger.error(f"Error getting positions: {str(e)}")
            return []
    
    def get_orders(self, status="all", limit=100):
        """Get orders"""
        if not self.enabled:
            return []
        
        try:
            orders = self.api.list_orders(status=status, limit=limit)
            return [order._raw for order in orders]
        except Exception as e:
            logger.error(f"Error getting orders: {str(e)}")
            return []
    
    def place_order(self, symbol, qty, side, order_type='market', time_in_force='day', limit_price=None):
        """
        Place an order
        
        Args:
            symbol: Asset symbol
            qty: Order quantity
            side: Order side ('buy' or 'sell')
            order_type: Order type ('market' or 'limit')
            time_in_force: Time in force ('day', 'gtc', 'ioc', 'fok')
            limit_price: Limit price (required for limit orders)
            
        Returns:
            Order object on success, None on error
        """
        if not self.enabled:
            logger.warning(f"Attempted to place order but Alpaca service is disabled")
            return None
        
        try:
            logger.info(f"Placing {order_type} order: {side} {qty} {symbol}")
            
            if order_type == 'limit' and limit_price is None:
                logger.error("Limit price is required for limit orders")
                return None
            
            order = self.api.submit_order(
                symbol=symbol,
                qty=qty,
                side=side,
                type=order_type,
                time_in_force=time_in_force,
                limit_price=limit_price
            )
            
            logger.info(f"Order placed successfully: {order.id}")
            return order._raw
        except Exception as e:
            logger.error(f"Error placing order: {str(e)}")
            return None
    
    def cancel_order(self, order_id):
        """Cancel an order by ID"""
        if not self.enabled:
            return False
        
        try:
            self.api.cancel_order(order_id)
            return True
        except Exception as e:
            logger.error(f"Error canceling order {order_id}: {str(e)}")
            return False
    
    def close_position(self, symbol):
        """Close a position for a symbol"""
        if not self.enabled:
            return False
        
        try:
            self.api.close_position(symbol)
            return True
        except Exception as e:
            logger.error(f"Error closing position for {symbol}: {str(e)}")
            return False
    
    def get_clock(self):
        """Get market clock"""
        if not self.enabled:
            return None
        
        try:
            return self.api.get_clock()
        except Exception as e:
            logger.error(f"Error getting market clock: {str(e)}")
            return None
    
    def get_market_status(self):
        """Get market status (open/closed)"""
        if not self.enabled:
            return {
                'is_open': False,
                'next_open': None,
                'next_close': None
            }
        
        try:
            clock = self.api.get_clock()
            return {
                'is_open': clock.is_open,
                'next_open': clock.next_open.isoformat(),
                'next_close': clock.next_close.isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting market status: {str(e)}")
            return {
                'is_open': False,
                'next_open': None,
                'next_close': None
            }
    
    def is_tradable(self, symbol):
        """Check if a symbol is tradable"""
        if not self.enabled:
            return False
        
        try:
            asset = self.api.get_asset(symbol)
            return asset.tradable
        except Exception as e:
            logger.error(f"Error checking if {symbol} is tradable: {str(e)}")
            return False

# Singleton instance
alpaca_service = None

def get_alpaca_service():
    """Get singleton instance of AlpacaService"""
    global alpaca_service
    
    if alpaca_service is None:
        alpaca_service = AlpacaService()
        
    return alpaca_service
