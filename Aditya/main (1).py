import telebot
import requests
import time
import asyncio
import httpx
from datetime import datetime

TOKEN = "8187044195:AAExR-MHGmnpTYTLCX_EvNAY2a2GyJl3ePM"
bot = telebot.TeleBot(TOKEN, parse_mode="Markdown")

# Function to format timestamp
def format_timestamp(timestamp):
    return datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S') if timestamp != 0 else "N/A"

# Escape markdown for safety
def escape_markdown(text):
    if text:
        return text.replace("_", "\\_").replace("*", "\\*").replace("[", "").replace("]", "").replace("", "\\")
    return text

# Function to handle missing or unavailable data
def get_safe(data, key, default="N/A"):
    return data.get(key, default)

# Handle /isbanned aur isbanned {uid} formats
@bot.message_handler(func=lambda message: 'isbanned' in message.text.lower())
def check_banned_status(message):
    try:
        # Extract user ID from the message
        command_parts = message.text.split()
        if len(command_parts) < 2:
            bot.reply_to(message, "Please provide a valid user ID. Usage: /isbanned {uid} or isbanned {uid}")
            return
        
        user_id = command_parts[1]
        api_url = f"http://amin-team-api.vercel.app/check_banned?player_id={user_id}"
        
        # Send web request to check ban status
        response = requests.get(api_url)
        if response.status_code == 200:
            data = response.json()  # Parse response as JSON
            if data['status'] == "BANNED":
                bot.reply_to(message, f"UID {user_id} is permanently banned 😕.")
            elif data['status'] == "NOT BANNED":
                bot.reply_to(message, f"UID {user_id} is not banned 😎.")
            else:
                bot.reply_to(message, f"UID {user_id} status: {data['status']}")
        else:
            bot.reply_to(message, f"Error: Unable to fetch data for User ID {user_id}. Please try again later.")
    except Exception as e:
        bot.reply_to(message, f"An error occurred: {str(e)}")

def process_map_info(message):
    try:
        parts = message.text.split(maxsplit=2)
        if len(parts) < 3:
            bot.reply_to(message, "*Error:* Use `/mapinfo {region} {Map Code}`.")
            return

        region = parts[1].lower()
        map_code_param = parts[2].replace("#", "%23")  # Convert # to %23 for API request
        
        api_url = f"https://freefireinfo.vercel.app/map?region={region}&code={map_code_param}&key=SHAHG"
        response = requests.get(api_url)
        if response.status_code == 200:
            data = response.json()
            if data["status"] == "success":
                craftland = data["data"]["Craftland Map Details"]

                # Safely retrieve each field with a default value if missing
                map_code = craftland.get("MapCode", "N/A")
                creator = craftland.get("Creator", "N/A")
                title = craftland.get("Title", "N/A")
                description = craftland.get("Description", "N/A")
                subscribers = craftland.get("Subscribers", "N/A")
                likes = craftland.get("Likes", "N/A")
                teams = craftland.get("Teams", "N/A")
                play_avg = craftland.get("PlayAverage", "N/A")
                rounds = craftland.get("Rounds", "N/A")
                tags = ", ".join(craftland.get("Tags", []))
                mode = craftland.get("Mode", "N/A")
                map_cover = craftland.get("MapCover", None)
                
                caption = (
                    f"🎮 *Craftland Map Info*\n\n"
                    f"🆔 *Map Code:* `{map_code}`\n"
                    f"👤 *Creator:* `{creator}`\n"
                    f"📌 *Title:* `{title}`\n"
                    f"📝 *Description:* `{description}`\n"
                    f"📢 *Subscribers:* `{subscribers}`\n"
                    f"❤️ *Likes:* `{likes}`\n"
                    f"👥 *Teams:* `{teams}`\n"
                    f"⏳ *Avg Play Time:* `{play_avg}` mins\n"
                    f"🔄 *Rounds:* `{rounds}`\n"
                    f"🏷️ *Tags:* `{tags}`\n"
                    f"🎯 *Mode:* `{mode}`"
                )

                if map_cover:
                    img_response = requests.get(map_cover)
                    if img_response.status_code == 200:
                        bot.send_photo(message.chat.id, BytesIO(img_response.content), caption=caption, reply_to_message_id=message.message_id)
                        return
                bot.reply_to(message, caption)
            else:
                bot.reply_to(message, "*Error:* No data found.")
        else:
            bot.reply_to(message, "*Error:* API request failed.")
    except Exception as e:
        bot.reply_to(message, f"*Error:* {str(e)}")

