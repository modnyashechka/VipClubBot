import asyncio
import random
from aiogram import Router, F, types, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery

from config import GAME_NAMES, WIN_AD
from database import db_get_user, db_save_user
import keyboards as kb
from helpers import (
    handle_no_money, is_happy_hour, get_tier, handle_whiskey_buff,
    handle_game_end_xp, get_50_50_mult, handle_loot_drops, render_bj_table,
    render_hilo_table, get_share_markup, process_loss_stats
)
games_router = Router()
CLAIMED_SHARES = set()


from helpers import (
    handle_no_money, is_happy_hour, get_tier, handle_whiskey_buff,
    handle_game_end_xp, get_50_50_mult, handle_loot_drops, render_bj_table,
    render_hilo_table, get_share_markup, process_loss_stats
)



@games_router.message(F.text.in_(GAME_NAMES))
async def pre_game_bet(message: types.Message, bot: Bot):
    user = db_get_user(message.from_user.id, message.from_user.username, message.from_user.full_name)
    if user["balance"] < 50: return await handle_no_money(bot, message, user)
    game_map = {"🎰 Pokies":"slots", "🎯 Darts":"darts", "🎳 Bowling":"bowling", "🏀 Basketball":"basketball", "🎲 Dice":"dice", "🔴 Roulette":"roulette", "📦 Chests":"chests", "🦅 Coin":"coin", "🃏 Hi-Lo":"hilo", "🪨 RPS":"rps", "🃏 Blackjack":"blackjack", "🦘 Roo Jump":"roojump", "🐊 Croc Pit":"crocpit"}
    user["pending_game"] = game_map[message.text]
    
    emoji = message.text.split(" ")[0]
    name = message.text.split(" ")[1].upper()
    hh_text = "\n\n🌙 <b>HAPPY HOUR IS ACTIVE!</b> (+Odds & Payouts!)" if is_happy_hour() else ""
    
    if game_map[message.text] == "hilo":
        user["balance"] -= 50 
        user["total_games"] += 1
        n = random.randint(1, 100)
        db_save_user(user)
        await message.answer(f"🃏 <b>HI-LO</b>\n━━━━━━━━━━━━━━\n{render_hilo_table(n)}\n<i>Pick your bet for the next card, mate!</i>{hh_text}", reply_markup=kb.get_hilo_kb(50, n), parse_mode="HTML")
        user = db_get_user(message.from_user.id)
        user["balance"] += 50 
        db_save_user(user)
    else:
        db_save_user(user)
        await message.answer(f"{emoji} <b>{name}</b> {emoji}\n━━━━━━━━━━━━━━\n<i>Place your bet, mate! (Min: 50)</i>{hh_text}", reply_markup=kb.bet_kb, parse_mode="HTML")

