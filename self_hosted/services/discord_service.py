import os
import logging
import asyncio
import discord
from discord.ext import commands
import threading
from datetime import datetime

logger = logging.getLogger(__name__)

class DiscordService:
    """Service for sending alerts to Discord"""
    
    def __init__(self):
        """Initialize the Discord bot client"""
        self.token = os.environ.get('DISCORD_TOKEN')
        self.channel_id = os.environ.get('DISCORD_CHANNEL_ID')
        
        if not self.token or not self.channel_id:
            logger.warning("Discord credentials not found. Discord alerts are disabled.")
            self.enabled = False
            return
            
        self.enabled = True
        self.bot = commands.Bot(command_prefix='!', intents=discord.Intents.default())
        self.bot_thread = None
        self.client_ready = False
        
        # Set up bot events
        @self.bot.event
        async def on_ready():
            logger.info(f'Discord Bot logged in as {self.bot.user}')
            self.client_ready = True
        
        # Start the bot in a separate thread
        self.start_bot()
    
    def start_bot(self):
        """Start the Discord bot in a separate thread"""
        if not self.enabled:
            return
            
        def run_bot():
            asyncio.set_event_loop(asyncio.new_event_loop())
            self.bot.run(self.token, log_handler=None)
        
        self.bot_thread = threading.Thread(target=run_bot)
        self.bot_thread.daemon = True
        self.bot_thread.start()
        logger.info("Discord bot thread started")
    
    async def _send_message(self, channel, content=None, embed=None):
        """Send a message to a specific channel"""
        if content:
            await channel.send(content=content)
        if embed:
            await channel.send(embed=embed)
    
    def send_signal_alert(self, signal):
        """
        Send a signal alert to Discord
        
        Args:
            signal (dict): Signal data including symbol, direction, confidence, etc.
        """
        if not self.enabled or not self.client_ready:
            logger.warning("Discord bot not ready. Signal alert not sent.")
            return False
        
        try:
            # Create an embed for the signal
            embed = discord.Embed(
                title=f"OG Strategy Signal: {signal['symbol']}",
                description=f"New {signal['direction']} signal detected",
                color=discord.Color.red() if signal['direction'] == 'BEARISH' else discord.Color.green(),
                timestamp=datetime.now()
            )
            
            # Add signal details
            embed.add_field(name="Symbol", value=signal['symbol'], inline=True)
            embed.add_field(name="Direction", value=signal['direction'], inline=True)
            embed.add_field(name="Confidence", value=f"{signal['confidence']:.2f}", inline=True)
            embed.add_field(name="Price", value=f"${signal['price_at_signal']:.2f}", inline=True)
            
            # Add timeframe and strategy if available
            if 'indicators' in signal and signal['indicators']:
                indicators = signal['indicators']
                if isinstance(indicators, str):
                    import json
                    try:
                        indicators = json.loads(indicators)
                    except:
                        indicators = {}
                
                if isinstance(indicators, dict):
                    if 'timeframe' in indicators:
                        embed.add_field(name="Timeframe", value=indicators['timeframe'], inline=True)
                    if 'strategy' in indicators:
                        embed.add_field(name="Strategy", value=indicators['strategy'], inline=True)
                    if 'setup_type' in indicators:
                        embed.add_field(name="Setup", value=indicators['setup_type'], inline=True)
                    
                    # Add key levels if available
                    if 'key_levels' in indicators and isinstance(indicators['key_levels'], dict):
                        key_levels = indicators['key_levels']
                        levels_text = ""
                        if 'entry' in key_levels:
                            levels_text += f"Entry: ${key_levels['entry']:.2f}\n"
                        if 'stop' in key_levels:
                            levels_text += f"Stop: ${key_levels['stop']:.2f}\n"
                        if 'target1' in key_levels:
                            levels_text += f"Target 1: ${key_levels['target1']:.2f}\n"
                        if 'target2' in key_levels:
                            levels_text += f"Target 2: ${key_levels['target2']:.2f}\n"
                        
                        if levels_text:
                            embed.add_field(name="Key Levels", value=levels_text, inline=False)
            
            # Set footer
            embed.set_footer(text="OG Strategy Lab")
            
            # Send the embed
            channel = self.bot.get_channel(int(self.channel_id))
            if channel:
                asyncio.run_coroutine_threadsafe(
                    self._send_message(channel, embed=embed),
                    self.bot.loop
                )
                logger.info(f"Signal alert sent to Discord for {signal['symbol']}")
                return True
            else:
                logger.error(f"Discord channel not found: {self.channel_id}")
                return False
        except Exception as e:
            logger.error(f"Error sending signal alert to Discord: {e}")
            return False
    
    def send_message(self, message):
        """
        Send a simple text message to Discord
        
        Args:
            message (str): The message to send
        """
        if not self.enabled or not self.client_ready:
            logger.warning("Discord bot not ready. Message not sent.")
            return False
        
        try:
            channel = self.bot.get_channel(int(self.channel_id))
            if channel:
                asyncio.run_coroutine_threadsafe(
                    self._send_message(channel, content=message),
                    self.bot.loop
                )
                logger.info("Message sent to Discord")
                return True
            else:
                logger.error(f"Discord channel not found: {self.channel_id}")
                return False
        except Exception as e:
            logger.error(f"Error sending message to Discord: {e}")
            return False