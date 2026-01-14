"""
Configuration file with environment variable support
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Telegram API credentials from environment variables
API_ID = int(os.getenv('TELEGRAM_API_ID', '12345678'))
API_HASH = os.getenv('TELEGRAM_API_HASH', '')
SESSION_STRING = os.getenv('TELEGRAM_SESSION_STRING', '')

# Admin user IDs from environment variable (comma-separated)
admin_ids_str = os.getenv('TELEGRAM_ADMIN_IDS', '')
if admin_ids_str:
    ADMIN_IDS = [int(id.strip()) for id in admin_ids_str.split(',') if id.strip().isdigit()]
else:
    ADMIN_IDS = []  # Will be validated in bot.py

# Bot settings
DOWNLOAD_DIR = os.getenv('DOWNLOAD_DIR', 'downloads')

# Cooldown settings
MIN_COOLDOWN = float(os.getenv('MIN_COOLDOWN', '1.0'))
MAX_COOLDOWN = float(os.getenv('MAX_COOLDOWN', '3.0'))

# Spam settings
DEFAULT_SPAM_COUNT = int(os.getenv('DEFAULT_SPAM_COUNT', '100'))
MAX_SPAM_COUNT = int(os.getenv('MAX_SPAM_COUNT', '1000'))

# Command execution settings
ALLOW_PARALLEL_COMMANDS = os.getenv('ALLOW_PARALLEL_COMMANDS', 'False').lower() == 'true'

# Debug settings
DEBUG_MODE = os.getenv('DEBUG_MODE', 'False').lower() == 'true'

# Logging settings
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Validation function
def validate_config():
    """Validate configuration and return any errors"""
    errors = []
    
    if API_ID == 12345678:
        errors.append("API_ID is not set or is using default value")
    
    if not API_HASH:
        errors.append("API_HASH is not set")
    
    if not SESSION_STRING:
        errors.append("SESSION_STRING is not set")
    
    if not ADMIN_IDS:
        errors.append("ADMIN_IDS is not set or invalid")
    
    if MIN_COOLDOWN < 0.5:
        errors.append("MIN_COOLDOWN is too low (minimum 0.5 seconds)")
    
    if MAX_SPAM_COUNT > 5000:
        errors.append("MAX_SPAM_COUNT is too high (maximum 5000)")
    
    return errors