@games_router.callback_query(F.data.startswith("bet_"))
async def process_bet(callback: types.CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    user = db_get_user(user_id)
    b_str = callback.data.split("_")[1]
    bet = user["balance"] if b_str == "all" else int(b_str)
    
    if bet < 50: return await callback.answer("Minimum bet is 50 chips, mate!", show_alert=True)
    if user["balance"] < bet: return await handle_no_money(bot, callback, user)
    
    game = user.get("pending_game")
    if not game: return await callback.answer("Session expired! Pick a game again.", show_alert=True)
    
    user["pending_game"] = None 
    tier = get_tier(bet)
    hh = is_happy_hour()
    whiskey_text = handle_whiskey_buff(user)
    hh_mark = "🌙" if hh else ""
    
    try:
        if game == "blackjack":
            user["balance"] -= bet
            user["total_games"] += 1
            db_save_user(user)
            await handle_game_end_xp(bot, user_id, user, bet)
            pscore = random.randint(2,11) + random.randint(2,11)
            dscore = random.randint(2,11)
            markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🖐 Hit Me", callback_data=f"bj_hit_{bet}_{pscore}_{dscore}"), InlineKeyboardButton(text="🛑 Stand", callback_data=f"bj_stand_{bet}_{pscore}_{dscore}")]
            ])
            await callback.message.edit_text(render_bj_table(pscore, dscore, bet) + "\n\n<i>What's the move, mate?</i>", parse_mode="HTML", reply_markup=markup)
            return

        elif game == "roojump":
            user["balance"] -= bet
            user["total_games"] += 1
            db_save_user(user)
            await handle_game_end_xp(bot, user_id, user, bet)
            markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🦘 1.5x", callback_data=f"roo_1.5_{bet}"), InlineKeyboardButton(text="🦘 2.0x", callback_data=f"roo_2.0_{bet}")],
                [InlineKeyboardButton(text="🚀 5.0x", callback_data=f"roo_5.0_{bet}"), InlineKeyboardButton(text="🔥 10.0x", callback_data=f"roo_10.0_{bet}")]
            ])
            await callback.message.edit_text(f"🦘 <b>ROO JUMP (CRASH)</b>\n━━━━━━━━━━━━━━\n💵 <b>Stake:</b> {bet}\n\n<i>Pick your target multiplier. If the Roo jumps higher than your target, you win big!</i>", parse_mode="HTML", reply_markup=markup)
            return

        elif game == "crocpit":
            user["balance"] -= bet
            user["total_games"] += 1
            db_save_user(user)
            await handle_game_end_xp(bot, user_id, user, bet)
            markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🌿 Swamp 1", callback_data=f"croc_0_{bet}"), InlineKeyboardButton(text="🌿 Swamp 2", callback_data=f"croc_1_{bet}"), InlineKeyboardButton(text="🌿 Swamp 3", callback_data=f"croc_2_{bet}")]
            ])
            await callback.message.edit_text(f"🐊 <b>CROC PIT</b>\n━━━━━━━━━━━━━━\n💵 <b>Stake:</b> {bet}\n\n<pre>   🌿      🌿      🌿\n  [1]     [2]     [3]</pre>\n<i>Two swamps are safe (1.5x payout), one has a hungry croc. Pick wisely, mate!</i>", parse_mode="HTML", reply_markup=markup)
            return

        if game in ["slots", "darts", "bowling", "basketball"]:
            await callback.message.edit_text(f"🎟 <b>BET LOCKED IN</b>\n━━━━━━━━━━━━━━\n💵 <b>Stake:</b> {bet} (Tier {tier})\n🎬 <i>Action!</i>", parse_mode="HTML")
            user["balance"] -= bet
            user["total_games"] += 1
            db_save_user(user)
            await handle_game_end_xp(bot, user_id, user, bet)
            
            emoji_map = {"slots":"🎰", "darts":"🎯", "bowling":"🎳", "basketball":"🏀"}
            msg = await callback.message.answer_dice(emoji=emoji_map[game])
            await asyncio.sleep(2.5)
            val = msg.dice.value
            user = db_get_user(user_id)
            
            if game == "slots":
                if tier == 1: mults = {1: 3, 22: 3, 43: 5, 64: 15}
                elif tier == 2: mults = {1: 3.5, 22: 3.5, 43: 6, 64: 20}
                else: mults = {1: 4, 22: 4, 43: 7, 64: 25}
                
                if val in mults:
                    m = mults[val] + (0.2 if user["whiskey_buff"] > 0 else 0) + (0.15 if hh else 0)
                    win_amt = int(bet * m)
                    hijacked = await handle_loot_drops(bot, callback, user_id, user, win_amt, bet, hh_mark, whiskey_text, use_answer=True)
                    if not hijacked:
                        await callback.message.answer(f"🎰 <b>[ {val} ]</b> 🎰\n🎉 <b>JACKPOT!</b> {hh_mark}\n━━━━━━━━━━━━━━\n📈 <b>Multiplier:</b> x{m:.2f}\n💵 <b>Won:</b> +{win_amt}\n🏦 <b>Stash:</b> {user['balance']}{whiskey_text}{WIN_AD}", parse_mode="HTML", disable_web_page_preview=True, reply_markup=get_share_markup(user_id, win_amt))
                else: 
                    await process_loss_stats(user, bet)
                    await callback.message.answer(f"🎰 <b>[ {val} ]</b> 🎰\n💀 <b>DEAD SPIN</b> 💀\n━━━━━━━━━━━━━━\n📉 <i>Better luck next time.</i>\n🏦 <b>Stash:</b> {user['balance']}{whiskey_text}", parse_mode="HTML")
                
            elif game == "darts" or game == "bowling":
                high_win = {1: 3.0, 2: 3.5, 3: 4.0}[tier] + (0.2 if user["whiskey_buff"] > 0 else 0) + (0.15 if hh else 0)
                low_win = {1: 1.5, 2: 1.6, 3: 1.8}[tier] + (0.2 if user["whiskey_buff"] > 0 else 0) + (0.15 if hh else 0)
                
                if val == 6:
                    win_amt = int(bet * high_win)
                    hijacked = await handle_loot_drops(bot, callback, user_id, user, win_amt, bet, hh_mark, whiskey_text, use_answer=True)
                    if not hijacked:
                        await callback.message.answer(f"🔥 <b>BULLSEYE!</b> {hh_mark}\n━━━━━━━━━━━━━━\n💵 <b>Won:</b> +{win_amt}\n🏦 <b>Stash:</b> {user['balance']}{whiskey_text}{WIN_AD}", parse_mode="HTML", disable_web_page_preview=True, reply_markup=get_share_markup(user_id, win_amt))
                elif val in [4, 5]:
                    win_amt = int(bet * low_win)
                    hijacked = await handle_loot_drops(bot, callback, user_id, user, win_amt, bet, hh_mark, whiskey_text, use_answer=True)
                    if not hijacked:
                        await callback.message.answer(f"👍 <b>GOOD SHOT!</b> {hh_mark}\n━━━━━━━━━━━━━━\n💵 <b>Won:</b> +{win_amt}\n🏦 <b>Stash:</b> {user['balance']}{whiskey_text}{WIN_AD}", parse_mode="HTML", disable_web_page_preview=True, reply_markup=get_share_markup(user_id, win_amt))
                else: 
                    await process_loss_stats(user, bet)
                    await callback.message.answer(f"🧱 <b>MISSED!</b>\n━━━━━━━━━━━━━━\n📉 <i>You lost your bet.</i>\n🏦 <b>Stash:</b> {user['balance']}{whiskey_text}", parse_mode="HTML")
                    
            elif game == "basketball":
                if val in [4, 5]:
                    win_amt = int(bet * get_50_50_mult(tier, user))
                    hijacked = await handle_loot_drops(bot, callback, user_id, user, win_amt, bet, hh_mark, whiskey_text, use_answer=True)
                    if not hijacked:
                        await callback.message.answer(f"🏀 <b>SWISH!</b> {hh_mark}\n━━━━━━━━━━━━━━\n💵 <b>Won:</b> +{win_amt}\n🏦 <b>Stash:</b> {user['balance']}{whiskey_text}{WIN_AD}", parse_mode="HTML", disable_web_page_preview=True, reply_markup=get_share_markup(user_id, win_amt))
                else: 
                    await process_loss_stats(user, bet)
                    await callback.message.answer(f"🧱 <b>BRICK!</b>\n━━━━━━━━━━━━━━\n📉 <i>You missed the shot.</i>\n🏦 <b>Stash:</b> {user['balance']}{whiskey_text}", parse_mode="HTML")
            db_save_user(user)

        elif game == "dice": await callback.message.edit_text(f"🎲 <b>DICE</b>\n━━━━━━━━━━━━━━\n💵 <b>Bet:</b> {bet}\n<i>Low or High?</i>", reply_markup=kb.get_dice_kb(bet), parse_mode="HTML")
        elif game == "roulette": await callback.message.edit_text(f"🔴 <b>ROULETTE</b>\n━━━━━━━━━━━━━━\n💵 <b>Bet:</b> {bet}\n<i>Pick your colour:</i>", reply_markup=kb.get_roulette_kb(bet), parse_mode="HTML")
        elif game == "chests": await callback.message.edit_text(f"📦 <b>CHESTS</b>\n━━━━━━━━━━━━━━\n💵 <b>Bet:</b> {bet}\n<i>Pick a chest!</i>", reply_markup=kb.get_chests_kb(bet), parse_mode="HTML")
        elif game == "coin": await callback.message.edit_text(f"🦅 <b>COIN FLIP</b>\n━━━━━━━━━━━━━━\n💵 <b>Bet:</b> {bet}\n<i>Heads or Tails?</i>", reply_markup=kb.get_coin_kb(bet), parse_mode="HTML")
        elif game == "rps": await callback.message.edit_text(f"🪨 <b>R-P-S</b>\n━━━━━━━━━━━━━━\n💵 <b>Bet:</b> {bet}\n<i>Choose your weapon!</i>", reply_markup=kb.get_rps_kb(bet), parse_mode="HTML")
        db_save_user(user)
    except Exception: pass 

