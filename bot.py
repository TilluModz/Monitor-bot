import os
import json
import time
import telebot
import requests
from threading import Thread
from flask import Flask
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# ==================================================
# CONFIG
# ==================================================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8585589215:AAHhpR362EsiYOXVDGEbVMCgsNSkJuzeu1o")
CHAT_ID = os.getenv("CHAT_ID", "7822776135")
ADMIN_IDS = [7822776135]
APPROVED_USERS = [7822776135]

MONITOR_FILE = "monitored_accounts.json"

# ==================================================
# FLASK KEEPALIVE (WEB SERVICE)
# ==================================================
app = Flask(__name__)

@app.route("/")
def home():
    return "Monitor Bot Running"

# start flask in another thread
def run_flask():
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))

Thread(target=run_flask).start()

# ==================================================
# TELEGRAM BOT INIT
# ==================================================
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# ==================================================
# JSON FILE LOAD / SAVE
# ==================================================
def load_monitors():
    if not os.path.exists(MONITOR_FILE):
        return {}
    try:
        with open(MONITOR_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_monitors(data):
    with open(MONITOR_FILE, "w") as f:
        json.dump(data, f)

monitored_accounts = load_monitors()

# ==================================================
# INSTAGRAM CHECKER
# ==================================================
def check_instagram_status(username):
    url = f"https://www.instagram.com/{username}/"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)

        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            exists = soup.find("meta", property="og:description") is not None
            return exists
        elif r.status_code == 404:
            return False
        else:
            return None

    except:
        return None

# ==================================================
# MONITORING SYSTEM
# ==================================================
def notify(username, status, user_id, start_time):
    end = datetime.now()
    diff = end - start_time

    h = diff.seconds // 3600
    m = (diff.seconds % 3600) // 60
    s = diff.seconds % 60
    d = diff.days

    duration = f"{d}d {h}h {m}m {s}s"

    if status == "unbanned":
        msg = f"@{username} is Recovered! Took {duration}"
    else:
        msg = f"@{username} is Smoked! Took {duration}"

    bot.send_message(user_id, msg)


def monitor(username):
    while username in monitored_accounts:
        exists = check_instagram_status(username)

        if exists is None:
            time.sleep(10)
            continue

        start_time = datetime.strptime(monitored_accounts[username]["start"], "%Y-%m-%d %H:%M:%S")
        user_id = monitored_accounts[username]["user_id"]
        mode = monitored_accounts[username]["mode"]

        if mode == "unban" and exists:
            notify(username, "unbanned", user_id, start_time)
            monitored_accounts.pop(username)
            save_monitors(monitored_accounts)
            break

        if mode == "ban" and not exists:
            notify(username, "banned", user_id, start_time)
            monitored_accounts.pop(username)
            save_monitors(monitored_accounts)
            break

        time.sleep(20)   # Fixed

# ==================================================
# TELEGRAM COMMANDS
# ==================================================
def is_allowed(uid):
    return uid in APPROVED_USERS


@bot.message_handler(commands=['start','help'])
def start(message):
    if not is_allowed(message.from_user.id):
        bot.reply_to(message, "🚫 Not authorized. DM @SIIYL")
        return

    text = """🤖 *Instagram Monitor Bot*

/ban username  
/unban username  
/status username  
/dikhade  
/rukja username  

ADMIN:
/approve id 1d 2h  
/unapprove id
"""
    bot.send_message(message.chat.id, text)


@bot.message_handler(commands=['status'])
def status(message):
    if not is_allowed(message.from_user.id):
        return bot.reply_to(message, "🚫 Not authorized")

    try:
        username = message.text.split()[1]
    except:
        return bot.reply_to(message, "Usage: /status username")

    exists = check_instagram_status(username)

    if exists is None:
        bot.reply_to(message, f"❗ Could not check @{username}")
    elif exists:
        bot.reply_to(message, f"✅ @{username} is Active.")
    else:
        bot.reply_to(message, f"🚨 @{username} is Banned.")


@bot.message_handler(commands=['ban'])
def ban(message):
    if not is_allowed(message.from_user.id):
        return bot.reply_to(message, "🚫 Not authorized")

    try:
        username = message.text.split()[1]
    except:
        return bot.reply_to(message, "Usage: /ban username")

    exists = check_instagram_status(username)

    if exists is None:
        return bot.reply_to(message, f"❗ Error checking @{username}")

    if not exists:
        return bot.reply_to(message, f"@{username} already banned.")

    monitored_accounts[username] = {
        "mode": "ban",
        "start": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user_id": message.from_user.id
    }
    save_monitors(monitored_accounts)
    Thread(target=monitor, args=(username,)).start()

    bot.reply_to(message, f"🚨 Monitoring @{username} for ban.")


@bot.message_handler(commands=['unban'])
def unban(message):
    if not is_allowed(message.from_user.id):
        return bot.reply_to(message, "🚫 Not authorized")

    try:
        username = message.text.split()[1]
    except:
        return bot.reply_to(message, "Usage: /unban username")

    exists = check_instagram_status(username)

    if exists is None:
        return bot.reply_to(message, f"❗ Error checking @{username}")

    if exists:
        return bot.reply_to(message, f"@{username} is already active.")

    monitored_accounts[username] = {
        "mode": "unban",
        "start": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user_id": message.from_user.id
    }
    save_monitors(monitored_accounts)
    Thread(target=monitor, args=(username,)).start()

    bot.reply_to(message, f"🚨 Monitoring @{username} for unban.")


@bot.message_handler(commands=['rukja'])
def stop(message):
    if not is_allowed(message.from_user.id):
        return bot.reply_to(message, "🚫 Not authorized")

    try:
        username = message.text.split()[1]
    except:
        return bot.reply_to(message, "Usage: /rukja username")

    if username in monitored_accounts:
        monitored_accounts.pop(username)
        save_monitors(monitored_accounts)
        bot.reply_to(message, f"🛑 Stopped monitoring @{username}.")
    else:
        bot.reply_to(message, f"@{username} not being monitored.")


@bot.message_handler(commands=['dikhade'])
def show(message):
    if not is_allowed(message.from_user.id):
        return bot.reply_to(message, "🚫 Not authorized")

    if not monitored_accounts:
        return bot.reply_to(message, "ℹ️ No active monitors.")

    msg = "📄 *Monitoring List:*\n"
    for u, d in monitored_accounts.items():
        msg += f"- @{u} ({d['mode']})\n"

    bot.reply_to(message, msg, parse_mode="Markdown")

# ==================================================
# BOT START
# ==================================================
bot.infinity_polling(skip_pending=True)