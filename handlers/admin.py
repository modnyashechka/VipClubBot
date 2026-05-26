import random
import string
import time
from datetime import datetime
from aiogram import Router, F, types, Bot
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import ADMIN_IDS, bot_state
from database import db_get_user, db_save_user, db_get_all_promos, db_save_promo, db_get_all_users, db_delete_promo
import keyboards as kb
from helpers import get_xp_tier, ai_spam_filter, add_xp

admin_router = Router()

async def show_player_card(message, target_id, u):
    tier = get_xp_tier(u["xp"])
    status = "🚫 BANNED" if u.get("is_banned") else "✅ Active"
    safe_name = str(u.get('full_name', 'N/A')).replace("<", "").replace(">", "")
    safe_user = str(u.get('username', 'N/A')).replace("<", "").replace(">", "")
    
    text = (f"👤 <b>PLAYER INFO</b>\n━━━━━━━━━━━━━━\n<b>Name:</b> {safe_name} (@{safe_user})\n<b>ID:</b> <code>{target_id}</code>\n"
            f"<b>Status:</b> {status}\n<b>Rank:</b> {tier} ({u['xp']} XP)\n🏦 <b>Stash:</b> {u['balance']}\n"
            f"🎲 <b>Games Today:</b> {u['daily_games']} | Total: {u['total_games']}\n🏆 <b>Won Chips:</b> {u['total_won_chips']}\n🫂 <b>Referrals:</b> {u['referrals']}")
    
    ban_btn = "✅ Unblock Player" if u.get("is_banned") else "🚫 Block Player"
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Edit Chips", callback_data=f"editchips_{target_id}"), InlineKeyboardButton(text="🎖 Edit XP", callback_data=f"editxp_{target_id}")],
        [InlineKeyboardButton(text="💬 Send Comment", callback_data=f"adminmsg_{target_id}")],
        [InlineKeyboardButton(text=ban_btn, callback_data=f"toggleban_{target_id}")]
    ])
    await message.answer(text, reply_markup=markup, parse_mode="HTML")

@admin_router.message(F.text == "🛠 Admin Instructions")
async def cmd_admin_help(message: types.Message):
    if message.from_user.id not in ADMIN_IDS: return
    user = db_get_user(message.from_user.id)
    user["state"] = "normal"
    db_save_user(user)
    text = (
        "🛠 <b>ADMIN PANEL INSTRUCTIONS</b>\n━━━━━━━━━━━━━━\n<b>1. 🔍 Player Search:</b>\nHit the search button and type the ID or @username. In the player card, you can edit chips, XP, send a DM, or ban them.\n\n"
        "<b>2. 🎟 Promo Codes:</b>\nGo to 'Promo Code' menu to generate codes for multiple users, or check active codes.\n\n"
        "<b>3. 🛑 Maintenance Mode:</b>\nType <code>/shutdown</code> — bot locks out normal players.\nType <code>/start_bot</code> — bot reopens and sends a 1500 chip apology to anyone who tried to play.\n\n"
        "<b>4. 🏆 Leaderboard:</b>\nType <code>/leaderboard</code> to get a copy-paste ready list of today's top players."
    )
    await message.answer(text, parse_mode="HTML")

@admin_router.message(F.text == "🔍 Player Search")
async def admin_player_search(message: types.Message):
    if message.from_user.id not in ADMIN_IDS: return
    user = db_get_user(message.from_user.id)
    user["state"] = "admin_search"
    db_save_user(user)
    await message.answer("🔍 <b>PLAYER SEARCH</b>\nType the player's ID or @username, mate:", reply_markup=kb.support_menu, parse_mode="HTML")

