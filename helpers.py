import pytz
import time
import random
import re
import string
import urllib.parse
from datetime import datetime
from aiogram import Bot, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import VIP_LINK, bot_state
from database import db_save_user, db_get_user


# Globalna lista najlepszych dzisiejszych wygranych (utrzymywana w pamięci podręcznej)
global_top_wins_today = []

def is_happy_hour():
    try:
        tz = pytz.timezone('Australia/Sydney')
        now = datetime.now(tz)
        d, h = now.weekday(), now.hour 
        if d == 4 and (h >= 21 or h < 1): return True
        elif d in [5, 6] and (h >= 21 or h < 3): return True
        elif d == 0 and (h >= 22 or h < 3): return True 
        elif d in [1, 2, 3] and (h >= 22 or h < 1): return True
        return False
    except Exception: return False

def get_tier(bet):
    if bet < 250: return 1
    elif bet < 500: return 2
    else: return 3

def get_50_50_mult(tier, user):
    base_mult = {1: 1.8, 2: 1.9, 3: 1.95}[tier]
    if user["whiskey_buff"] > 0: base_mult += 0.2  
    if is_happy_hour(): base_mult += 0.15 
    return base_mult

def get_xp_tier(xp):
    if xp < 1000: return "⚙️ Iron"
    elif xp < 5000: return "🥉 Bronze"
    elif xp < 15000: return "🥈 Silver"
    elif xp < 50000: return "🥇 Gold"
    elif xp < 100000: return "💎 Diamond"
    else: return "👑 Legend"

async def add_xp(bot: Bot, user_id, amount):
    user = db_get_user(user_id)
    old_tier = get_xp_tier(user["xp"])
    user["xp"] += amount
    new_tier = get_xp_tier(user["xp"])
    db_save_user(user)
    
    tiers = ["⚙️ Iron", "🥉 Bronze", "🥈 Silver", "🥇 Gold", "💎 Diamond", "👑 Legend"]
    try:
        old_idx = tiers.index(old_tier)
        new_idx = tiers.index(new_tier)
    except:
        old_idx, new_idx = 0, 0
        
    if old_idx < new_idx:
        from config import SECRET_GOLD_CHANNEL
        msg = f"🆙 <b>RANK UP, MATE!</b>\n━━━━━━━━━━━━━━\nBloody oath, you just hit <b>{new_tier}</b>!"
        if old_idx < 3 and new_idx >= 3:
            msg += f"\n\n🏆 <b>GOLD PERK UNLOCKED!</b>\nFair dinkum! You've gained access to the secret VIP vault for exclusive promo codes: {SECRET_GOLD_CHANNEL}"
        try: await bot.send_message(user_id, msg, parse_mode="HTML")
        except: pass

async def ai_spam_filter(text: str) -> bool:
    if not text: return False
    text = text.lower()
    if len(text) < 10: return False
    if "http" in text or "t.me" in text or "www." in text: return False
    if re.search(r'(.)\1{4,}', text): return False
    spam_words = ["crypto", "invest", "buy", "купить", "крипта", "заработок", "scam", "free money", "guaranteed", "100x"]
    if any(word in text for word in spam_words): return False
    return True

async def update_streak(bot: Bot, user_id, message: types.Message):
    from database import db_save_promo
    user = db_get_user(user_id, message.from_user.username, message.from_user.full_name)
    now = datetime.now()
    today_str = now.strftime('%Y-%m-%d')
    last_str = user.get("last_login_date")
    
    if last_str != today_str:
        last_date = datetime.strptime(last_str, '%Y-%m-%d') if last_str else now
        diff = (now.date() - last_date.date()).days
        
        if diff == 1: 
            user["login_streak"] += 1
        elif diff > 1:
            user["login_streak"] = 1
            user["claimed_streaks"] = []
            
        user["last_login_date"] = today_str
        streak = user["login_streak"]
        claimed = user["claimed_streaks"]
        rewards = {5: 5000, 10: 10000, 15: 15000, 20: 20000, 30: 30000}
        
        if streak in rewards and streak not in claimed:
            amt = rewards[streak]
            claimed.append(streak)
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            db_save_promo(code, amt, 1, set())
            tier = get_xp_tier(user["xp"])
            try:
                await message.answer(
                    f"🔥 <b>STREAK MILESTONE!</b> 🔥\n━━━━━━━━━━━━━━\n"
                    f"<i>Bloody legend! You've logged in <b>{streak} days</b> in a row.</i>\n\n"
                    f"Here is your personal Promo Code for the <b>{tier}</b> tier reward:\n<code>{code}</code>\n\n"
                    f"Chuck it in '🎟 Promo Code' in the Bonuses menu to snag your <b>{amt} chips</b>!", parse_mode="HTML") 
            except: pass
        db_save_user(user)

