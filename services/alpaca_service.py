# alpaca_service.py

import os
import logging
import json
import pandas as pd
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class AlpacaService:
    """
    Service for interacting with Alpaca API for both market data and trading
    """
    
    def __init__(self):
        """Initialize Alpaca service"""
        self.api = None
        self.enabled = False
        self.api_key = os.environ.get('ALPACA_API_KEY')
        self.api_secret = os.environ.get('ALPACA_API_SECRET')
        self.base_url = os.environ.get('ALPACA_API_BASE_URL', 'https://paper-api.alpaca.markets')
        self.data_url = os.environ.get('ALPACA_DATA_URL', 'https://data.alpaca.markets')
        self.paper_trading = self.base_url == 'https://paper-api.alpaca.markets'
        
        # Try to initialize the API
        self._initialize_api()
        
    def _initialize_api(self):
        """Initialize Alpaca API client"""
        try:
            if not self.api_key or not self.api_secret:
                logger.warning("Alpaca API credentials not found. Some features will be disabled.")
                self.enabled = False
                return
            
            # Import Alpaca API here to avoid issues if it's not installed
            import alpaca_trade_api as tradeapi
            
            # Initialize API
            self.api = tradeapi.REST(
                key_id=self.api_key,
                secret_key=self.api_secret,
                base_url=self.base_url,
                api_version='v2'
            )
            
            # Test connection
            account = self.api.get_account()
            
            # Set enabled flag
            self.enabled = True
            
            logger.info(f"Alpaca API initialized successfully. Paper trading: {self.paper_trading}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Alpaca API: {str(e)}")
            self.enabled = False
    
    def check_api_status(self):
        """Check the status of Alpaca API"""
        if not self.enabled:
            return {
                'status': 'disabled',
                'message': 'Alpaca API is not configured'
            }
        
        try:
            # Check account status
            account = self.api.get_account()
            
            return {
                'status': 'enabled',
                'message': 'Alpaca API is connected',
                'account': {
                    'id': account.id,
                    'status': account.status,
                    'equity': float(account.equity),
                    'cash': float(account.cash),
                    'buying_power': float(account.buying_power),
                    'paper_trading': self.paper_trading
                }
            }
        except Exception as e:
            logger.error(f"Failed to check Alpaca API status: {str(e)}")
            
            return {
                'status': 'error',
                'message': f"Failed to connect to Alpaca API: {str(e)}"
            }
    
    def get_account(self):
        """Get account information from Alpaca"""
        if not self.enabled:
            return None
        
        try:
            account = self.api.get_account()
            
            # Convert to dictionary for easier serialization
            return {
                'id': account.id,
                'status': account.status,
                'equity': float(account.equity),
                'cash': float(account.cash),
                'buying_power': float(account.buying_power),
                'pattern_day_trader': account.pattern_day_trader,
                'trading_blocked': account.trading_blocked,
                'paper_trading': self.paper_trading,
                'day_trades_remaining': int(account.daytrading_buying_power) / int(account.multiplier) / float(account.equity) * 100 if float(account.equity) > 0 else 0,
                'multiplier': float(account.multiplier),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get account information: {str(e)}")
            return None
    
    def get_market_status(self):
        """Get current market status from Alpaca"""
        if not self.enabled:
            return {
                'is_open': False,
                'message': 'Alpaca API not configured',
                'next_open': None,
                'next_close': None
            }
        
        try:
            clock = self.api.get_clock()
            
            # Convert to dictionary for easier serialization
            return {
                'is_open': clock.is_open,
                'timestamp': clock.timestamp.isoformat(),
                'next_open': clock.next_open.isoformat() if clock.next_open else None,
                'next_close': clock.next_close.isoformat() if clock.next_close else None
            }
        except Exception as e:
            logger.error(f"Failed to get market status: {str(e)}")
            
            return {
                'is_open': False,
                'message': f"Error getting market status: {str(e)}",
                'next_open': None,
                'next_close': None
            }
    
    def get_bars(self, symbol, timeframe='1Day', limit=100):
        """
        Get price bars for a symbol
        
        Args:
            symbol: Asset symbol
            timeframe: Bar timeframe (1Day, 1Hour, etc.)
            limit: Maximum number of bars to return
            
        Returns:
            List of bars or None on error
        """
        if not self.enabled:
            return None
        
        try:
            # Import directly here
            import alpaca_trade_api as tradeapi
            
            # Get bars from Alpaca
            bars = self.api.get_bars(
                symbol,
                timeframe,
                limit=limit
            ).df
            
            # Convert dataframe to list of dictionaries
            bars_list = []
            for index, row in bars.iterrows():
                bars_list.append({
                    'timestamp': index.isoformat(),
                    'open': float(row['open']),
                    'high': float(row['high']),
                    'low': float(row['low']),
                    'close': float(row['close']),
                    'volume': int(row['volume'])
                })
            
            return bars_list
        except Exception as e:
            logger.error(f"Failed to get bars for {symbol}: {str(e)}")
            return None
    
    def place_order(self, symbol, qty, side, order_type='market', time_in_force='day', limit_price=None):
        """
        Place an order with Alpaca
        
        Args:
            symbol: Asset symbol
            qty: Order quantity
            side: Order side (buy or sell)
            order_type: Order type (market, limit, etc.)
            time_in_force: Time in force (day, gtc, etc.)
            limit_price: Limit price for limit orders
            
        Returns:
            Order information or None on error
        """
        if not self.enabled:
            logger.error("Cannot place order, Alpaca API not configured")
            return None
        
        try:
            # Place order
            order = self.api.submit_order(
                symbol=symbol,
                qty=qty,
                side=side,
                type=order_type,
                time_in_force=time_in_force,
                limit_price=limit_price
            )
            
            logger.info(f"Placed {side} order for {qty} {symbol} shares at {limit_price if limit_price else 'market price'}")
            
            # Convert to dictionary
            return {
                'id': order.id,
                'client_order_id': order.client_order_id,
                'symbol': order.symbol,
                'side': order.side,
                'qty': float(order.qty),
                'filled_qty': float(order.filled_qty) if hasattr(order, 'filled_qty') else 0,
                'type': order.type,
                'limit_price': float(order.limit_price) if hasattr(order, 'limit_price') and order.limit_price else None,
                'status': order.status,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to place order for {symbol}: {str(e)}")
            return None
    
    def get_positions(self):
        """
        Get current positions from Alpaca
        
        Returns:
            List of positions or None on error
        """
        if not self.enabled:
            return None
        
        try:
            positions = self.api.list_positions()
            
            # Convert to list of dictionaries
            positions_list = []
            for pos in positions:
                positions_list.append({
                    'symbol': pos.symbol,
                    'qty': float(pos.qty),
                    'market_value': float(pos.market_value),
                    'cost_basis': float(pos.cost_basis),
                    'unrealized_pl': float(pos.unrealized_pl),
                    'unrealized_plpc': float(pos.unrealized_plpc),
                    'current_price': float(pos.current_price),
                    'avg_entry_price': float(pos.avg_entry_price),
                    'side': 'long' if float(pos.qty) > 0 else 'short',
                    'timestamp': datetime.now().isoformat()
                })
            
            return positions_list
        except Exception as e:
            logger.error(f"Failed to get positions: {str(e)}")
            return None
    
    def get_orders(self, status='all', limit=100):
        """
        Get orders from Alpaca
        
        Args:
            status: Order status (open, closed, all)
            limit: Maximum number of orders to return
            
        Returns:
            List of orders or None on error
        """
        if not self.enabled:
            return None
        
        try:
            if status == 'open':
                orders = self.api.list_orders(status='open', limit=limit)
            elif status == 'closed':
                orders = self.api.list_orders(status='closed', limit=limit)
            else:
                # Get both open and closed orders
                open_orders = self.api.list_orders(status='open', limit=limit)
                closed_orders = self.api.list_orders(status='closed', limit=limit)
                orders = open_orders + closed_orders
            
            # Convert to list of dictionaries
            orders_list = []
            for order in orders:
                order_dict = {
                    'id': order.id,
                    'client_order_id': order.client_order_id,
                    'symbol': order.symbol,
                    'side': order.side,
                    'qty': float(order.qty),
                    'type': order.type,
                    'status': order.status,
                    'created_at': order.created_at.isoformat(),
                    'filled_at': order.filled_at.isoformat() if hasattr(order, 'filled_at') and order.filled_at else None,
                    'filled_qty': float(order.filled_qty) if hasattr(order, 'filled_qty') else 0
                }
                
                if hasattr(order, 'limit_price') and order.limit_price:
                    order_dict['limit_price'] = float(order.limit_price)
                
                orders_list.append(order_dict)
            
            return orders_list
        except Exception as e:
            logger.error(f"Failed to get orders: {str(e)}")
            return None

# Singleton instance
alpaca_service = None

def get_alpaca_service():
    """Get singleton instance of AlpacaService"""
    global alpaca_service
    
    if alpaca_service is None:
        alpaca_service = AlpacaService()
        
    return alpaca_service
