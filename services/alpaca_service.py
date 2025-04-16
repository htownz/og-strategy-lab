# alpaca_service.py

import os
import logging
import time
from datetime import datetime, timedelta
import json
import alpaca_trade_api as tradeapi
from alpaca_trade_api.rest import APIError

logger = logging.getLogger(__name__)

class AlpacaService:
    """
    Service for interacting with Alpaca API for market data and trading
    """
    
    def __init__(self):
        """Initialize Alpaca API client"""
        self.api_key = os.environ.get('ALPACA_API_KEY')
        self.api_secret = os.environ.get('ALPACA_API_SECRET')
        self.base_url = os.environ.get('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')
        
        self.api = None
        self.enabled = self.api_key is not None and self.api_secret is not None
        
        if self.enabled:
            self._initialize_api()
        else:
            logger.warning("Alpaca service disabled: Missing API credentials")
    
    def _initialize_api(self):
        """Initialize the Alpaca API client"""
        try:
            self.api = tradeapi.REST(
                key_id=self.api_key,
                secret_key=self.api_secret,
                base_url=self.base_url,
                api_version='v2'
            )
            logger.info(f"Initialized Alpaca API client with base URL: {self.base_url}")
        except Exception as e:
            logger.error(f"Failed to initialize Alpaca API client: {str(e)}")
            self.api = None
            self.enabled = False
    
    def get_account(self):
        """
        Get Alpaca account information
        
        Returns:
            Account object or None if error