@admin_router.message(Command("leaderboard"))
async def cmd_leaderboard(message: types.Message):
    if message.from_user.id not in ADMIN_IDS: return
    users = db_get_all_users()
    sorted_users = sorted(users, key=lambda x: x.get("daily_games", 0), reverse=True)
    text = "🔥 <b>TODAY'S MOST ACTIVE LEGENDS</b> 🔥\n\n"
    found = False
    for i, u in enumerate(sorted_users[:10]):
        if u.get("daily_games", 0) == 0: continue
        found = True
        name = u.get("username") or u.get("full_name") or "Unknown"
        tier = get_xp_tier(u.get("xp", 0)).split(" ")[1] 
        text += f"{i+1}. <b>{name}</b> ({tier}) - {u['daily_games']} games\n"
    if not found: text += "No games played today, mate."
    text += "\n<i>Copy this and drop it in the VIP channel!</i>"
    await message.answer(text, parse_mode="HTML")

@admin_router.message(Command("shutdown"))
async def cmd_shutdown(message: types.Message):
    if message.from_user.id in ADMIN_IDS:
        bot_state["maintenance"] = True
        await message.answer("🛑 <b>MAINTENANCE MODE ON</b>\nBot locked. Players will get a polite Aussie apology.", parse_mode="HTML")

@admin_router.message(Command("start_bot"))
async def cmd_start_bot(message: types.Message, bot: Bot):
    if message.from_user.id not in ADMIN_IDS: return
    bot_state["maintenance"] = False
    count = 0
    for uid in list(bot_state["affected_users"]):
        try:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            db_save_promo(code, 1500, 1, set())
            await bot.send_message(uid, f"✅ <b>WE'RE BACK ONLINE, MATE!</b>\n━━━━━━━━━━━━━━\nThanks for holding your horses! As an apology for the downtime, grab this promo code for <b>1500 chips</b>:\n<code>{code}</code>\n\nChuck it in '🎟 Promo Code' to claim it.", parse_mode="HTML")
            count += 1
        except Exception: pass
    bot_state["affected_users"].clear()
    await message.answer(f"✅ <b>MAINTENANCE MODE OFF</b>\nBot is fully operational. Apology sent to {count} players.", parse_mode="HTML")