@games_router.callback_query(F.data.startswith("bj_"))
async def process_blackjack(callback: types.CallbackQuery, bot: Bot):
    parts = callback.data.split("_")
    action, bet, pscore, dscore = parts[1], int(parts[2]), int(parts[3]), int(parts[4])
    user_id = callback.from_user.id
    user = db_get_user(user_id)
    hh_mark = "🌙" if is_happy_hour() else ""
    whiskey_text = handle_whiskey_buff(user)
    
    if action == "hit":
        pscore += random.randint(2,11)
        if pscore > 21:
            await process_loss_stats(user, bet)
            await callback.message.edit_text(render_bj_table(pscore, dscore, bet) + f"\n\n💀 <b>BUST!</b> You went over 21.\n📉 <i>Lost: {bet} chips</i>\n🏦 <b>Stash:</b> {user['balance']}{whiskey_text}", parse_mode="HTML")
        else:
            markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🖐 Hit Me", callback_data=f"bj_hit_{bet}_{pscore}_{dscore}"), InlineKeyboardButton(text="🛑 Stand", callback_data=f"bj_stand_{bet}_{pscore}_{dscore}")]
            ])
            await callback.message.edit_text(render_bj_table(pscore, dscore, bet) + "\n\n<i>Hit again or Stand?</i>", parse_mode="HTML", reply_markup=markup)
    elif action == "stand":
        while dscore < 17: dscore += random.randint(2,11)
        text = render_bj_table(pscore, dscore, bet) + "\n\n"
        
        if dscore > 21 or pscore > dscore:
            mult = 2.0 + (0.15 if is_happy_hour() else 0) + (0.2 if user["whiskey_buff"] > 0 else 0)
            win_amt = int(bet * mult)
            hijacked = await handle_loot_drops(bot, callback, user_id, user, win_amt, bet, hh_mark, whiskey_text)
            if not hijacked:
                text += f"✅ <b>YOU WON!</b> {hh_mark}\n💵 <b>Won:</b> +{win_amt}\n🏦 <b>Stash:</b> {user['balance']}{whiskey_text}{WIN_AD}"
                await callback.message.edit_text(text, parse_mode="HTML", disable_web_page_preview=True, reply_markup=get_share_markup(user_id, win_amt))
        elif pscore == dscore:
            user["balance"] += bet
            text += f"🤝 <b>PUSH! (Tie)</b> Bet refunded.\n🏦 <b>Stash:</b> {user['balance']}{whiskey_text}"
            await callback.message.edit_text(text, parse_mode="HTML")
        else:
            await process_loss_stats(user, bet)
            text += f"💀 <b>DEALER WINS!</b>\n📉 <i>Lost: {bet}</i>\n🏦 <b>Stash:</b> {user['balance']}{whiskey_text}"
            await callback.message.edit_text(text, parse_mode="HTML")
    db_save_user(user)

