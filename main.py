import asyncio
import time
import random
from datetime import datetime
from aiogram import Bot, Dispatcher, BaseMiddleware, types

#import nest_asyncio
#nest_asyncio.apply()

from config import BOT_TOKEN, ADMIN_IDS, bot_state
from database import init_db, db_get_user, db_save_user, db_get_all_users, db_save_promo
from handlers import main_router
import keyboards as kb

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Kompilacja warstwy Middleware do weryfikacji blokad kont oraz trybu konserwacji
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

# Automatyczne wątki przetwarzania danych w tle (Cron Jobs)
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