# Handle `/mapinfo` command
@bot.message_handler(commands=["mapinfo"])
def mapinfo_command(message):
    process_map_info(message)

# Handle "mapinfo" text messages (without /)
@bot.message_handler(func=lambda message: message.text.lower().startswith("mapinfo"))
def mapinfo_text(message):
    process_map_info(message)

import re
import json
import os
import datetime
import requests
import telebot
import time
from telebot import types
from io import BytesIO
from PIL import Image
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=10)

DETAILS_URL_TEMPLATE = "https://player-info-test-2.vercel.app/ADITYA-PLAYER-INFO?uid={uid}&key=ADITYA"
OUTFIT_URL_TEMPLATE   = "https://player-image-1.vercel.app/generate-image?uid={uid}&region={region}&key=ADITYA"
BANNER_URL_TEMPLATE   = "https://player-image-2.vercel.app/generate-image?uid={uid}&region={region}&key=ADITYA"

def split_response(text):
    text = text.strip()
    r1_marker, r2_marker = "Response 1:", "Response 2:"
    if r1_marker in text and r2_marker in text:
        parts = text.split(r2_marker, 1)
        return parts[0].replace(r1_marker, "").strip(), parts[1].strip()
    return None, None

def parse_region(details_text):
    match = re.search(r"(?:Region:|in region)\s*([A-Za-z0-9]+)", details_text, re.IGNORECASE)
    return match.group(1).strip().lower() if match else None

def convert_image_to_sticker(image, fmt="WEBP"):
    sticker_io = BytesIO()
    image.save(sticker_io, format=fmt)
    sticker_io.seek(0)
    return sticker_io

@bot.message_handler(func=lambda message: 'get' in message.text.lower())
def handle_get(message: types.Message):
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, ("Usage: Get <uid>"), parse_mode="MARKDOWN")
        return

    uid = parts[1].strip()
    
    if not uid.isdigit() or len(uid) not in (8, 9, 10, 11):
        bot.reply_to(message, ("This UID does not exist in the Garena Database or has not Fully Registered in a Region"), parse_mode="MARKDOWN")
        return

    details_url = DETAILS_URL_TEMPLATE.format(uid=uid)
    reply_msg = bot.reply_to(message, (f"Fetching details for UID `{uid}`..."), parse_mode="MARKDOWN")

    try:
        details_resp = requests.get(details_url)
        details_resp.raise_for_status()
        details_text = details_resp.text
    except Exception:
        bot.edit_message_text(("This UID does not exist in the Garena Database or has not Fully Registered in a Region"), chat_id=reply_msg.chat.id, message_id=reply_msg.message_id, parse_mode="MARKDOWN")
        return

    resp1, resp2 = split_response(details_text)
    if resp1 is None:
        bot.edit_message_text((details_text), chat_id=reply_msg.chat.id, message_id=reply_msg.message_id, parse_mode="MARKDOWN")
        return

    bot.edit_message_text((resp1), chat_id=reply_msg.chat.id, message_id=reply_msg.message_id, parse_mode="MARKDOWN")
    
    if resp2:
        time.sleep(2)
        bot.edit_message_text((resp2), chat_id=reply_msg.chat.id, message_id=reply_msg.message_id, parse_mode="MARKDOWN")

    region = parse_region(details_text)
    outfit_url = OUTFIT_URL_TEMPLATE.format(uid=uid, region=region)
    banner_url = BANNER_URL_TEMPLATE.format(uid=uid, region=region)

    future_outfit = executor.submit(requests.get, outfit_url)
    future_banner = executor.submit(requests.get, banner_url)

    try:
        outfit_resp = future_outfit.result()
        outfit_resp.raise_for_status()
        outfit_bytes = outfit_resp.content
    except Exception:
        outfit_bytes = None
        bot.reply_to(message, ("This account has not equipped any custom outfit! 🗿"), parse_mode="MARKDOWN")

    try:
        banner_resp = future_banner.result()
        banner_resp.raise_for_status()
        banner_bytes = banner_resp.content
    except Exception as e:
        bot.reply_to(message, (f"Banner image not available: {e}"), parse_mode="MARKDOWN")
        return

    try:
        banner_img = Image.open(BytesIO(banner_bytes)).convert("RGBA")
        banner_sticker = convert_image_to_sticker(banner_img)
    except Exception as e:
        bot.reply_to(message, (f"Error processing banner image: {e}"), parse_mode="MARKDOWN")
        return

    if outfit_bytes:
        bot.send_photo(message.chat.id, outfit_bytes, reply_to_message_id=message.message_id)
    bot.send_sticker(message.chat.id, banner_sticker, reply_to_message_id=message.message_id)