@games_router.callback_query(F.data.startswith("roo_"))
async def process_roo(callback: types.CallbackQuery, bot: Bot):
    parts = callback.data.split("_")
    target, bet = float(parts[1]), int(parts[2])
    user_id = callback.from_user.id
    user = db_get_user(user_id)
    hh = is_happy_hour()
    hh_mark = "🌙" if hh else ""
    whiskey_text = handle_whiskey_buff(user)
    
    await callback.message.edit_text("🦘 <i>The Roo is warming up...</i>\n\n<pre>[ . . . 🦘 . . . ]</pre>", parse_mode="HTML")
    await asyncio.sleep(1)
    await callback.message.edit_text("🦘 <i>He's airborne! Going up, mate!</i>\n\n<pre>[ . . 🚀🦘 . . . ]</pre>", parse_mode="HTML")
    await asyncio.sleep(1)
    
    u = random.uniform(0, 0.95)
    if hh: u = random.uniform(0.1, 0.96) 
    crash = round(1.0 / (1.0 - u), 2)
    
    if crash >= target:
        mult = target + (0.2 if user["whiskey_buff"] > 0 else 0)
        win_amt = int(bet * mult)
        hijacked = await handle_loot_drops(bot, callback, user_id, user, win_amt, bet, hh_mark, whiskey_text)
        if not hijacked:
            await callback.message.edit_text(f"🦘 <b>ROO JUMPED TO {crash}x!</b> {hh_mark}\n<pre>[ . ☁️🦘☁️ . . . ]</pre>\n━━━━━━━━━━━━━━\n🎯 <b>Target:</b> {target}x\n✅ <b>YOU WON!</b>\n💵 <b>Won:</b> +{win_amt}\n🏦 <b>Stash:</b> {user['balance']}{whiskey_text}{WIN_AD}", parse_mode="HTML", disable_web_page_preview=True, reply_markup=get_share_markup(user_id, win_amt))
    else:
        await process_loss_stats(user, bet)
        await callback.message.edit_text(f"💥 <b>CRASH AT {crash}x!</b>\n<pre>[ . . . 💥 . . . ]</pre>\n━━━━━━━━━━━━━━\n🎯 <b>Target:</b> {target}x\n❌ <b>The Roo fell short!</b>\n📉 <i>Lost: {bet}</i>\n🏦 <b>Stash:</b> {user['balance']}{whiskey_text}", parse_mode="HTML")
    db_save_user(user)

