import telebot
import yt_dlp
import io

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
        "quiet": True
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            video_url = info["url"]
            title = info.get("title", "video")

        video_file = io.BytesIO()
        video_file.name = f"{title}.mp4"

        with yt_dlp.YoutubeDL({"format": "best", "outtmpl": "-", "quiet": True}) as ydl:
            ydl.download([url])

        bot.send_video(message.chat.id, video_file)
        video_file.close()

    except Exception as e:
        bot.reply_to(message, f"Error: {str(e)}")

bot.polling()