import subprocess
import telebot

# Replace with your actual bot token
BOT_TOKEN = "7350733208:AAFNkFut9X7A3TAAPjXdjJ1_A3NbCqLEYzw"
bot = telebot.TeleBot(BOT_TOKEN)

# Store user IDs dynamically (a simple list for now; ideally, use a database)
user_ids = set()

# Function to handle new users
@bot.message_handler(commands=['start'])
def welcome_message(message):
    user_ids.add(message.chat.id)  # Store user ID
    bot.send_message(message.chat.id, "Welcome! You'll receive a notification when installations are done.")

# List of large libraries to install
libraries = [
    "tensorflow",
    "torch",
    "spacy",
    "transformers",
    "opencv-python",
    "scipy",
    "xgboost",
    "lightgbm",
    "dask",
    "numpy",
    "pandas",
    "matplotlib"
]

# Function to install libraries
def install_libraries():
    for lib in libraries:
        subprocess.run(["pip", "install", lib], check=True)

    # Downloading large models for spaCy
    subprocess.run(["python", "-m", "spacy", "download", "en_core_web_lg"], check=True)

# Function to send message to all users
def send_message_to_all():
    for user_id in user_ids:
        bot.send_message(user_id, "Installation of large libraries is Done!")

# Start bot in the background to collect users
import threading
threading.Thread(target=bot.polling, daemon=True).start()

# Run installation and send message to all users
try:
    install_libraries()
    send_message_to_all()
except Exception as e:
    print(f"Error: {e}")
