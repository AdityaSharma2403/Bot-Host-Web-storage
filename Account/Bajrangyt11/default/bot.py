import telebot
import requests
from io import BytesIO
from PIL import Image

# Replace with your bot token
BOT_TOKEN = "7443226580:AAGcEoq1853TNtvM1WaHm03-5KTuCQANsUw"

# Initialize bot
bot = telebot.TeleBot(BOT_TOKEN)

# API Endpoints
INFO_API = "https://ariiflexlabs-playerinfo.onrender.com/ff_info?uid={uid}&region={region}"
IMAGE_API = "https://player-image-1.vercel.app/generate-image?bg=https://iili.io/2pEKU8b.png&uid={uid}&region={region}&key=ADITYA"
STICKER_API = "https://player-image-2.vercel.app/generate-image?uid={uid}&region={region}&key=ADITYA"

# Valid Regions
VALID_REGIONS = ["ind", "sg", "br", "ru", "id", "tw", "us", "vn", "th", "me", "pk", "cis", "bd", "na"]

@bot.message_handler(commands=['get'])
@bot.message_handler(func=lambda message: message.text.lower().startswith("get"))  
def get_player_info(message):
    try:
        parts = message.text.split()

        if len(parts) < 2:
            bot.reply_to(message, "❌ ᴜꜱᴀɢᴇ: /ɢᴇᴛ <ʀᴇɢɪᴏɴ> <ᴜɪᴅ>, /ɢᴇᴛ <ᴜɪᴅ>, ɢᴇᴛ <ʀᴇɢɪᴏɴ> <ᴜɪᴅ> ᴏʀ ɢᴇᴛ <ᴜɪᴅ>`", parse_mode="Markdown")
            return

        if len(parts) == 2:  # Only UID provided
            uid = parts[1]
            fetching_msg = bot.reply_to(message, f"⏳ *ғᴇᴛᴄʜɪɴɢ  `{uid}` ɪɴғᴏ ғᴏʀ ᴀʟʟ ᴠᴀʟɪᴅ ʀᴇɢɪᴏɴs, ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ...*", parse_mode="Markdown")
            for region in VALID_REGIONS:
                response = requests.get(INFO_API.format(uid=uid, region=region))
                if response.status_code == 200 and "AccountInfo" in response.json():
                    bot.delete_message(message.chat.id, fetching_msg.message_id)
                    send_player_info(message, response.json(), uid, region)
                    return
            bot.edit_message_text("❌ *ɪɴᴠᴀʟɪᴅ ᴜɪᴅ ᴏʀ ɴᴏ ᴠᴀʟɪᴅ ʀᴇɢɪᴏɴ ꜰᴏᴜɴᴅ.*", message.chat.id, fetching_msg.message_id, parse_mode="Markdown")

        elif len(parts) == 3:  # Region and UID provided
            region, uid = parts[1], parts[2]
            if region.lower() not in VALID_REGIONS:
                bot.reply_to(message, "❌ *ɪɴᴠᴀʟɪᴅ ʀᴇɢɪᴏɴ. ᴜꜱᴇ ᴀ ᴠᴀʟɪᴅ ʀᴇɢɪᴏɴ ʟɪᴋᴇ:* `ɪɴᴅ`, `ꜱɢ`, `ʙʀ`, `ʀᴜ`, ᴇᴛᴄ.*", parse_mode="Markdown")
                return

            fetching_msg = bot.reply_to(message, f"⏳ *ꜰᴇᴛᴄʜɪɴɢ `{UID}` ɪɴꜰᴏ ꜰᴏʀ ʀᴇɢɪᴏɴ: `{REGION}`, ᴘʟᴇᴀꜱᴇ ᴡᴀɪᴛ...*", parse_mode="Markdown")
            response = requests.get(INFO_API.format(uid=uid, region=region))
            if response.status_code == 200 and "AccountInfo" in response.json():
                bot.delete_message(message.chat.id, fetching_msg.message_id)
                send_player_info(message, response.json(), uid, region)
            else:
                bot.edit_message_text("❌ *ɪɴᴠᴀʟɪᴅ ᴜɪᴅ ᴏʀ ʀᴇɢɪᴏɴ. ᴘʟᴇᴀꜱᴇ ᴛʀʏ ᴀɢᴀɪɴ.*", message.chat.id, fetching_msg.message_id, parse_mode="Markdown")

    except Exception as e:
        bot.reply_to(message, f"❌ *Error: {str(e)}*", parse_mode="Markdown")

