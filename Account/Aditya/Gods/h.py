import re
import logging
import time
import asyncio
from flask import Flask, request, jsonify, send_file
import httpx
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


async def fetch_image_async(url: str, client: httpx.AsyncClient) -> Image.Image:
    """Fetch and return an image from a URL asynchronously."""
    try:
        logging.info("Fetching image from %s", url)
        response = await client.get(url)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content)).convert("RGBA")
        logging.info("Image fetched successfully from %s", url)
        return img
    except Exception as e:
        logging.error("Error fetching image from %s: %s", url, e)
        return None


async def fetch_equipped_outfits_async(uid: str, region: str, client: httpx.AsyncClient):
    """Fetch EquippedOutfit and EquippedSkills from the API asynchronously."""
    try:
        api_url = API_URL.format(uid=uid, region=region)
        logging.info("Fetching equipped outfits from %s", api_url)
        response = await client.get(api_url)
        response.raise_for_status()
        data = response.json()
        outfits = data.get("AccountProfileInfo", {}).get("EquippedOutfit", [])
        skills = data.get("AccountProfileInfo", {}).get("EquippedSkills", [])
        logging.info("Fetched outfits: %s, skills: %s", outfits, skills)
        return outfits, skills
    except Exception as e:
        logging.error("Error fetching data: %s", e)
        return [], []


def extract_valid_skill_code(skills) -> str:
    """Find the first valid 3-5 digit skill code and modify its last digit to '6'."""
    for skill in skills:
        skill_str = str(skill)
        if 3 <= len(skill_str) <= 5:
            return skill_str[:-1] + "6"
    return None


