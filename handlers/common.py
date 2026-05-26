import time
import random
import string
import qrcode
from io import BytesIO
from aiogram import Router, F, types, Bot
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile

from config import ADMIN_IDS, VIP_LINK, REAL_CASH_LINK, bot_state
from database import db_get_user, db_save_user, db_get_promo, db_save_promo
import keyboards as kb
from helpers import update_streak, get_xp_tier, check_subscription, handle_no_money

common_router = Router()

@common_router.message(Command("start"))
async def cmd_start(message: types.Message, bot: Bot):
    user_id = message.from_user.id
    user = db_get_user(user_id, message.from_user.username, message.from_user.full_name)
    is_new = (user["total_games"] == 0 and user["balance"] == 500 and user["xp"] == 0)
    user["state"] = "normal"
    
    args = message.text.split()
    if len(args) > 1:
        payload = args[1]
        # Sprawdzanie czy użytkownik kliknął w link za udostępnienie wygranej (Format: share_ID)
        if payload.startswith("share_"):
            try:
                sharer_id = int(payload.split("_")[1])
                if sharer_id != user_id:
                    sharer_user = db_get_user(sharer_id)
                    sharer_user["balance"] += 100
                    db_save_user(sharer_user)
                    try:
                        await bot.send_message(sharer_id, "💰 <b>SHARE BONUS!</b> A mate used your link! <b>+100 chips</b> added to your stash!", parse_mode="HTML")
                    except: pass
            except ValueError: pass
        # Standardowy system poleceń (Referral)
        else:
            try:
                ref_id = int(payload)
                if ref_id != user_id:
                    days_inactive = (time.time() - user.get("last_active", time.time())) / 86400
                    if is_new or days_inactive >= 5:
                        if not user.get("referral_pending"): 
                            user["referrer_id"] = ref_id
                            user["referral_pending"] = True
                            await message.answer("🎉 <b>BONZA!</b> You used a mate's invite link! <b>Play just ONE game</b> to instantly unlock 1000 chips for you, and a reward for your mate!", parse_mode="HTML")
            except ValueError: pass

    db_save_user(user)
    await update_streak(bot, user_id, message)

    if is_new:
        welcome_text = (
            f"🌟 <b>WELCOME TO THE VIP LOUNGE!</b> 🌟\n━━━━━━━━━━━━━━\n"
            f"<i>G'day, {message.from_user.first_name}! Here is a quick guide:</i>\n\n"
            f"🕹 <b>PLAY GAMES:</b> Multiply your chips in various mini-games.\n"
            f"🎁 <b>BONUSES:</b> Score free chips daily, smash quests, and earn XP to rank up.\n"
            f"💱 <b>CASH OUT:</b> Swap your chips for real cash promo codes!\n"
            f"🔥 <b>REAL CASH:</b> Hit the VIP club for massive payouts.\n\n"
            f"🏦 <b>Your starting Stash:</b> {user['balance']} 🪙\n👇 <i>Hit a button below to get cracking!</i>"
        )
    else:
        welcome_text = f"🌟 <b>WELCOME BACK, MATE!</b> 🌟\n━━━━━━━━━━━━━━\n<i>G'day, {message.from_user.first_name}!</i>\n\n🏦 <b>Stash:</b> {user['balance']} 🪙\n\n👇 <i>What's the game plan for today?</i>"

    await message.answer(welcome_text, reply_markup=kb.get_main_menu(user_id), parse_mode="HTML")

@common_router.message(F.text == "❌ Cancel Action")
async def cancel_action(message: types.Message):
    user = db_get_user(message.from_user.id)
    user["state"] = "normal"
    user["reply_to"] = None
    db_save_user(user)
    await message.answer("🏠 <i>Action Cancelled. Returned to the Main Pub.</i>", reply_markup=kb.get_main_menu(message.from_user.id), parse_mode="HTML")