@admin_router.callback_query(F.data == "admin_active_promos")
async def admin_active_promos_list(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS: return
    promos = db_get_all_promos()
    if not promos: return await callback.message.answer("No active promo codes right now, mate.", parse_mode="HTML")
    text = "📝 <b>ACTIVE PROMO CODES</b>\n━━━━━━━━━━━━━━\n"
    for p in promos:
        text += f"<code>{p['code']}</code> | <b>{p['amount']} chips</b> | Uses left: {p['uses']}\n"
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()

@admin_router.callback_query(F.data == "admin_promo_enter")
async def cq_admin_promo_enter(callback: types.CallbackQuery):
    user = db_get_user(callback.from_user.id)
    user["state"] = "waiting_promo"
    db_save_user(user)
    await callback.message.answer("🎟 <b>ENTER PROMO CODE</b>\n<i>Send me your promo code below:</i>", reply_markup=kb.support_menu, parse_mode="HTML")
    await callback.answer()

@admin_router.callback_query(F.data == "admin_promo_gen")
async def cq_admin_promo_gen(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS: return
    user = db_get_user(callback.from_user.id)
    user["state"] = "admin_gen_promo_amt"
    db_save_user(user)
    await callback.message.answer("🛠 <b>GENERATE PROMO</b>\n<i>Type the chip amount for this promo code:</i>", reply_markup=kb.support_menu, parse_mode="HTML")
    await callback.answer()

@admin_router.callback_query(F.data.startswith("editchips_"))
async def admin_edit_chips_btn(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS: return
    admin = db_get_user(callback.from_user.id)
    admin["state"] = "admin_edit_chips"
    admin["reply_to"] = int(callback.data.split("_")[1])
    db_save_user(admin)
    await callback.message.answer("💰 <b>EDIT CHIPS</b>\n<i>Type the EXACT amount of chips for their stash:</i>", reply_markup=kb.support_menu, parse_mode="HTML")
    await callback.answer()

@admin_router.callback_query(F.data.startswith("editxp_"))
async def admin_edit_xp_btn(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS: return
    admin = db_get_user(callback.from_user.id)
    admin["state"] = "admin_edit_xp"
    admin["reply_to"] = int(callback.data.split("_")[1])
    db_save_user(admin)
    await callback.message.answer("🎖 <b>EDIT XP (Rank)</b>\n<i>Type the EXACT amount of XP (Rank updates automatically):</i>", reply_markup=kb.support_menu, parse_mode="HTML")
    await callback.answer()

@admin_router.callback_query(F.data.startswith("adminmsg_"))
async def admin_send_comment_btn(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS: return
    admin = db_get_user(callback.from_user.id)
    admin["state"] = "admin_send_comment"
    admin["reply_to"] = int(callback.data.split("_")[1])
    db_save_user(admin)
    await callback.message.answer("💬 <b>SEND COMMENT</b>\n<i>Type the message you want to send this player:</i>", reply_markup=kb.support_menu, parse_mode="HTML")
    await callback.answer()

@admin_router.callback_query(F.data.startswith("toggleban_"))
async def admin_toggle_ban_btn(callback: types.CallbackQuery, bot: Bot):
    if callback.from_user.id not in ADMIN_IDS: return
    target_id = int(callback.data.split("_")[1])
    target_user = db_get_user(target_id)
    
    if target_user.get("is_banned"):
        target_user["is_banned"] = False
        await callback.answer("✅ Player Unblocked!")
        await callback.message.answer("Player unblocked successfully, mate.")
    else:
        target_user["is_banned"] = True
        try: await bot.send_message(target_id, "⚠️ Telegram has blocked this bot for you, mate. Further actions are disabled.")
        except: pass
        await callback.answer("🚫 Player Blocked!")
        await callback.message.answer("Player banned. The dummy message has been sent to them.")
    
    db_save_user(target_user)
    await show_player_card(callback.message, target_id, target_user)

@admin_router.callback_query(F.data.startswith("reply_user_"))
async def admin_reply_btn(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS: return
    admin = db_get_user(callback.from_user.id)
    admin["state"] = "replying"
    admin["reply_to"] = int(callback.data.split("_")[2])
    db_save_user(admin)
    await callback.message.answer("⌨️ <b>REPLY MODE</b>\n<i>Type your message to the player:</i>", reply_markup=kb.support_menu, parse_mode="HTML")
    await callback.answer()

@admin_router.callback_query(F.data.startswith("givechips_"))
async def admin_give_chips_btn(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS: return
    admin = db_get_user(callback.from_user.id)
    admin["state"] = "giving_chips"
    admin["reply_to"] = int(callback.data.split("_")[1])
    db_save_user(admin)
    await callback.message.answer("💰 <b>GIVE CHIPS</b>\n<i>Type the exact amount of chips to toss their way:</i>", reply_markup=kb.support_menu, parse_mode="HTML")
    await callback.answer()

@admin_router.callback_query(F.data.startswith("givexp_"))
async def admin_give_xp_btn(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS: return
    admin = db_get_user(callback.from_user.id)
    admin["state"] = "giving_xp"
    admin["reply_to"] = int(callback.data.split("_")[1])
    db_save_user(admin)
    await callback.message.answer("🎖 <b>GIVE XP</b>\n<i>Type the exact amount of XP to grant:</i>", reply_markup=kb.support_menu, parse_mode="HTML")
    await callback.answer()

@admin_router.message(F.photo | F.document)
async def verify_story_photo(message: types.Message, bot: Bot):
    user = db_get_user(message.from_user.id, message.from_user.username, message.from_user.full_name)
    if user.get("state") != "waiting_story": return 
    
    if message.photo: photo = message.photo[-1].file_id
    elif message.document and message.document.mime_type.startswith('image/'): photo = message.document.file_id
    else: return await message.answer("Mate, that's not a picture! Send a proper screenshot.")
        
    gen_time = user.get("story_link_gen_time")
    dt_str = datetime.fromtimestamp(gen_time).strftime('%Y-%m-%d %H:%M:%S') if gen_time else "Never generated"
    tier = get_xp_tier(user["xp"])
    
    safe_name = (message.from_user.full_name or "Unknown").replace("<", "").replace(">", "").replace("&", "")
    safe_user = (message.from_user.username or "No Username").replace("<", "").replace(">", "").replace("&", "")
    
    cap = (f"📸 <b>NEW STORY PROOF</b>\n👤 <b>Player:</b> <a href='tg://user?id={message.from_user.id}'>{safe_name}</a> (@{safe_user})\n"
           f"🏅 <b>Rank:</b> {tier}\n🕒 <b>Link Gen Time:</b> {dt_str}\n⚠️ <b>Link used by others:</b> No (Unique to this user ID)\n\n<i>Have a squiz and decide, Admin!</i>")
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Approve", callback_data=f"approve_story_{message.from_user.id}"),
         InlineKeyboardButton(text="❌ Reject", callback_data=f"reject_story_{message.from_user.id}")]
    ])
    
    for adm in ADMIN_IDS:
        try: await bot.send_photo(adm, photo, caption=cap, reply_markup=markup, parse_mode="HTML")
        except: pass
        
    await message.answer("✅ <b>Proof sent to the Admins!</b>\n<i>Hold your horses, mate. We'll verify it shortly...</i>", parse_mode="HTML")
    user["state"] = "normal"
    db_save_user(user)

@admin_router.callback_query(F.data.startswith("approve_story_"))
async def approve_story(callback: types.CallbackQuery, bot: Bot):
    if callback.from_user.id not in ADMIN_IDS: return
    user_id = int(callback.data.split("_")[2])
    user = db_get_user(user_id)
    
    user["last_story_claim"] = time.time()
    user["balance"] += 2000
    db_save_user(user)
    await add_xp(bot, user_id, 500)
    
    try: await bot.send_message(user_id, "🎉 <b>STORY VERIFIED!</b>\n━━━━━━━━━━━━━━\nBloody legend! +2000 chips and +500 XP chucked into your stash!", parse_mode="HTML")
    except: pass
    await callback.message.edit_caption(caption="✅ <b>Story Approved & Rewarded!</b>", reply_markup=None)
    await callback.answer("Bonus granted!")

@admin_router.callback_query(F.data.startswith("reject_story_"))
async def reject_story(callback: types.CallbackQuery, bot: Bot):
    if callback.from_user.id not in ADMIN_IDS: return
    user_id = int(callback.data.split("_")[2])
    try: await bot.send_message(user_id, "❌ <b>STORY REJECTED</b>\n━━━━━━━━━━━━━━\nMate, your story proof was rejected by the admin. Ensure the link is visible and try again via the Quests menu.", parse_mode="HTML")
    except: pass
    await callback.message.edit_caption(caption="❌ <b>Story Rejected!</b>", reply_markup=None)
    await callback.answer("User notified!")

@admin_router.message(lambda msg: db_get_user(msg.from_user.id).get("state") != "normal")
async def process_states(message: types.Message, bot: Bot):
    user = db_get_user(message.from_user.id)
    state = user["state"]
    text = message.text or message.caption
    if not text: return
    
    if state == "support":
        if not await ai_spam_filter(text):
            return await message.answer("🚫 <b>AI Filter Blocked This Message</b>\n<i>Looks dodgy, mate. Please send a clear text describing your issue.</i>", parse_mode="HTML")
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💬 Reply", callback_data=f"reply_user_{message.from_user.id}")],
            [InlineKeyboardButton(text="💸 Give Chips", callback_data=f"givechips_{message.from_user.id}"), InlineKeyboardButton(text="🎖 Give XP", callback_data=f"givexp_{message.from_user.id}")]
        ])
        safe_name = (message.from_user.full_name or "Unknown").replace("<", "").replace(">", "")
        safe_user = (message.from_user.username or "No Username").replace("<", "").replace(">", "")
        admin_text = f"🚨 <b>NEW TICKET</b>\n👤 <b>From:</b> <a href='tg://user?id={message.from_user.id}'>{safe_name}</a> (@{safe_user} | <code>{message.from_user.id}</code>)\n💬 <b>Msg:</b> {text}"
        
        for adm in ADMIN_IDS:
            try: await bot.send_message(adm, admin_text, reply_markup=markup, parse_mode="HTML")
            except: pass
            
        user["state"] = "normal"
        db_save_user(user)
        await message.answer("✅ <b>Message Sent!</b> We'll shout back shortly, mate.", reply_markup=kb.get_main_menu(message.from_user.id), parse_mode="HTML")

    elif state == "replying":
        target_id = user["reply_to"]
        try:
            await bot.send_message(target_id, f"👨‍💻 <b>ADMIN RESPONSE</b>\n━━━━━━━━━━━━━━\n{text}", parse_mode="HTML")
            await message.answer("✅ <b>Reply sent!</b>", reply_markup=kb.get_main_menu(message.from_user.id), parse_mode="HTML")
        except: await message.answer("❌ Failed to send message.", reply_markup=kb.get_main_menu(message.from_user.id))
        user["state"] = "normal"; user["reply_to"] = None; db_save_user(user)

    elif state == "giving_chips":
        if not text.isdigit(): return await message.answer("❌ Invalid amount. Must be a number, mate.")
        amount = int(text)
        target_id = user["reply_to"]
        try:
            target_user = db_get_user(target_id)
            target_user["balance"] += amount
            db_save_user(target_user)
            await bot.send_message(target_id, f"🎁 <b>ADMIN BONUS</b>\n━━━━━━━━━━━━━━\nSupport team chucked <b>{amount} chips</b> into your stash!\n🏦 <b>Stash:</b> {target_user['balance']}", parse_mode="HTML")
            await message.answer(f"✅ <b>Successfully gave {amount} chips!</b>", reply_markup=kb.get_main_menu(message.from_user.id), parse_mode="HTML")
        except Exception as e: await message.answer(f"❌ Error: {e}", reply_markup=kb.get_main_menu(message.from_user.id))
        user["state"] = "normal"; user["reply_to"] = None; db_save_user(user)

    elif state == "giving_xp":
        if not text.isdigit(): return await message.answer("❌ Invalid amount. Must be a number, mate.")
        amount = int(text)
        target_id = user["reply_to"]
        try:
            await add_xp(bot, target_id, amount)
            await bot.send_message(target_id, f"🎖 <b>ADMIN XP BONUS</b>\n━━━━━━━━━━━━━━\nSupport team awarded you <b>{amount} XP</b>! Keep climbing the ranks, mate!", parse_mode="HTML")
            await message.answer(f"✅ <b>Successfully gave {amount} XP!</b>", reply_markup=kb.get_main_menu(message.from_user.id), parse_mode="HTML")
        except Exception as e: await message.answer(f"❌ Error: {e}", reply_markup=kb.get_main_menu(message.from_user.id))
        user["state"] = "normal"; user["reply_to"] = None; db_save_user(user)

    elif state == "waiting_promo":
        code = text.strip()
        promo = db_get_promo(code)
        if promo:
            if message.from_user.id in promo["claimed_by"]:
                await message.answer("❌ <b>You've already claimed this code, mate!</b>", parse_mode="HTML")
            elif promo["uses"] > 0:
                promo["uses"] -= 1
                promo["claimed_by"].add(message.from_user.id)
                user["balance"] += promo["amount"]
                if promo["uses"] == 0: db_delete_promo(code)
                else: db_save_promo(code, promo["amount"], promo["uses"], promo["claimed_by"])
                user["state"] = "normal"
                db_save_user(user)
                await message.answer(f"🎉 <b>PROMO CODE ACCEPTED!</b>\n━━━━━━━━━━━━━━\n+{promo['amount']} chips added to your stash!\n🏦 <b>Stash:</b> {user['balance']} 🪙", reply_markup=kb.get_main_menu(message.from_user.id), parse_mode="HTML")
            else: await message.answer("❌ <b>This promo code has reached its maximum uses!</b>", parse_mode="HTML")
        else: await message.answer("❌ <b>Dodgy or Expired Promo Code.</b>\nGive it another crack or Cancel.", parse_mode="HTML")
            
    elif state == "admin_gen_promo_amt":
        if not text.isdigit(): return await message.answer("❌ Invalid amount. Needs to be a number.")
        user["temp_promo_amt"] = int(text)
        user["state"] = "admin_gen_promo_uses"
        db_save_user(user)
        await message.answer("🛠 <b>GENERATE PROMO (Step 2)</b>\n<i>How many players can use this code? (Enter number):</i>", parse_mode="HTML")
        
    elif state == "admin_gen_promo_uses":
        if not text.isdigit(): return await message.answer("❌ Invalid uses count. Needs to be a number.")
        uses = int(text)
        amt = user["temp_promo_amt"]
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        db_save_promo(code, amt, uses, set())
        user["state"] = "normal"
        db_save_user(user)
        await message.answer(f"✅ <b>PROMO CREATED</b>\n━━━━━━━━━━━━━━\nCode: <code>{code}</code>\nAmount: {amt} chips\nUses: {uses} times", reply_markup=kb.get_main_menu(message.from_user.id), parse_mode="HTML")

    elif state == "admin_search":
        query = text.replace("@", "").lower()
        target_id = None
        users = db_get_all_users()
        if query.isdigit():
            if any(u["user_id"] == int(query) for u in users): target_id = int(query)
        else:
            for u in users:
                if u.get("username") and u["username"].lower() == query:
                    target_id = u["user_id"]; break
        
        if not target_id: return await message.answer("❌ User not found in database, mate.")
        u = db_get_user(target_id)
        user["state"] = "normal"
        db_save_user(user)
        await show_player_card(message, target_id, u)
        
    elif state == "admin_edit_chips":
        if not text.lstrip('-').isdigit(): return await message.answer("❌ Enter a valid exact number for balance.")
        target_id = user["reply_to"]
        t_user = db_get_user(target_id)
        t_user["balance"] = int(text)
        db_save_user(t_user)
        user["state"] = "normal"
        db_save_user(user)
        await message.answer(f"✅ Balance updated to {text} chips.", reply_markup=kb.get_main_menu(message.from_user.id))
        
    elif state == "admin_edit_xp":
        if not text.isdigit(): return await message.answer("❌ Enter a valid exact number for XP.")
        target_id = user["reply_to"]
        t_user = db_get_user(target_id)
        t_user["xp"] = int(text)
        db_save_user(t_user)
        await add_xp(bot, target_id, 0) 
        user["state"] = "normal"
        db_save_user(user)
        await message.answer(f"✅ XP updated to {text}.", reply_markup=kb.get_main_menu(message.from_user.id))

    elif state == "admin_send_comment":
        target_id = user["reply_to"]
        try:
            await bot.send_message(target_id, f"💬 <b>Message from the Admins:</b>\n\n{text}", parse_mode="HTML")
            await message.answer("✅ Message sent to user.", reply_markup=kb.get_main_menu(message.from_user.id))
        except: await message.answer("❌ Failed to send message.", reply_markup=kb.get_main_menu(message.from_user.id))
        user["state"] = "normal"; db_save_user(user)