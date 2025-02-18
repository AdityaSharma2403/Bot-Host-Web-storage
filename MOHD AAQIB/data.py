import json
import time
from flask import Flask, request

# Telegram Bot Token
BOT_TOKEN = "7920046087:AAHmENmGaTOh_2FeI1trgY0KK0QmCXUkEmc"
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Free Fire Search API
SEARCH_API_KEY = "wlx_demon"
SEARCH_API_BASE = "https://wlx-search-api.vercel.app/search"

# Main Admin Telegram ID
ADMIN_ID = 5112593221  # Your Telegram ID

# Dictionary to store allowed groups and their expiration timestamps
allowed_groups = {}

# Flask app for webhook
app = Flask(__name__)

def send_message(chat_id, text):
    """ Sends a message to a Telegram chat. """
    url = f"{API_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    requests.post(url, json=payload)

def search_player(player_name):
    """ Searches for a player in the Free Fire database. """
    params = {"query": player_name, "key": SEARCH_API_KEY}
    response = requests.get(SEARCH_API_BASE, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        return None

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    """ Handles incoming Telegram messages. """
    global allowed_groups
    data = request.json

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        user_id = data["message"]["from"]["id"]
        text = data["message"].get("text", "")

        # Check if the bot is allowed in this chat
        current_time = time.time()
        if chat_id not in allowed_groups or allowed_groups[chat_id] < current_time:
            if user_id != ADMIN_ID:
                send_message(chat_id, "❌ This bot is not allowed in this group. Ask the admin to allow it.")
                return "Unauthorized", 403

        # Handle /search command
        if text.startswith("/search "):
            player_name = text.split("/search ", 1)[1]
            results = search_player(player_name)

            if results and "players" in results:
                response_text = "🔍 <b>Search Results:</b>\n\n"
                for player in results["players"]:
                    response_text += (
                        f"🎮 Name: {player['name']}\n"
                        f"🆔 ID: {player['id']}\n"
                        f"⭐ Level: {player.get('level', 'N/A')}\n"
                        f"🏆 Rank: {player.get('rank', 'N/A')}\n"
                        f"❤️ Likes: {player.get('likes', 'N/A')}\n"
                        "--------------------\n"
                    )
                send_message(chat_id, response_text)
            else:
                send_message(chat_id, "⚠️ No matching player found.")

        # Handle /allow command (Admin Only)
        elif text.startswith("/allow "):
            if user_id == ADMIN_ID:
                try:
                    days = int(text.split("/allow ", 1)[1])
                    expire_time = current_time + (days * 86400)  # Convert days to seconds
                    allowed_groups[chat_id] = expire_time
                    send_message(chat_id, f"✅ This group is now allowed for {days} days.")
                except ValueError:
                    send_message(chat_id, "⚠️ Please provide a valid number of days.")

    return "OK", 200

if __name__ == "__main__":
    app.run(port=5000, debug=True)
