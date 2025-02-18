import re
import logging
from flask import Flask, request, jsonify, send_file
import requests
from io import BytesIO
from PIL import Image

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Default Background Image URL
BG_IMAGE_URL = "https://i.ibb.co/N240RkCg/IMG-20250215-010130-294.jpg"

# Predefined Positions & Sizes for outfit items and character image
IMAGE_POSITIONS = {
    "HEADS": {"x": 480, "y": 60, "width": 100, "height": 100},
    "FACEPAINTS": {"x": 515, "y": 185, "width": 85, "height": 85},
    "MASKS": {"x": 495, "y": 305, "width": 100, "height": 100},
    "TOPS": {"x": 40, "y": 140, "width": 115, "height": 115},
    "SECOND_TOP": {"x": 45, "y": 315, "width": 110, "height": 110},
    "BOTTOMS": {"x": 75, "y": 485, "width": 120, "height": 115},
    "SHOES": {"x": 455, "y": 485, "width": 120, "height": 120},
    "CHARACTER": {"x": 115, "y": 100, "width": 425, "height": 525}
}

# Fallback Outfit IDs for outfit images
FALLBACK_ITEMS = {
    "HEADS": "211000000",
    "MASKS": "208000000",
    "FACEPAINTS": "214000000",
    "TOPS": "203000000",  # Fallback for TOPS and SECOND_TOP
    "BOTTOMS": "204000000",
    "SHOES": "205000000"
}

# Base URLs for outfit images, API and character image API
GITHUB_BASE_URL = "https://raw.githubusercontent.com/AdityaSharma2403/OUTFIT-S/main/{}/{}.png"
API_URL = "https://ariiflexlabs-playerinfo.onrender.com/ff_info?uid={uid}&region={region}"
CHARACTER_API = "https://character-roan.vercel.app/Character_name/Id={}"

# URL for the custom font (not used in this version)
FONT_URL = "https://raw.githubusercontent.com/AdityaSharma2403/Bancheck/main/GFF-Latin-Bold.ttf"

# URL for the overlay layer image
OVERLAY_LAYER_URL = "https://i.ibb.co/39993PDP/IMG-20250128-032242-357-removebg.png"

def fetch_image(url):
    """Fetch and return an image from a URL."""
    try:
        logging.info("Fetching image from %s", url)
        response = requests.get(url)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content)).convert("RGBA")
        logging.info("Image fetched successfully from %s", url)
        return img
    except Exception as e:
        logging.error("Error fetching image from %s: %s", url, e)
        return None

def fetch_equipped_outfits(uid, region):
    """Fetch EquippedOutfit and EquippedSkills from the API."""
    try:
        response = requests.get(API_URL.format(uid=uid, region=region))
        if response.status_code == 200:
            data = response.json()
            outfits = data.get("AccountProfileInfo", {}).get("EquippedOutfit", [])
            skills = data.get("AccountProfileInfo", {}).get("EquippedSkills", [])
            return outfits, skills
        logging.error(f"API Response Error: {response.status_code}")
    except Exception as e:
        logging.error(f"Error fetching data: {e}")
    return [], []

def extract_valid_skill_code(skills):
    """Find the first valid 3-5 digit skill code and modify its last digit to '6'."""
    for skill in skills:
        skill_str = str(skill)
        if 3 <= len(skill_str) <= 5:
            return skill_str[:-1] + "6"
    return None

def assign_outfits(equipped_outfits):
    """
    Assign outfits based on category.
    For outfit IDs starting with "203", assign the first encountered to TOPS 
    and the second to SECOND_TOP. Other categories are assigned as before.
    """
    outfit_candidates = {
        "HEADS": [],
        "MASKS": [],
        "FACEPAINTS": None,
        "TOPS": None,
        "SECOND_TOP": None,
        "BOTTOMS": None,
        "SHOES": None
    }
    
    top_count = 0
    for outfit_id in equipped_outfits:
        outfit_id_str = str(outfit_id)
        prefix = outfit_id_str[:3]
        if prefix == "211":
            outfit_candidates["HEADS"].append(outfit_id_str)
            outfit_candidates["MASKS"].append(outfit_id_str)
        elif prefix == "214":
            if outfit_candidates["FACEPAINTS"] is None:
                outfit_candidates["FACEPAINTS"] = outfit_id_str
        elif prefix == "203":
            top_count += 1
            if top_count == 1:
                outfit_candidates["TOPS"] = outfit_id_str
            elif top_count == 2:
                outfit_candidates["SECOND_TOP"] = outfit_id_str
        elif prefix == "204":
            if outfit_candidates["BOTTOMS"] is None:
                outfit_candidates["BOTTOMS"] = outfit_id_str
        elif prefix == "205":
            if outfit_candidates["SHOES"] is None:
                outfit_candidates["SHOES"] = outfit_id_str
    return outfit_candidates