import datetime
import logging
import requests
import telebot

def format_custom_time(dt_str):  
    dt = datetime.datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")  
    formatted_time = dt.strftime("%d %B %Y %I:%M:%S %p")  
    return formatted_time[:-2] + formatted_time[-2:].lower()  
  
def format_time(ts):  
    try:  
        if ts == "Not Found":  
            return ts  
        ts_int = int(ts)  
        dt = datetime.datetime.utcfromtimestamp(ts_int)  
        return format_custom_time(dt.strftime("%Y-%m-%d %H:%M:%S"))  
    except Exception as e:  
        logging.error("Error formatting time: %s", e)  
        return ts  

# Handle /event or event command
@bot.message_handler(func=lambda message: message.text.lower().startswith('/event') or message.text.lower().startswith('event'))
def event(message):
    try:
        command_parts = message.text.split()
        if len(command_parts) < 2:
            bot.reply_to(message, "Please provide a region code. Usage: `/event {region_code}` or `event {region_code}`.", parse_mode='Markdown')
            return

        region_code = command_parts[1].lower()
        api_url = f"https://api.nowgarena.com/api/events?region={region_code}&key=projetoswq"

        response = requests.get(api_url, timeout=10)
        if response.status_code != 200:
            bot.reply_to(message, f"*Error:* Unable to fetch data. Status code: `{response.status_code}`", parse_mode='Markdown')
            return

        data = response.json()
        if not data or 'events' not in data or not data['events']:
            bot.reply_to(message, f"No events currently available for the region `{region_code.upper()}`.", parse_mode='Markdown')
            return

        events = data['events']
        formatted_message = f"🎉 *Events in Region:* `{region_code.upper()}`\n\n"

        for event in events:
            title = event.get('title', 'N/A')
            image_url = event.get('image', '')
            start_time = format_time(event.get('start'))
            end_time = format_time(event.get('end'))

            formatted_message += (
                f"*Title:* {title}\n"
                f"*Start:* {start_time}\n"
                f"*End:* {end_time}\n"
                f"[View Banner]({image_url})\n\n" if image_url else ""
            )

        bot.reply_to(message, formatted_message, parse_mode='Markdown', disable_web_page_preview=True)

    except requests.RequestException as req_err:
        bot.reply_to(message, f"*Network error:* `{req_err}`", parse_mode='Markdown')
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        bot.reply_to(message, f"*An error occurred:* `{str(e)}`", parse_mode='Markdown')

import telebot
import requests

# API Endpoint (fixed for IND server)
API_URL = "https://vstech.serv00.net/freeapi.php?uid={uid}&region=ind&key=narayan"

