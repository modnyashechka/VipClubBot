from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMIN_IDS

def get_main_menu(user_id):
    kb = [
        [KeyboardButton(text="🕹️ Play Games"), KeyboardButton(text="🔥 PLAY FOR REAL CASH 🔥")],
        [KeyboardButton(text="🎁 Bonuses, Perks & Quests"), KeyboardButton(text="👤 Profile & Settings")],
        [KeyboardButton(text="💱 Cash Out"), KeyboardButton(text="📦 Mystery Box")],
        [KeyboardButton(text="🆘 Support")]
    ]
    if user_id in ADMIN_IDS:
        kb.append([KeyboardButton(text="🛠 Admin Instructions"), KeyboardButton(text="🔍 Player Search")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

bonuses_menu = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="🎡 Daily Spin"), KeyboardButton(text="📋 Quests")],
    [KeyboardButton(text="🎟 Promo Code"), KeyboardButton(text="📢 VIP Bonus")],
    [KeyboardButton(text="🔙 Back to Main Pub")]
], resize_keyboard=True)

profile_menu = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="📊 My Stats"), KeyboardButton(text="📖 The Rules")],
    [KeyboardButton(text="🔙 Back to Main Pub")]
], resize_keyboard=True)

support_menu = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Cancel Action")]], resize_keyboard=True)

games_menu = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="🎰 Pokies"), KeyboardButton(text="🔴 Roulette"), KeyboardButton(text="🎲 Dice")],
    [KeyboardButton(text="🃏 Blackjack"), KeyboardButton(text="🦘 Roo Jump"), KeyboardButton(text="🐊 Croc Pit")],
    [KeyboardButton(text="📦 Chests"), KeyboardButton(text="🦅 Coin"), KeyboardButton(text="🏀 Basketball")],
    [KeyboardButton(text="🎯 Darts"), KeyboardButton(text="🎳 Bowling"), KeyboardButton(text="🃏 Hi-Lo")],
    [KeyboardButton(text="🪨 RPS"), KeyboardButton(text="🥃 Buy Whiskey")],
    [KeyboardButton(text="🔙 Back to Main Pub")]
], resize_keyboard=True)

bet_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🟢 50", callback_data="bet_50"), InlineKeyboardButton(text="🔵 100", callback_data="bet_100")],
    [InlineKeyboardButton(text="🟣 250", callback_data="bet_250"), InlineKeyboardButton(text="🟡 500", callback_data="bet_500")],
    [InlineKeyboardButton(text="🔥 MAX BET (ALL IN) 🔥", callback_data="bet_all")]
])

def get_roulette_kb(b): return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔴 RED", callback_data=f"roulette_red_{b}"), InlineKeyboardButton(text="⚫ BLACK", callback_data=f"roulette_black_{b}"), InlineKeyboardButton(text="🟢 ZERO", callback_data=f"roulette_green_{b}")]])
def get_chests_kb(b): return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🟥 Chest 1", callback_data=f"chest_0_{b}"), InlineKeyboardButton(text="🟩 Chest 2", callback_data=f"chest_1_{b}"), InlineKeyboardButton(text="🟦 Chest 3", callback_data=f"chest_2_{b}")]])
def get_coin_kb(b): return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🟡 Gold Heads", callback_data=f"coin_heads_{b}"), InlineKeyboardButton(text="⚪ Silver Tails", callback_data=f"coin_tails_{b}")]])
def get_hilo_kb(b, n): return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔺 HIGHER", callback_data=f"hilo_higher_{b}_{n}"), InlineKeyboardButton(text="🔻 LOWER", callback_data=f"hilo_lower_{b}_{n}")]])
def get_rps_kb(b): return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🪨 Rock", callback_data=f"rps_rock_{b}"), InlineKeyboardButton(text="📄 Paper", callback_data=f"rps_paper_{b}"), InlineKeyboardButton(text="✂️ Scissors", callback_data=f"rps_scissors_{b}")]])
def get_dice_kb(b): return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📉 LOW (1-3)", callback_data=f"dice_low_{b}"), InlineKeyboardButton(text="📈 HIGH (4-6)", callback_data=f"dice_high_{b}")]])