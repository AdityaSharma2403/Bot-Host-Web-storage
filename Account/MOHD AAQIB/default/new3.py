import telebot
import requests
import asyncio
import aiohttp
import json
import time
from datetime import datetime, timedelta
from PIL import Image
from io import BytesIO
import re

# Bot Token
TOKEN = "7748948464:AAEI-TAYOzuELx8dGUHRqfBqs2Wy4Fczphc"
bot = telebot.TeleBot(TOKEN)

# Main Admin ID
MAIN_ADMIN_ID = 5112593221

# Allowed groups storage
allowed_groups = {}

# Function to format timestamp
def format_timestamp(timestamp):
    try:
        return datetime.utcfromtimestamp(int(timestamp)).strftime('%Y-%m-%d %H:%M:%S') if timestamp else "N/A"
    except:
        return "Invalid Timestamp"

# Function to send async requests
async def make_request(session, url, retries=10, delay=1):
    for _ in range(retries):
        try:
            async with session.get(url) as response:
                response.raise_for_status()
                return await response.text()
        except (aiohttp.ClientError, asyncio.TimeoutError):
            await asyncio.sleep(delay)
    return None

# Check if a user is banned
@bot.message_handler(func=lambda message: message.text.lower().startswith("isbanned"))
def check_banned_status(message):
    command_parts = message.text.split()
    if len(command_parts) < 2:
        bot.reply_to(message, "Usage: /isbanned {uid}")
        return

    user_id = command_parts[1]
    api_url = f"http://amin-team-api.vercel.app/check_banned?player_id={user_id}"
    
    response = requests.get(api_url)
    if response.status_code == 200:
        data = response.json()
        status = data.get("status", "UNKNOWN")
        bot.reply_to(message, f"UID {user_id} status: {status}")
    else:
        bot.reply_to(message, "Error fetching data. Please try again later.")

# Get map info
@bot.message_handler(func=lambda message: message.text.lower().startswith("mapinfo"))
def get_map_info(message):
    command_parts = message.text.split()
    if len(command_parts) < 2:
        bot.reply_to(message, "Usage: /mapinfo {map_code}")
        return

    map_code = command_parts[1].lstrip('#')
    regions = ["IND", "SG", "BR", "RU", "ID", "TW", "US", "VN", "TH", "ME", "PK", "CIS", "BD"]
    
    for region in regions:
        api_url = f"https://freefireinfo.vercel.app/map?region={region}&code=%23{map_code}&key=SHAH"
        response = requests.get(api_url)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                details = data['data'].get('Craftland Map Details', {})
                if details:
                    msg = "\n".join([f"{key}: {value}" for key, value in details.items()])
                    bot.reply_to(message, f"Region: {region}\n{msg}")
                    return

    bot.reply_to(message, "No valid data found.")

# Get player info
@bot.message_handler(func=lambda message: message.text.lower().startswith(("get", "/get")))
def get_info(message):
    asyncio.run(process_info(message))

async def process_info(message):
    user_id = message.chat.id
    uid = message.text.split()[1] if len(message.text.split()) > 1 else None

    if not uid or not uid.isdigit():
        bot.reply_to(message, "Usage: /get <uid>")
        return

    async with aiohttp.ClientSession() as session:
        url1 = f"https://player-info-final-original-1.vercel.app/ADITYA-PLAYER-INFO?uid={uid}&key=ADITYA"
        response1 = await make_request(session, url1)
        if response1:
            bot.reply_to(message, response1)

# Fetch event info
@bot.message_handler(func=lambda message: message.text.lower().startswith(('/event', 'event')))
def event(message):
    command_parts = message.text.split()
    if len(command_parts) < 2:
        bot.reply_to(message, "Usage: /event {region_code}")
        return

    region_code = command_parts[1]
    api_url = f"https://api.nowgarena.com/api/events?region={region_code}&key=projetoswq"

    response = requests.get(api_url)
    if response.status_code == 200:
        data = response.json()
        events = data.get("events", [])
        if events:
            msg = f"🎉 Events in {region_code.upper()}:\n\n"
            for event in events:
                title = event.get('title', 'N/A')
                start = format_timestamp(event.get('start', 0))
                end = format_timestamp(event.get('end', 0))
                img = event.get('image', 'No Image Available')
                msg += f"*{title}*\nStart: {start}\nEnd: {end}\n[View Banner]({img})\n\n"
            bot.reply_to(message, msg, parse_mode='Markdown')
        else:
            bot.reply_to(message, "No events available for this region.")
    else:
        bot.reply_to(message, "Error fetching data.")

# Send visits
@bot.message_handler(func=lambda message: message.text.lower().startswith(('visit', '/visit')))
def handle_visit(message):
    command_parts = message.text.split()
    if len(command_parts) != 3:
        bot.reply_to(message, "Usage: /visit <number_of_requests> <uid>")
        return

    try:
        total_requests = int(command_parts[1])
        uid = command_parts[2]
    except ValueError:
        bot.reply_to(message, "Invalid number format.")
        return

    if total_requests < 1000 or total_requests > 10000 or total_requests % 1000 != 0:
        bot.reply_to(message, "Number must be between 1000-10000 and a multiple of 1000.")
        return

    url = f"https://foxvisit.vercel.app/visit?uid={uid}"
    success_count = sum(1 for _ in range(total_requests // 1000) if requests.get(url).status_code == 200)

    bot.reply_to(message, f"Successfully sent {success_count * 1000}/{total_requests} visits to UID {uid}.")

# Allow bot in a group
@bot.message_handler(commands=['allow'])
def allow_group(message):
    if message.from_user.id != MAIN_ADMIN_ID:
        bot.reply_to(message, "You are not authorized to use this command.")
        return

    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /allow <days>")
        return

    try:
        days = int(parts[1])
        expiration_time = datetime.now() + timedelta(days=days)
        allowed_groups[message.chat.id] = expiration_time
        bot.reply_to(message, f"Bot allowed for {days} days until {expiration_time.strftime('%Y-%m-%d %H:%M:%S')}")
    except ValueError:
        bot.reply_to(message, "Invalid number format.")

@bot.message_handler(func=lambda message: True)
def check_if_allowed(message):
    if message.chat.id in allowed_groups and datetime.now() < allowed_groups[message.chat.id]:
        return
    bot.reply_to(message, "Bot not allowed in this group or permission expired.")

# Run the bot
try:
    print("Bot is running...")
    bot.polling()
except Exception as e:
    print(f"Error: {e}")