def handle_whiskey_buff(user):
    if user["whiskey_buff"] > 0:
        user["whiskey_buff"] -= 1
        if user["whiskey_buff"] > 0: return f"\n🥃 <i>Whiskey Boost Active! ({user['whiskey_buff']} spins left)</i>"
        else: return f"\n🥃 <i>Whiskey wore off. Head's clear now, mate.</i>"
    return ""

async def check_subscription(bot: Bot, user_id: int) -> bool:
    from config import CHANNEL_ID
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception: return False

async def handle_no_money(bot: Bot, event, user):
    if not user.get("claimed_sub_bonus", False):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Subscribe to VIP", url=VIP_LINK)],
            [InlineKeyboardButton(text="🎁 Claim 2000 Chips", callback_data="check_sub_bonus")]
        ])
        text = "⚠️ <b>STASH IS EMPTY</b> ⚠️\n━━━━━━━━━━━━━━\n<i>Subscribe to our VIP channel to cop a massive <b>2000 CHIPS</b> refill, mate!</i>"
        if isinstance(event, types.Message): await event.answer(text, reply_markup=kb, parse_mode="HTML")
        else: 
            await event.message.answer(text, reply_markup=kb, parse_mode="HTML")
            await event.answer()
    else:
        text = "⚠️ <b>DEAD BROKE</b> ⚠️\n━━━━━━━━━━━━━━\n<i>Not enough chips, mate!</i> Spin the Daily Wheel or smash <b>PLAY FOR REAL CASH</b>."
        if isinstance(event, types.Message): await event.answer(text, parse_mode="HTML")
        else: await event.answer("Not enough chips, mate!", show_alert=True)

# NOWY PARAMETR I ZMIENIONA NAZWA: "Share wins for Bonus" z bonusem +100 chips przy przejściu z linku referencyjnego
def get_share_markup(user_id, win_amt):
    bot_link = f"https://t.me/{bot_state.get('bot_username', 'Vipclubcasinobot')}?start=share_{user_id}"
    share_text = f"🔥 Strewth! Just bagged {win_amt} chips playing on the VIP Club bot! Come join the fun, smash my link and snap a 1000 chips bonus instantly, plus I'll score a 100 bonus chips: {bot_link}"
    share_url = f"https://t.me/share/url?url=&text={urllib.parse.quote(share_text)}"
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📤 Share wins for Bonus", url=share_url)]])

async def process_win_stats(bot: Bot, user_id, user, win_amt):
    user["total_won_chips"] += win_amt
    user["win_streak"] += 1
    user["weekly_days"].add(datetime.now().weekday())
    user["inactivity_reminded"] = False
    
    global global_top_wins_today
    global_top_wins_today.append({"id": user_id, "name": user['full_name'], "win": win_amt})
    global_top_wins_today = sorted(global_top_wins_today, key=lambda x: x["win"], reverse=True)[:10]
    
    streak_xp = 0
    if user["win_streak"] == 3: streak_xp = 100
    elif user["win_streak"] == 5: streak_xp = 300
    elif user["win_streak"] == 10: streak_xp = 1000
    
    if streak_xp > 0:
        await add_xp(bot, user_id, streak_xp)
        try: await bot.send_message(user_id, f"🔥 <b>STREAK BONUS!</b> You hit {user['win_streak']} wins in a row! (+{streak_xp} XP)", parse_mode="HTML")
        except: pass

