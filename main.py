import asyncio
import time
import random
import string  # ИСПРАВЛЕНО: Без tego генерация промокодов выдавала бы ошибку!
from datetime import datetime
from aiogram import Bot, Dispatcher, BaseMiddleware, types
from aiogram.filters import Command, CommandObject
from aiogram import F
import io
from PIL import Image

# Новый официальный SDK от Google (Актуальный для 2026 года)
from google import genai  

from config import BOT_TOKEN, ADMIN_IDS, bot_state
from database import init_db, db_get_user, db_save_user, db_get_all_users, db_save_promo
from handlers import main_router
import keyboards as kb

# Инициализация нового клиента Google GenAI
GEMINI_API_KEY = "AIzaSyDHTrmIgmDenBABSiqAnyTICs4rsDzFsuM"
ai_client = genai.Client(api_key=GEMINI_API_KEY)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ---------------------------------------------------------
# ВАЖНО: ВСТАВЬ СЮДА ID ИЛИ @USERNAME ТВОЕГО КАНАЛА
# ---------------------------------------------------------
CHANNEL_ID = -1003927802145

# Компиляция слоя Middleware для проверки банов и техработ
class SecurityMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user_id = getattr(event.from_user, 'id', None) if getattr(event, 'from_user', None) else None
        if user_id:
            u = db_get_user(user_id)
            if u and u.get("is_banned", False):
                return
            if bot_state["maintenance"] and user_id not in ADMIN_IDS:
                bot_state["affected_users"].add(user_id)
                if isinstance(event, types.Message):
                    await event.answer("⚠️ <b>MAINTENANCE IN PROGRESS</b> ⚠️\n━━━━━━━━━━━━━━\n<i>G'day mate, the bot is currently under the hood for some tuning and is temporarily locked. The admins sincerely apologize for the hassle!</i>\n\nHang tight, we'll be back online before you know it.", parse_mode="HTML")
                elif isinstance(event, types.CallbackQuery):
                    await event.answer("Bot is under maintenance, mate. Hold your horses.", show_alert=True)
                return 
        return await handler(event, data)

#

# ---------------------------------------------------------
# КОМАНДА /START (РЕФЕРАЛЫ + ПРОВЕРКА КАНАЛА)
# ---------------------------------------------------------
@dp.message(Command("start"))
async def cmd_start(message: types.Message, command: CommandObject, bot: Bot):
    user_id = message.from_user.id
    user = db_get_user(user_id)
    
    # 1. ЗАПОМИНАЕМ, КТО ПРИГЛАСИЛ (Используем правильные ключи из твоей БД!)
    args = command.args
    if args and args.startswith("ref_") and not user.get("referrer_id"):
        try:
            ref_id = int(args.split("_")[1])
            if ref_id != user_id:
                user["referrer_id"] = ref_id
                user["referral_pending"] = True  # Флаг, что фишки еще не выданы
                db_save_user(user)
        except ValueError:
            pass

    # 2. ПРОВЕРЯЕМ ПОДПИСКУ НА КАНАЛ
    is_in_channel = False
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        if member.status in ['member', 'administrator', 'creator']:
            is_in_channel = True
    except Exception as e:
        print(f"⚠️ Ошибка проверки канала: {e}")

    # 3. ЛОГИКА ВЫДАЧИ БОНУСОВ
    if user.get("referral_pending") and user.get("referrer_id"):
        if is_in_channel:
            # ДРУГ ПОДПИСАЛСЯ - ПЛАТИМ ОБОИМ!
            ref_id = user["referrer_id"]
            referrer = db_get_user(ref_id)
            
            # Награда пригласившему
            referrer["balance"] += 100
            referrer["referrals"] = referrer.get("referrals", 0) + 1
            db_save_user(referrer)
            
            # Награда новому игроку (снимаем флаг pending, чтобы не платить дважды)
            user["balance"] += 500
            user["referral_pending"] = False
            db_save_user(user)
            
            try:
                await bot.send_message(
                    ref_id, 
                    "🎉 <b>Bloody legend!</b> Your mate joined the channel! <b>+100 Bonus Chips!</b> 💰",
                    parse_mode="HTML"
                )
            except: pass
            
            await message.answer(
                "🎉 <b>Bonza!</b> You joined via a friend's link and subscribed! You get <b>500 Bonus Chips</b>!\n\nWelcome to VipClubX Bonus Game! 🎰", 
                reply_markup=kb.get_main_menu(user_id), 
                parse_mode="HTML"
            )
            return
        else:
            # ДРУГ ЕЩЕ НЕ ПОДПИСАН - ТОРМОЗИМ ЕГО
            await message.answer(
                "🛑 <b>Hold your horses, mate!</b>\n\n"
                "You were invited by a friend, but to get your free chips, you MUST join our channel first!\n\n"
                "1️⃣ Join here: <b>@ТВОЙ_КАНАЛ_СЮДА</b>\n"
                "2️⃣ Come back and press /start again!",
                parse_mode="HTML"
            )
            return

    # 4. ОБЫЧНЫЙ СТАРТ (Без рефералки или если всё уже получено)
    await message.answer(
        "G'day mate! Welcome to VipClubX! Ready to smash the Pokies? 🎰\n\n<i>Use the menu to navigate.</i>", 
        reply_markup=kb.get_main_menu(user_id), 
        parse_mode="HTML"
    )
    
    
