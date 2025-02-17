import logging
from datetime import datetime
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.helpers import escape_markdown

# Configure Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Constants
BOT_TOKEN = "8047305869:AAGsqhyZ0P7XZcatJgzHc5hDMM_BjqiLS-U"  # Replace with your bot token
ALLOWED_GROUP_ID = -1002281705732  # Replace with your group ID

# Utility Functions
def get_profile_info(uid, region):
    url = f"https://krishna-psi.vercel.app/profile_info?uid={uid}&region={region}&key=teamXkrishna"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching profile info: {e}")
        return None

def format_timestamp(timestamp):
    try:
        if isinstance(timestamp, str) and timestamp.isdigit():
            timestamp = int(timestamp)
        return datetime.fromtimestamp(timestamp).strftime('%d %B %Y %H:%M:%S')
    except Exception as e:
        logger.error(f"Error formatting timestamp: {e}")
        return "Not Available"

def fetch_item_name(item_id):
    if not item_id:
        return "N/A"
    # Add logic to fetch item name from item ID if required
    return f"ItemName_{item_id}"

# Message Handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ALLOWED_GROUP_ID:
        await update.message.reply_text("This bot can only be used in the specified group.")
        return

    message_text = update.message.text

    if message_text.startswith("Get"):
        parts = message_text.split()
        if len(parts) != 3:
            await update.message.reply_text("Please provide UID and Region in the format: Get <Region> <UID>")
            return

        region, uid = parts[1], parts[2]
        message = await update.message.reply_text(f"Fetching details for UID {uid} in region {region}, please wait...")

        profile_data = get_profile_info(uid, region)
        if not profile_data:
            await message.edit_text("Sorry, there was an issue fetching data. Please try again later.")
            return

        account_info = profile_data.get('AccountInfo', {})
        social_info = profile_data.get('socialinfo', {})
        guild_info = profile_data.get('GuildInfo', {})
        pet_info = profile_data.get('petInfo', {})
        credit_score_info = profile_data.get('creditScoreInfo', {})
        captainBasicInfo = profile_data.get('captainBasicInfo', {})

        title_name = fetch_item_name(account_info.get('Title'))
        leader_title_name = fetch_item_name(captainBasicInfo.get('title'))
        pet_type_name = fetch_item_name(pet_info.get('id'))

        created_at = format_timestamp(account_info.get('AccountCreateTime', 'Not Available'))
        last_login = format_timestamp(account_info.get('AccountLastLogin', 'Not Available'))
        leader_created_at = format_timestamp(captainBasicInfo.get('createAt', 'Not Available'))
        leader_last_login = format_timestamp(captainBasicInfo.get('lastLoginAt', 'Not Available'))

        formatted_message = (
            f"<b>ACCOUNT INFO:</b>\n\n"
            f"┌🧑‍💻 <b>ACCOUNT BASIC INFO</b>\n"
            f"├─ <b>Name:</b> {escape_markdown(account_info.get('AccountName', 'Unknown'))}\n"
            f"├─ <b>UID:</b> {uid}\n"
            f"├─ <b>Level:</b> {account_info.get('AccountLevel', 'N/A')} (Exp: {account_info.get('AccountEXP', 'N/A')})\n"
            f"├─ <b>Region:</b> {region}\n"
            f"├─ <b>Likes:</b> {account_info.get('AccountLikes', 'N/A')}\n"
            f"├─ <b>Honor Score:</b> {credit_score_info.get('creditScore', 'N/A')}\n"
            f"├─ <b>Title:</b> {escape_markdown(title_name)}\n"
            f"└─ <b>Signature:</b> {escape_markdown(social_info.get('AccountSignature', 'No Signature'))}\n\n"

            f"┌🎮 <b>ACCOUNT ACTIVITY</b>\n"
            f"├─ <b>Most Recent OB:</b> {account_info.get('ReleaseVersion', 'N/A')}\n"
            f"├─ <b>Booyah Pass:</b> {account_info.get('hasElitePass', 'Free Version')}\n"
            f"├─ <b>Current BP Badges:</b> {account_info.get('AccountBPBadges', 'N/A')}\n"
            f"├─ <b>BR Rank:</b> {account_info.get('BrRankPoint', 'N/A')}\n"
            f"├─ <b>CS Points:</b> {account_info.get('CsRankPoint', 'N/A')}\n"
            f"├─ <b>Created At:</b> {created_at}\n"
            f"└─ <b>Last Login:</b> {last_login}\n\n"

            f"┌👕 <b>ACCOUNT OVERVIEW</b>\n"
            f"├─ <b>Avatar ID:</b> {account_info.get('AccountAvatarId', 'Default')}\n"
            f"├─ <b>Banner ID:</b> {account_info.get('AccountBannerId', 'Default')}\n"
            f"├─ <b>Equipped Skills:</b> {profile_data.get('AccountProfileInfo', {}).get('EquippedSkills', 'N/A')}\n"
            f"├─ <b>Equipped Gun ID:</b> {account_info.get('EquippedWeapon', 'N/A')}\n"
            f"└─ <b>Outfits:</b> <b>Graphically Presented Below! 😉\n\n</b>"

            f"┌🐾 <b>PET DETAILS</b>\n"
            f"├─ <b>Equipped?:</b> {pet_info.get('isSelected', 'No')}\n"
            f"├─ <b>Pet Name:</b> {escape_markdown(pet_info.get('name', 'N/A'))}\n"
            f"├─ <b>Pet Type:</b> {escape_markdown(pet_type_name)}\n"
            f"├─ <b>Pet Exp:</b> {pet_info.get('exp', 'N/A')}\n"
            f"└─ <b>Pet Level:</b> {pet_info.get('level', 'N/A')}\n\n"

            f"┌🛡️ <b>GUILD INFO</b>\n"
            f"├─ <b>Guild Name:</b> {escape_markdown(guild_info.get('GuildName', 'N/A'))}\n"
            f"├─ <b>Guild ID:</b> {guild_info.get('GuildID', 'N/A')}\n"
            f"├─ <b>Guild Level:</b> {guild_info.get('GuildLevel', 'N/A')}\n"
            f"├─ <b>Guild Members:</b> {guild_info.get('GuildMember', 'N/A')}\n"
            f"└─ <b>Leader Info:</b>\n"
            f"    ├─ <b>Leader Name:</b> {escape_markdown(captainBasicInfo.get('nickname', 'N/A'))}\n"
            f"    ├─ <b>Leader UID:</b> {captainBasicInfo.get('accountId', 'N/A')}\n"
            f"    ├─ <b>Leader Level:</b> {captainBasicInfo.get('level', 'N/A')}\n"
            f"    ├─ <b>Leader Created At:</b> {leader_created_at}\n"
            f"    ├─ <b>Leader Last Login:</b> {leader_last_login}\n"
            f"    ├─ <b>Leader Title:</b> {escape_markdown(leader_title_name)}\n"
            f"    └─ <b>Leader BR Points:</b> {captainBasicInfo.get('rankingPoints', 'N/A')}\n\n"

            f"<b>OWNER:</b> ☠ Tanhung11231 ✔\n\n"
            f"<b>FREE FIRE VIP:</b> ☠ https://t.me/freefirevipvn\n"
            f"<b>Main Group: https://t.me/checkinfo132</b> ☠ "
        )

        await message.edit_text(formatted_message, parse_mode="HTML")

# Main Function
def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling()

if __name__ == '__main__':
    main()