import telebot
import requests
import time
import httpx
from datetime import datetime

API_TOKEN = "7645208429:AAEsWBJV8_3ShQaXkDrxWenZAJM0kTJHvbI"
bot = telebot.TeleBot(API_TOKEN)

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

@bot.message_handler(func=lambda message: 'mapinfo' in message.text.lower())
def get_map_info(message):
    try:
        # Extract map_code from the message
        command_parts = message.text.split()
        if len(command_parts) < 2:
            bot.reply_to(message, "Please provide a map code. Usage: /mapinfo {map_code}")
            return
        
        map_code = command_parts[1].lstrip('#')  # Remove any leading '#' from map code
        
        # List of region codes to check
        region_codes = ["IND", "SG", "BR", "RU", "ID", "TW", "US", "VN", "TH", "ME", "PK", "CIS", "BD"]
        valid_response = False  # Flag to check if any response is valid
        
        # Iterate through region codes and check for valid data
        for region_code in region_codes:
            api_url = f"https://freefireinfo.vercel.app/map?region={region_code}&code=%23{map_code}&key=SHAH"
            response = requests.get(api_url)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    # Extract Craftland Map details
                    craftland_details = data['data'].get('Craftland Map Details', {})
                    if craftland_details:
                        # Format the map details into a readable message
                        map_info = f"Region: {region_code}\n"
                        map_info += "Craftland Map Details:\n"
                        map_info += f"MapCode: {craftland_details.get('MapCode', 'N/A')}\n"
                        map_info += f"Creator: {craftland_details.get('Creator', 'N/A')}\n"
                        map_info += f"Title: {craftland_details.get('Title', 'N/A')}\n"
                        map_info += f"Description: {craftland_details.get('Description', 'N/A')}\n"
                        map_info += f"Subscribers: {craftland_details.get('Subscribers', 'N/A')}\n"
                        map_info += f"Likes: {craftland_details.get('Likes', 'N/A')}\n"
                        map_info += f"Teams: {craftland_details.get('Teams', 'N/A')}\n"
                        map_info += f"PlayAverage: {craftland_details.get('PlayAverage', 'N/A')}\n"
                        map_info += f"Rounds: {craftland_details.get('Rounds', 'N/A')}\n"
                        map_info += f"Mode: {craftland_details.get('Mode', 'N/A')}\n"

                        # Send the map info to the user and mark the response as valid
                        bot.reply_to(message, map_info)
                        valid_response = True
                        break  # Stop checking other regions as we have valid data
            
        if not valid_response:
            bot.reply_to(message, "No valid data found for the given map code in any region.")
    except Exception as e:
        bot.reply_to(message, f"An error occurred: {str(e)}")

import asyncio
import telebot
import re
import aiohttp
import json
import os
from PIL import Image
from io import BytesIO

# Async request function with retries
async def make_request(session, url, retries=3, delay=2):
    for i in range(retries):
        try:
            async with session.get(url) as response:
                response.raise_for_status()
                return await response.text()
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            if i < retries - 1:
                print(f"Error: {e}. Retrying... ({i + 1}/{retries})")
                await asyncio.sleep(delay)
            else:
                print(f"Error: {e}. Max retries reached.")
                return None

# ✅ /get Command Handler
@bot.message_handler(func=lambda message: message.text.lower().startswith(('get', '/get')))
def get_info(message):
    asyncio.run(process_info(message)) 

