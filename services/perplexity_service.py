"""
Perplexity API Integration Service for OG Signal Bot

This module provides integration with Perplexity's API for enhanced market data,
research capabilities, and AI-powered trade opportunity identification.

Key features:
- Real-time market research and news analysis
- Comprehensive ticker analysis with market sentiment extraction
- Pattern recognition for OG strategy components
- Multi-source data aggregation for higher confidence signals
"""

import os
import requests
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any

# Set up logging
logger = logging.getLogger(__name__)

# API configuration
PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY", "")
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"

# Define available models
PERPLEXITY_MODELS = {
    "small": "llama-3.1-sonar-small-128k-online",  # Default
    "large": "llama-3.1-sonar-large-128k-online",
    "huge": "llama-3.1-sonar-huge-128k-online"
}

# Default model selection
DEFAULT_MODEL = PERPLEXITY_MODELS["small"]

class PerplexityService:
    """Service for interacting with Perplexity API to enhance market data analysis"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Perplexity service
        
        Args:
            api_key: Optional API key (falls back to environment variable)
        """
        self.api_key = api_key or PERPLEXITY_API_KEY
        self.api_url = PERPLEXITY_API_URL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Cache for storing recent responses (to avoid duplicate API calls)
        self.cache = {}
        self.cache_ttl = 300  # seconds (5 minutes)
        
        # Check if API key is available
        if not self.api_key:
            logger.warning("Perplexity API key not found. Functionality will be limited.")
            self.available = False
        else:
            self.available = True
    
    def query(self, 
              prompt: str, 
              system_message: Optional[str] = None,
              model: str = DEFAULT_MODEL,
              max_tokens: Optional[int] = None,
              temperature: float = 0.2,
              top_p: float = 0.9,
              search_domain_filter: Optional[List[str]] = None,
              search_recency_filter: str = "month",
              return_sources: bool = True,
              cache_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a query to Perplexity API
        
        Args:
            prompt: The primary question or request
            system_message: Optional system message for context
            model: Model to use (defaults to small)
            max_tokens: Maximum tokens to generate
            temperature: Creativity setting (0.0-1.0)
            top_p: Nucleus sampling parameter
            search_domain_filter: Optional domain restrictions
            search_recency_filter: Time period for search results
            return_sources: Whether to include citation sources
            cache_key: Optional cache key for caching responses
            
        Returns:
            Response dictionary with data and metadata
        """
        if not self.available:
            logger.warning("Perplexity API not available - API key missing")
            return {
                "error": "API key not available",
                "content": None,
                "sources": [],
                "usage": None
            }
        
        # Check cache if a cache key is provided
        if cache_key:
            cached_response = self._check_cache(cache_key)
            if cached_response:
                logger.info(f"Retrieved response from cache for key: {cache_key}")
                return cached_response
        
        # Prepare messages
        messages = []
        if system_message:
            messages.append({
                "role": "system",
                "content": system_message
            })
        
        messages.append({
            "role": "user", 
            "content": prompt
        })
        
        # Prepare request data
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "search_recency_filter": search_recency_filter,
            "return_images": False,
            "return_related_questions": False,
            "frequency_penalty": 1
        }
        
        # Add optional parameters
        if max_tokens:
            payload["max_tokens"] = max_tokens
            
        if search_domain_filter:
            payload["search_domain_filter"] = search_domain_filter
            
        # Make API request
        try:
            logger.info(f"Sending query to Perplexity API: {prompt[:100]}...")
            response = requests.post(
                self.api_url,
                headers=self.headers,
                data=json.dumps(payload)
            )
            
            # Handle response
            if response.status_code == 200:
                data = response.json()
                result = {
                    "content": data["choices"][0]["message"]["content"],
                    "sources": data.get("citations", []),
                    "usage": data.get("usage", {}),
                    "model": data.get("model", model)
                }
                
                # Cache the result if a cache key was provided
                if cache_key:
                    self._cache_response(cache_key, result)
                    
                return result
            else:
                logger.error(f"Perplexity API error: {response.status_code} - {response.text}")
                return {
                    "error": f"API error: {response.status_code}",
                    "content": None,
                    "sources": [],
                    "usage": None
                }
                
        except Exception as e:
            logger.error(f"Error querying Perplexity API: {str(e)}")
            return {
                "error": str(e),
                "content": None,
                "sources": [],
                "usage": None
            }
    
    def _check_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """Check if a valid cache entry exists for the given key"""
        if key in self.cache:
            timestamp, data = self.cache[key]
            if datetime.now() - timestamp < timedelta(seconds=self.cache_ttl):
                return data
            else:
                # Clean up expired entry
                del self.cache[key]
        return None
    
    def _cache_response(self, key: str, data: Dict[str, Any]) -> None:
        """Cache a response with the current timestamp"""
        self.cache[key] = (datetime.now(), data)
        
    def clean_cache(self) -> None:
        """Clean expired entries from the cache"""
        now = datetime.now()
        expired_keys = [
            key for key, (timestamp, _) in self.cache.items()
            if now - timestamp >= timedelta(seconds=self.cache_ttl)
        ]
        for key in expired_keys:
            del self.cache[key]
            
    # Specialized market data and analysis methods
    
    def analyze_ticker(self, 
                        ticker: str, 
                        include_news: bool = True,
                        technical_analysis: bool = True,
                        og_pattern_focus: bool = True) -> Dict[str, Any]:
        """
        Perform comprehensive analysis of a ticker using Perplexity
        
        Args:
            ticker: Stock symbol to analyze
            include_news: Include recent news analysis
            technical_analysis: Include technical analysis
            og_pattern_focus: Focus on OG strategy pattern components
            
        Returns:
            Comprehensive analysis result
        """
        # Build an appropriate system message to guide the model
        system_message = (
            "You are a professional market analyst specializing in options trading and the OG Strategy "
            "which involves EMA Cloud, Order Blocks (OB), Fair Value Gaps (FVG), and volume analysis. "
            "Provide factual, data-backed analysis with specific price levels and indicators. "
            "Analyze current market conditions, price action, and relevant news catalysts. "
            "Identify key support/resistance levels, potential entry/exit points, and risk factors."
        )
        
        # Build the prompt based on requirements
        prompt_components = [
            f"Analyze {ticker} for trading opportunities with the following focus:",
            "1. Current price, market cap, and recent price action",
        ]
        
        if technical_analysis:
            prompt_components.extend([
                "2. Key technical indicators (RSI, MACD, moving averages)",
                "3. Support and resistance levels with specific price targets"
            ])
            
        if og_pattern_focus:
            prompt_components.extend([
                "4. OG Strategy pattern analysis:",
                "   - EMA Cloud setup and alignment",
                "   - Presence of Order Blocks (OB) near current price",
                "   - Fair Value Gaps (FVG) identification",
                "   - Volume pattern confirmation",
                "5. Probability of successful OG pattern formation in the next 1-3 days"
            ])
            
        if include_news:
            prompt_components.extend([
                "6. Recent news catalysts and their impact",
                "7. Unusual options activity or institutional positioning"
            ])
            
        prompt_components.append(
            "8. CONCLUSION: Provide a clear trading opportunity assessment with specific entry, stop, and target levels if appropriate."
        )
        
        # Combine into final prompt
        prompt = "\n".join(prompt_components)
        
        # Use the ticker as cache key for this analysis
        cache_key = f"ticker_analysis_{ticker}_{datetime.now().strftime('%Y-%m-%d')}"
        
        # Query the API
        return self.query(
            prompt=prompt,
            system_message=system_message,
            model=PERPLEXITY_MODELS["large"],  # Use larger model for better analysis
            search_recency_filter="day",  # Use very recent data
            cache_key=cache_key,
            temperature=0.1  # Lower temperature for more factual responses
        )
    
    def find_og_patterns(self, 
                         watchlist: List[str], 
                         timeframe: str = "1D") -> Dict[str, Any]:
        """
        Scan a watchlist for potential OG strategy setups
        
        Args:
            watchlist: List of ticker symbols to scan
            timeframe: Timeframe for analysis (e.g., "1D", "4H", "1H")
            
        Returns:
            Dictionary with potential OG pattern matches
        """
        system_message = (
            "You are an expert options trading system focused on the OG Strategy pattern recognition. "
            "The OG Strategy looks for specific setups combining: "
            "1. EMA Cloud alignment (8/21 EMA crossovers) "
            "2. Order Blocks (OB) - significant buying/selling zones "
            "3. Fair Value Gaps (FVG) - unfilled price gaps "
            "4. Volume confirmation "
            "For each ticker, assess if it shows an emerging or complete OG pattern, providing a confidence score (0-100%) and specific price levels."
        )
        
        # Format the tickers into a comma-separated list
        tickers_list = ", ".join(watchlist)
        max_displayed = 15
        if len(watchlist) > max_displayed:
            tickers_display = ", ".join(watchlist[:max_displayed]) + f" and {len(watchlist) - max_displayed} more"
        else:
            tickers_display = tickers_list
        
        prompt = (
            f"Analyze the following tickers for OG Strategy pattern setups on the {timeframe} timeframe: {tickers_display}\n\n"
            f"For each ticker showing a potential setup, provide:\n"
            f"1. Pattern strength (0-100%)\n"
            f"2. Pattern direction (BULLISH/BEARISH)\n"
            f"3. Key levels (entry, stop, target)\n"
            f"4. Which components are present (EMA Cloud, OB, FVG, Volume)\n"
            f"5. Time sensitivity (how soon to act)\n\n"
            f"Format your response as a structured analysis with a SUMMARY section first listing the top 3-5 opportunities, "
            f"followed by DETAILS for each identified setup. Only include tickers with real potential."
        )
        
        # Create a unique cache key
        cache_key = f"og_scan_{timeframe}_{hash(tickers_list)}_{datetime.now().strftime('%Y-%m-%d_%H')}"
        
        return self.query(
            prompt=prompt,
            system_message=system_message,
            model=PERPLEXITY_MODELS["large"],
            search_recency_filter="day",
            cache_key=cache_key,
            temperature=0.2
        )
    
    def get_market_sentiment(self, tickers: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Get overall market sentiment and optionally sentiment for specific tickers
        
        Args:
            tickers: Optional list of specific tickers to analyze
            
        Returns:
            Market sentiment analysis
        """
        system_message = (
            "You are a market sentiment analysis system. Provide objective analysis of current market conditions "
            "based on key indices, recent market moves, economic data, fear/greed indicators, and news catalysts. "
            "Be precise and data-focused, avoiding speculation. Rate sentiment on a scale from -5 (extremely bearish) "
            "to +5 (extremely bullish) with clear justification."
        )
        
        if tickers:
            tickers_str = ", ".join(tickers)
            prompt = (
                f"Provide a comprehensive market sentiment analysis with specific focus on these tickers: {tickers_str}\n\n"
                f"Include:\n"
                f"1. Overall market sentiment (-5 to +5 scale) with explanation\n"
                f"2. Sector-specific sentiment\n"
                f"3. Individual sentiment ratings for each ticker in the list\n"
                f"4. Key market-moving events today\n"
                f"5. Options flow sentiment\n"
                f"6. Retail vs institutional positioning\n\n"
                f"Present your analysis in a structured format with clear sentiment scores and supporting data."
            )
        else:
            prompt = (
                "Provide a comprehensive market sentiment analysis.\n\n"
                "Include:\n"
                "1. Overall market sentiment (-5 to +5 scale) with explanation\n"
                "2. Major index performance today\n"
                "3. Sector-by-sector breakdown\n"
                "4. Key market-moving events\n"
                "5. Options market sentiment\n"
                "6. VIX and fear/greed indicators\n"
                "7. Institutional money flow\n\n"
                "Present your analysis in a structured format with clear sentiment scores and supporting data."
            )
        
        # Create a unique cache key that expires hourly
        cache_key = f"market_sentiment_{datetime.now().strftime('%Y-%m-%d_%H')}"
        if tickers:
            cache_key += f"_{hash(str(tickers))}"
        
        return self.query(
            prompt=prompt,
            system_message=system_message,
            model=PERPLEXITY_MODELS["large"],
            search_recency_filter="day",
            cache_key=cache_key,
            temperature=0.1  # Lower temperature for more consistent analysis
        )

    def extract_og_parameters(self, ticker: str) -> Dict[str, Any]:
        """
        Extract specific OG strategy parameters for a given ticker
        
        Args:
            ticker: Stock symbol to analyze
            
        Returns:
            Dictionary with extracted OG strategy parameters
        """
        system_message = (
            "You are a specialized parameter extraction system for the OG Strategy trading methodology. "
            "Extract precise numerical values and clear boolean indicators only. "
            "Format your response as a structured JSON object with the exact parameters needed to execute the strategy. "
            "Include entry price, stop loss, targets, confidence level (0-1), and component confirmations."
        )
        
        prompt = (
            f"Analyze {ticker} and extract precise OG Strategy parameters in JSON format.\n\n"
            f"Focus on determining these specific values:\n"
            f"1. Clear BULLISH or BEARISH direction\n"
            f"2. Exact entry price level\n"
            f"3. Exact stop loss level\n"
            f"4. Primary and secondary price targets\n"
            f"5. Component confirmations (true/false for each: ema_cloud, order_block, fvg, volume)\n"
            f"6. Confidence score as a decimal between 0 and 1\n"
            f"7. Recommended expiration timeframe for options\n"
            f"8. Optimal strike price based on the pattern\n\n"
            f"Format your response as a valid JSON object that can be directly parsed by a trading system."
        )
        
        # Use a shorter cache TTL for parameter extraction (1 hour)
        cache_key = f"og_params_{ticker}_{datetime.now().strftime('%Y-%m-%d_%H')}"
        
        result = self.query(
            prompt=prompt,
            system_message=system_message,
            model=PERPLEXITY_MODELS["large"],
            search_recency_filter="day",
            cache_key=cache_key,
            temperature=0.1
        )
        
        # Try to parse the JSON response
        try:
            if result.get("content"):
                content = result["content"]
                
                # Try to extract JSON if it's wrapped in markdown code blocks
                if "```json" in content and "```" in content.split("```json", 1)[1]:
                    json_str = content.split("```json", 1)[1].split("```", 1)[0].strip()
                elif "```" in content and "```" in content.split("```", 1)[1]:
                    json_str = content.split("```", 1)[1].split("```", 1)[0].strip()
                else:
                    json_str = content
                
                # Parse the JSON
                parameters = json.loads(json_str)
                
                # Add metadata from the response
                result["parsed_parameters"] = parameters
                
            return result
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse JSON response for {ticker}: {str(e)}")
            result["error"] = f"JSON parsing error: {str(e)}"
            return result

# Helper functions

def get_perplexity_service() -> PerplexityService:
    """Singleton accessor for the PerplexityService"""
    global _perplexity_service_instance
    if not _perplexity_service_instance:
        _perplexity_service_instance = PerplexityService()
    return _perplexity_service_instance

# Initialize singleton instance
_perplexity_service_instance = None