async def handle_game_end_xp(bot: Bot, user_id, user, bet):
    if not user["first_game"]:
        user["first_game"] = True
        guide = (
            "🎓 <b>THE XP & RANK RUNDOWN</b>\n━━━━━━━━━━━━━━\n"
            "<i>Good onya for having your first spin! Here's how you climb the ranks:</i>\n\n"
            "🎖 <b>Earn XP by:</b>\n"
            "• Playing games (High bets = More XP)\n"
            "• Posting daily stories (+500 XP)\n"
            "• Inviting mates (+1000 XP)\n"
            "• Hitting 50 games in a day (+2000 XP)\n"
            "• Hitting Win Streaks (3, 5, 10 wins)\n\n"
            "🏆 <b>Ranks:</b> Iron ⚙️ ➔ Bronze 🥉 ➔ Silver 🥈 ➔ Gold 🥇 ➔ Diamond 💎 ➔ Legend 👑\n"
            "<i>Hit GOLD to unlock a secret channel with exclusive promos!</i>"
        )
        try: await bot.send_message(user_id, guide, parse_mode="HTML")
        except: pass
    
    if user.get("referral_pending") and user.get("referrer_id"):
        ref_id = user["referrer_id"]
        r_user = db_get_user(ref_id)
        user["balance"] += 1000
        user["referral_pending"] = False
        user["referrer_id"] = None
        try: await bot.send_message(user_id, "🎉 <b>PROMISE KEPT!</b> You played your first game from an invite. <b>+1000 chips</b> added to your stash!", parse_mode="HTML")
        except: pass
        
        r_user["referrals"] += 1
        r_user["balance"] += 3000
        db_save_user(r_user)
        await add_xp(bot, ref_id, 1000)
        try: await bot.send_message(ref_id, f"🫂 <b>MATE JOINED & PLAYED!</b>\nYour mate just finished a game! You scored <b>3000 chips</b> and <b>1000 XP</b>! (Total invites: {r_user['referrals']})", parse_mode="HTML")
        except: pass

    game_xp = 10 + (bet // 50)
    user["xp"] += game_xp
    user["daily_games"] += 1
    
    if user["daily_games"] == 50:
        user["xp"] += 2000
        try: await bot.send_message(user_id, f"🔥 <b>DAILY GRIND RECORD!</b> You played 50 games today! (+2000 XP)", parse_mode="HTML")
        except: pass

async def handle_loot_drops(bot: Bot, callback: types.CallbackQuery, user_id, user, win_amt, bet, hh_mark, whiskey_text, use_answer=False):
    if random.random() < 0.05 and user.get("mystery_boxes_today", 0) < 1:
        user["mystery_boxes_today"] += 1
        user["inventory"].append({'type': 'mystery_box', 'drop_time': time.time(), 'base_win': win_amt, 'bet': bet})
        msg = (f"🎁 <b>MYSTERY BOX DROP!</b> {hh_mark}\n"
               f"━━━━━━━━━━━━━━\n"
               f"<i>Strewth! Instead of your regular win of {win_amt} chips, you scored a <b>Mystery Box</b>!</i>\n\n"
               f"<b>What is it?</b> It's a locked vault that guarantees your base win PLUS a massive bonus (up to 500 extra chips or a promo code)!\n"
               f"<b>Where is it?</b> Check the '📦 Mystery Box' button in the Main Pub.\n"
               f"<b>When does it open?</b> Automatically in exactly 4 days!\n\n"
               f"🏦 <b>Stash:</b> {user['balance']} {whiskey_text}")
        if use_answer: await callback.message.answer(msg, parse_mode="HTML")
        else: await callback.message.edit_text(msg, parse_mode="HTML")
        return True
    
    user["balance"] += win_amt
    await process_win_stats(bot, user_id, user, win_amt)
    
    if random.random() < 0.10 and user.get("luck_bombs_today", 0) < 2:
        user["luck_bombs_today"] += 1
        user["inventory"].append({'type': 'luck_bomb', 'drop_time': time.time()})
        msg = (f"💣 <b>LUCK BOMB DROP!</b>\n"
               f"━━━━━━━━━━━━━━\n"
               f"<i>Bloody oath! Alongside your win, you just picked up a <b>Luck Bomb</b>!</i>\n\n"
               f"<b>What is it?</b> A ticking chip bomb that explodes into 100-1000 free chips!\n"
               f"<b>Where is it?</b> Check the '📦 Mystery Box' button in the Main Pub.\n"
               f"<b>When does it explode?</b> Automatically in exactly 24 hours!\n")
        await callback.message.answer(msg, parse_mode="HTML")
        
    return False

def render_bj_table(pscore, dscore, bet):
    dp, pp = str(dscore), str(pscore)
    return (
        f"🃏 <b>BLACKJACK (21)</b>\n━━━━━━━━━━━━━━\n💵 <b>Stake:</b> {bet}\n\n"
        f"<pre>\n DEALER: {dscore}\n ┌───────┐ \n │{dp.ljust(3)}    │ \n │   ♠   │ \n │    {dp.rjust(3)}│ \n └───────┘ \n\n"
        f" YOU: {pscore}\n ┌───────┐ \n │{pp.ljust(3)}    │ \n │   ♦   │ \n │    {pp.rjust(3)}│ \n └───────┘ \n</pre>"
    )

def render_hilo_table(num, next_num=None):
    n1 = str(num)
    n2 = "??" if next_num is None else str(next_num)
    return (
        f"<pre>\n CURRENT    NEXT\n ┌───────┐  ┌───────┐\n │{n1.ljust(3)}    │  │{n2.ljust(3)}    │\n │   ♣   │  │   ?   │\n"
        f" │    {n1.rjust(3)}│  │    {n2.rjust(3)}│\n └───────┘  └───────┘\n</pre>"
    )
async def process_loss_stats(user, bet_amt):
    user["win_streak"] = 0
    user["weekly_losses"] += bet_amt
    user["weekly_days"].add(datetime.now().weekday())
    user["inactivity_reminded"] = False