# Автоматические фоновые задачи (Cron Jobs)
async def background_jobs():
    last_daily_date = datetime.now().date()
    last_hh_notif = time.time()
    
    while True:
        await asyncio.sleep(60) 
        now = datetime.now()
        current_date = now.date()
        users = db_get_all_users()
        
        # 1. Sprawdzanie i przetwarzanie Mystery Boxów i Bomb
        for u in users:
            uid = u["user_id"]
            if "inventory" not in u or not u["inventory"]: continue
            new_inv = []
            changed = False
            for item in u["inventory"]:
                elapsed = time.time() - item["drop_time"]
                if item["type"] == "luck_bomb" and elapsed >= 86400:
                    prize = random.choices([100, 250, 500, 1000], weights=[50, 30, 15, 5])[0]
                    u["balance"] += prize
                    changed = True
                    try: await bot.send_message(uid, f"💣 <b>BOOM! LUCK BOMB EXPLODED!</b>\n━━━━━━━━━━━━━━\n<i>Your bomb went off and scattered <b>{prize} chips</b> everywhere!</i>\n🏦 <b>Stash:</b> {u['balance']} 🪙", parse_mode="HTML")
                    except: pass
                elif item["type"] == "mystery_box" and elapsed >= 4 * 86400:
                    base = item["base_win"]
                    bet = item["bet"]
                    bonus_chips = random.choices([100, 200, 300, 500], weights=[40, 30, 20, 10])[0] + int(bet * 0.5)
                    total_win = base + bonus_chips
                    changed = True
                    
                    if random.random() < 0.1:
                        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                        db_save_promo(code, total_win, 1, set())
                        try: await bot.send_message(uid, f"🎁 <b>MYSTERY BOX UNLOCKED!</b>\n━━━━━━━━━━━━━━\n<i>Instead of pure chips, you found a <b>Promo Code</b> worth {total_win} chips!</i>\n\nCode: <code>{code}</code>\nClaim it in the Bonuses menu!", parse_mode="HTML")
                        except: pass
                    else:
                        u["balance"] += total_win
                        try: await bot.send_message(uid, f"🎁 <b>MYSTERY BOX UNLOCKED!</b>\n━━━━━━━━━━━━━━\n<i>You recovered your base win of {base} chips PLUS a bonus of {bonus_chips} chips!</i>\n\n💵 <b>Added:</b> +{total_win}\n🏦 <b>Stash:</b> {u['balance']} 🪙", parse_mode="HTML")
                        except: pass
                else:
                    new_inv.append(item)
            if changed:
                u["inventory"] = new_inv
                db_save_user(u)
        
        # 2. Reset dzienny o północy i naliczanie cashbacku w poniedziałki
        if current_date != last_daily_date:
            from helpers import global_top_wins_today
            sorted_users = sorted(users, key=lambda x: x.get("daily_games", 0), reverse=True)
            admin_msg = "🏆 <b>TOP 10 ACTIVE LEGENDS TODAY</b> 🏆\n\n"
            found = False
            for i, u_card in enumerate(sorted_users[:10]):
                if u_card.get("daily_games", 0) > 0:
                    found = True
                    name = str(u_card.get("username") or u_card.get("full_name") or "Unknown").replace("<","").replace(">","")
                    admin_msg += f"{i+1}. <b>{name}</b> - {u_card['daily_games']} games\n"
            if found:
                for adm in ADMIN_IDS:
                    try: await bot.send_message(adm, admin_msg, parse_mode="HTML")
                    except: pass
            
            global_top_wins_today.clear()
            is_monday = (current_date.weekday() == 0)
            
            for u in users:
                u["daily_games"] = 0
                u["luck_bombs_today"] = 0
                u["mystery_boxes_today"] = 0
                if is_monday:
                    if len(u["weekly_days"]) == 7 and u["weekly_losses"] > 0:
                        cb = int(u["weekly_losses"] * 0.07)
                        u["balance"] += cb
                        try: await bot.send_message(u["user_id"], f"💸 <b>MONDAY CASHBACK!</b>\n━━━━━━━━━━━━━━\nLegend! You played every day last week. Here's <b>7% of your losses</b> back!\n\n💵 <b>+{cb} Chips</b> added to your stash!", parse_mode="HTML")
                        except: pass
                    u["weekly_days"].clear()
                    u["weekly_losses"] = 0
                db_save_user(u)
            last_daily_date = current_date

        # 3. Przypomnienie o Happy Hour co 4 dni
        if time.time() - last_hh_notif >= 4 * 86400:
            for u in users:
                if time.time() - u["last_active"] < 7 * 86400:
                    try: await bot.send_message(u["user_id"], "🌙 <b>HAPPY HOURS ARE ON!</b>\n━━━━━━━━━━━━━━\nDon't forget, mates! Log in during Aussie nights (22:00-01:00 weekday, 21:00-03:00 weekends AEST) for better odds and bigger payouts!", parse_mode="HTML")
                    except: pass
            last_hh_notif = time.time()

        # 4. Sprawdzanie nieaktywności użytkowników (7 dni)
        for u in users:
            if time.time() - u["last_active"] > 7 * 86400 and not u["inactivity_reminded"]:
                u["inactivity_reminded"] = True
                u["balance"] += 2000
                db_save_user(u)
                try: await bot.send_message(u["user_id"], "👋 <b>LONG TIME NO SEE, MATE!</b>\n━━━━━━━━━━━━━━\nWe missed ya at the pub! The boys chucked <b>2000 chips</b> into your stash to get you back in the game. Come have a spin!", reply_markup=kb.get_main_menu(u["user_id"]), parse_mode="HTML")
                except: pass


