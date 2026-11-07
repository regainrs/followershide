import os
import threading
from flask import Flask
import base64
import json
import re
import urllib.error
import urllib.parse
import urllib.request
import telebot
from telebot import types

# 1. Render ke Web Service ke liye Flask dummy app (Port binding fix)
app = Flask(__name__)

@app.route('/')
def home():
    return "EPROOX Followers Hide Bot is active and running 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# Your Telegram Bot Token & Channel List
TOKEN = "9167961260:AAFe0Ee4hCOfqH3MR91AHwVc9YFrvkMCo-Y"
CHANNELS = [
    {"username": "@eproox", "url": "https://t.me/eproox"},
    {"username": "@workked", "url": "https://t.me/workked"},
    {"username": "@serverchats", "url": "https://t.me/serverchats"}
]

bot = telebot.TeleBot(TOKEN)
user_state = {}

def check_all_subscriptions(user_id):
    for ch in CHANNELS:
        try:
            member = bot.get_chat_member(ch["username"], user_id)
            print(f"[DEBUG] User {user_id} status in {ch['username']}: {member.status}")
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except Exception as e:
            print(f"[ERROR] Failed to check {ch['username']}: {e}")
            return False
    return True

def parse_session(sid):
    if not sid:
        return None, "Empty sessionid"
    if sid.startswith("sessionid="):
        sid = sid[len("sessionid="):]
    if any(ord(c) <= 32 or ord(c) >= 127 or c in ';,"\\' for c in sid):
        return None, "Invalid characters in sessionid"

    m = re.fullmatch(r"([1-9][0-9]*)(?::|%3[aA])(.+)", sid)
    if not m:
        return None, "Wrong format!"

    return {
        "raw": sid,
        "uid": m.group(1),
        "token_len": len(m.group(2)),
    }, None

def hide_lists(sessionid):
    if not sessionid or any(ord(c) <= 32 or ord(c) >= 127 or c in ';,"\\' for c in sessionid):
        raise ValueError("Invalid sessionid format")
    m = re.fullmatch(r"([1-9][0-9]*)(?::|%3[aA]).+", sessionid)
    if not m:
        raise ValueError("Wrong sessionid format")
    uid = m.group(1)

    tok = base64.b64encode(json.dumps({
        "ds_user_id": uid,
        "sessionid": sessionid,
        "should_use_header_over_cookies": True,
    }, separators=(",", ":")).encode()).decode()

    name = "IGSettingsBooleanMutation"
    form = {
        "method": "post",
        "format": "json",
        "server_timestamps": "true",
        "locale": "user",
        "fb_api_req_friendly_name": name,
        "client_doc_id": "2669261950526978627082629536",
        "variables": json.dumps({
            "setting_id": "hide_followers_following_list",
            "allow_error_codes": True,
            "callsite": "account_privacy",
            "value": True,
        }),
    }

    req = urllib.request.Request(
        "https://i.instagram.com/graphql/query",
        data=urllib.parse.urlencode(form).encode(),
        headers={
            "Authorization": "Bearer IGT:2:" + tok,
            "Cookie": f"sessionid={sessionid}; ds_user_id={uid}",
            "IG-INTENDED-USER-ID": uid,
            "X-IG-App-ID": "124024574287414",
            "X-Auth-Type": "instagram",
            "User-Agent": "Instagram 453.0.0",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept-Encoding": "identity",
            "X-GraphQL-Client-Library": "pando",
            "X-FB-Friendly-Name": name,
        },
        method="POST",
    )

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            raise RuntimeError("redirect refused")

    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}), NoRedirect()
    )

    try:
        with opener.open(req, timeout=15) as r:
            return json.loads(r.read(1024 * 1024 + 1))
    except urllib.error.HTTPError as e:
        with e:
            raw = e.read(16385)
        try:
            b = json.loads(raw)
            msg = b.get("message") or b.get("error_type") or ""
        except Exception:
            msg = ""
        
        if e.code == 400:
            raise RuntimeError("Invalid Session ID or Session Expired!")
        elif e.code == 403:
            raise RuntimeError("Access Blocked by Instagram (IP / Rate Limit Issue).")
        else:
            raise RuntimeError(f"Instagram Error (HTTP {e.code}): {msg}".strip())

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    user_state[user_id] = None

    if not check_all_subscriptions(user_id):
        markup = types.InlineKeyboardMarkup(row_width=1)
        for ch in CHANNELS:
            btn = types.InlineKeyboardButton(f"📢 Join {ch['username']}", url=ch['url'])
            markup.add(btn)
        
        check_btn = types.InlineKeyboardButton("🔄 Joined / Verify", callback_data="check_join")
        markup.add(check_btn)
        
        bot.reply_to(
            message,
            "⚠️ **Access Denied!**\n\n"
            "You must join ALL 3 channels below to use this bot.\n"
            "Please join them all and click **'Joined / Verify'**.",
            reply_markup=markup,
            parse_mode="Markdown"
        )
        return

    show_main_menu(message)

