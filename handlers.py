"""Event handlers for the bot"""

import asyncio
import logging
from telethon import events
from utils import random_delay, is_admin, get_env_bool
import os

logger = logging.getLogger(__name__)

class BotHandlers:
    def __init__(self, client, config=None):
        self.client = client
        self.config = config
        self.bot_id = None
        
        # Single command execution control
        self.is_command_active = False
        self.current_task = None
        self.stop_command = False
        self.active_command_type = None  # 'tagging' or 'spam'
        
        # Check if parallel commands are allowed from env
        self.allow_parallel_commands = get_env_bool('ALLOW_PARALLEL_COMMANDS', False)
        
        # Debug mode
        self.debug_mode = get_env_bool('DEBUG_MODE', False)
    
    def register_handlers(self):
        """Register all event handlers"""
        
        # Basic commands
        @self.client.on(events.NewMessage(pattern='/ping'))
        async def ping_handler(event):
            await self.handle_ping(event)
        
        @self.client.on(events.NewMessage(pattern='/id'))
        async def id_handler(event):
            await self.handle_id(event)
        
        @self.client.on(events.NewMessage(pattern='/stats'))
        async def stats_handler(event):
            await self.handle_stats(event)
        
        # Tagging commands
        @self.client.on(events.NewMessage(pattern=r'/tagall(?:\s+(.*))?'))
        async def tag_all_handler(event):
            await self.handle_tagall(event)
        
        # Stop commands
        @self.client.on(events.NewMessage(pattern=r'/(stoptag|stopspam)'))
        async def stop_command_handler(event):
            await self.handle_stop_command(event)
        
        # Spam commands
        @self.client.on(events.NewMessage(pattern=r'/spam(\d+)?(?:\s+(.*))?'))
        async def spam_handler(event):
            await self.handle_spam(event)
        
        # Debug: Log all messages
        if self.debug_mode:
            @self.client.on(events.NewMessage)
            async def debug_handler(event):
                if event.text:
                    logger.debug(f"DEBUG: Chat {event.chat_id} | User {event.sender_id} | Message: {event.text}")
    
    def log_debug(self, message):
        """Log debug message if debug mode is enabled"""
        if self.debug_mode:
            logger.debug(f"DEBUG: {message}")
    
    # Basic command handlers
    async def handle_ping(self, event):
        """Test if bot is working"""
        self.log_debug(f"Ping received from {event.sender_id}")
        if is_admin(event.sender_id, bot_id=self.bot_id):
            logger.info(f"Ping command received from {event.sender_id}")
            await event.delete()
    
    async def handle_id(self, event):
        """Get chat and user ID"""
        self.log_debug(f"ID command from {event.sender_id}")
        if is_admin(event.sender_id, bot_id=self.bot_id):
            logger.info(f"ID command - Chat: {event.chat_id}, User: {event.sender_id}")
            await event.delete()
    
    async def handle_stats(self, event):
        """Get group statistics"""
        self.log_debug(f"Stats command from {event.sender_id}")
        if not is_admin(event.sender_id, bot_id=self.bot_id):
            return
        
        try:
            await event.delete()
            
            total = 0
            bots = 0
            deleted = 0
            users = 0
            
            async for user in self.client.iter_participants(event.chat_id):
                total += 1
                if user.bot:
                    bots += 1
                elif user.deleted:
                    deleted += 1
                else:
                    users += 1
            
            logger.info(f"Stats - Chat: {event.chat_id}, Total: {total}, Users: {users}, Bots: {bots}, Deleted: {deleted}")
            
        except Exception as e:
            logger.error(f"Stats error: {e}")
    
    # Command status check
    def is_command_running(self, command_type=None):
        """
        Check if a command is currently running
        If command_type is specified, check if that specific command type is running
        """
        if not self.is_command_active:
            return False
        
        if not self.allow_parallel_commands and command_type and self.active_command_type != command_type:
            return False
        
        if not self.allow_parallel_commands:
            return True
        
        return False
    
    async def handle_tagall(self, event):
        """Tag all members in group"""
        self.log_debug(f"Tagall command received from {event.sender_id} in chat {event.chat_id}")
        
        try:
            # Check permissions
            if not is_admin(event.sender_id, bot_id=self.bot_id):
                self.log_debug(f"User {event.sender_id} is not admin")
                await event.delete()
                return
            
            # Check if group
            if not event.is_group:
                self.log_debug(f"Chat {event.chat_id} is not a group")
                await event.delete()
                return
            
            # Check if command is already active (if parallel not allowed)
            if not self.allow_parallel_commands and self.is_command_running():
                logger.warning(f"Another command ({self.active_command_type}) is already active. Ignoring tagall from {event.sender_id}")
                await event.delete()
                return
            
            # Delete command
            await event.delete()
            
            # Set command as active
            self.is_command_active = True
            self.stop_command = False
            self.active_command_type = 'tagging'
            
            # Get text from command
            command_text = event.pattern_match.group(1)
            if command_text:
                command_text = command_text.strip()
            else:
                command_text = ""
            
            logger.info(f"Tagall command received in chat {event.chat_id} with text: '{command_text}'")
            
            # Check if replying to a message
            reply_message = None
            reply_msg = None
            if event.is_reply:
                self.log_debug(f"Tagall is replying to a message")
                try:
                    reply_msg = await event.get_reply_message()
                    if reply_msg:
                        reply_message = reply_msg.text or reply_msg.raw_text or ""
                        self.log_debug(f"Reply message: {reply_message[:50]}...")
                except Exception as e:
                    logger.error(f"Error getting reply message: {e}")
            
            # Run tagging in background task
            self.current_task = asyncio.create_task(
                self.execute_tagging(event, command_text, reply_message, reply_msg)
            )
            
            try:
                await self.current_task
            except asyncio.CancelledError:
                logger.info("Tagging task was cancelled")
            except Exception as e:
                logger.error(f"Tagall task error: {e}")
            finally:
                self.reset_command_state()
                    
        except Exception as e:
            logger.error(f"Tagall handler error: {e}")
            import traceback
            traceback.print_exc()
            self.reset_command_state()
    
    async def execute_tagging(self, event, command_text, reply_message, reply_msg):
        """Execute the actual tagging process"""
        try:
            # Get all participants
            participants = []
            self.log_debug(f"Starting to fetch participants from chat {event.chat_id}")
            
            try:
                participant_count = 0
                async for user in self.client.iter_participants(event.chat_id):
                    if self.stop_command:
                        logger.info("Tagging stopped by user")
                        return
                    
                    participant_count += 1
                    if participant_count % 50 == 0:
                        self.log_debug(f"Fetched {participant_count} participants so far...")
                    
                    # Skip bots, deleted accounts, and self
                    if user.bot:
                        continue
                    if user.deleted:
                        continue
                    if user.is_self:
                        continue
                    
                    participants.append(user)
                    
            except Exception as e:
                logger.error(f"Error getting participants: {e}")
                import traceback
                traceback.print_exc()
                return
            
            if not participants:
                logger.warning("No members found to tag")
                return
            
            logger.info(f"Found {len(participants)} members to tag")
            
            # Get cooldown from environment
            min_cooldown = float(os.getenv('MIN_COOLDOWN', '1.0'))
            max_cooldown = float(os.getenv('MAX_COOLDOWN', '3.0'))
            
            self.log_debug(f"Using cooldown: {min_cooldown}-{max_cooldown}s")
            
            # Tag each user in separate message
            tagged_count = 0
            for index, user in enumerate(participants):
                # Check if stop command was issued
                if self.stop_command:
                    logger.info(f"Tagging stopped after {tagged_count} members")
                    return
                
                self.log_debug(f"Processing user {index+1}/{len(participants)}: {user.id}")
                
                try:
                    # Create mention
                    if user.username:
                        mention = f"@{user.username}"
                        self.log_debug(f"Using username mention: {mention}")
                    else:
                        name = user.first_name or "User"
                        mention = f"[{name}](tg://user?id={user.id})"
                        self.log_debug(f"Using ID mention: {mention}")
                    
                    final_message = ""
                    
                    # Case 1: Replying to a message that contains {mention}
                    if reply_message and "{mention}" in reply_message:
                        final_message = reply_message.replace("{mention}", mention)
                        self.log_debug(f"Case 1 - Reply with placeholder: {final_message[:50]}...")
                        await self.client.send_message(event.chat_id, final_message)
                    
                    # Case 2: Replying to a message without {mention} but with command text
                    elif event.is_reply and command_text:
                        final_message = f"{command_text}\n{mention}"
                        self.log_debug(f"Case 2 - Reply with text: {final_message[:50]}...")
                        await self.client.send_message(
                            event.chat_id, 
                            final_message, 
                            reply_to=reply_msg.id if reply_msg else None
                        )
                    
                    # Case 3: Replying to a message without {mention} and without command text
                    elif event.is_reply:
                        final_message = mention
                        self.log_debug(f"Case 3 - Reply without text: {final_message}")
                        await self.client.send_message(
                            event.chat_id, 
                            final_message, 
                            reply_to=reply_msg.id if reply_msg else None
                        )
                    
                    # Case 4: Not replying but has command text
                    elif command_text:
                        final_message = f"{command_text}\n{mention}"
                        self.log_debug(f"Case 4 - No reply with text: {final_message[:50]}...")
                        await self.client.send_message(event.chat_id, final_message)
                    
                    # Case 5: Default - just mention
                    else:
                        final_message = mention
                        self.log_debug(f"Case 5 - Default: {final_message}")
                        await self.client.send_message(event.chat_id, final_message)
                    
                    tagged_count += 1
                    
                    # Log progress every 10 users
                    if tagged_count % 10 == 0:
                        logger.info(f"Tagging progress: {tagged_count}/{len(participants)}")
                    
                    # Apply cooldown with stop checking
                    self.log_debug(f"Applying cooldown for {tagged_count}/{len(participants)}")
                    continue_delay = await random_delay(
                        min_cooldown,
                        max_cooldown,
                        lambda: self.stop_command
                    )
                    
                    if not continue_delay:
                        logger.info(f"Tagging stopped during cooldown after {tagged_count} members")
                        return
                    
                except Exception as e:
                    logger.error(f"Error mentioning user {user.id}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            logger.info(f"✅ Successfully tagged {tagged_count} members")
            
        except Exception as e:
            logger.error(f"Execute tagging error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.reset_command_state()
    
    async def handle_spam(self, event):
        """Handle spam command"""
        self.log_debug(f"Spam command received from {event.sender_id}")
        
        try:
            # Check permissions
            if not is_admin(event.sender_id, bot_id=self.bot_id):
                self.log_debug(f"User {event.sender_id} is not admin")
                await event.delete()
                return
            
            # Check if command is already active (if parallel not allowed)
            if not self.allow_parallel_commands and self.is_command_running():
                logger.warning(f"Another command ({self.active_command_type}) is already active. Ignoring spam from {event.sender_id}")
                await event.delete()
                return
            
            # Delete command
            await event.delete()
            
            # Parse command
            pattern_match = event.pattern_match
            
            # Extract count and text
            spam_count = pattern_match.group(1)
            spam_text = pattern_match.group(2)
            
            self.log_debug(f"Raw spam_count: {spam_count}, spam_text: {spam_text}")
            
            # Clean up text
            if spam_text:
                spam_text = spam_text.strip()
            else:
                spam_text = ""
            
            # Get spam settings from environment
            default_spam_count = int(os.getenv('DEFAULT_SPAM_COUNT', '100'))
            max_spam_count = int(os.getenv('MAX_SPAM_COUNT', '1000'))
            
            # Set count
            if spam_count:
                try:
                    count = int(spam_count)
                    if count > max_spam_count:
                        logger.warning(f"Spam count {count} exceeds maximum {max_spam_count}")
                        return
                except ValueError:
                    count = default_spam_count
            else:
                count = default_spam_count
            
            if not spam_text:
                logger.warning("Spam command received without text")
                return
            
            logger.info(f"Spam command received: {count} times with text: '{spam_text}'")
            
            # Set command as active
            self.is_command_active = True
            self.stop_command = False
            self.active_command_type = 'spam'
            
            # Check if replying to a message
            reply_msg = None
            if event.is_reply:
                try:
                    reply_msg = await event.get_reply_message()
                    self.log_debug(f"Spam is replying to message {reply_msg.id}")
                except Exception as e:
                    logger.error(f"Error getting reply message for spam: {e}")
            
            # Run spamming in background task
            self.current_task = asyncio.create_task(
                self.execute_spam(event, count, spam_text, reply_msg)
            )
            
            try:
                await self.current_task
            except asyncio.CancelledError:
                logger.info("Spam task was cancelled")
            except Exception as e:
                logger.error(f"Spam task error: {e}")
            finally:
                self.reset_command_state()
                    
        except Exception as e:
            logger.error(f"Spam command error: {e}")
            import traceback
            traceback.print_exc()
            self.reset_command_state()
    
    async def execute_spam(self, event, count, text, reply_msg=None):
        """Execute the spam with same logic as tagging"""
        try:
            logger.info(f"Starting spam: {count} messages in chat {event.chat_id}")
            
            # Get cooldown from environment
            min_cooldown = float(os.getenv('MIN_COOLDOWN', '1.0'))
            max_cooldown = float(os.getenv('MAX_COOLDOWN', '3.0'))
            
            sent_count = 0
            for i in range(count):
                # Check if stop command was issued
                if self.stop_command:
                    logger.info(f"Spam stopped after {sent_count} messages")
                    return
                
                try:
                    # Send message (same logic as tagging)
                    if reply_msg:
                        # If replying to a message, reply to it
                        await self.client.send_message(
                            event.chat_id, 
                            text, 
                            reply_to=reply_msg.id
                        )
                    else:
                        # Send as normal message
                        await self.client.send_message(event.chat_id, text)
                    
                    sent_count += 1
                    
                    # Log progress
                    if count <= 10 or sent_count % 10 == 0 or sent_count == count:
                        logger.info(f"Spam progress: {sent_count}/{count}")
                    
                    # Apply cooldown with stop checking (SAME AS TAGGING)
                    continue_delay = await random_delay(
                        min_cooldown,
                        max_cooldown,
                        lambda: self.stop_command
                    )
                    
                    if not continue_delay:
                        logger.info(f"Spam stopped during cooldown after {sent_count} messages")
                        return
                    
                except Exception as e:
                    logger.error(f"Error sending spam message {i+1}: {e}")
                    continue
            
            logger.info(f"✅ Spam completed: {sent_count}/{count} messages sent")
            
        except Exception as e:
            logger.error(f"Execute spam error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.reset_command_state()
    
    async def handle_stop_command(self, event):
        """Stop ongoing command process"""
        self.log_debug(f"Stop command received from {event.sender_id}")
        
        if not is_admin(event.sender_id, bot_id=self.bot_id):
            await event.delete()
            return
        
        if not self.is_command_active:
            logger.info("Stop command received but no command is active")
            await event.delete()
            return
        
        self.stop_command = True
        command_type = self.active_command_type or "command"
        logger.info(f"Stop command received from {event.sender_id}. Stopping {command_type}...")
        await event.delete()
    
    def reset_command_state(self):
        """Reset all command state variables"""
        self.log_debug("Resetting command state")
        if not self.allow_parallel_commands:
            self.is_command_active = False
            self.stop_command = False
            self.active_command_type = None
            self.current_task = None