import sqlite3
import json
import time
from datetime import datetime

DB_PATH = "bot_casino.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Tabel of users
    cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance INTEGER,
    xp INTEGER DEFAULT 0,
    win_streak INTEGER DEFAULT 0,
    total_games INTEGER DEFAULT 0,
    daily_games INTEGER DEFAULT 0,
    luck_bombs_today INTEGER DEFAULT 0,
    mystery_boxes_today INTEGER DEFAULT 0,
    whiskey_buff INTEGER DEFAULT 0,
    last_active REAL,
    inactivity_reminded BOOLEAN DEFAULT 0,
    inventory TEXT,
    weekly_days TEXT,
    weekly_losses INTEGER DEFAULT 0,
    is_banned BOOLEAN DEFAULT 0,
    
    -- Nowe kolumny dla systemu polecen i weryfikacji Story (Wazne przecinki!)
    referred_by INTEGER DEFAULT 0,
    ref_reward_paid BOOLEAN DEFAULT 0,
    story_claimed BOOLEAN DEFAULT 0
)
""")
    
    # Tabela kodów promocyjnych
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS promo_codes (
        code TEXT PRIMARY KEY,
        amount INTEGER,
        uses INTEGER,
        claimed_by TEXT DEFAULT '[]'
    )
    """)
    
    conn.commit()
    conn.close()

def db_get_user(user_id, username=None, full_name=None):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    if not row:
        cursor.execute("""
        INSERT INTO users (user_id, username, full_name, last_login_date, last_active)
        VALUES (?, ?, ?, ?, ?)
        """, (user_id, username, full_name, today_str, time.time()))
        conn.commit()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        
    user = dict(row)
    user["weekly_days"] = set(json.loads(user["weekly_days"]))
    user["claimed_streaks"] = json.loads(user["claimed_streaks"])
    user["inventory"] = json.loads(user["inventory"])
    
    # Aktualizacja pól tekstowych i czasu aktywności
    user["last_active"] = time.time()
    if username: user["username"] = username
    if full_name: user["full_name"] = full_name
    
    conn.close()
    return user

def db_save_user(user):
    conn = get_db()
    cursor = conn.cursor()
    
    # Przygotowanie struktur JSON/Tekstowych dla SQL
    weekly_days_json = json.dumps(list(user["weekly_days"]))
    claimed_streaks_json = json.dumps(user["claimed_streaks"])
    inventory_json = json.dumps(user["inventory"])
    
    cursor.execute("""
    UPDATE users SET
        username = ?, full_name = ?, balance = ?, xp = ?, first_game = ?, daily_games = ?,
        win_streak = ?, weekly_losses = ?, weekly_days = ?, inactivity_reminded = ?,
        last_daily = ?, last_active = ?, claimed_sub_bonus = ?, pending_game = ?,
        whiskey_buff = ?, state = ?, reply_to = ?, temp_promo_amt = ?, total_games = ?,
        total_won_chips = ?, login_streak = ?, last_login_date = ?, referrals = ?,
        referrer_id = ?, referral_pending = ?, last_story_claim = ?, story_link_gen_time = ?,
        is_banned = ?, claimed_streaks = ?, inventory = ?, luck_bombs_today = ?, mystery_boxes_today = ?
    WHERE user_id = ?
    """, (
        user["username"], user["full_name"], user["balance"], user["xp"], int(user["first_game"]), user["daily_games"],
        user["win_streak"], user["weekly_losses"], weekly_days_json, int(user["inactivity_reminded"]),
        user["last_daily"], user["last_active"], int(user["claimed_sub_bonus"]), user["pending_game"],
        user["whiskey_buff"], user["state"], user["reply_to"], user["temp_promo_amt"], user["total_games"],
        user["total_won_chips"], user["login_streak"], user["last_login_date"], user["referrals"],
        user["referrer_id"], int(user["referral_pending"]), user["last_story_claim"], user["story_link_gen_time"],
        int(user["is_banned"]), claimed_streaks_json, inventory_json, user["luck_bombs_today"], user["mystery_boxes_today"],
        user["user_id"]
    ))
    conn.commit()
    conn.close()

def db_get_all_users():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    rows = cursor.fetchall()
    users = []
    for r in rows:
        u = dict(r)
        u["weekly_days"] = set(json.loads(u["weekly_days"]))
        u["claimed_streaks"] = json.loads(u["claimed_streaks"])
        u["inventory"] = json.loads(u["inventory"])
        users.append(u)
    conn.close()
    return users

def db_get_promo(code):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM promo_codes WHERE code = ?", (code,))
    row = cursor.fetchone()
    conn.close()
    if row:
        res = dict(row)
        res["claimed_by"] = set(json.loads(res["claimed_by"]))
        return res
    return None

def db_save_promo(code, amount, uses, claimed_by_set):
    conn = get_db()
    cursor = conn.cursor()
    claimed_by_json = json.dumps(list(claimed_by_set))
    cursor.execute("""
    INSERT INTO promo_codes (code, amount, uses, claimed_by)
    VALUES (?, ?, ?, ?)
    ON CONFLICT(code) DO UPDATE SET
        amount = excluded.amount,
        uses = excluded.uses,
        claimed_by = excluded.claimed_by
    """, (code, amount, uses, claimed_by_json))
    conn.commit()
    conn.close()

def db_delete_promo(code):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM promo_codes WHERE code = ?", (code,))
    conn.commit()
    conn.close()

def db_get_all_promos():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM promo_codes")
    rows = cursor.fetchall()
    promos = []
    for r in rows:
        p = dict(r)
        p["claimed_by"] = set(json.loads(p["claimed_by"]))
        promos.append(p)
    conn.close()
    return promos