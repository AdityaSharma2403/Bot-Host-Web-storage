import telebot
import requests
import asyncio
import aiohttp
import json
import time
import re
from datetime import datetime
from PIL import Image
from io import BytesIO

# ✅ Initialize Bot
TOKEN = "7748948464:AAEI-TAYOzuELx8dGUHRqfBqs2Wy4Fczphc"
bot = telebot.TeleBot(TOKEN)

# ✅ Format timestamp function
def format_timestamp(timestamp):
    try:
        return datetime.utcfromtimestamp(int(timestamp)).strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return "Invalid Timestamp"

# ✅ Safe data extraction
def get_safe(data, key, default="N/A"):
    return data.get(key, default)

# ✅ Markdown escape for safety
def escape_markdown(text):
    if text:
        return text.replace("_", "\\_").replace("*", "\\*").replace("[", "").replace("]", "").replace("", "\\")
    return text

# ✅ Async function to send API requests
async def make_request(session, url, retries=10, delay=0):
    for i in range(retries):
        try:
            async with session.get(url) as response:
                response.raise_for_status()

                content_type = response.headers.get("Content-Type", "")
                if "image" in content_type:
                    return await response.read()  # Return binary data

                return await response.text()  # Return text response
        except (aiohttp.ClientError, asyncio.TimeoutError):
            if i < retries - 1:
                await asyncio.sleep(delay)
            else:
                return None

# ✅ Handle /isbanned command
@bot.message_handler(func=lambda message: 'isbanned' in message.text.lower())
def check_banned_status(message):
    try:
        command_parts = message.text.split()
        if len(command_parts) < 2:
            bot.reply_to(message, "Usage: /isbanned {uid}")
            return
        
        user_id = command_parts[1]
        api_url = f"http://amin-team-api.vercel.app/check_banned?player_id={user_id}"

        response = requests.get(api_url)
        if response.status_code == 200:
            data = response.json()
            status_msg = f"UID {user_id} status: {data.get('status', 'Unknown')}"
            bot.reply_to(message, status_msg)
        else:
            bot.reply_to(message, f"Error fetching data for UID {user_id}.")
    except Exception as e:
        bot.reply_to(message, f"An error occurred: {str(e)}")

# ✅ Handle /mapinfo command
@bot.message_handler(func=lambda message: 'mapinfo' in message.text.lower())
def get_map_info(message):
    try:
        command_parts = message.text.split()
        if len(command_parts) < 2:
            bot.reply_to(message, "Usage: /mapinfo {map_code}")
            return

        map_code = command_parts[1].lstrip('#')
        region_codes = ["IND", "SG", "BR", "RU", "ID", "TW", "US", "VN", "TH", "ME", "PK", "CIS", "BD"]

        for region_code in region_codes:
            api_url = f"https://freefireinfo.vercel.app/map?region={region_code}&code=%23{map_code}&key=SHAH"
            response = requests.get(api_url)

            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    craftland_details = data['data'].get('Craftland Map Details', {})
                    if craftland_details:
                        map_info = f"Region: {region_code}\n" + "\n".join(
                            f"{key}: {value}" for key, value in craftland_details.items()
                        )
                        bot.reply_to(message, map_info)
                        return
        bot.reply_to(message, "No valid data found for the given map code.")
    except Exception as e:
        bot.reply_to(message, f"An error occurred: {str(e)}")

# ✅ Handle /event command
@bot.message_handler(func=lambda message: message.text.lower().startswith(('/event', 'event')))
def event(message):
    try:
        command_parts = message.text.split()
        if len(command_parts) < 2:
            bot.reply_to(message, "Usage: /event {region_code}")
            return

        region_code = command_parts[1]
        api_url = f"https://api.nowgarena.com//api/events?region={region_code}&key=projetoswq"

        response = requests.get(api_url)
        if response.status_code == 200:
            data = response.json()
            if data.get('events'):
                formatted_message = f"🎉 *Events in Region:* `{region_code.upper()}`\n\n"
                for event in data['events']:
                    title = event.get('title', 'N/A')
                    image_url = event.get('image', 'No Image Available')
                    start_time = format_timestamp(event.get('start', 0))
                    end_time = format_timestamp(event.get('end', 0))
                    formatted_message += f"*{title}*\nStart: {start_time}\nEnd: {end_time}\n[View Banner]({image_url})\n\n"
                bot.reply_to(message, formatted_message, parse_mode='Markdown')
            else:
                bot.reply_to(message, f"No events available for region {region_code}.")
        else:
            bot.reply_to(message, f"Error fetching events. Status code: {response.status_code}")
    except Exception as e:
        bot.reply_to(message, f"An error occurred: {str(e)}")

# ✅ Handle /visit command (NEW FORMAT: `/visit ind {uid}`)
def send_requests_batches(url, batches):
    success_count = 0
    for _ in range(batches):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                success_count += 1
        except requests.RequestException:
            pass
    return success_count

@bot.message_handler(func=lambda message: message.text.lower().startswith(('/visit', 'visit')))
def handle_visit(message):
    try:
        command_parts = message.text.split()
        if len(command_parts) != 3 or command_parts[1].lower() != 'ind':
            bot.reply_to(message, "Usage: /visit ind {uid}")
            return

        uid = command_parts[2]  
        total_requests = 1000  
        batches = total_requests // 1000  

        processing_message = bot.reply_to(message, "Processing... Please wait.")
        url = f"https://glff-visit-api-fric.onrender.com/pranto/?uid=1277813232"

        start_time = time.time()
        success_count = send_requests_batches(url, batches)
        elapsed_time = time.time() - start_time

        result_message = f"Successfully sent {success_count * 1000} visits to UID {uid}.\nTime taken: {elapsed_time:.2f} seconds."
        bot.edit_message_text(result_message, chat_id=message.chat.id, message_id=processing_message.message_id)
    except Exception as e:
        bot.reply_to(message, f"An error occurred: {str(e)}")

# ✅ Start the bot
try:
    print("Bot is running...")
    bot.polling()
except Exception as e:
    print(f"Error: {e}")