@common_router.message(F.text == "🔙 Back to Main Pub")
async def go_back_main(message: types.Message): 
    user = db_get_user(message.from_user.id)
    user["state"] = "normal"
    db_save_user(user)
    await message.answer("🏠 <b>MAIN PUB</b>\n━━━━━━━━━━━━━━\n<i>What's the plan, mate?</i>", reply_markup=kb.get_main_menu(message.from_user.id), parse_mode="HTML")

@common_router.message(F.text == "🕹️ Play Games")
async def open_games_menu(message: types.Message): 
    user = db_get_user(message.from_user.id)
    user["state"] = "normal"
    db_save_user(user)
    await message.answer("🎰 <b>GAME FLOOR</b> 🎰\n━━━━━━━━━━━━━━\n<i>Pick your poison, mate:</i>", reply_markup=kb.games_menu, parse_mode="HTML")

@common_router.message(F.text == "📦 Mystery Box")
async def open_mystery_box_menu(message: types.Message):
    user = db_get_user(message.from_user.id)
    user["state"] = "normal"
    db_save_user(user)
    inv = user.get("inventory", [])
    if not inv:
        await message.answer("📦 <b>MYSTERY BOX & BOMBS</b>\n━━━━━━━━━━━━━━\n<i>Your stash is completely empty, mate. Play some games to find loot!</i>", parse_mode="HTML")
        return
    
    text = "📦 <b>YOUR LOOT STASH</b>\n━━━━━━━━━━━━━━\n"
    for item in inv:
        elapsed = time.time() - item["drop_time"]
        if item["type"] == "luck_bomb":
            rem = max(0, 86400 - elapsed)
            hours, rem_sec = divmod(rem, 3600)
            mins, _ = divmod(rem_sec, 60)
            text += f"💣 <b>Luck Bomb</b> - Explodes in: <i>{int(hours)}h {int(mins)}m</i>\n"
        elif item["type"] == "mystery_box":
            rem = max(0, (4 * 86400) - elapsed)
            days, rem_sec = divmod(rem, 86400)
            hours, _ = divmod(rem_sec, 3600)
            text += f"🎁 <b>Mystery Box</b> - Unlocks in: <i>{int(days)}d {int(hours)}h</i>\n"
    
    text += "\n<i>Just hang tight, mate. They'll open automatically when the timer hits zero!</i>"
    await message.answer(text, parse_mode="HTML")

@common_router.message(F.text == "🎁 Bonuses, Perks & Quests")
async def open_bonuses(message: types.Message):
    user = db_get_user(message.from_user.id)
    user["state"] = "normal"
    db_save_user(user)
    text = (
        "🎁 <b>THE BONUS LOUNGE</b>\n━━━━━━━━━━━━━━\n<i>Here's all the bloody ripper perks you can score:</i>\n\n"
        "🎡 <b>Daily Wheel:</b> Spin it once a day for a chance at the 5000 chip Jackpot.\n"
        "📋 <b>Quests:</b> Post stories (Daily +2000 chips) or invite mates (+3000 chips)!\n"
        "💸 <b>Cashback:</b> Play every single day (Mon-Sun) and get <b>7% of your losses back</b> on Monday morning!\n"
        "🌟 <b>XP & Ranks:</b> Earn XP by playing and hitting win streaks. Reach Gold to unlock the Secret Promo Vault!\n"
        "🎟 <b>Promo Codes:</b> Enter codes here to grab free stash."
    )
    await message.answer(text, reply_markup=kb.bonuses_menu, parse_mode="HTML")

@common_router.message(F.text == "👤 Profile & Settings")
async def open_profile(message: types.Message):
    user = db_get_user(message.from_user.id)
    user["state"] = "normal"
    db_save_user(user)
    await message.answer("👤 <b>PROFILE SETTINGS</b>\n<i>Check your stats and info here.</i>", reply_markup=kb.profile_menu, parse_mode="HTML")