def send_player_info(message, data, uid, region):
    """Formats and sends player info as a reply to the user."""
    chat_id = message.chat.id

    info = data["AccountInfo"]
    guild = data.get("GuildInfo", {})
    pet = data.get("petInfo", {})
    leader = data.get("captainBasicInfo", {})

    msg = f"""
╭─❰ ʙᴇsɪᴄ ɪɴғᴏ ❱  
│ 👤 ɴ𝗮𝗺𝗲: `{info.get("AccountName", "N/A")}`  
│ 🆔 ᴜɪᴅ: `{uid}`  
│ 🎮 ʟ𝗲𝘃𝗲𝗹: `{info.get("AccountLevel", "N/A")}`  
│ 🌍 ʀ𝗲𝗴𝗶𝗼𝗻: `{region}`  
│ 👍 ʟ𝗶𝗸𝗲𝘀: `{info.get("AccountLikes", "N/A")}`  
│ 🏅 ʜ𝗼𝗻𝗼𝗿 s𝗰𝗼𝗿𝗲: `{data.get("creditScoreInfo", {}).get("creditScore", "N/A")}`  
│ 🌟 ᴄ𝗲𝗹𝗲𝗯𝗿𝗶𝘁𝘆 s𝘁𝗮𝘁𝘂𝘀: `{info.get("celebrityStatus", "N/A")}`  
│ 🔥 ᴇ𝘃𝗼 ᴀ𝗰𝗰𝗲𝘀𝘀 ʙ𝗮𝗱𝗴𝗲: `{info.get("hasElitePass", False)}`  
│ 🎭 ᴛ𝗶𝘁𝗹𝗲: `{info.get("Title", "N/A")}`  
│ ✍️ sɪ𝗴𝗻𝗮𝘁𝘂𝗿𝗲: `{data.get("socialinfo", {}).get("AccountSignature", "N/A")}`  
╰─────────────── 
╭─❰ ᴀᴄᴄᴏᴜɴᴛ ᴀᴄᴛɪᴠɪᴛʏ ❱  
├─ 🔄 ᴍ𝗼𝘀𝘁 ʀ𝗲𝗰𝗲𝗻𝘁 ᴏʙ: {data.get("recentOb", "N/A")}  
├─ 🎫 ғ𝗶𝗿𝗲 ᴘ𝗮ss: {"Premium" if info.get("hasElitePass", False) else "Free"}  
├─ 🏆 ᴄ𝘂𝗿𝗿𝗲𝗻𝘁 ʙᴘ ʙ𝗮𝗱𝗴𝗲𝘀: {info.get("currentBpBadges", "N/A")}  
├─ 📈 ʙʀ ʀ𝗮𝗻𝗸: {info.get("BrMaxRank", "N/A")} ({info.get("BrRankPoint", "N/A")})  
├─ 🎯 ᴄs ᴘ𝗼𝗶𝗻𝘁𝘀: {info.get("CsRankPoint", "N/A")}  
├─ 📅 ᴀ𝗰𝗰𝗼𝘂𝗻𝘁 ᴄ𝗿𝗲𝗮𝘁𝗲𝗱: {info.get("AccountCreateTime", "N/A")}  
├─ ⏳ ʟ𝗮𝘀𝘁 ʟᴏ𝗴𝗶𝗻: {info.get("AccountLastLogin", "N/A")}  
╰───────────────  

╭─❰ ᴀᴄᴄᴏᴜɴᴛ ᴏᴠᴇʀᴠɪᴇᴡ ❱  
├─ 🖼️ ᴀ𝘃𝗮𝘁𝗮𝗿 & ʙᴀɴɴᴇʀ: 👇  
├─ 📌 ᴘ𝗶𝗻 ɪᴅ: {info.get("pinId", "N/A")}  
├─ 🛡️ ᴇ𝗾𝘜𝗜𝗣𝗣𝗘𝗗 s𝗸𝗶𝗹𝗹𝘀: {info.get("equippedSkills", "N/A")}  
├─ 🔫 ᴇ𝗾𝘜𝗜𝗣𝗣𝗘𝗗 ɢ𝘂𝗻𝘀: {info.get("equippedGuns", "N/A")}  
├─ 🎥 ᴇ𝗾𝘜𝗜𝗣𝗣𝗘𝗗 ᴀ𝗻𝗶𝗺𝗮𝘁𝗶𝗼𝗻: {info.get("equippedAnimation", "N/A")}  
├─ ⚡ ᴛ𝗿𝗮𝗻𝘀𝗳𝗼𝗿𝗺 ᴀ𝗻𝗶𝗺𝗮𝘁𝗶𝗼𝗻: {info.get("transformAnimation", "N/A")}  
├─ 👗 ᴏ𝘜𝘁𝗳𝗶𝘁𝘀:   👇
╰───────────────  

╭─❰ 𝗣𝗘𝗧 𝗜𝗡𝗙𝗢 ❱  
├─ 🐾 ᴇ𝗾𝘜𝗜𝗣𝗣𝗘𝗗: {pet.get("equipped", "N/A")}  
├─ 🐕 ᴘ𝗲𝘁 ɴ𝗮𝗺𝗲: {pet.get("id", "No Pet")}  
├─ 🦴 ᴘ𝗲𝘁 ᴛʏ𝗽𝗲: {pet.get("skinId", "N/A")}  
├─ 🎖️ ᴘ𝗲𝘁 ᴇ𝘅𝗽: {pet.get("exp", "N/A")}  
├─ 🔼 ᴘ𝗲𝘁 ʟ𝗲𝘃𝗲𝗹: {pet.get("level", "N/A")}  
╰───────────────  

╭─❰ ɢᴜɪʟᴅ ɪɴғᴏ ❱  
├─ 🏰 ɢ𝘂𝗶𝗹𝗱 ɴ𝗮𝗺𝗲: {guild.get("GuildName", "No Guild")}  
├─ 🆔 ɢ𝘂𝗶𝗹𝗱 ɪᴅ: {guild.get("GuildID", "N/A")}  
├─ 🎖️ ɢ𝘂𝗶𝗹𝗱 ʟ𝗲𝘃𝗲𝗹: {guild.get("GuildLevel", "N/A")}  
├─ 👥 ᴍ𝗲𝗺𝗯𝗲𝗿𝘀: {guild.get("GuildMember", "N/A")}  
╰───────────────  

╭─❰ ʟᴇᴀᴅᴇʀ ɪɴғᴏ ❱  
├─ 👑 ɴ𝗮𝗺𝗲: {leader.get("nickname", "N/A")}  
├─ 🆔 ᴜɪᴅ: {leader.get("accountId", "N/A")}  
├─ 🎮 ʟ𝗲𝘃𝗲𝗹: {leader.get("level", "N/A")}  
├─ 📅 ᴄ𝗿𝗲𝗮𝘁𝗲𝗱 ᴀ𝘁: {leader.get("createdAt", "N/A")}  
├─ ⏳ ʟ𝗮𝘀𝘁 ʟᴏ𝗴𝗶𝗻: {leader.get("lastLogin", "N/A")}  
├─ 🎭 ᴛ𝗶𝘁𝗹𝗲: {leader.get("title", "N/A")}  
├─ 🏆 ᴄ𝘂𝗿𝗿𝗲𝗻𝘁 ʙᴘ ʙ𝗮𝗱𝗴𝗲𝘀: {leader.get("currentBpBadges", "N/A")}  
├─ 📈 ʙʀ ᴘ𝗼𝗶𝗻𝘁𝘀: {leader.get("brPoints", "N/A ")}  
├─ 🎯 ᴄs ᴘ𝗼𝗶𝗻𝘁𝘀: {leader.get("csPoints", "N/A")}  
╰───────────────  

╭─❰ ᴏᴡɴᴇʀs ❱  
├─ 🎮 [ᴄᴏ-ᴏᴡɴᴇʀ: ɪʀᴏɴ ᴍᴀɴ](t.me/Iromanhindigaming) - [ʏᴏᴜᴛᴜʙᴇ](https://youtube.com/@ironmanhindigaming)  
├─ 🔥 [ᴏᴡɴᴇʀ: ᴍᴀʀᴄᴏ](t.me/PAPA_CHIPS) - [ʏᴏᴜᴛᴜʙᴇ](https://youtube.com/@electro.gamer.99?s=si=fmpZQvOEpAVshPa7)  
╰───────────────  
"""
    bot.reply_to(message, msg, parse_mode="Markdown", disable_web_page_preview=True)

    # Send Player Image
    image_url = IMAGE_API.format(uid=uid, region=region)
    bot.send_photo(chat_id, image_url, caption="🖼️ *Here is the player image!*", reply_to_message_id=message.message_id)

    # Download sticker image and convert to WebP format
    sticker_url = STICKER_API.format(uid=uid, region=region)
    sticker_response = requests.get(sticker_url)

    if sticker_response.status_code == 200:
        image = Image.open(BytesIO(sticker_response.content))
        webp_io = BytesIO()
        image.save(webp_io, format="WEBP")
        webp_io.seek(0)
        bot.send_sticker(chat_id, webp_io, reply_to_message_id=message.message_id)
    else:
        bot.reply_to(message, "❌ *ꜰᴀɪʟᴇᴅ ᴛᴏ ꜰᴇᴛᴄʜ ᴀᴠᴀᴛᴀʀ ʙᴀɴɴᴇʀ*", parse_mode="Markdown")

# Start the bot
print("Bot is running...")
bot.polling(none_stop=True)