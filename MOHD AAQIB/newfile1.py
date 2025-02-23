import telebot
import requests
import time
import httpx
from datetime import datetime

TOKEN = "7748948464:AAEI-TAYOzuELx8dGUHRqfBqs2Wy4Fczphc"
bot = telebot.TeleBot(TOKEN)

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
                bot.reply_to(message, f"UID {user_id} is not banned ☠️.")
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
import aiohttp
import json
import os
from PIL import Image
from io import BytesIO
import re  # ✅ Added for removing <pre> t

# ✅ Async request function
async def make_request(session, url, retries=10, delay=0):
    for i in range(retries):
        try:
            async with session.get(url) as response:
                response.raise_for_status()

                # Detect if response is an image
                content_type = response.headers.get("Content-Type", "")
                if "image" in content_type:
                    return await response.read()  # Return binary data

                return await response.text()  # Return text response
        except (aiohttp.ClientError, asyncio.TimeoutError):
            if i < retries - 1:
                await asyncio.sleep(delay)
            else:
                return None

# ✅ /get Command Handler
@bot.message_handler(func=lambda message: message.text.lower().startswith(("get", "/get")))
def get_info(message):
    asyncio.run(process_info(message))  

# ✅ Main processing function
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
            return  # ⛔ Stops API searching if API 1 fails

        data1 = response1.replace("N/A", "Not Found")
        bot.edit_message_text(f"{data1}", sent_message.chat.id, sent_message.message_id, parse_mode="Markdown")

        url2 = f"https://player-region-info.vercel.app/ADITYA-REGION-INFO?uid={uid}&key=ADITYA"
        response2 = await make_request(session, url2)
        if not response2:
            return  # ❌ No error message for API 2 failure

        region = response2.strip()

        url3 = f"https://player-info-final-original-2.vercel.app/ADITYA-PLAYER-INFO?uid={uid}&region={region}&key=ADITYA"
        response3 = await make_request(session, url3)
        if response3:
            # ✅ Remove <pre> and </pre> before sending
            data3_clean = re.sub(r"</?pre>", "", response3).replace("N/A", "Not Found")
            bot.edit_message_text(f"{data3_clean}", sent_message.chat.id, sent_message.message_id, parse_mode="Markdown")

        url4 = f"https://player-image-info.vercel.app/ADITYA-PLAYER-INFO?uid={uid}&region={region}&key=ADITYA"
        response4 = await make_request(session, url4)
        if response4:
            try:
                image_data = json.loads(response4)
                await create_and_send_image(user_id, image_data, message)
            except json.JSONDecodeError:
                pass  # ❌ No error message for JSON parsing failure

        url5 = f"https://player-image-2.vercel.app/generate-image?uid={uid}&region={region}&key=ADITYA"
        response5 = await make_request(session, url5)
        if response5:
            await send_fifth_api_sticker(user_id, response5, message)

# ✅ Function to create and send image
async def create_and_send_image(user_id, image_data, message):
    async with aiohttp.ClientSession() as session:
        async with session.get("https://i.ibb.co/kghkzfrk/IMG-20250128-094830-355-ai-brush-removebg-sgo6bgx.png") as resp:
            bg_image = Image.open(BytesIO(await resp.read())).convert("RGBA")

        outfit_links = image_data.get("EquippedOutfitImage", [])[:7]
        outfit_positions = [
            {"x": 480, "y": 60, "width": 100, "height": 100},
            {"x": 515, "y": 185, "width": 85, "height": 85},
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
                    img = img.resize((pos["width"], pos["height"]))
                    bg_image.paste(img, (pos["x"], pos["y"]), img)
            except:
                pass  # ❌ No error message for failed outfit image loading

        EquippedSkill_link = image_data.get("EquippedSkillsImage", "").split(", ")[0]
        if EquippedSkill_link:
            try:
                async with session.get(EquippedSkill_link) as resp:
                    img = Image.open(BytesIO(await resp.read())).convert("RGBA")
                    EquippedSkill_position = {"x": 115, "y": 100, "width": 425, "height": 525}
                    img = img.resize((EquippedSkill_position["width"], EquippedSkill_position["height"]))
                    bg_image.paste(img, (EquippedSkill_position["x"], EquippedSkill_position["y"]), img)
            except:
                pass  # ❌ No error message for failed skill image loading

        img_path = "final_image.png"
        bg_image.save(img_path)

        try:
            with open(img_path, "rb") as img_file:
                bot.send_photo(user_id, img_file, reply_to_message_id=message.message_id)
        except:
            pass  # ❌ No error message for failed image sending

# ✅ Function to send fifth API image as a sticker
async def send_fifth_api_sticker(user_id, response5, message):
    try:
        img_bytes = BytesIO(response5)
        img_bytes.seek(0)
        bot.send_sticker(user_id, img_bytes, reply_to_message_id=message.message_id)
    except:
        pass  # ❌ No error message for failed sticker sending

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
        api_url = f"https://ff-event-nine.vercel.app/events?region={ind'cis'pk'ru'bd"

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
        return datetime.fromtimestamp(int(timestamp), datetime.UTC).strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return "Invalid Timestamp"

def send_requests_ultra_fast(url, total_requests):
    success_count = 0
    for _ in range(total_requests):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                success_count += 1
        except requests.RequestException:
            pass  # Handle failed requests silently
    return success_count

def send_requests_batches(url, batches):
    """Send API requests for each batch.
    
    Each successful API call counts as sending 1000 visits.
    """
    success_count = 0
    for _ in range(batches):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                success_count += 1
        except requests.RequestException:
            pass  # Silently ignore any failed requests
    return success_count

@bot.message_handler(func=lambda message: message.text.lower().startswith(('visit', '/visit')))
def handle_visit(message):
    try:
        # Split the command into parts
        command_parts = message.text.split()
        if len(command_parts) != 3:
            bot.reply_to(message, "Usage: visit <number_of_requests> <uid>")
            return

        # Extract the total number of visits and the UID
        try:
            total_requests = int(command_parts[1])
            uid = command_parts[2]
        except ValueError:
            bot.reply_to(message, "Invalid number format for the number of requests.")
            return

        # Validate the input according to the requirements
        if total_requests < 1000:
            bot.reply_to(message, "Number of requests must be at least 1000.")
            return
        if total_requests > 10000:
            bot.reply_to(message, "Number of requests must not exceed 100000.")
            return
        if total_requests % 1000 != 0:
            bot.reply_to(message, "Number of requests must be a multiple of 1000.")
            return

        # Determine how many API calls (batches) to make
        batches = total_requests // 1000

        # Inform the user that processing has started
        processing_message = bot.reply_to(message, "Processing... Please wait.")

        # Construct the API URL (the API does not need region info)
        url = f"https://foxvisit.vercel.app/visit?uid={uid}"

        # Start timing
        start_time = time.time()

        # Send the API requests for the required number of batches
        success_count = send_requests_batches(url, batches)

        # Calculate the elapsed time
        elapsed_time = time.time() - start_time

        # Each successful batch sends 1000 visits
        result_message = (
            f"Successfully sent {success_count * 1000}/{total_requests} visits to UID {uid}.\n"
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