async def main():
    init_db()  # Uruchomienie SQLite
    print("Database SQL initialized successfully.")
    print("Bot is fired up and ready to go, mate...")
    
    me = await bot.get_me()
    bot_state["bot_username"] = me.username
    
    dp.message.middleware(SecurityMiddleware())
    dp.callback_query.middleware(SecurityMiddleware())
    
# === ФИНАЛЬНЫЙ ИСПРАВЛЕННЫЙ ПЕРЕХВАТЧИК СКРИНШОТОВ ДЛЯ ИИ ===
    @dp.message(F.photo | F.document)
    async def handle_story_screenshot(message: types.Message, bot: Bot):
        user_id = message.from_user.id
        user = db_get_user(user_id)
        
        if user.get("story_claimed", False):
            await message.answer("❌ <b>Yeah, nah.</b> You've already claimed your Story bonus, mate!", parse_mode="HTML")
            return
            
        processing_msg = await message.answer("🤖 Let me run this past the AI to verify your Story... Hang tight, mate!")
        
        try:
            # Вытягиваем фото или документ
            if message.photo:
                photo_obj = message.photo[-1]
            elif message.document and message.document.mime_type.startswith('image/'):
                photo_obj = message.document
            else:
                await processing_msg.edit_text("❌ Mate, that doesn't look like an image file!")
                return

            # Скачиваем в оперативную память
            file_io = io.BytesIO()
            await bot.download(photo_obj, destination=file_io)
            file_io.seek(0)
            
            img = Image.open(file_io)

            # Инструкция для ИИ
            prompt = (
                "You are an automated moderator for a Telegram bot. "
                "Analyze this screenshot. Reply strictly with one word: YES or NO. "
                "Rules to answer YES: "
                "1. The image MUST contain the exact text '@VipClubXQ7_bot' or 't.me/VipClubXQ7_bot' clearly visible. "
                "If the rule fails, answer NO."
            )

            # ИСПРАВЛЕНИЕ: Указываем точную версию модели 'gemini-1.5-flash-latest'
            response = ai_client.models.generate_content(
                model='gemini-2.5-flash',  # Полное имя решает проблему с 404!
                contents=[img, prompt]
            )
            
            result_text = response.text.strip().upper()
            ai_verified_successfully = "YES" in result_text

        except Exception as e:
            print(f"⚠️ Ошибка ИИ: {e}")
            await processing_msg.edit_text("❌ Bloody hell, the AI servers are down or rate-limited. Try again in a minute!")
            return
        
        # Выдаем награду
        if ai_verified_successfully:
            user["balance"] += 500
            user["story_claimed"] = True
            db_save_user(user)
            await processing_msg.edit_text(
                "✅ <b>Fair dinkum!</b> The AI spotted the link and verified your Story. <b>500 Chips</b> added to your stash! Go smash the Pokies! 🎰",
                parse_mode="HTML"
            )
        else:
            await processing_msg.edit_text(
                "❌ <b>Strewth!</b> The AI couldn't spot the <b>@VipClubXQ7_bot</b> link on this image. Make sure it's clearly visible in your Story, mate!",
                parse_mode="HTML"
            )
    # ====================================================================
    # Сначала проверяются команды из main.py, затем всё остальное из handlers
    dp.include_router(main_router)
    
    asyncio.create_task(background_jobs())
    
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        print(f"⚠️ Strewth, an error: {e}")
    finally:
        print("🛑 Closing the Telegram session...")
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())