# Main processing function
async def process_info(message):
    user_id = message.chat.id  
    uid = message.text.split()[1] if len(message.text.split()) > 1 else None

    if not uid or not uid.isdigit():
        bot.reply_to(message, "*Usage:* `Get <uid>`\n_UID should contain only numbers._", parse_mode="Markdown")
        return

    async with aiohttp.ClientSession() as session:
        url1 = f"https://player-info-final-original-1.vercel.app/ADITYA-PLAYER-INFO?uid={uid}&key=ADITYA"
        sent_message = bot.reply_to(message, f"Fetching details for UID `{uid}`...", parse_mode="Markdown")
        response1 = await make_request(session, url1)

        if not response1:
            bot.edit_message_text("⚠️ *Error:* UID not found in the database.", sent_message.chat.id, sent_message.message_id, parse_mode="Markdown")
            return

        data1 = re.sub(r"<pre.*?>|</pre>", "", response1).replace("N/A", "Not Found")
        bot.edit_message_text(f"{data1}", sent_message.chat.id, sent_message.message_id, parse_mode="Markdown")

        url2 = f"https://player-region-info.vercel.app/ADITYA-REGION-INFO?uid={uid}&key=ADITYA"
        response2 = await make_request(session, url2)
        if not response2:
            bot.send_message(user_id, "⚠️ *Error:* Region data missing.", parse_mode="Markdown")
            return

        region = re.sub(r"<pre.*?>|</pre>", "", response2).strip()

        url3 = f"https://player-info-final-original-2.vercel.app/ADITYA-PLAYER-INFO?uid={uid}&region={region}&key=ADITYA"
        response3 = await make_request(session, url3)
        if response3:
            data3 = re.sub(r"<pre.*?>|</pre>", "", response3).replace("N/A", "Not Found")
            bot.edit_message_text(f"{data3}", sent_message.chat.id, sent_message.message_id, parse_mode="Markdown")

        url4 = f"https://player-image-info.vercel.app/ADITYA-PLAYER-INFO?uid={uid}&region={region}&key=ADITYA"
        response4 = await make_request(session, url4)
        if response4:
            try:
                image_data = json.loads(response4)
                await create_and_send_image(user_id, image_data, message)  # ✅ Pass message
            except json.JSONDecodeError:
                bot.send_message(user_id, "⚠️ *Error:* Failed to parse image data.", parse_mode="Markdown")

async def create_and_send_image(user_id, image_data, message):
    async with aiohttp.ClientSession() as session:

        # Load background image
        async with session.get("https://i.ibb.co/kghkzfrk/IMG-20250128-094830-355-ai-brush-removebg-sgo6bgx.png") as resp:
            bg_image = Image.open(BytesIO(await resp.read())).convert("RGBA")

        # **Outfit Images (Max 7)**
        outfit_links = image_data.get("EquippedOutfitImage", [])[:7]  # Ensure max 7 outfits
        outfit_positions = [
            {"x": 480, "y": 60, "width": 100, "height": 100},
            {"x": 515, "y": 185 ,"width": 85, "height": 85},
            {"x": 495, "y": 305, "width": 100, "height": 100},
            {"x": 40, "y": 140, "width": 115, "height": 115},
            {"x": 75, "y": 485, "width": 120, "height": 115},
            {"x": 455, "y": 485, "width": 120, "height": 120},
            {"x": 45, "y": 315, "width": 110, "height": 110}
        ]

        for idx, img_url in enumerate(outfit_links):
            try:
                async with session.get(img_url) as resp:
                    img = Image.open(BytesIO(await resp.read())).convert("RGBA")
                    pos = outfit_positions[idx]
                    img = img.resize((pos["width"], pos["height"]))  # Resize using width & height
                    bg_image.paste(img, (pos["x"], pos["y"]), img)
            except Exception as e:
                print(f"Error loading outfit image: {e}")

        EquippedSkill_link = image_data.get("EquippedSkillsImage", "").split(", ")[0]  # Select only 1 skill image
        if EquippedSkill_link:
            try:
                async with session.get(EquippedSkill_link) as resp:
                    img = Image.open(BytesIO(await resp.read())).convert("RGBA")
                    EquippedSkill_position = {"x": 115, "y": 100, "width": 425, "height": 525}  # Skill Image Position
                    img = img.resize((EquippedSkill_position["width"], EquippedSkill_position["height"]))  # Resize skill image
                    bg_image.paste(img, (EquippedSkill_position["x"], EquippedSkill_position["y"]), img)
            except Exception as e:
                print(f"Error loading skill image: {e}")
        else:
            print("No skill image found.")

        # Save and send the image
        img_path = os.path.abspath("final_image.png")
        bg_image.save(img_path)

        # Fix for sending image - handling failed image processing
        try:
            with open(img_path, "rb") as img_file:
                bot.send_photo(user_id, img_file, reply_to_message_id=message.message_id)  # ✅ Reply to user
        except Exception as e:
            bot.send_message(user_id, f"⚠️ *Error:* Failed to send image. {str(e)}", parse_mode="Markdown")

