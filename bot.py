#!/usr/bin/env python3
"""
Telegram UserBot with environment variable support
"""

import asyncio
import logging
import os
import sys
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.sessions import StringSession

# Import modules
import config
from handlers import BotHandlers

# Load environment variables
load_dotenv()

class TelegramUserBot:
    def __init__(self):
        self.client = None
        self.handlers = None
        
    def setup_logging(self):
        """Configure logging from environment variables"""
        log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        log_format = os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # Map string level to logging constant
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        
        log_level = level_map.get(log_level, logging.INFO)
        
        logging.basicConfig(
            level=log_level,
            format=log_format
        )
        
        return logging.getLogger(__name__)
    
    def validate_and_display_config(self):
        """Validate configuration and display settings"""
        print("=" * 60)
        print("🔧 Telegram UserBot Configuration Check")
        print("=" * 60)
        
        # Check for .env file
        env_file = '.env'
        if os.path.exists(env_file):
            print(f"✅ Found environment file: {env_file}")
        else:
            print(f"⚠️  Warning: {env_file} file not found")
            print(f"   Create one from {env_file}.example")
        
        # Validate configuration
        errors = config.validate_config()
        
        if errors:
            print("❌ Configuration errors found:")
            for error in errors:
                print(f"   - {error}")
            print("=" * 60)
            return False
        
        # Display current configuration
        print("✅ Configuration loaded successfully!")
        print("\n📋 Current Settings:")
        print(f"   API ID: {'*' * 8 if config.API_ID != 12345678 else 'NOT SET'}")
        print(f"   API Hash: {'*' * 16 if config.API_HASH else 'NOT SET'}")
        print(f"   Session: {'*' * 20 if config.SESSION_STRING else 'NOT SET'}")
        print(f"   Admin IDs: {len(config.ADMIN_IDS)} admin(s)")
        print(f"   Cooldown: {config.MIN_COOLDOWN}-{config.MAX_COOLDOWN}s")
        print(f"   Max Spam: {config.MAX_SPAM_COUNT} messages")
        print(f"   Parallel Commands: {config.ALLOW_PARALLEL_COMMANDS}")
        print("=" * 60)
        
        return True
    
    async def start(self):
        """Start the bot"""
        logger = self.setup_logging()
        
        try:
            # Validate configuration
            if not self.validate_and_display_config():
                print("❌ Please fix configuration errors and try again")
                sys.exit(1)
            
            # Optional proxy configuration
            proxy = None
            proxy_str = os.getenv('TELEGRAM_PROXY')
            if proxy_str:
                print(f"🔗 Using proxy: {proxy_str}")
                # Parse proxy string (format: protocol://user:pass@host:port)
                proxy = proxy_str
            
            # Create client
            self.client = TelegramClient(
                StringSession(config.SESSION_STRING),
                config.API_ID,
                config.API_HASH,
                proxy=proxy
            )
            
            # Initialize handlers
            self.handlers = BotHandlers(self.client, config)
            
            # Start client
            await self.client.start()
            
            # Get bot's own ID
            me = await self.client.get_me()
            self.handlers.bot_id = me.id
            
            # Register event handlers
            self.handlers.register_handlers()
            
            # Create download directory
            os.makedirs(config.DOWNLOAD_DIR, exist_ok=True)
            
            # Display startup info
            self.display_startup_info(me)
            
            # Keep running
            await self.client.run_until_disconnected()
            
        except Exception as e:
            logger.error(f"❌ Failed to start bot: {e}")
            raise
    
    def display_startup_info(self, me):
        """Display startup information"""
        print("=" * 60)
        print("🚀 Telegram UserBot Started Successfully!")
        print("=" * 60)
        print(f"🤖 Logged in as: {me.first_name} (ID: {me.id})")
        print(f"📱 Phone: {me.phone}")
        print("=" * 60)
        print("📝 Available Commands:")
        print("  /ping          - Test if bot is working")
        print("  /id            - Get chat and user ID")
        print("  /stats         - Get group statistics")
        print("  /tagall [text] - Tag all members in group")
        print("  /spam[count] [text] - Spam messages")
        print("  /stoptag       - Stop ongoing tagging/spam")
        print("  /stopspam      - Stop ongoing spam/tagging")
        print("=" * 60)
        print("⚙️  Environment Settings:")
        print(f"  Cooldown: {config.MIN_COOLDOWN}-{config.MAX_COOLDOWN} seconds")
        print(f"  Max Spam: {config.MAX_SPAM_COUNT} messages")
        print(f"  Default Spam: {config.DEFAULT_SPAM_COUNT} messages")
        print(f"  Parallel Commands: {config.ALLOW_PARALLEL_COMMANDS}")
        print("=" * 60)
        print("🔒 Bot is running silently...")
        print("📊 Check terminal for logs")
        print("=" * 60)
    
    async def stop(self):
        """Stop the bot gracefully"""
        if self.client:
            await self.client.disconnect()
        print("\n🛑 Bot stopped gracefully")

def main():
    """Main entry point"""
    bot = TelegramUserBot()
    
    try:
        # Run bot
        asyncio.run(bot.start())
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        try:
            asyncio.run(bot.stop())
        except:
            pass

if __name__ == '__main__':
    main()