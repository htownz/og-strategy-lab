"""
Market Data Service - Fetches real-time market data for the OG Strategy Matcher
Supports multiple data providers with Alpaca as the primary source
"""

import os
import time
import logging
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import threading
import requests
import pandas as pd

# Try importing Alpaca, but continue with mock data if not available
try:
    import alpaca_trade_api as alpaca
    from alpaca_trade_api.rest import REST
    from alpaca_trade_api.stream import Stream
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False

logger = logging.getLogger(__name__)

class MarketDataService:
    """
    Provides real-time and historical market data for the OG Strategy Matcher.
    Primary data source is Alpaca, with options to use alternative providers.
    """
    
    def __init__(self):
        """Initialize the market data service with configuration"""
        self.alpaca_api = None
        self.alpaca_stream = None
        self.api_key = os.environ.get('ALPACA_API_KEY')
        self.api_secret = os.environ.get('ALPACA_API_SECRET')
        self.base_url = os.environ.get('ALPACA_API_BASE_URL', 'https://paper-api.alpaca.markets')
        self.data_url = os.environ.get('ALPACA_DATA_URL', 'https://data.alpaca.markets')
        
        # Cache for market data
        self.price_cache = {}
        self.candle_cache = {}
        self.last_updated = {}
        self.watchlist = []
        
        # Initialize Alpaca if credentials are available
        if self.api_key and self.api_secret and ALPACA_AVAILABLE:
            try:
                self.alpaca_api = REST(
                    key_id=self.api_key,
                    secret_key=self.api_secret,
                    base_url=self.base_url,
                    data_url=self.data_url
                )
                logger.info("Alpaca API initialized successfully")
                
                # Initialize Alpaca stream
                self.alpaca_stream = Stream(
                    key_id=self.api_key,
                    secret_key=self.api_secret,
                    base_url=self.base_url,
                    data_feed='iex'  # Use IEX for real-time data
                )
                
            except Exception as e:
                logger.error(f"Error initializing Alpaca API: {str(e)}")
                self.alpaca_api = None
        else:
            logger.warning("Alpaca API credentials not found. Using demo mode.")
    
    def is_market_open(self) -> bool:
        """Check if the market is currently open"""
        if not self.alpaca_api:
            # If no Alpaca API, assume market is open during regular hours
            now = datetime.now().time()
            return (
                datetime.now().weekday() < 5 and  # Monday to Friday
                (now >= datetime.strptime("09:30", "%H:%M").time() and
                 now <= datetime.strptime("16:00", "%H:%M").time())
            )
        
        try:
            clock = self.alpaca_api.get_clock()
            return clock.is_open
        except Exception as e:
            logger.error(f"Error checking market status: {str(e)}")
            return False
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Get the current price for a symbol
        
        Args:
            symbol: The stock symbol (e.g., 'AAPL')
            
        Returns:
            Current price as a float, or None if unavailable
        """
        # Check cache first (if recent)
        if symbol in self.price_cache:
            last_update = self.last_updated.get(symbol, datetime.min)
            if (datetime.now() - last_update).seconds < 60:  # Cache for 60 seconds
                return self.price_cache[symbol]
        
        # If Alpaca API is available, use it
        if self.alpaca_api:
            try:
                # Get latest trade
                latest_trade = self.alpaca_api.get_latest_trade(symbol)
                price = latest_trade.price
                
                # Update cache
                self.price_cache[symbol] = price
                self.last_updated[symbol] = datetime.now()
                
                return price
            except Exception as e:
                logger.error(f"Error getting current price for {symbol}: {str(e)}")
        
        # Fallback to example prices for common symbols
        fallback_prices = {
            'SPY': 450.25,
            'QQQ': 370.50,
            'AAPL': 175.30,
            'MSFT': 340.20,
            'GOOGL': 2950.75,
            'AMZN': 145.30,
            'TSLA': 912.45,
            'AMD': 95.20,
            'NVDA': 320.80,
        }
        
        if symbol in fallback_prices:
            logger.warning(f"Using fallback price data for {symbol}")
            return fallback_prices[symbol]
        
        # For other symbols, generate a reasonable price
        import random
        base_price = 100.0
        variation = random.uniform(-20, 20)
        simulated_price = base_price + variation
        
        logger.warning(f"Using simulated price for {symbol}: {simulated_price}")
        return simulated_price
    
    def get_bars(self, symbol: str, timeframe: str = '1D', limit: int = 100) -> Optional[List[Dict[str, Any]]]:
        """
        Get price bars/candles for a symbol
        
        Args:
            symbol: The stock symbol
            timeframe: Time period for each bar ('1Min', '5Min', '15Min', '1H', '1D', etc.)
            limit: Maximum number of bars to retrieve
            
        Returns:
            List of bar data dictionaries, or None if unavailable
        """
        cache_key = f"{symbol}_{timeframe}_{limit}"
        
        # Check cache first (if recent)
        if cache_key in self.candle_cache:
            last_update = self.last_updated.get(cache_key, datetime.min)
            if (datetime.now() - last_update).seconds < 300:  # Cache for 5 minutes
                return self.candle_cache[cache_key]
        
        # If Alpaca API is available, use it
        if self.alpaca_api:
            try:
                # Get bars from Alpaca
                bars = self.alpaca_api.get_bars(
                    symbol,
                    timeframe,
                    limit=limit
                ).df.reset_index()
                
                # Convert to list of dictionaries
                bars_list = []
                for _, row in bars.iterrows():
                    bar_dict = {
                        'timestamp': row['timestamp'].isoformat(),
                        'open': float(row['open']),
                        'high': float(row['high']),
                        'low': float(row['low']),
                        'close': float(row['close']),
                        'volume': int(row['volume'])
                    }
                    bars_list.append(bar_dict)
                
                # Update cache
                self.candle_cache[cache_key] = bars_list
                self.last_updated[cache_key] = datetime.now()
                
                return bars_list
            except Exception as e:
                logger.error(f"Error getting bars for {symbol}: {str(e)}")
        
        # If no Alpaca or error occurred, generate simulated data
        logger.warning(f"Using simulated bar data for {symbol}")
        return self._generate_simulated_bars(symbol, limit)
    
    def get_prev_close(self, symbol: str) -> Optional[float]:
        """
        Get the previous day's closing price for a symbol
        
        Args:
            symbol: The stock symbol (e.g., 'AAPL')
            
        Returns:
            Previous closing price as a float, or None if unavailable
        """
        # If Alpaca API is available, use it to get historical data
        if self.alpaca_api:
            try:
                # Get yesterday's bar
                yesterday = datetime.now() - timedelta(days=1)
                bars = self.alpaca_api.get_bars(
                    symbol,
                    "1D",
                    start=yesterday.strftime('%Y-%m-%d'),
                    end=datetime.now().strftime('%Y-%m-%d'),
                    limit=1
                ).df
                
                if not bars.empty:
                    return float(bars.iloc[0]['close'])
            except Exception as e:
                logger.error(f"Error getting previous close for {symbol}: {str(e)}")
        
        # Otherwise get bars and use most recent close
        bars = self.get_bars(symbol, timeframe='1D', limit=2)
        if bars and len(bars) > 1:
            return bars[-2]['close']
        
        # Fallback to current price -1%
        current_price = self.get_current_price(symbol)
        if current_price:
            return current_price * 0.99
            
        return None
        
    def get_options_chain(self, symbol: str, expiration_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Get options chain data for a symbol
        
        In production, this would call Alpaca or another provider's API.
        For demo, we'll return structured example data.
        
        Args:
            symbol: The stock symbol
            expiration_date: Optional specific expiration date in YYYY-MM-DD format
            
        Returns:
            Dictionary with options chain data
        """
        # In a real implementation, this would make API calls to Alpaca or Barchart
        # For now, we'll call the existing options_analyzer code
        from options_analyzer import get_options_chain as existing_get_options_chain
        return existing_get_options_chain(symbol, expiration_date)
    
    def start_streaming(self, symbols: List[str], callback=None):
        """
        Start streaming real-time data for the given symbols
        
        Args:
            symbols: List of stock symbols to stream
            callback: Function to call with updates
        """
        if not self.alpaca_stream:
            logger.warning("Alpaca streaming not available")
            return False
        
        try:
            # Define handlers for streaming data
            async def trade_callback(trade):
                symbol = trade.symbol
                price = trade.price
                
                # Update cache
                self.price_cache[symbol] = price
                self.last_updated[symbol] = datetime.now()
                
                # Call user callback if provided
                if callback:
                    callback('trade', symbol, price)
            
            # Subscribe to trades for the specified symbols
            for symbol in symbols:
                self.alpaca_stream.subscribe_trades(trade_callback, symbol)
            
            # Start the stream in a separate thread
            threading.Thread(target=self.alpaca_stream.run, daemon=True).start()
            logger.info(f"Started streaming for symbols: {', '.join(symbols)}")
            return True
            
        except Exception as e:
            logger.error(f"Error starting Alpaca stream: {str(e)}")
            return False
    
    def _generate_simulated_bars(self, symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Generate simulated bar data for demo purposes"""
        import random
        
        # Get a base price for the symbol
        base_price = self.get_current_price(symbol) or 100.0
        
        # Generate bars with reasonable price movements
        bars = []
        current_price = base_price * 0.9  # Start 10% below current price
        
        # Get a random trend bias (-0.1 to 0.1)
        trend = random.uniform(-0.1, 0.1)
        
        for i in range(limit):
            # Calculate time (going backwards from now)
            timestamp = datetime.now() - timedelta(days=limit-i)
            
            # Random daily move (-2% to +2%) with slight trend bias
            daily_change = random.uniform(-0.02, 0.02) + trend
            
            # Calculate OHLC
            open_price = current_price
            close_price = open_price * (1 + daily_change)
            high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.01))
            low_price = min(open_price, close_price) * (1 - random.uniform(0, 0.01))
            
            # Random volume
            volume = int(random.uniform(100000, 5000000))
            
            # Add bar
            bar = {
                'timestamp': timestamp.isoformat(),
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'close': close_price,
                'volume': volume
            }
            bars.append(bar)
            
            # Set up for next bar
            current_price = close_price
        
        return bars
    
    def set_watchlist(self, symbols: List[str]):
        """Set the list of symbols to actively monitor"""
        self.watchlist = symbols
        
        # Start streaming for these symbols if possible
        if self.alpaca_api and self.alpaca_stream:
            self.start_streaming(symbols)
    
    def get_watchlist(self) -> List[str]:
        """Get the current watchlist"""
        return self.watchlist


# Singleton instance for the application to use
_market_data_service = None

def get_market_data_service() -> MarketDataService:
    """Get the singleton market data service instance"""
    global _market_data_service
    if _market_data_service is None:
        _market_data_service = MarketDataService()
    return _market_data_service


def get_historical_data(symbol: str, start_date: str, end_date: str, timeframe: str = '1D') -> pd.DataFrame:
    """
    Get historical market data for backtesting
    
    Args:
        symbol: The stock symbol
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        timeframe: Data timeframe (1D, 1H, etc.)
        
    Returns:
        Pandas DataFrame with historical data
    """
    
    service = get_market_data_service()
    
    # If Alpaca API is available, use it
    if service.alpaca_api:
        try:
            # Get historical data from Alpaca
            df = service.alpaca_api.get_bars(
                symbol,
                timeframe,
                start=start_date,
                end=end_date,
                adjustment='all'  # Adjust for splits, dividends, etc.
            ).df
            
            if not df.empty:
                return df
        except Exception as e:
            logger.error(f"Error getting historical data for {symbol}: {str(e)}")
    
    # Fallback to simulated data
    logger.warning(f"Using simulated historical data for {symbol}")
    
    # Convert dates to datetime
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    
    # Determine number of periods based on timeframe
    if timeframe == '1D':
        # Calculate business days between dates
        num_days = (end - start).days
        business_days = num_days - (num_days // 7) * 2  # Rough approximation
        periods = max(business_days, 1)
    elif timeframe == '1H':
        # Trading hours per day: about 6.5 hours (9:30 AM - 4:00 PM)
        periods = (end - start).days * 6
    else:
        # Default to 100 periods
        periods = 100
        
    # Generate simulated data
    bars = service._generate_simulated_bars(symbol, periods)
    
    # Convert to DataFrame
    df = pd.DataFrame(bars)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.set_index('timestamp')
    
    return df