# Like command handler – works for both "/like {uid}" and "like {uid}"
@bot.message_handler(func=lambda message: message.text and message.text.lower().startswith(("/lishke", "lijdke")))
def like_command(message):
    parts = message.text.split()
    if len(parts) != 2:
        bot.reply_to(
            message,
            "Usage: /like {uid} or like {uid}\nThis bot only works for IND server."
        )
        return

    uid = parts[1]
    # Send an initial message and capture it so we can edit later
    sent_message = bot.reply_to(message, "Like Sending...")

    # Format the API URL and make the request
    api_url = API_URL.format(uid=uid)
    response = requests.get(api_url)

    if response.status_code == 200:
        data = response.json()
        status_code = data.get('status', 0)
        # If the account has reached max likes, inform the user
        if status_code == 2:
            bot.edit_message_text(
                chat_id=sent_message.chat.id,
                message_id=sent_message.message_id,
                text=f"Account with UID {uid} has reached the maximum likes for today. Please try again tomorrow."
            )
            return

        # If the like data is missing, ask the user to check the UID
        if 'LikesbeforeCommand' not in data or 'LikesafterCommand' not in data:
            bot.edit_message_text(
                chat_id=sent_message.chat.id,
                message_id=sent_message.message_id,
                text=f"No like data found for UID {uid}. Please check if the UID is correct.\nThis bot only works for IND server."
            )
            return

        # Otherwise, prepare the formatted response
        formatted_text = (
            "Likes Sent ✅\n"
            f"Player Nickname: {data.get('PlayerNickname', 'N/A')}\n"
            f"Before Likes: {data.get('LikesbeforeCommand', 'N/A')}\n"
            f"After Likes: {data.get('LikesafterCommand', 'N/A')}\n"
            f"Likes Given By Bot: {data.get('LikesGivenByAPI', 'N/A')}"
        )
        bot.edit_message_text(
            chat_id=sent_message.chat.id,
            message_id=sent_message.message_id,
            text=formatted_text
        )
    else:
        bot.edit_message_text(
            chat_id=sent_message.chat.id,
            message_id=sent_message.message_id,
            text="API Error! Server did not return a valid response."
        )
import telebot
import requests
import json

API_KEY = "23092003"
VALID_REGIONS = ["vn", "ind", "me"]

@bot.message_handler(func=lambda message: message.text.lower().startswith(("/spam", "spam")))
def spam_command(message):
    try:
        args = message.text.split()
        if len(args) < 3:
            bot.reply_to(message, "Usage: /spam {region} {uid}\nExample: /spam vn 12345678")
            return
        
        region = args[1].lower().strip()
        uid = args[2].strip()

        if region not in VALID_REGIONS:
            bot.reply_to(message, f"❌ Invalid region! Use only: {', '.join(VALID_REGIONS)}")
            return

        url = f"https://freefire-virusteam.vercel.app/{region}/spamkb?key={API_KEY}&uid={uid}"
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()

            # If UID is validated, format the message properly
            if "UID Validated - API connected" in data:
                user_info = data["UID Validated - API connected"]
                formatted_message = (
                    f'**Spam Friend Request Send Successful**\n'
                    f'**UID:** {user_info["UID"]}\n'
                    f'**Name:** {user_info["Name"]}\n'
                    f'**Level:** {user_info["Level"]}\n'
                    f'**Region:** {user_info["Region"]}\n'
                    f'**Time Sent:** {user_info["Time Sent"]}'
                )
                bot.reply_to(message, formatted_message, parse_mode="MarkdownV2")
                return
            
            # Handle other types of messages
            elif "message" in data:
                bot.reply_to(message, data["message"])
                return

        elif response.status_code == 400:
            data = response.json()
            if "vsteam" in data:
                bot.reply_to(message, data["vsteam"])
            else:
                bot.reply_to(message, "❌ Invalid request.")

        elif response.status_code == 500:
            data = response.json()
            if "vsteam" in data:
                bot.reply_to(message, data["vsteam"])
            else:
                bot.reply_to(message, "❌ Internal Server Error.")

        else:
            bot.reply_to(message, f"❌ API Error {response.status_code}: {response.text}")

    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

import requests
import os
import telebot
import zipfile
import threading
import time

def get_wishlist(region, uid, retries=3, timeout=10):
    url = f"https://ariflex-labs-wishlist-api.vercel.app/items_info?uid={uid}&region={region}"

    for _ in range(retries):  # Retry logic
        try:
            response = requests.get(url, timeout=timeout)
            if response.status_code == 200:
                data = response.json()
                if "items" in data and data["items"]:
                    return data["items"]
        except requests.exceptions.RequestException:
            time.sleep(2)  # Wait before retrying

    return None  # If all retries fail

def download_image(item_id, folder_name):
    """Download image in parallel for fast speed."""
    image_url = f"https://item-id-image.vercel.app/image/{item_id}?key=ADITYA"
    
    for _ in range(3):  # Retry logic for image download
        try:
            img_response = requests.get(image_url, timeout=10)
            if img_response.status_code == 200:
                img_path = os.path.join(folder_name, f"{item_id}.jpg")
                with open(img_path, "wb") as img_file:
                    img_file.write(img_response.content)
                return
        except requests.exceptions.RequestException:
            time.sleep(0)  # Retry after 1 sec