@games_router.callback_query(F.data.startswith("croc_"))
async def process_croc(callback: types.CallbackQuery, bot: Bot):
    parts = callback.data.split("_")
    choice, bet = int(parts[1]), int(parts[2])
    user_id = callback.from_user.id
    user = db_get_user(user_id)
    hh = is_happy_hour()
    hh_mark = "🌙" if hh else ""
    whiskey_text = handle_whiskey_buff(user)
    
    await callback.message.edit_text("🌿 <i>Wading into the swamp...</i>\n\n<pre>   🌿      🌿      🌿\n  [1]     [2]     [3]</pre>", parse_mode="HTML")
    await asyncio.sleep(1)
    await callback.message.edit_text("💦 <i>Water is getting deep...</i>\n\n<pre>   🌿      🌿      🌿\n  [1]     [2]     [3]</pre>", parse_mode="HTML")
    await asyncio.sleep(1)
    
    croc_pos = random.randint(0, 2)
    if hh and croc_pos == choice and random.random() < 0.2: croc_pos = (choice + 1) % 3 
        
    if choice != croc_pos:
        mult = 1.5 + (0.15 if hh else 0) + (0.2 if user["whiskey_buff"] > 0 else 0)
        win_amt = int(bet * mult)
        swamps = ["🌿", "🌿", "🌿"]
        swamps[croc_pos] = "🐊"
        swamps[choice] = "💰"
        
        hijacked = await handle_loot_drops(bot, callback, user_id, user, win_amt, bet, hh_mark, whiskey_text)
        if not hijacked:
            await callback.message.edit_text(f"💰 <b>SAFE!</b> {hh_mark}\n<pre>   {swamps[0]}      {swamps[1]}      {swamps[2]}\n  [1]     [2]     [3]</pre>\n━━━━━━━━━━━━━━\n✅ <b>YOU WON!</b>\n💵 <b>Won:</b> +{win_amt}\n🏦 <b>Stash:</b> {user['balance']}{whiskey_text}{WIN_AD}", parse_mode="HTML", disable_web_page_preview=True, reply_markup=get_share_markup(user_id, win_amt))
    else:
        await process_loss_stats(user, bet)
        swamps = ["🌿", "🌿", "🌿"]
        swamps[croc_pos] = "🐊"
        await callback.message.edit_text(f"🐊 <b>CHOMP!</b>\n<pre>   {swamps[0]}      {swamps[1]}      {swamps[2]}\n  [1]     [2]     [3]</pre>\n━━━━━━━━━━━━━━\n❌ <b>You found the croc!</b>\n📉 <i>Lost: {bet}</i>\n🏦 <b>Stash:</b> {user['balance']}{whiskey_text}", parse_mode="HTML")
    db_save_user(user)