def assign_outfits(equipped_outfits):
    """
    Assign outfits based on category.
    For outfit IDs starting with "203", assign the first encountered to TOPS and the second to SECOND_TOP.
    Other categories are assigned as before.
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


async def load_category_image_async(category: str, candidate, fallback: str, client: httpx.AsyncClient) -> Image.Image:
    """
    Load the outfit image for a given category asynchronously.
    For HEADS and MASKS, candidate is a list; for others, it's a string.
    """
    if category in ["HEADS", "MASKS"]:
        for candidate_id in candidate:
            img_url = GITHUB_BASE_URL.format(category, candidate_id)
            try:
                response = await client.get(img_url)
                if response.status_code == 200:
                    return Image.open(BytesIO(response.content)).convert("RGBA")
            except Exception as e:
                logging.warning(f"Error loading {category} with {candidate_id}: {e}")
        # Try fallback if none succeeded.
        img_url = GITHUB_BASE_URL.format(category, fallback)
    else:
        img_url = GITHUB_BASE_URL.format(category, candidate or fallback)
    try:
        response = await client.get(img_url)
        if response.status_code == 200:
            return Image.open(BytesIO(response.content)).convert("RGBA")
    except Exception as e:
        logging.error(f"Error loading fallback for {category}: {e}")
    return None


async def fetch_character_image_async(character_id: str, client: httpx.AsyncClient) -> Image.Image:
    """Fetch and return the character image using the CHARACTER_API asynchronously."""
    char_url = CHARACTER_API.format(character_id)
    try:
        char_response = await client.get(char_url)
        char_response.raise_for_status()
        char_data = char_response.json()
        char_image_url = char_data.get("Png Image")
        if char_image_url:
            img_response = await client.get(char_image_url)
            if img_response.status_code == 200:
                char_img = Image.open(BytesIO(img_response.content)).convert("RGBA")
                return char_img
    except Exception as e:
        logging.error(f"Error loading character image: {e}")
    return None


async def overlay_images_async(bg_url: str, outfit_items: dict, character_id: str = None) -> BytesIO:
    """
    Create a composite image with concurrent fetching.
    
    Stacking order:
      1. Background image (from bg_url)
      2. Overlay layer from OVERLAY_LAYER_URL
      3. Outfit images overlaid in predefined positions
      4. Character image (if available) overlaid last
    """
    async with httpx.AsyncClient(timeout=20.0) as client:
        # Schedule concurrent fetching of background and overlay images.
        bg_task = asyncio.create_task(fetch_image_async(bg_url, client))
        overlay_task = asyncio.create_task(fetch_image_async(OVERLAY_LAYER_URL, client))
        
        # Prepare tasks for outfit images.
        outfit_tasks = {}
        for category, pos in IMAGE_POSITIONS.items():
            if category == "CHARACTER":
                continue
            if category in ["HEADS", "MASKS"]:
                candidate_list = outfit_items.get(category, [])
                fallback = FALLBACK_ITEMS[category]
                task = asyncio.create_task(load_category_image_async(category, candidate_list, fallback, client))
            elif category == "TOPS":
                candidate = outfit_items.get("TOPS")
                fallback = FALLBACK_ITEMS["TOPS"]
                task = asyncio.create_task(load_category_image_async(category, candidate, fallback, client))
            elif category == "SECOND_TOP":
                candidate = outfit_items.get("SECOND_TOP")
                fallback = FALLBACK_ITEMS["TOPS"]
                task = asyncio.create_task(load_category_image_async("TOPS", candidate, fallback, client))
            else:
                candidate = outfit_items.get(category)
                fallback = FALLBACK_ITEMS.get(category)
                task = asyncio.create_task(load_category_image_async(category, candidate, fallback, client))
            outfit_tasks[category] = task
        
        # Schedule fetching of the character image if available.
        char_task = asyncio.create_task(fetch_character_image_async(character_id, client)) if character_id else None

        # Await the background and overlay images.
        bg = await bg_task
        if bg is None:
            raise Exception("Failed to load background image.")
        overlay_img = await overlay_task

        # Await outfit images.
        outfit_images = {cat: await task for cat, task in outfit_tasks.items()}
        char_img = await char_task if char_task else None

    # Resize the background to match the overlay image's size if available.
    if overlay_img:
        final_size = overlay_img.size
        bg = bg.resize(final_size, Image.LANCZOS)
        bg.paste(overlay_img, (0, 0), overlay_img)
    else:
        logging.warning("Failed to load overlay layer image; proceeding with background as is.")

    # Overlay each outfit image.
    for category, pos in IMAGE_POSITIONS.items():
        if category == "CHARACTER":
            continue
        img = outfit_images.get(category)
        if img:
            img = img.resize((pos["width"], pos["height"]))
            bg.paste(img, (pos["x"], pos["y"]), img)

    # Overlay character image if available.
    if char_img:
        pos = IMAGE_POSITIONS["CHARACTER"]
        char_img = char_img.resize((pos["width"], pos["height"]))
        bg.paste(char_img, (pos["x"], pos["y"]), char_img)

    # Save final composite image to a BytesIO stream.
    output = BytesIO()
    bg.save(output, format="PNG")
    output.seek(0)
    return output


@app.route('/generate-image', methods=['GET'])
async def generate_image_route():
    start_time = time.time()
    try:
        uid = request.args.get("uid")
        if not uid:
            return jsonify({"error": "Please provide UID"}), 400

        # Validate region.
        region_param = request.args.get("region")
        valid_regions = ["ind", "sg", "br", "ru", "id", "tw", "us", "vn", "th", "me", "pk", "cis", "bd", "na"]
        if region_param:
            region_param = region_param.lower()
            if region_param not in valid_regions:
                return jsonify({"error": "Invalid Region. Please enter a valid region."}), 400
            search_regions = [region_param]
        else:
            search_regions = valid_regions

        async with httpx.AsyncClient(timeout=20.0) as client:
            # Try to fetch API data concurrently across the possible regions.
            used_region = None
            equipped_outfits = None
            equipped_skills = None
            for reg in search_regions:
                outfits, skills = await fetch_equipped_outfits_async(uid, reg, client)
                if outfits:
                    used_region = reg
                    equipped_outfits = outfits
                    equipped_skills = skills
                    break

        if not used_region:
            return jsonify({"error": "Invalid UID or no valid API response received"}), 400

        logging.info(f"Using region: {used_region} for UID: {uid}")

        # Use provided background URL or default.
        bg_url = request.args.get("bg", BG_IMAGE_URL)

        outfit_items = assign_outfits(equipped_outfits)
        character_id = extract_valid_skill_code(equipped_skills)
        final_image = await overlay_images_async(bg_url, outfit_items, character_id)

        elapsed_time = time.time() - start_time
        print(f"Image generation took {elapsed_time:.2f} seconds")

        return send_file(final_image, mimetype='image/png')
    except Exception as e:
        logging.error(f"Error generating image: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    # For best async performance, run this app with an ASGI server (e.g. Hypercorn or Uvicorn)
    app.run(host='0.0.0.0', port=5000)