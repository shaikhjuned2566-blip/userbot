"""
Utility functions with environment variable support
"""

import asyncio
import random
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

async def random_delay(min_delay=None, max_delay=None, stop_flag=None):
    """
    Wait for a random delay with environment variable support
    """
    # Use environment variables if not specified
    if min_delay is None:
        min_delay = float(os.getenv('MIN_COOLDOWN', '1.0'))
    if max_delay is None:
        max_delay = float(os.getenv('MAX_COOLDOWN', '3.0'))
    
    cooldown = random.uniform(min_delay, max_delay)
    wait_time = 0
    
    while wait_time < cooldown:
        if stop_flag and stop_flag():
            return False
        await asyncio.sleep(0.1)
        wait_time += 0.1
    
    return True

def is_admin(user_id, admin_ids=None, bot_id=None):
    """Check if user is admin or bot itself"""
    if admin_ids is None:
        # Load admin IDs from environment
        admin_ids_str = os.getenv('TELEGRAM_ADMIN_IDS', '')
        admin_ids = [int(id.strip()) for id in admin_ids_str.split(',') if id.strip().isdigit()]
    
    return user_id in admin_ids or (bot_id is not None and user_id == bot_id)

def get_env_int(key, default):
    """Get integer from environment variable"""
    value = os.getenv(key)
    if value and value.isdigit():
        return int(value)
    return default

def get_env_float(key, default):
    """Get float from environment variable"""
    value = os.getenv(key)
    if value:
        try:
            return float(value)
        except ValueError:
            pass
    return default

def get_env_bool(key, default=False):
    """Get boolean from environment variable"""
    value = os.getenv(key, str(default))
    return value.lower() in ('true', 'yes', '1', 'on', 'y')

def get_admin_ids():
    """Get admin IDs from environment variable"""
    admin_ids_str = os.getenv('TELEGRAM_ADMIN_IDS', '')
    if admin_ids_str:
        return [int(id.strip()) for id in admin_ids_str.split(',') if id.strip().isdigit()]
    return []