@games_router.callback_query(F.data.startswith("roulette_"))
async def process_roulette(callback: types.CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    parts = callback.data.split("_")
    choice, bet = parts[1], int(parts[2])
    user = db_get_user(user_id)
    if user["balance"] < bet: return await handle_no_money(bot, callback, user)
    
    user["balance"] -= bet 
    user["total_games"] += 1
    db_save_user(user)
    await handle_game_end_xp(bot, user_id, user, bet)
    
    await callback.message.edit_text("🌀 <i>The wheel is spinning...</i>\n\n[🔴] 🎡 [⚫]", parse_mode="HTML")
    await asyncio.sleep(0.6)
    await callback.message.edit_text("🌀 <i>The ball is bouncing around...</i>\n\n[⚫] 🎡 [🟢]", parse_mode="HTML")
    await asyncio.sleep(0.6)
    await callback.message.edit_text("🌀 <i>It's slowing down, mate...</i>\n\n[🟢] 🎡 [🔴]", parse_mode="HTML")
    await asyncio.sleep(0.6)
    
    user = db_get_user(user_id)
    tier = get_tier(bet)
    zero_mult = {1: 8.0, 2: 9.0, 3: 10.0}[tier]
    if user["whiskey_buff"] > 0: zero_mult += 2.0
    hh = is_happy_hour()
    if hh: zero_mult += 1.0
    col_mult = get_50_50_mult(tier, user)
    
    r_num = random.randint(0, 36)
    r_col = "green" if r_num == 0 else ("black" if r_num % 2 == 0 else "red")
    if hh and r_col != choice and random.random() < 0.20: r_col = choice
    whiskey_text = handle_whiskey_buff(user)
    hh_mark = "🌙" if hh else ""
    
    if choice == r_col:
        win = int(bet * zero_mult) if choice == "green" else int(bet * col_mult)
        hijacked = await handle_loot_drops(bot, callback, user_id, user, win, bet, hh_mark, whiskey_text)
        if not hijacked:
            await callback.message.edit_text(f"✅ <b>YOU WON!</b> {hh_mark}\n━━━━━━━━━━━━━━\n📍 Landed on: {r_col.upper()}\n💵 <b>Won:</b> +{win}\n🏦 <b>Stash:</b> {user['balance']}{whiskey_text}{WIN_AD}", parse_mode="HTML", disable_web_page_preview=True, reply_markup=get_share_markup(user_id, win))
    else: 
        await process_loss_stats(user, bet)
        await callback.message.edit_text(f"❌ <b>YOU LOST</b>\n━━━━━━━━━━━━━━\n📍 Landed on: {r_col.upper()}\n📉 <i>Lost: {bet}</i>\n🏦 <b>Stash:</b> {user['balance']}{whiskey_text}", parse_mode="HTML")
    db_save_user(user)

@games_router.callback_query(F.data.startswith("dice_"))
async def process_dice(callback: types.CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    parts = callback.data.split("_")
    choice, bet = parts[1], int(parts[2])
    user = db_get_user(user_id)
    if user["balance"] < bet: return await handle_no_money(bot, callback, user)
    
    user["balance"] -= bet
    user["total_games"] += 1
    db_save_user(user)
    await handle_game_end_xp(bot, user_id, user, bet)
    
    await callback.message.edit_text("🎲 <i>Shaking the dice...</i>", parse_mode="HTML")
    await asyncio.sleep(0.5)
    
    msg = await callback.message.answer_dice(emoji="🎲")
    await asyncio.sleep(3)
    val = msg.dice.value
    is_low = val in [1, 2, 3]
    
    user = db_get_user(user_id)
    whiskey_text = handle_whiskey_buff(user)
    hh = is_happy_hour()
    hh_mark = "🌙" if hh else ""
    
    if (choice == "low" and is_low) or (choice == "high" and not is_low):
        win_amt = int(bet * get_50_50_mult(get_tier(bet), user))
        hijacked = await handle_loot_drops(bot, callback, user_id, user, win_amt, bet, hh_mark, whiskey_text)
        if not hijacked:
            await callback.message.answer(f"✅ <b>YOU WON!</b> {hh_mark}\n━━━━━━━━━━━━━━\n📍 Rolled a: <b>{val}</b>\n💵 <b>Won:</b> +{win_amt}\n🏦 <b>Stash:</b> {user['balance']}{whiskey_text}{WIN_AD}", parse_mode="HTML", disable_web_page_preview=True, reply_markup=get_share_markup(user_id, win_amt))
    else: 
        await process_loss_stats(user, bet)
        await callback.message.answer(f"❌ <b>YOU LOST</b>\n━━━━━━━━━━━━━━\n📍 Rolled a: <b>{val}</b>\n📉 <i>Lost: {bet}</i>\n🏦 <b>Stash:</b> {user['balance']}{whiskey_text}", parse_mode="HTML")
    db_save_user(user)

@games_router.callback_query(F.data.startswith("chest_"))
async def process_chests(callback: types.CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    parts = callback.data.split("_")
    choice_idx, bet = int(parts[1]), int(parts[2])
    user = db_get_user(user_id)
    if user["balance"] < bet: return await handle_no_money(bot, callback, user)
    
    user["balance"] -= bet
    user["total_games"] += 1
    db_save_user(user)
    await handle_game_end_xp(bot, user_id, user, bet)
    
    await callback.message.edit_text("📦 <i>Approaching the chests...</i>\n\n<pre> [ 📦 ]  [ 📦 ]  [ 📦 ] </pre>", parse_mode="HTML")
    await asyncio.sleep(1)
    
    user = db_get_user(user_id)
    tier = get_tier(bet)
    mult = {1: 2.5, 2: 2.7, 3: 2.8}[tier]
    hh = is_happy_hour()
    winning = random.randint(0, 2) 
    if hh and winning != choice_idx and random.random() < 0.20: winning = choice_idx
    
    whiskey_text = handle_whiskey_buff(user)
    if user["whiskey_buff"] > 0: mult += 0.2
    if hh: mult += 0.15
    hh_mark = "🌙" if hh else ""
    
    if choice_idx == winning:
        win_amt = int(bet * mult)
        boxes = ["📦", "📦", "📦"]
        boxes[winning] = "💎"
        hijacked = await handle_loot_drops(bot, callback, user_id, user, win_amt, bet, hh_mark, whiskey_text)
        if not hijacked:
            await callback.message.edit_text(f"💎 <b>LOOT FOUND!</b> {hh_mark}\n<pre> [ {boxes[0]} ]  [ {boxes[1]} ]  [ {boxes[2]} ] </pre>\n━━━━━━━━━━━━━━\n💵 <b>Won:</b> +{win_amt}\n🏦 <b>Stash:</b> {user['balance']}{whiskey_text}{WIN_AD}", parse_mode="HTML", disable_web_page_preview=True, reply_markup=get_share_markup(user_id, win_amt))
    else: 
        await process_loss_stats(user, bet)
        boxes = ["📦", "📦", "📦"]
        boxes[winning] = "💎"
        boxes[choice_idx] = "💀"
        await callback.message.edit_text(f"💀 <b>EMPTY CHEST</b> 💀\n<pre> [ {boxes[0]} ]  [ {boxes[1]} ]  [ {boxes[2]} ] </pre>\n━━━━━━━━━━━━━━\n📍 <i>Loot was in chest {winning + 1}.</i>\n🏦 <b>Stash:</b> {user['balance']}{whiskey_text}", parse_mode="HTML")
    db_save_user(user)

@games_router.callback_query(F.data.startswith("coin_"))
async def process_coin(callback: types.CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    parts = callback.data.split("_")
    choice, bet = parts[1], int(parts[2])
    user = db_get_user(user_id)
    if user["balance"] < bet: return await handle_no_money(bot, callback, user)
    
    user["balance"] -= bet
    user["total_games"] += 1
    db_save_user(user)
    await handle_game_end_xp(bot, user_id, user, bet)
    
    await callback.message.edit_text(r"🪙 <i>Flipping the dingo dollar...</i>\n\n<pre>   ( \ )   </pre>", parse_mode="HTML")
    await asyncio.sleep(0.5)
    await callback.message.edit_text("🪙 <i>Spinning high in the air...</i>\n\n<pre>   ( - )   </pre>", parse_mode="HTML")
    await asyncio.sleep(0.5)
    
    res = random.choice(["heads", "tails"])
    hh = is_happy_hour()
    if hh and res != choice and random.random() < 0.20: res = choice
    
    user = db_get_user(user_id)
    whiskey_text = handle_whiskey_buff(user)
    hh_mark = "🌙" if hh else ""
    
    if choice == res:
        win_amt = int(bet * get_50_50_mult(get_tier(bet), user))
        emoji = "🟡" if res == "heads" else "⚪"
        hijacked = await handle_loot_drops(bot, callback, user_id, user, win_amt, bet, hh_mark, whiskey_text)
        if not hijacked:
            await callback.message.edit_text(f"✅ <b>YOU WON!</b> {hh_mark}\n<pre>   ( {emoji} )   </pre>\n━━━━━━━━━━━━━━\n📍 It's: <b>{res.upper()}</b>\n💵 <b>Won:</b> +{win_amt}\n🏦 <b>Stash:</b> {user['balance']}{whiskey_text}{WIN_AD}", parse_mode="HTML", disable_web_page_preview=True, reply_markup=get_share_markup(user_id, win_amt))
    else: 
        await process_loss_stats(user, bet)
        emoji = "🟡" if res == "heads" else "⚪"
        await callback.message.edit_text(f"❌ <b>YOU LOST</b>\n<pre>   ( {emoji} )   </pre>\n━━━━━━━━━━━━━━\n📍 It's: <b>{res.upper()}</b>\n📉 <i>Lost: {bet}</i>\n🏦 <b>Stash:</b> {user['balance']}{whiskey_text}", parse_mode="HTML")
    db_save_user(user)

@games_router.callback_query(F.data.startswith("hilo_"))
async def process_hilo(callback: types.CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    parts = callback.data.split("_")
    choice, bet, old_num = parts[1], int(parts[2]), int(parts[3])
    user = db_get_user(user_id)
    if user["balance"] < bet: return await handle_no_money(bot, callback, user)
    
    user["balance"] -= bet
    user["total_games"] += 1
    db_save_user(user)
    await handle_game_end_xp(bot, user_id, user, bet)
    
    await callback.message.edit_text("🃏 <i>Drawing card...</i>\n" + render_hilo_table(old_num, None), parse_mode="HTML")
    await asyncio.sleep(1)
    
    new_num = random.randint(1, 100)
    hh = is_happy_hour()
    if hh and random.random() < 0.20:
        if choice == "higher" and new_num <= old_num: new_num = random.randint(old_num+1, 101)
        elif choice == "lower" and new_num >= old_num: new_num = random.randint(1, max(2, old_num))
            
    text = f"🃏 <b>HI-LO RESULT</b> 🃏\n━━━━━━━━━━━━━━\n{render_hilo_table(old_num, new_num)}\n"
    user = db_get_user(user_id)
    whiskey_text = handle_whiskey_buff(user)
    hh_mark = "🌙" if hh else ""
    
    if old_num == new_num:
        user["balance"] += bet
        text += f"🤝 <b>TIE!</b> Bet refunded.\n🏦 <b>Stash:</b> {user['balance']}{whiskey_text}"
        await callback.message.edit_text(text, parse_mode="HTML")
    elif (choice == "higher" and new_num > old_num) or (choice == "lower" and new_num < old_num):
        win_amt = int(bet * get_50_50_mult(get_tier(bet), user))
        hijacked = await handle_loot_drops(bot, callback, user_id, user, win_amt, bet, hh_mark, whiskey_text)
        if not hijacked:
            text += f"✅ <b>YOU WON!</b> {hh_mark}\n💵 <b>Won:</b> +{win_amt}\n🏦 <b>Stash:</b> {user['balance']}{whiskey_text}{WIN_AD}"
            await callback.message.edit_text(text, parse_mode="HTML", disable_web_page_preview=True, reply_markup=get_share_markup(user_id, win_amt))
    else: 
        await process_loss_stats(user, bet)
        text += f"❌ <b>YOU LOST</b>\n📉 <i>Lost: {bet}</i>\n🏦 <b>Stash:</b> {user['balance']}{whiskey_text}"
        await callback.message.edit_text(text, parse_mode="HTML")
    db_save_user(user)

@games_router.callback_query(F.data.startswith("rps_"))
async def process_rps(callback: types.CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    parts = callback.data.split("_")
    choice, bet = parts[1], int(parts[2])
    user = db_get_user(user_id)
    if user["balance"] < bet: return await handle_no_money(bot, callback, user)
    
    user["balance"] -= bet
    user["total_games"] += 1
    db_save_user(user)
    await handle_game_end_xp(bot, user_id, user, bet)
    
    await callback.message.edit_text("✊ <i>Rock...</i>", parse_mode="HTML")
    await asyncio.sleep(0.5)
    await callback.message.edit_text("✋ <i>Paper...</i>", parse_mode="HTML")
    await asyncio.sleep(0.5)
    await callback.message.edit_text("✌️ <i>Scissors... SHOOT!</i>", parse_mode="HTML")
    await asyncio.sleep(0.5)
    
    bot_choice = random.choice(["rock", "paper", "scissors"])
    emo = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}
    hh = is_happy_hour()
    if hh and random.random() < 0.20:
        if choice == "rock": bot_choice = "scissors"
        elif choice == "paper": bot_choice = "rock"
        else: bot_choice = "paper"
    
    text = f"⚔️ <b>BATTLE RESULT</b> ⚔️\n━━━━━━━━━━━━━━\n🧑‍💼 You: {emo[choice]}\n🤖 Dealer: {emo[bot_choice]}\n\n"
    user = db_get_user(user_id)
    whiskey_text = handle_whiskey_buff(user)
    hh_mark = "🌙" if hh else ""
    
    if choice == bot_choice:
        user["balance"] += bet 
        text += f"🤝 <b>DRAW!</b> Bet refunded.\n🏦 <b>Stash:</b> {user['balance']}{whiskey_text}"
        await callback.message.edit_text(text, parse_mode="HTML")
    elif (choice == "rock" and bot_choice == "scissors") or (choice == "paper" and bot_choice == "rock") or (choice == "scissors" and bot_choice == "paper"):
        win_amt = int(bet * get_50_50_mult(get_tier(bet), user))
        hijacked = await handle_loot_drops(bot, callback, user_id, user, win_amt, bet, hh_mark, whiskey_text)
        if not hijacked:
            text += f"✅ <b>YOU WON!</b> {hh_mark}\n💵 <b>Won:</b> +{win_amt}\n🏦 <b>Stash:</b> {user['balance']}{whiskey_text}{WIN_AD}"
            await callback.message.edit_text(text, parse_mode="HTML", disable_web_page_preview=True, reply_markup=get_share_markup(user_id, win_amt))
    else: 
        await process_loss_stats(user, bet)
        text += f"💀 <b>DEALER WINS!</b>\n📉 <i>Lost: {bet}</i>\n🏦 <b>Stash:</b> {user['balance']}{whiskey_text}"
        await callback.message.edit_text(text, parse_mode="HTML")
    db_save_user(user)

# ==========================================
# OBSŁUGA PRZYCISKU "CLAIM 100 BONUS CHIPS"
# ==========================================
@games_router.callback_query(F.data.startswith("claim_share_"))
async def process_share_bonus(callback: CallbackQuery):
    user_id = callback.from_user.id
    parts = callback.data.split("_")
    
    # Format to: claim_share_{game_id}_{win_amount}
    game_id = parts[2]
    win_amount = parts[3]
    unique_claim_key = f"{user_id}_{game_id}"
    
    # Sprawdzamy, czy gracz już odebrał bonus
    if unique_claim_key in CLAIMED_SHARES:
        await callback.answer("❌ You already claimed your chips for this win, mate!", show_alert=True)
        return
        
    user = db_get_user(user_id)
    user["balance"] += 100
    CLAIMED_SHARES.add(unique_claim_key)
    db_save_user(user)
    
    await callback.answer("🎉 Good on ya! 100 Bonus Chips credited to your stash!", show_alert=True)

@games_router.callback_query(F.data == "ask_for_story_screen")
async def ask_story(callback: CallbackQuery):
    await callback.message.answer(
        "📸 <b>Bonza!</b>\n\nTo claim your massive 500 Chips Story bonus:\n1. Post a Story on Telegram with our link.\n2. Take a screenshot of your Story.\n3. Send the photo to me right here!",
        parse_mode="HTML"
    )
    await callback.answer()

