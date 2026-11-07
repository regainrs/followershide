import os
import threading
from flask import Flask
import telebot

# Aapka Telegram Bot Token
TOKEN = "7759089766:AAEU-XG5851lU62F-H44Vw9fQ3r3c738nv8u0"
bot = telebot.TeleBot(TOKEN)

# 1. Render ke Web Service ke liye Flask server (Port binding fix ke liye)
app = Flask(__name__)

@app.route('/')
def home():
    return "EPROOX Followers Hide Bot is active!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# 2. Telegram Bot Handlers
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    try:
        # reply_to ki jagah send_message use kiya hai taaki 400 Bad Request error na aaye
        bot.send_message(
            message.chat.id, 
            "👋 Welcome! EPROOX Followers Hide Bot is active."
        )
    except Exception as e:
        print(f"Error in start command: {e}")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    try:
        bot.send_message(message.chat.id, f"Received: {message.text}")
    except Exception as e:
        print(f"Error handling message: {e}")

# Main execution entry point
if __name__ == "__main__":
    # Flask web server ko background thread me start karein
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Telegram bot polling start karein
    print("Starting Telegram Bot polling...")
    bot.infinity_polling(skip_pending=True)