@common_router.message(F.text == "📢 VIP Bonus")
async def join_vip_menu(message: types.Message):
    user = db_get_user(message.from_user.id)
    user["state"] = "normal"
    db_save_user(user)
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Join Channel Now", url=VIP_LINK)],
        [InlineKeyboardButton(text="🎁 Check & Claim 2000 Chips", callback_data="check_sub_bonus")]
    ])
    await message.answer("📢 <b>VIP CHANNEL ACCESS</b>\n━━━━━━━━━━━━━━\n<i>Join our exclusive channel to stay updated on big wins and cop an instant <b>2000 CHIPS</b> bonus, mate!</i>", reply_markup=markup, parse_mode="HTML")

@common_router.callback_query(F.data == "check_sub_bonus")
async def process_sub_bonus(callback: types.CallbackQuery, bot: Bot):
    user = db_get_user(callback.from_user.id)
    if user.get("claimed_sub_bonus"): return await callback.answer("Already claimed, mate!", show_alert=True)
    if await check_subscription(bot, callback.from_user.id):
        user["balance"] += 2000
        user["claimed_sub_bonus"] = True
        db_save_user(user)
        await callback.message.edit_text(f"🎉 <b>BONUS UNLOCKED!</b> 🎉\n━━━━━━━━━━━━━━\n💵 +2000 chips!\n🏦 <b>Stash:</b> {user['balance']} 🪙", parse_mode="HTML")
    else: await callback.answer("❌ Haven't joined yet, mate!", show_alert=True)

@common_router.message(F.text == "🥃 Buy Whiskey")
async def buy_whiskey(message: types.Message, bot: Bot):
    user = db_get_user(message.from_user.id, message.from_user.username, message.from_user.full_name)
    user["state"] = "normal"
    if user["balance"] < 500: return await handle_no_money(bot, message, user)
    if user["whiskey_buff"] > 0: return await message.answer(f"🥃 <i>Finish your glass first, mate! (Buff active for {user['whiskey_buff']} more rounds)</i>", parse_mode="HTML")
    user["balance"] -= 500
    user["whiskey_buff"] = 3
    db_save_user(user)
    await message.answer(f"🥃 <b>CHEERS!</b> 🥃\n━━━━━━━━━━━━━━\n<i>Liquid courage flows through your veins!</i>\n\n🍀 <b>BUFF ACTIVE:</b>\nMultipliers boosted for <b>3 games</b>.\n\n🏦 <b>Stash:</b> {user['balance']} 🪙", parse_mode="HTML")

@common_router.message(F.text == "📖 The Rules")
async def show_rules(message: types.Message):
    user = db_get_user(message.from_user.id)
    user["state"] = "normal"
    db_save_user(user)
    rules_text = "📜 <b>THE RULES</b> 📜\n━━━━━━━━━━━━━━\n<i>Higher bets unlock better odds! (Min: 50)</i>\n\n🟢 <b>TIER 1 (50 - 249 chips):</b>\n ├ 50/50 Games: <b>x1.8</b>\n └ Chests: <b>x2.5</b>\n\n🟣 <b>TIER 2 (250 - 499 chips):</b>\n ├ 50/50 Games: <b>x1.9</b>\n └ Chests: <b>x2.7</b>\n\n🟡 <b>TIER 3 (500+ chips):</b>\n ├ 50/50 Games: <b>x1.95</b>\n └ Chests: <b>x2.8</b>\n\n🥃 <b>WHISKEY BUFF (500 chips):</b>\n └ Adds <b>+0.2</b> to ALL multipliers for 3 games!\n\n🌙 <b>HAPPY HOURS:</b>\n └ Daily: 22:00-01:00 AEST. Weekends: 21:00-03:00 AEST. Win chance & multipliers boosted!\n\n🎯 <b>CASH OUT:</b>\n └ Use the Cash Out menu to turn chips into real dingo dollars!"
    await message.answer(rules_text, parse_mode="HTML")

