"""
Quick script to test Telegram connection.
Usage: python scripts/test_telegram.py
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.telegram import send_telegram_message
from app.core.config import get_settings

def test():
    settings = get_settings()
    print("Testing Telegram Connection...")
    print(f"Token: {settings.telegram_bot_token[:10]}...")
    print(f"Chat ID: {settings.telegram_chat_id}")
    
    success = send_telegram_message("🧪 *Manual Connection Test*\nIf you are reading this, your Telegram Bot is correctly linked to FOREXBOT!")
    
    if success:
        print("\n✅ SUCCESS! Check your Telegram app.")
    else:
        print("\n❌ FAILED. Check your .env file or Bot Token/Chat ID.")

if __name__ == "__main__":
    test()
