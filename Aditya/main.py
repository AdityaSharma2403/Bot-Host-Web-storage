import telebot
import yt_dlp
import os

TOKEN = "7851168491:AAElhmwJjBhWbEI3OQo0UAnilCMt_9hfBMI"
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Send me a video link, and I'll download it for you!")

@bot.message_handler(func=lambda message: True)
def download_video(message):
    url = message.text.strip()
    
    if not url.startswith(("http://", "https://")):
        bot.reply_to(message, "Please send a valid video link.")
        return

    bot.reply_to(message, "Downloading video, please wait...")

    ydl_opts = {
        "format": "bestvideo+bestaudio/best",
        "noplaylist": True,
        "outtmpl": "downloaded_video.mp4",
        "quiet": True
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get("title", "video")

        # Send the video
        with open("downloaded_video.mp4", "rb") as video_file:
            bot.send_video(message.chat.id, video_file, caption=title)

        # Cleanup the downloaded file
        os.remove("downloaded_video.mp4")

    except Exception as e:
        bot.reply_to(message, f"Error: {str(e)}")

bot.polling()