@common_router.message(F.text == "🎡 Daily Spin")
async def daily_bonus(message: types.Message):
    user = db_get_user(message.from_user.id, message.from_user.username, message.from_user.full_name)
    user["state"] = "normal"
    current_time = time.time()
    if current_time - user["last_daily"] < 86400:
        return await message.answer(f"⏳ <b>COOLDOWN</b>\n━━━━━━━━━━━━━━\n<i>Come back in</i> <b>{int((86400 - (current_time - user['last_daily'])) // 3600)} hours</b>, mate.", parse_mode="HTML")
    user["last_daily"] = current_time
    
    prizes = [("💀 Bugger all", 0), ("💩 Try again later", 50), ("🔵 100 chips", 100), ("🟣 250 chips", 250), ("🟡 500 chips", 500), ("🔥 1000 chips", 1000), ("💎 JACKPOT", 5000)]
    weights = [15, 20, 30, 20, 10, 4, 1]
    p_name, p_val = random.choices(prizes, weights=weights, k=1)[0]
    user["balance"] += p_val
    db_save_user(user)
    await message.answer(f"🎡 <b>WHEEL OF FORTUNE</b> 🎡\n━━━━━━━━━━━━━━\n🎁 <b>Prize:</b> {p_name}!\n🏦 <b>Stash:</b> {user['balance']} 🪙", parse_mode="HTML")

@common_router.message(F.text == "🔥 PLAY FOR REAL CASH 🔥")
async def go_to_casino(message: types.Message): 
    user = db_get_user(message.from_user.id)
    user["state"] = "normal"
    db_save_user(user)
    await message.answer("💸 <b>REAL MONEY MODE</b> 💸\n━━━━━━━━━━━━━━\n<i>Snag a <b>100% match bonus</b> right now, mate!</i>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🎰 Hit the VIP Club 🚀", url=REAL_CASH_LINK)]]), parse_mode="HTML")

@common_router.message(F.text == "📊 My Stats")
async def my_stats(message: types.Message):
    user = db_get_user(message.from_user.id, message.from_user.username, message.from_user.full_name)
    user["state"] = "normal"
    db_save_user(user)
    tier = get_xp_tier(user["xp"])
    text = (
        f"📊 <b>YOUR STATS</b> 📊\n━━━━━━━━━━━━━━\n👤 <b>Player:</b> {message.from_user.first_name}\n🏅 <b>Rank:</b> {tier}\n"
        f"🎖 <b>XP:</b> {user['xp']}\n🏦 <b>Stash:</b> {user['balance']} 🪙\n\n🔥 <b>Current Win Streak:</b> {user['win_streak']}\n"
        f"🎲 <b>Total Games:</b> {user['total_games']}\n🏆 <b>Total Chips Won:</b> {user['total_won_chips']}\n🫂 <b>Mates Invited:</b> {user['referrals']}"
    )
    await message.answer(text, parse_mode="HTML")

@common_router.message(F.text == "📋 Quests")
async def show_quests(message: types.Message):
    user = db_get_user(message.from_user.id, message.from_user.username, message.from_user.full_name)
    user["state"] = "normal"
    db_save_user(user)
    can_claim_story = (time.time() - user.get("last_story_claim", 0) >= 86400)
    s_stat = "🎁 2000 chips + 500 XP" if can_claim_story else "✅ Done (Wait 24h)"
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📸 Post to Stories ({s_stat})", callback_data="quest_stories")],
        [InlineKeyboardButton(text=f"🫂 Invite Mates (🎁 3000 chips + 1000 XP)", callback_data="quest_referral")]
    ])
    await message.answer("📋 <b>DAILY QUESTS</b> 📋\n━━━━━━━━━━━━━━\n<i>Smash these tasks to earn huge chip rewards and XP to rank up, mate!</i>", reply_markup=markup, parse_mode="HTML")

