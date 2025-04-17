# signal_service.py

import os
import json
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from models import Signal, db

logger = logging.getLogger(__name__)

class SignalService:
    """
    Service for generating and processing trading signals
    """
    
    def __init__(self):
        """Initialize signal service"""
        self.signal_window = 14  # Number of days to look back for signals
        
        # Import services here to avoid circular imports
        from alpaca_service import get_alpaca_service
        from discord_service import get_discord_service
        
        self.alpaca = get_alpaca_service()
        self.discord = get_discord_service()
        
        logger.info("Signal service initialized")
        
    def generate_signal(self, symbol, direction, confidence, price, indicators=None, strategy_name=None, timeframe=None):
        """
        Generate a new trading signal
        
        Args:
            symbol: Asset symbol
            direction: Signal direction (BULLISH or BEARISH)
            confidence: Signal confidence (0.0 to 1.0)
            price: Asset price at signal time
            indicators: Dictionary of technical indicators
            strategy_name: Optional name of the strategy that generated this signal
            timeframe: Optional timeframe for the signal
            
        Returns:
            Created Signal object or None on error
        """
        try:
            # Create indicators JSON if provided
            indicators_json = indicators
            if indicators and isinstance(indicators, dict):
                indicators_json = indicators
            
            # Create new signal
            signal = Signal(
                symbol=symbol,
                direction=direction.upper(),
                confidence=float(confidence),
                price_at_signal=float(price),
                indicators=indicators_json,
                timestamp=datetime.utcnow(),
                strategy_name=strategy_name,
                timeframe=timeframe
            )
            
            # Save to database
            db.session.add(signal)
            db.session.commit()
            
            logger.info(f"Generated signal: {symbol} {direction} with confidence {confidence:.2f}")
            
            # Send to Discord if enabled
            if hasattr(self.discord, 'enabled') and self.discord.enabled:
                self.discord.send_signal(signal)
            
            # Broadcast via Socket.IO if available
            try:
                from socketio_service import get_socketio_service
                socketio_service = get_socketio_service()
                if socketio_service:
                    socketio_service.broadcast_signal(signal)
            except Exception as e:
                logger.warning(f"Could not broadcast signal via Socket.IO: {str(e)}")
            
            return signal
        except Exception as e:
            logger.error(f"Error generating signal: {str(e)}")
            db.session.rollback()
            return None
    
    def get_recent_signals(self, limit=20, symbol=None, direction=None, signal_id=None):
        """
        Get recent trading signals with optional filtering
        
        Args:
            limit: Maximum number of signals to return
            symbol: Optional filter by symbol
            direction: Optional filter by direction
            signal_id: Optional filter by signal ID
            
        Returns:
            List of Signal objects
        """
        try:
            query = Signal.query.order_by(Signal.timestamp.desc())
            
            if symbol:
                query = query.filter(Signal.symbol == symbol)
                
            if direction:
                query = query.filter(Signal.direction == direction.upper())
                
            if signal_id:
                query = query.filter(Signal.id == signal_id)
                
            return query.limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting recent signals: {str(e)}")
            return []
    
    def generate_og_signal(self, symbol, timeframe='1D', contract_type=None, expiry=None):
        """
        Generate an OG strategy signal for a symbol
        
        Args:
            symbol: Asset symbol
            timeframe: Chart timeframe (1D, 1H, etc.)
            contract_type: Optional option contract type (CALL or PUT)
            expiry: Optional option expiry date
            
        Returns:
            Generated Signal object or None on error
        """
        try:
            # Get market data from Alpaca
            if not hasattr(self.alpaca, 'enabled') or not self.alpaca.enabled:
                logger.error("Alpaca service is not configured, cannot generate OG signal")
                return None
            
            # Adjust timeframe for Alpaca API
            alpaca_timeframe = timeframe
            if timeframe == '1D':
                alpaca_timeframe = '1Day'
            elif timeframe == '1H':
                alpaca_timeframe = '1Hour'
            
            # Get bars
            bars = self.alpaca.get_bars(symbol, alpaca_timeframe, limit=50)
            if bars is None or len(bars) < 20:
                logger.error(f"Insufficient data for {symbol} to generate OG signal")
                return None
            
            # Convert to pandas DataFrame
            df = pd.DataFrame(bars)
            
            # Calculate EMAs
            df['ema8'] = df['close'].ewm(span=8, adjust=False).mean()
            df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
            
            # Detect EMA cloud setup
            df['ema_cloud'] = (df['ema8'] > df['ema21'])
            
            # Check for OG pattern
            # Simplified example - in a real system, you'd have more complex logic
            current_price = df['close'].iloc[-1]
            ema8 = df['ema8'].iloc[-1]
            ema21 = df['ema21'].iloc[-1]
            
            # BULLISH: Price above EMA8, EMA8 above EMA21, with increasing volume
            bullish = (current_price > ema8 and ema8 > ema21 and 
                       df['volume'].iloc[-1] > df['volume'].iloc[-2])
            
            # BEARISH: Price below EMA8, EMA8 below EMA21, with increasing volume
            bearish = (current_price < ema8 and ema8 < ema21 and 
                       df['volume'].iloc[-1] > df['volume'].iloc[-2])
            
            # Determine direction and confidence
            if bullish:
                direction = "BULLISH"
                confidence = 0.7  # Base confidence
                
                # Add more confidence based on volume and price action
                volume_ratio = df['volume'].iloc[-1] / df['volume'].iloc[-10:-1].mean()
                if volume_ratio > 1.5:
                    confidence += 0.1
                
                # Calculate key levels
                entry = current_price
                stop = min(df['low'].iloc[-5:])
                target1 = entry + (entry - stop)
                target2 = entry + 2 * (entry - stop)
                
                # Determine option contract details if provided
                contract = {}
                if contract_type and contract_type.upper() == 'CALL':
                    strike = np.ceil(current_price / 5) * 5  # Round to nearest $5 above
                    contract = {
                        'type': 'CALL',
                        'strike': float(strike)
                    }
                    if expiry:
                        contract['expiration'] = expiry
                
                # Create indicators dictionary
                indicators = {
                    'strategy': 'OG Strategy',
                    'timeframe': timeframe,
                    'technical_signals': {
                        'ema_cloud': True,
                        'ob_fvg': True,
                        'volume': True if volume_ratio > 1.2 else False,
                        'price_action': True
                    },
                    'key_levels': {
                        'entry': float(entry),
                        'stop': float(stop),
                        'target1': float(target1),
                        'target2': float(target2)
                    },
                    'setup_type': 'EMA + FVG + OB'
                }
                
                if contract:
                    indicators['contract'] = contract
                
                # Generate the signal
                return self.generate_signal(
                    symbol=symbol,
                    direction=direction,
                    confidence=confidence,
                    price=current_price,
                    indicators=indicators,
                    strategy_name="OG Strategy",
                    timeframe=timeframe
                )
                
            elif bearish:
                direction = "BEARISH"
                confidence = 0.7  # Base confidence
                
                # Add more confidence based on volume and price action
                volume_ratio = df['volume'].iloc[-1] / df['volume'].iloc[-10:-1].mean()
                if volume_ratio > 1.5:
                    confidence += 0.1
                
                # Calculate key levels
                entry = current_price
                stop = max(df['high'].iloc[-5:])
                target1 = entry - (stop - entry)
                target2 = entry - 2 * (stop - entry)
                
                # Determine option contract details if provided
                contract = {}
                if contract_type and contract_type.upper() == 'PUT':
                    strike = np.floor(current_price / 5) * 5  # Round to nearest $5 below
                    contract = {
                        'type': 'PUT',
                        'strike': float(strike)
                    }
                    if expiry:
                        contract['expiration'] = expiry
                
                # Create indicators dictionary
                indicators = {
                    'strategy': 'OG Strategy',
                    'timeframe': timeframe,
                    'technical_signals': {
                        'ema_cloud': True,
                        'ob_fvg': True,
                        'volume': True if volume_ratio > 1.2 else False,
                        'price_action': True
                    },
                    'key_levels': {
                        'entry': float(entry),
                        'stop': float(stop),
                        'target1': float(target1),
                        'target2': float(target2)
                    },
                    'setup_type': 'EMA + FVG + OB'
                }
                
                if contract:
                    indicators['contract'] = contract
                
                # Generate the signal
                return self.generate_signal(
                    symbol=symbol,
                    direction=direction,
                    confidence=confidence,
                    price=current_price,
                    indicators=indicators,
                    strategy_name="OG Strategy",
                    timeframe=timeframe
                )
            
            else:
                logger.info(f"No OG pattern detected for {symbol}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating OG signal for {symbol}: {str(e)}")
            return None
    
    def scan_watchlist(self, symbols, timeframe='1D'):
        """
        Scan a watchlist for OG strategy setups
        
        Args:
            symbols: List of symbols to scan
            timeframe: Chart timeframe
            
        Returns:
            Dictionary with scan results
        """
        results = {
            'timestamp': datetime.utcnow().isoformat(),
            'timeframe': timeframe,
            'total_symbols': len(symbols),
            'signals': [],
            'errors': []
        }
        
        for symbol in symbols:
            try:
                signal = self.generate_og_signal(symbol, timeframe)
                if signal:
                    results['signals'].append(signal.to_dict())
            except Exception as e:
                logger.error(f"Error scanning {symbol}: {str(e)}")
                results['errors'].append({
                    'symbol': symbol,
                    'error': str(e)
                })
        
        results['signals_found'] = len(results['signals'])
        results['errors_count'] = len(results['errors'])
        
        return results

# Singleton instance
signal_service = None

def get_signal_service():
    """Get singleton instance of SignalService"""
    global signal_service
    
    if signal_service is None:
        signal_service = SignalService()
        
    return signal_service
