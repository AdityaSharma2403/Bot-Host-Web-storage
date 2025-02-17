import telebot
import os

# Replace with your bot token from BotFather
TOKEN = "8191199392:AAHGGHb6D3e74ekjHL0EDf8BT0Qm6xFWlCQ"
bot = telebot.TeleBot(TOKEN)

# Command to list files in the bot's directory
@bot.message_handler(commands=['list'])
def list_files(message):
    files = os.listdir('.')
    file_list = "\n".join(files) if files else "Directory is empty."
    bot.reply_to(message, f"Files in directory:\n{file_list}")

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Hi")

# Command to change directory
@bot.message_handler(commands=['ch'])
def change_directory(message):
    try:
        new_dir = message.text.split(' ', 1)[1]
        os.chdir(new_dir)
        bot.reply_to(message, f"Changed directory to: {os.getcwd()}")
    except IndexError:
        bot.reply_to(message, "Usage: /ch <directory>")
    except FileNotFoundError:
        bot.reply_to(message, "Directory not found.")
    except Exception as e:
        bot.reply_to(message, f"Error: {str(e)}")

# Command to send a requested file
@bot.message_handler(commands=['get'])
def send_file(message):
    try:
        file_name = message.text.split(' ', 1)[1]
        if os.path.exists(file_name):
            with open(file_name, 'rb') as file:
                bot.send_document(message.chat.id, file)
        else:
            bot.reply_to(message, "File not found.")
    except IndexError:
        bot.reply_to(message, "Usage: /get <filename>")

# Start the bot
if __name__ == "__main__":
    print("Bot is running...")
    bot.polling(none_stop=True)
