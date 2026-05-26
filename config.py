import urllib.parse

# Token bota oraz ID administratorów
BOT_TOKEN = "8890563409:AAGL1gG18wQfV3jnX6NRtB5GHZsa8R6pE44"
ADMIN_IDS = [8688322030, 7315484080]  

# Kanały i Linki
CHANNEL_ID = -1003927802145 
VIP_LINK = "https://t.me/+WBNCk3fF670yYTM1"
REAL_CASH_LINK = "https://t.me/Vipclubcasinobot?start=Gamebot"
SECRET_GOLD_CHANNEL = "https://t.me/+SecretGoldLounge" 

# Reklama wygranej
WIN_AD = f"\n\n🔥 <i>Bloody legend, you won! You'll have even better luck in the VIP club, give it a crack bro!</i>\n👉 <b><a href='{REAL_CASH_LINK}'>PLAY & WIN REAL CASH</a></b>"

# Lista gier
GAME_NAMES = ["🎰 Pokies", "🎯 Darts", "🎳 Bowling", "🏀 Basketball", "🎲 Dice", "🔴 Roulette", "📦 Chests", "🦅 Coin", "🃏 Hi-Lo", "🪨 RPS", "🃏 Blackjack", "🦘 Roo Jump", "🐊 Croc Pit"]

# Globalne konfiguracje stanu bota (przechowywane w pamięci podręcznej sesji)
bot_state = {
    "maintenance": False, 
    "affected_users": set(),
    "bot_username": "Vipclubcasinobot"
}