@bot.message_handler(func=lambda message: message.text.lower().startswith(("/wishlist", "wishlist")))
def wishlist(message):
    try:
        args = message.text.split()[1:]  # Extract arguments after command
        if len(args) != 2:
            bot.reply_to(message, "Usage: /wishlist {region} {uid}", reply_to_message_id=message.message_id)  # Send as reply
            return

        region, uid = args
        wishlist_items = get_wishlist(region, uid)

        if wishlist_items:
            folder_name = f"Wishlist_{region}_{uid}_image"  # Folder for this UID
            os.makedirs(folder_name, exist_ok=True)

            response_text = "\nㅤItem ID                Added Time\n"
            response_text += "---------------------------------------\n"

            threads = []  # Multi-threading for fast downloads
            for item in wishlist_items[:100]:  # ✅ Max 100 images download karega
                item_id = item["itemId"]
                added_time = time.strftime("%d/%m/%y, %H:%M:%S", time.gmtime(item["releaseTime"]))
                response_text += f"{item_id:<20} {added_time}\n"

                thread = threading.Thread(target=download_image, args=(item_id, folder_name))
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()  # Wait for all downloads

            # Create ZIP file
            zip_filename = f"{folder_name}.zip"
            with zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(folder_name):
                    for file in files:
                        zipf.write(os.path.join(root, file), arcname=file)

            # Save response text as file
            text_filename = f"{folder_name}/wishlist_{uid}.txt"
            with open(text_filename, "w") as text_file:
                text_file.write(response_text)

            # Send response text first (as reply)
            bot.reply_to(message, f"\n```{response_text}```\n", parse_mode="Markdown", reply_to_message_id=message.message_id)

            # Send ZIP file (as reply)
            with open(zip_filename, "rb") as zip_file:
                bot.send_document(message.chat.id, zip_file, reply_to_message_id=message.message_id)

            # Cleanup
            for file in os.listdir(folder_name):
                os.remove(os.path.join(folder_name, file))
            os.rmdir(folder_name)
            os.remove(zip_filename)

        else:
            bot.reply_to(message, "❌ Check UID or Region.", reply_to_message_id=message.message_id)  # Send as reply

    except Exception as e:
        bot.reply_to(message, f"❌ An error occurred: {str(e)}", reply_to_message_id=message.message_id)  # Send as reply

async def fetch_api(region, uid):
    url = f"https://ariflexlab.vercel.app/send_visit?uid={uid}&region={region}"
    start_time = time.time()  # Start timing
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            end_time = time.time()  # End timing
            execution_time = round(end_time - start_time, 2)
            return await response.text(), execution_time

@bot.message_handler(func=lambda message: message.text.lower().startswith(("/visit", "visit")))
def visit_command(message):
    parts = message.text.split()
    if len(parts) != 3:
        bot.reply_to(message, "Usage: `/visit {region} {uid}`")
        return
    
    region, uid = parts[1], parts[2]
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    response_text, execution_time = loop.run_until_complete(fetch_api(region, uid))

    bot.reply_to(message, f"""
✅ Successfully sent *100* visits to UID *{uid}* in region *{region}*.
⏳ Time taken: *{execution_time}* seconds.

🚀 [Don't Forget To Use This Bot](https://t.me/ff_wishlistadderbot?start=7024870103)

🚀 [JOIN API CHANNEL](https://t.me/ariflexlabs)
""")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "👋 *Welcome to the Free Fire Bot!*\n\n"
        "Here are some commands you can use:\n"
        "• `/isbanned {uid}` – Check if a user is banned\n"
        "• `/mapinfo {region} {Map Code}` – Get map information\n"
        "• `/get {uid}` – Retrieve detailed player info\n"
        "• `/event {region_code}` – See current events\n"
        "• `/like {uid}` – Send likes\n"
        "• `/spam {region} {uid}` – Send spam friend requests\n"
        "• `/wishlist {region} {uid}` – Get wishlist details\n"
        "• `/visit {region} {uid}` – Send visits\n\n"
        "Enjoy using the bot and have fun!"
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

# Run the bot
try:
    print("Bot is running...")
    bot.polling(none_stop=True, timeout=60)
except Exception as e:
    print(f"Error: {e}")