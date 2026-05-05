"""
Telegram notification service.
Uses standard urllib to avoid extra dependencies like 'requests'.
"""

import json
import urllib.parse
import urllib.request
from datetime import datetime

from app.core.config import get_settings
from app.core.logger import get_logger

logger = get_logger("services.telegram")


def send_telegram_message(message: str) -> bool:
    """Send a message to the configured Telegram chat.
    
    Args:
        message: Text to send.
        
    Returns:
        True if successful, False otherwise.
    """
    settings = get_settings()
    token = settings.telegram_bot_token
    chat_id = settings.telegram_chat_id

    if not token or not chat_id:
        logger.debug("Telegram not configured (missing token or chat_id)")
        return False

    # Clean up token if it contains 'bot' prefix (common user error)
    if not token.startswith("bot") and ":" in token:
        token = f"bot{token}"

    url = f"https://api.telegram.org/{token}/sendMessage"
    
    # Format message with timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_message = f"🤖 *FOREXBOT*\n🕒 {timestamp}\n\n{message}"
    
    data = {
        "chat_id": chat_id,
        "text": full_message,
        "parse_mode": "Markdown"
    }
    
    try:
        encoded_data = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(
            url, 
            data=encoded_data, 
            headers={"Content-Type": "application/json"}
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                logger.info(f"Telegram message sent successfully")
                return True
            else:
                logger.error(f"Telegram API returned status: {response.status}")
                return False
                
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")
        return False


def send_heartbeat(symbol_list: list[str]) -> bool:
    """Send a system health heartbeat message."""
    symbols = ", ".join(symbol_list)
    message = (
        "✅ *Heartbeat Check*\n"
        "Status: ACTIVE\n"
        f"Scanning: {symbols}\n"
        "Everything is running correctly on the VPS."
    )
    return send_telegram_message(message)
