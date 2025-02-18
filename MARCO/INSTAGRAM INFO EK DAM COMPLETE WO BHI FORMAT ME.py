import telebot
import requests
from bs4 import BeautifulSoup
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# Telegram bot token
BOT_TOKEN = "7998114530:AAGcXANM1fiA-SVwYzHlv2X3M90RfQ-jmm8"
bot = telebot.TeleBot(BOT_TOKEN)

# Welcome message
@bot.message_handler(commands=['start'])
def welcome_message(message):
    first_name = message.from_user.first_name  # Extract the user's first name
    bot.reply_to(
        message,
        f"**WELCOME {first_name.upper()} TO THE INSTAGRAM INFO BOT**\n\n"
        "_Send your Instagram username in this format:_\n"
        "`/insta <username>`\n\n"
        "**EXAMPLE:**\n"
        "`/insta __iam__marco___`\n\n"
        "CREDIT = @ITZ_MARCO_777",
        parse_mode="Markdown"
    )

# Command handler for /insta
@bot.message_handler(commands=['insta'])
def get_instagram_info(message):
    try:
        username = message.text.split()[1]
        bot.reply_to(message, f"Fetching information for @{username}... Please wait.")

        url = f"https://www.instagram.com/{username}/"
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract meta description (contains followers, following, posts)
            description = soup.find('meta', attrs={'name': 'description'})['content']
            image_url = soup.find('meta', attrs={'property': 'og:image'})['content']

            # Extract numerical details
            details = description.split("-")[0].strip().split(", ")
            followers = details[0].split()[0]
            following = details[1].split()[0]
            posts = details[2].split()[0]

            # Extract bio
            bio = description.split("-")[-1].strip()

            # Structured Response
            response_text = f"""```
Instagram Info for @{username}

FOLLOWERS = {followers}
FOLLOWING = {following}
POSTS     = {posts}

{bio}
```"""

            bot.reply_to(message, response_text, parse_mode="Markdown")
            bot.send_photo(message.chat.id, image_url)

            # Add inline button for credits
            markup = InlineKeyboardMarkup()
            credit_button = InlineKeyboardButton(
                "CREDIT: @PAPA_CHIPS", 
                url="https://youtube.com/@electro.gamer.99?si=8IsNAZaKaAe-eVT7"
            )
            markup.add(credit_button)
            bot.send_message(message.chat.id, "For more details, click below:", reply_markup=markup)
        else:
            bot.reply_to(message, f"**Could not find user @{username}. Please check the username.**")
    except Exception as e:
        bot.reply_to(message, "Error: Please use the command like this: /insta <username>")

# Start the bot
print("  Bot is running...")
bot.polling()