def load_category_image(category, candidate, fallback):
    """
    Load the outfit image for a given category.
    For HEADS and MASKS, candidate is a list; for others, it's a string.
    """
    if category in ["HEADS", "MASKS"]:
        for candidate_id in candidate:
            img_url = GITHUB_BASE_URL.format(category, candidate_id)
            try:
                img_response = requests.get(img_url)
                if img_response.status_code == 200:
                    return Image.open(BytesIO(img_response.content)).convert("RGBA")
            except Exception as e:
                logging.warning(f"Error loading {category} with {candidate_id}: {e}")
        img_url = GITHUB_BASE_URL.format(category, fallback)
    else:
        img_url = GITHUB_BASE_URL.format(category, candidate or fallback)
    try:
        img_response = requests.get(img_url)
        if img_response.status_code == 200:
            return Image.open(BytesIO(img_response.content)).convert("RGBA")
    except Exception as e:
        logging.error(f"Error loading fallback for {category}: {e}")
    return None

def overlay_images(bg_url, outfit_items, character_id=None):
    """
    Create a composite image with the following stacking order:
      1. Background image (using the provided bg URL if present; else default).
      2. Overlay layer from OVERLAY_LAYER_URL (its size is used as final).
      3. Outfit images are overlaid.
      4. Character image (if available) is overlaid.
    """
    # Use provided background URL or default.
    bg = fetch_image(bg_url)
    if bg is None:
        raise Exception("Failed to load background image.")

    # Fetch overlay layer image.
    overlay_img = fetch_image(OVERLAY_LAYER_URL)
    if overlay_img:
        # Use the overlay layer's size as final composite size.
        final_size = overlay_img.size
        bg = bg.resize(final_size, Image.LANCZOS)
        # Paste overlay layer onto background.
        bg.paste(overlay_img, (0, 0), overlay_img)
    else:
        logging.warning("Failed to load overlay layer image; proceeding with background as is.")

    # Overlay outfit images.
    for category, pos in IMAGE_POSITIONS.items():
        if category == "CHARACTER":
            continue
        if category in ["HEADS", "MASKS"]:
            candidate_list = outfit_items.get(category, [])
            fallback = FALLBACK_ITEMS[category]
            img = load_category_image(category, candidate_list, fallback)
        elif category == "TOPS":
            candidate = outfit_items.get("TOPS")
            fallback = FALLBACK_ITEMS["TOPS"]
            img = load_category_image(category, candidate, fallback)
        elif category == "SECOND_TOP":
            candidate = outfit_items.get("SECOND_TOP")
            fallback = FALLBACK_ITEMS["TOPS"]
            img = load_category_image("TOPS", candidate, fallback)
        else:
            candidate = outfit_items.get(category)
            fallback = FALLBACK_ITEMS.get(category)
            img = load_category_image(category, candidate, fallback)
        if img:
            img = img.resize((pos["width"], pos["height"]))
            bg.paste(img, (pos["x"], pos["y"]), img)
    
    # Overlay character image if available.
    if character_id:
        char_url = CHARACTER_API.format(character_id)
        try:
            char_response = requests.get(char_url)
            if char_response.status_code == 200:
                char_data = char_response.json()
                char_image_url = char_data.get("Png Image")
                if char_image_url:
                    img_response = requests.get(char_image_url)
                    if img_response.status_code == 200:
                        char_img = Image.open(BytesIO(img_response.content)).convert("RGBA")
                        char_img = char_img.resize((IMAGE_POSITIONS["CHARACTER"]["width"], IMAGE_POSITIONS["CHARACTER"]["height"]))
                        bg.paste(char_img, (IMAGE_POSITIONS["CHARACTER"]["x"], IMAGE_POSITIONS["CHARACTER"]["y"]), char_img)
        except Exception as e:
            logging.error(f"Error loading character image: {e}")

    # Save final composite image.
    output = BytesIO()
    bg.save(output, format="PNG")
    output.seek(0)
    return output

@app.route('/generate-image', methods=['GET'])
def generate_image_route():
    try:
        uid = request.args.get("uid")
        region = request.args.get("region")
        if not uid or not region:
            return jsonify({"error": "Missing uid or region"}), 400

        # Validate API key.
        api_key = request.args.get('key')
        if api_key != 'ADITYA':
            return jsonify({"error": "Invalid API key"}), 403

        # Check for optional background image URL.
        bg_url = request.args.get("bg", BG_IMAGE_URL)

        equipped_outfits, equipped_skills = fetch_equipped_outfits(uid, region)
        if not equipped_outfits:
            return jsonify({"error": "No valid API response received"}), 500

        outfit_items = assign_outfits(equipped_outfits)
        character_id = extract_valid_skill_code(equipped_skills)
        final_image = overlay_images(bg_url, outfit_items, character_id)
        return send_file(final_image, mimetype='image/png')
    except Exception as e:
        logging.error(f"Error generating image: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