@common_router.callback_query(F.data == "quest_stories")
async def cq_stories(callback: types.CallbackQuery):
    user = db_get_user(callback.from_user.id)
    if time.time() - user.get("last_story_claim", 0) < 86400:
        rem = int((86400 - (time.time() - user["last_story_claim"])) // 3600)
        return await callback.answer(f"Hold your horses, mate! You can post another story in {rem} hours.", show_alert=True)

    ref_link = f"https://t.me/{bot_state.get('bot_username', 'Vipclubcasinobot')}?start={callback.from_user.id}"
    user["story_link_gen_time"] = time.time()
    user["state"] = "waiting_story"
    db_save_user(user)
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(ref_link); qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    bio = BytesIO(); img.save(bio, "PNG"); bio.seek(0)
    
    text = (
        f"📸 <b>YOUR PERSONAL STORY LINK</b>\n━━━━━━━━━━━━━━\n<i>To cop this bonus, simply copy the text below and chuck it on your Instagram/Telegram story along with the QR code:</i>\n\n"
        f"<code>Hey mates! Try your luck in this ripper bot. Use my link to get a 1000 chips bonus: {ref_link}</code>\n\n<i>(Tap the text to copy it)</i>\n\nOnce it's posted, send me a screenshot of your story right here, and the admin will verify it!"
    )
    await callback.message.answer_photo(photo=BufferedInputFile(bio.getvalue(), filename="qr.png"), caption=text, parse_mode="HTML")
    await callback.answer()

@common_router.callback_query(F.data == "quest_referral")
async def cq_referral(callback: types.CallbackQuery):
    user = db_get_user(callback.from_user.id)
    ref_link = f"https://t.me/{bot_state.get('bot_username', 'Vipclubcasinobot')}?start={callback.from_user.id}"
    text = (
        f"🫂 <b>INVITE YOUR MATES</b>\n━━━━━━━━━━━━━━\nInvite mates to snag <b>3000 chips</b> and <b>1000 XP</b> per friend!\n\n"
        f"<b>THE RULES:</b>\n1. Your mate must be brand new OR inactive for 5+ days.\n2. They MUST play at least <b>1 game</b> for you to get the rewards!\n\n"
        f"📊 <b>Total Successful Invites:</b> {user['referrals']}\n\n<i>Just copy the text below and send it to your mates:</i>\n\n"
        f"<code>Mate, jump in and play this bot! There's a solid chance to make some real dingo dollars here, and as a new player, you'll cop a bonza 1000 chips bonus. Join here: {ref_link}</code>\n\n<i>(Tap the text to copy)</i>"
    )
    markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Back", callback_data="back_quests")]])
    await callback.message.edit_text(text, reply_markup=markup, parse_mode="HTML")

@common_router.callback_query(F.data == "back_quests")
async def cq_back_quests(callback: types.CallbackQuery, bot: Bot):
    await callback.message.delete()
    # Przekierowanie strukturalne wywołania wiadomości
    callback.message.from_user = callback.from_user
    await show_quests(callback.message)

@common_router.message(F.text == "💱 Cash Out")
async def exchange_menu(message: types.Message, bot: Bot):
    user = db_get_user(message.from_user.id, message.from_user.username, message.from_user.full_name)
    user["state"] = "normal"
    db_save_user(user)
    subbed = await check_subscription(bot, message.from_user.id)
    story = (time.time() - user.get("last_story_claim", 0) < 86400)
    ref = user.get("referrals", 0) >= 1
    
    if subbed and story and ref:
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💵 10,000 Chips -> $5", callback_data="exchange_10000_5")],
            [InlineKeyboardButton(text="💵 20,000 Chips -> $10", callback_data="exchange_20000_10")],
            [InlineKeyboardButton(text="💵 30,000 Chips -> $15", callback_data="exchange_30000_15")]
        ])
        await message.answer(f"💱 <b>CASH OUT</b>\n━━━━━━━━━━━━━━\n🏦 <b>Your Stash:</b> {user['balance']} 🪙\n<i>Pick a reward to generate your real cash promo code, mate:</i>", reply_markup=markup, parse_mode="HTML")
    else:
        markup = InlineKeyboardMarkup(inline_keyboard=[])
        if not subbed: markup.inline_keyboard.append([InlineKeyboardButton(text="📢 1. Join VIP Channel", url=VIP_LINK)])
        if not story: markup.inline_keyboard.append([InlineKeyboardButton(text="📸 2. Do the Story Quest", callback_data="quest_stories")])
        if not ref: markup.inline_keyboard.append([InlineKeyboardButton(text="🫂 3. Get Referral Link", callback_data="quest_referral")])
        status_sub = "✅" if subbed else "❌"
        status_story = "✅" if story else "❌"
        status_ref = "✅" if ref else "❌"
        text = (
            f"💱 <b>CASH OUT REQUIREMENTS</b>\n━━━━━━━━━━━━━━\n<i>Hold up, mate! To swap your chips for real dingo dollars, you gotta complete these 3 simple tasks first:</i>\n\n"
            f"{status_sub} <b>1. Join VIP Channel</b>\n{status_story} <b>2. Post a Story</b> (within 24h)\n{status_ref} <b>3. Invite at least 1 mate</b>\n\n"
            f"<i>Think this is a bit of hard yakka? Remember, you're getting real cash for it, mate!</i>\n\n👇 Smash the buttons below to sort it out quick!"
        )
        await message.answer(text, reply_markup=markup, parse_mode="HTML")