def show_main_menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    btn_hide = types.KeyboardButton("🔒 HIDE FOLLOWERS")
    btn_support = types.KeyboardButton("💬 SUPPORT")
    markup.add(btn_hide, btn_support)

    welcome_text = (
        "✨ **E P R O X - IG Followers Hider Bot** ✨\n\n"
        "Welcome! Choose an option from the keyboard below:\n\n"
        "⚡ *Developer:* `@regainrs`"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def handle_verification(call):
    user_id = call.from_user.id
    if check_all_subscriptions(user_id):
        bot.answer_callback_query(call.id, "Verified successfully!")
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        show_main_menu(call.message)
    else:
        bot.answer_callback_query(call.id, "You have not joined all channels yet! Please join all 3.", show_alert=True)

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    text = message.text.strip() if message.text else ""

    if text == "🔒 HIDE FOLLOWERS":
        user_state[user_id] = "waiting_for_session"
        bot.reply_to(
            message,
            "📥 **Please send your Instagram `sessionid` now:**",
            parse_mode="Markdown"
        )

    elif text == "💬 SUPPORT":
        user_state[user_id] = None
        support_text = (
            "💬 **Support Desk**\n\n"
            "If you are facing any issue, please contact @regainrs."
        )
        bot.reply_to(message, support_text, parse_mode="Markdown")

    elif user_state.get(user_id) == "waiting_for_session":
        sid = text
        user_state[user_id] = None

        info, err = parse_session(sid)
        if err:
            bot.reply_to(message, f"❌ **Error:** Invalid Session ID Format!", parse_mode="Markdown")
            return

        bot.reply_to(message, f"⏳ Processing request for UID: `{info['uid']}`...", parse_mode="Markdown")

        try:
            body = hide_lists(info["raw"])
            data = body.get("data") if isinstance(body, dict) else {}
            root = "xdt_api__v1__settings__set_bool"
            res = next((v for k, v in (data or {}).items() if k == root or k.startswith(root + "(")), {})

            ok = (
                isinstance(body, dict)
                and not body.get("errors")
                and not body.get("error")
                and body.get("status") != "fail"
                and isinstance(res, dict)
                and res.get("value") is True
            )

            if ok:
                response_msg = (
                    f"✅ **Success!**\n"
                    f"🔒 Followers/Following list has been hidden successfully.\n"
                    f"👤 **Account UID:** `{info['uid']}`"
                )
            else:
                response_msg = f"❌ **Failed:** Invalid Session ID or rejected by Instagram."

            bot.reply_to(message, response_msg, parse_mode="Markdown")

        except Exception as e:
            bot.reply_to(message, f"❌ **Error:** `{str(e)}`", parse_mode="Markdown")

    else:
        bot.reply_to(message, "Please select an option from the keyboard or click /start.")

if __name__ == "__main__":
    # Flask web server ko background thread me start karein
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    print("[*] EPROOX Telegram Bot with Multi-Channel Force Join & Flask Port Binding is running 24/7...")
    bot.infinity_polling(skip_pending=True)
