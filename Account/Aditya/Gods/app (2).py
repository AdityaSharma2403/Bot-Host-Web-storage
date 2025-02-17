import re
from flask import Flask, request, jsonify, send_file
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

app = Flask(__name__)

# Avatar image position on background
AVATAR_POSITION = {"x": 0, "y": 0, "width": 60, "height": 60}

# Updated font sizes (Increased by 10)
ACCOUNT_NAME_POSITION = {"x": 62, "y": 0, "font_size": 70}  # Increased from 50
ACCOUNT_LEVEL_POSITION = {"x": 190, "y": 50, "font_size": 60}  # Increased from 40
GUILD_NAME_POSITION = {"x": 62, "y": 40, "font_size": 60}  # Increased from 40

# Function to fetch images (Mirror effect removed)
def fetch_image(url):
    """Helper function to fetch an image from a URL."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content)).convert("RGBA")
        return img
    except Exception as e:
        print(f"Error fetching image from {url}: {e}")
        return None

# Function to clean AccountLevel by keeping only numbers
def clean_account_level(text):
    """Keep only numeric characters and remove any non-numeric characters."""
    return re.sub(r'[^0-9]', '', text) if text else "Unknown"

# Validate API key
def validate_key():
    """Function to validate API key."""
    api_key = request.args.get('key')
    if api_key != 'ADITYA':
        return jsonify({"error": "Invalid API key"}), 403
    return None

@app.route('/generate-image', methods=['GET'])
def generate_image():
    """API to generate and return an image."""
    validation_error = validate_key()
    if validation_error:
        return validation_error

    try:
        uid = request.args.get('uid')
        region = request.args.get('region')

        if not uid or not region:
            return jsonify({"error": "Missing uid or region"}), 400

        # Fetch player info
        api_url = f"https://player-image-info.vercel.app/ADITYA-PLAYER-INFO?uid={uid}&region={region}&key=ADITYA"
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        image_data = response.json()

        # Fetch and validate background image (No mirroring)
        banner_image_url = image_data.get("AccountBannerIdImage")
        if not banner_image_url or banner_image_url == "Not Found":
            return jsonify({"error": "AccountBannerIdImage not found"}), 400

        bg_image = fetch_image(banner_image_url)  # No mirroring
        if not bg_image:
            return jsonify({"error": f"Failed to load background image from URL: {banner_image_url}"}), 500

        # Process avatar image (if available)
        avatar_image_url = image_data.get("AccountAvatarIdImage")
        if avatar_image_url and avatar_image_url != "Not Found":
            avatar_img = fetch_image(avatar_image_url)
            if avatar_img:
                avatar_img = avatar_img.resize((AVATAR_POSITION["width"], AVATAR_POSITION["height"]))
                bg_image.paste(avatar_img, (AVATAR_POSITION["x"], AVATAR_POSITION["y"]), avatar_img)

        # Extract necessary text data
        account_name = image_data.get("AccountName", "Unknown")
        account_level = clean_account_level(image_data.get("AccountLevel", "Unknown"))
        guild_name = image_data.get("GuildName", "Unknown")

        formatted_account_level = f"Lvl. {account_level}" if account_level else "Lvl. Unknown"

        # Draw text on the image
        draw = ImageDraw.Draw(bg_image)

        # Load font (system default)
        font = ImageFont.load_default()

        # Draw AccountName text (Increased size)
        draw.text((ACCOUNT_NAME_POSITION["x"], ACCOUNT_NAME_POSITION["y"]), account_name, font=font, fill="white")

        # Draw AccountLevel text (Increased size)
        draw.text((ACCOUNT_LEVEL_POSITION["x"], ACCOUNT_LEVEL_POSITION["y"]), formatted_account_level, font=font, fill="white")

        # Draw GuildName text (Increased size)
        draw.text((GUILD_NAME_POSITION["x"], GUILD_NAME_POSITION["y"]), guild_name, font=font, fill="white")

        # Save the final image to a BytesIO object
        output_image = BytesIO()
        bg_image.save(output_image, format="PNG", optimize=True, quality=100)
        output_image.seek(0)

        return send_file(output_image, mimetype='image/png')

    except Exception as e:
        return jsonify({"error": f"Internal Server Error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)