# Function to handle the command /event {region_code} or event {region_code}
import requests
from datetime import datetime

@bot.message_handler(func=lambda message: message.text.lower().startswith('/event') or message.text.lower().startswith('event'))
def event(message):
    try:
        # Extract region code from the message
        command_parts = message.text.split()
        if len(command_parts) < 2:
            bot.reply_to(message, "Please provide a region code. Usage: /event {region_code} or event {region_code}")
            return

        region_code = command_parts[1]
        api_url = f"https://api.nowgarena.com//api/events?region={region_code}&key=projetoswq"

        # Fetch the data from the API
        response = requests.get(api_url)
        if response.status_code == 200:
            data = response.json()

            # Check if events exist in the API response
            if data.get('events'):
                events = data['events']
                formatted_message = f"🎉 *Events in Region:* `{region_code.upper()}`\n\n"

                for event in events:
                    title = event.get('title', 'N/A')
                    image_url = event.get('image', 'No Image Available')
                    start_time = format_timestamp(event.get('start', 0))
                    end_time = format_timestamp(event.get('end', 0))

                    formatted_message += (
                        f"*Title:* {title}\n"
                        f"*Start:* {start_time}\n"
                        f"*End:* {end_time}\n"
                        f"[View Banner]({image_url})\n\n"
                    )
            else:
                formatted_message = f"No events currently available for the region code: {region_code}."
        else:
            formatted_message = f"Error: Unable to fetch data. Status code: {response.status_code}"

        # Send the formatted message
        bot.reply_to(message, formatted_message, parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"An error occurred: {str(e)}")


def format_timestamp(timestamp):
    """
    Convert a timestamp to a readable date and time string.
    """
    try:
        return datetime.utcfromtimestamp(int(timestamp)).strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return "Invalid Timestamp"

# Universal handler for 'visit' and '/visit'
@bot.message_handler(func=lambda message: message.text.lower().startswith(('visit', '/visit')))
def handle_visit(message):
    try:
        # Parse the command arguments
        command_parts = message.text.split()
        if len(command_parts) != 3:
            bot.reply_to(message, "Usage: visit <number_of_requests> <uid>")
            return

        # Extract number of requests and UID
        try:
            total_requests = int(command_parts[1]) // 100  # Divide by 100 to convert to batches
        except ValueError:
            bot.reply_to(message, "Invalid number format for the number of requests.")
            return

        uid = command_parts[2]

        # Validate input
        if total_requests <= 0:
            bot.reply_to(message, "Number of requests must be at least 100.")
            return

        # Send "Processing..." message
        processing_message = bot.reply_to(message, "Processing... Please wait.")

        # Construct the URL
        url = f"https://ariiflexlabs.vercel.app/send_visit?uid={uid}"

        # Start timing
        start_time = time.time()

        # Send requests
        success_count = send_requests_ultra_fast(url, total_requests)

        # Calculate elapsed time
        elapsed_time = time.time() - start_time

        # Edit "Processing..." message with the result
        result_message = (
            f"Successfully sent {success_count * 100}/{total_requests * 100} views to UID {uid}.\n"
            f"Time taken: {elapsed_time:.2f} seconds."
        )
        bot.edit_message_text(result_message, chat_id=message.chat.id, message_id=processing_message.message_id)
    except Exception as e:
        bot.reply_to(message, f"An error occurred: {str(e)}")

# Run the bot
try:
    print("Bot is running...")
    bot.polling()
except Exception as e:
    print(f"Error: {e}")