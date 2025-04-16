import os
import logging
import alpaca_trade_api as tradeapi
from datetime import datetime

logger = logging.getLogger(__name__)

class AlpacaService:
    """Service for interacting with Alpaca for trading and market data"""
    
    def __init__(self):
        """Initialize Alpaca API client"""
        self.api_key = os.environ.get('ALPACA_API_KEY')
        self.api_secret = os.environ.get('ALPACA_SECRET_KEY')
        self.base_url = os.environ.get('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')
        
        if not self.api_key or not self.api_secret:
            logger.warning("Alpaca API credentials not found. Trading functionality is disabled.")
            self.enabled = False
            return
        
        try:
            self.api = tradeapi.REST(
                self.api_key,
                self.api_secret,
                self.base_url,
                api_version='v2'
            )
            self.enabled = True
            account = self.api.get_account()
            logger.info(f"Alpaca API initialized. Account status: {account.status}")
        except Exception as e:
            logger.error(f"Failed to initialize Alpaca API: {e}")
            self.enabled = False
    
    def get_account_info(self):
        """Get account information from Alpaca"""
        if not self.enabled:
            return {"error": "Alpaca API not enabled"}
        
        try:
            account = self.api.get_account()
            return {
                "id": account.id,
                "status": account.status,
                "currency": account.currency,
                "buying_power": float(account.buying_power),
                "cash": float(account.cash),
                "portfolio_value": float(account.portfolio_value),
                "pattern_day_trader": account.pattern_day_trader,
                "trading_blocked": account.trading_blocked,
                "trades_blocked": account.trades_blocked,
                "account_blocked": account.account_blocked
            }
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return {"error": str(e)}
    
    def get_positions(self):
        """Get current positions from Alpaca"""
        if not self.enabled:
            return {"error": "Alpaca API not enabled"}
        
        try:
            positions = self.api.list_positions()
            return [{
                "symbol": position.symbol,
                "qty": int(position.qty),
                "market_value": float(position.market_value),
                "avg_entry_price": float(position.avg_entry_price),
                "current_price": float(position.current_price),
                "unrealized_pl": float(position.unrealized_pl),
                "unrealized_plpc": float(position.unrealized_plpc),
                "side": "long" if int(position.qty) > 0 else "short"
            } for position in positions]
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return {"error": str(e)}
    
    def get_orders(self, status='all', limit=100):
        """Get orders from Alpaca"""
        if not self.enabled:
            return {"error": "Alpaca API not enabled"}
        
        try:
            orders = self.api.list_orders(status=status, limit=limit)
            return [{
                "id": order.id,
                "client_order_id": order.client_order_id,
                "symbol": order.symbol,
                "side": order.side,
                "qty": float(order.qty),
                "type": order.type,
                "time_in_force": order.time_in_force,
                "limit_price": float(order.limit_price) if order.limit_price else None,
                "stop_price": float(order.stop_price) if order.stop_price else None,
                "filled_qty": float(order.filled_qty),
                "status": order.status,
                "created_at": order.created_at.isoformat() if order.created_at else None,
                "filled_at": order.filled_at.isoformat() if order.filled_at else None,
                "expired_at": order.expired_at.isoformat() if order.expired_at else None,
                "canceled_at": order.canceled_at.isoformat() if order.canceled_at else None
            } for order in orders]
        except Exception as e:
            logger.error(f"Error getting orders: {e}")
            return {"error": str(e)}
    
    def place_order(self, symbol, qty, side, order_type='market', time_in_force='day', limit_price=None, stop_price=None):
        """
        Place an order with Alpaca
        
        Args:
            symbol (str): Stock symbol
            qty (int): Quantity to buy/sell
            side (str): 'buy' or 'sell'
            order_type (str): 'market', 'limit', 'stop', 'stop_limit'
            time_in_force (str): 'day', 'gtc', 'opg', 'cls', 'ioc', 'fok'
            limit_price (float): Limit price for limit orders
            stop_price (float): Stop price for stop orders
            
        Returns:
            dict: Order information or error message
        """
        if not self.enabled:
            return {"error": "Alpaca API not enabled"}
        
        try:
            # Generate a client order ID with timestamp
            client_order_id = f"og_signal_{symbol}_{side}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # Place the order
            order = self.api.submit_order(
                symbol=symbol,
                qty=qty,
                side=side,
                type=order_type,
                time_in_force=time_in_force,
                limit_price=limit_price,
                stop_price=stop_price,
                client_order_id=client_order_id
            )
            
            logger.info(f"Order placed: {symbol} {side} {qty} shares at {order_type}")
            
            # Return order information
            return {
                "id": order.id,
                "client_order_id": order.client_order_id,
                "symbol": order.symbol,
                "side": order.side,
                "qty": float(order.qty),
                "type": order.type,
                "time_in_force": order.time_in_force,
                "limit_price": float(order.limit_price) if order.limit_price else None,
                "stop_price": float(order.stop_price) if order.stop_price else None,
                "status": order.status,
                "created_at": order.created_at.isoformat() if order.created_at else None
            }
            
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return {"error": str(e)}
    
    def get_current_price(self, symbol):
        """
        Get the current price of a symbol
        
        Args:
            symbol (str): Stock symbol
            
        Returns:
            float: Current price or None if error
        """
        if not self.enabled:
            return None
        
        try:
            # Get the latest trade
            barset = self.api.get_latest_trade(symbol)
            return float(barset.price)
        except Exception as e:
            logger.error(f"Error getting current price for {symbol}: {e}")
            return None
    
    def get_bars(self, symbol, timeframe='1D', limit=100):
        """
        Get price bars for a symbol
        
        Args:
            symbol (str): Stock symbol
            timeframe (str): Time period of each bar ('1Min', '5Min', '15Min', '1H', '1D')
            limit (int): Number of bars to retrieve
            
        Returns:
            list: List of bar data or empty list if error
        """
        if not self.enabled:
            return []
        
        try:
            # Get the bars
            bars = self.api.get_bars(symbol, timeframe, limit=limit)
            
            # Format the bars data
            return [{
                "symbol": bar.symbol,
                "timestamp": bar.t.isoformat(),
                "open": float(bar.o),
                "high": float(bar.h),
                "low": float(bar.l),
                "close": float(bar.c),
                "volume": int(bar.v)
            } for bar in bars]
        except Exception as e:
            logger.error(f"Error getting bars for {symbol}: {e}")
            return []