@common_router.callback_query(F.data.startswith("exchange_"))
async def process_exchange(callback: types.CallbackQuery):
    user = db_get_user(callback.from_user.id)
    parts = callback.data.split("_")
    cost, reward = int(parts[1]), int(parts[2])
    if user["balance"] < cost: return await callback.answer(f"❌ You need {cost} chips, mate!", show_alert=True)
    user["balance"] -= cost 
    
    chars = string.ascii_uppercase + string.digits
    code = ''.join(random.choices(chars, k=10))
    promo = f"BONUS{reward}-{code}"
    db_save_promo(promo, reward, 1, set())
    db_save_user(user)
    
    link = f"https://t.me/Vipclubcasinobot?start={reward}$Gamebot"
    markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"🎰 Claim ${reward} Cash Here", url=link)]])
    await callback.message.edit_text(f"🎉 <b>EXCHANGE SUCCESSFUL!</b> 🎉\n━━━━━━━━━━━━━━\n🔥 <i>{cost} chips burned!</i>\n\n🎁 <b>Your ${reward} Promo Code:</b>\n<code>{promo}</code>\n<i>(Tap to copy and send to VIP Support if needed)</i>\n\n🏦 <b>Remaining Stash:</b> {user['balance']} 🪙", reply_markup=markup, parse_mode="HTML")

@common_router.message(F.text == "🎟 Promo Code")
async def promo_menu_btn(message: types.Message):
    if message.from_user.id in ADMIN_IDS:
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✍️ Enter Promo Code", callback_data="admin_promo_enter")],
            [InlineKeyboardButton(text="🛠 Generate Promo", callback_data="admin_promo_gen")],
            [InlineKeyboardButton(text="📝 Active Promo Codes", callback_data="admin_active_promos")]
        ])
        await message.answer("🎟 <b>Promo Code Menu (Admin)</b>", reply_markup=markup, parse_mode="HTML")
    else:
        user = db_get_user(message.from_user.id)
        user["state"] = "waiting_promo"
        db_save_user(user)
        await message.answer("🎟 <b>ENTER PROMO CODE</b>\n━━━━━━━━━━━━━━\n<i>Chuck your promo code down below, mate:</i>", reply_markup=kb.support_menu, parse_mode="HTML")

@common_router.message(F.text == "🆘 Support")
async def ask_support(message: types.Message):
    user = db_get_user(message.from_user.id, message.from_user.username, message.from_user.full_name)
    user["state"] = "support"
    db_save_user(user)
    await message.answer("🆘 <b>SUPPORT DESK</b>\n━━━━━━━━━━━━━━\n<i>Got an issue? Describe it clearly in one message, mate.</i>", reply_markup=kb.support_menu, parse_mode="HTML")