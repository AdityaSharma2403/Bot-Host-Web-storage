from flask import Flask, request, jsonify, Response
import requests, datetime, logging, time

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# ----------------------------------
# Skill Mapping Data (Based on your input)
# ----------------------------------
SKILL_MAPPING = {
    "106": {"Character Name": "Olivia", "Skill id": "106", "Png Image": "https://dl.dir.freefiremobile.com/common/web_event/official2.ff.garena.all/202211/435b2230bb59c6a7f087d841e7dc8590.png"},
    "206": {"Character Name": "Kelly", "Skill id": "206", "Png Image": "https://dl.dir.freefiremobile.com/common/web_event/official2.ff.garena.all/202311/a80ef2744fa83dc119cc09249d70444e.png"},
    "306": {"Character Name": "Ford", "Skill id": "306", "Png Image": "https://dl.dir/freefiremobile.com/common/web_event/official2.ff.garena.all/202211/e4eba268be6b474381acc6c4b282f5ea.png"},
    "406": {"Character Name": "Andrew", "Skill id": "406", "Png Image": "https://freefiremobile-a.akamaihd.net/common/web_event/official2.ff.garena.all/img/20228/564762d9a1137afaf2c9abb0ea8862b7.png"},
    "506": {"Character Name": "Nikita", "Skill id": "506", "Png Image": "https://freefiremobile-a.akamaihd.net/common/web_event/official2.ff.garena.all/img/20228/93bac478d8b64e0a6b31fee8c75220d9.png"},
    "606": {"Character Name": "Misha", "Skill id": "606", "Png Image": "https://freefiremobile-a.akamaihd.net/common/web_event/official2.ff.garena.all/img/20228/33110529f97da7fc1bf681e61a1de2bb.png"},
    "706": {"Character Name": "Maxim", "Skill id": "706", "Png Image": "https://freefiremobile-a.akamaihd.net/common/web_event/official2.ff.garena.all/img/20228/59dc42433e877fa0cc3bb69b74dbf2c8.png"},
    "806": {"Character Name": "Kla", "Skill id": "806", "Png Image": "https://freefiremobile-a.akamaihd.net/common/web_event/official2.ff.garena.all/img/20228/1655985bf74931458766921ee6bb6e0a.png"},
    "906": {"Character Name": "Paloma", "Skill id": "906", "Png Image": "https://freefiremobile-a.akamaihd.net/common/web_event/official2.ff.garena.all/img/20228/93a87a41a13af14c2346379a0d917d36.png"},
    "1006": {"Character Name": "Miguel", "Skill id": "1006", "Png Image": "https://freefiremobile-a.akamaihd.net/common/web_event/official2.ff.garena.all/img/20228/041a8586fe9d5461a7f28510fb5786d0.png"},
    "1106": {"Character Name": "Caroline", "Skill id": "1106", "Png Image": "https://freefiremobile-a.akamaihd.net/common/web_event/official2.ff.garena.all/img/20228/aa43b9f99d6a367a5123dbae9f6cd5c6.png"},
    "1206": {"Character Name": "Wukong", "Skill id": "1206", "Png Image": "https://dl.dir/freefiremobile.com/common/web_event/official2.ff.garena.all/20229/c0f1547f51f4c2b99e28ef4ec52db084.png"},
    "1306": {"Character Name": "Antonio", "Skill id": "1306", "Png Image": "https://freefiremobile-a.akamaihd.net/common/web_event/official2.ff.garena.all/img/20228/c87a2bcb4b4ab665908df11672aa191d.png"},
    "1406": {"Character Name": "Moco", "Skill id": "1406", "Png Image": "https://freefiremobile-a.akamaihd.net/common/web_event/official2.ff.garena.all/img/20228/769ceca68c62ec35cdbf90f1c0d7c73f.png"},
    "1506": {"Character Name": "Hayato", "Skill id": "1506", "Png Image": "https://freefiremobile-a.akamaihd.net/common/web_event/official2.ff.garena.all/img/20228/d8800f78f00e9831fc157a04aa3078aa.png"},
    "1706": {"Character Name": "Laura", "Skill id": "1706", "Png Image": "https://freefiremobile-a.akamaihd.net/common/web_event/official2.ff.garena.all/img/20228/a742beadf78c01fb9e05aabc51c9369e.png"},
    "1806": {"Character Name": "Rafael", "Skill id": "1806", "Png Image": "https://freefiremobile-a.akamaihd.net/common/web_event/official2.ff.garena.all/img/20228/738a885af3eb66c1415a0ac61bfd304b.png"},
    "1906": {"Character Name": "A124", "Skill id": "1906", "Png Image": "https://freefiremobile-a.akamaihd.net/common/web_event/official2.ff.garena.all/img/20228/ab1469c59a10c4669482e1ab625357dd.png"},
    "2006": {"Character Name": "Joseph", "Skill id": "2006", "Png Image": "https://freefiremobile-a.akamaihd.net/common/web_event/official2.ff.garena.all/img/20228/07d65d842e613a0cc22794f953c44be3.png"},
    "2106": {"Character Name": "Shani", "Skill id": "2106", "Png Image": "https://dl.dir/freefiremobile.com/common/web_event/official2.ff.garena.all/20229/2a790a2ca70a797b5384a122ad7d8d10.png"},
    "2206": {"Character Name": "Alok", "Skill id": "2206", "Png Image": "https://freefiremobile-a.akamaihd.net/common/web_event/official2.ff.garena.all/img/20228/c62e709e3ad8387f5484bb12e1cc81a9.png"},
    "2306": {"Character Name": "Alvaro", "Skill id": "2306", "Png Image": "https://freefiremobile-a.akamaihd.net/common/web_event/official2.ff.garena.all/img/20228/d5c0af0ac8632385f2cdb0500874b2a5.png"},
    "2406": {"Character Name": "Notora", "Skill id": "2406", "Png Image": "https://freefiremobile-a.akamaihd.net/common/web_event/official2.ff.garena.all/img/20228/fab6aa1cb1c6ce92652a3f184d265b76.png"},
    "2506": {"Character Name": "Kelly The Swift", "Skill id": "2506", "Png Image": "https://i.postimg.cc/BnpRPsjv/Kelly-The-Swift.png"},
    "2606": {"Character Name": "Steffie", "Skill id": "2606", "Png Image": "https://freefiremobile-a.akamaihd.net/common/web_event/official2.ff.garena.all/img/20228/809499ee33234f1c72c6a3ab120e85dd.png"},
    "2706": {"Character Name": "Jota", "Skill id": "2706", "Png Image": "https://dl.dir/freefiremobile.com/common/web_event/official2.ff.garena.all/20229/5ae1530683a65bdfd81f6f7f7552650c.png"},
    "2806": {"Character Name": "Kapella", "Skill id": "2806", "Png Image": "https://freefiremobile-a.akamaihd.net/common/web_event/official2.ff.garena.all/img/20228/9c6b10d2984125fbdd96fae9e0a84518.png"},
    "2906": {"Character Name": "Luqueta", "Skill id": "2906", "Png Image": "https://dl.dir/freefiremobile.com/common/web_event/official2.ff.garena.all/20229/28b704e964e8057d7fc76e1a2cca7d26.png"},
    "3006": {"Character Name": "Wolfrahh", "Skill id": "3006", "Png Image": "https://freefiremobile-a.akamaihd.net/common/web_event/official2.ff.garena.all/img/20228/e4169a44d8a6e83549b3b7f8a7820c1e.png"},
    "3106": {"Character Name": "Clu", "Skill id": "3106", "Png Image": "https://freefiremobile-a.akamaihd.net/common/web_event/official2.ff.garena.all/img/20228/81def6541fb94bd20887bad6b5a725cf.png"},
    "3206": {"Character Name": "Elite Hayato", "Skill id": "3206", "Png Image": "https://i.postimg.cc/KzH9r8bZ/Hayato-Firebrand.png"},
    "3306": {"Character Name": "Jai", "Skill id": "3306", "Png Image": "https://dl.dir/freefiremobile.com/common/web_event/official2.ff.garena.all/202412/077ccf77edb55d6b9d529e4afc1ae965.png"},
    "3406": {"Character Name": "K", "Skill id": "3406", "Png Image": "https://freefiremobile-a.akamaihd.net/common/web_event/official2.ff.garena.all/img/20228/cace792e96191c1623da45de2e52a589.png"},
    "3506": {"Character Name": "Dasha", "Skill id": "3506", "Png Image": "https://freefiremobile-a.akamaihd.net/common/web_event/official2.ff.garena.all/img/20228/8d2bc4db79fe889ab6541ae2dd7cd2cb.png"},
    "3806": {"Character Name": "Chrono", "Skill id": "3806", "Png Image": "https://dl.dir/freefiremobile.com/common/web_event/official2.ff.garena.all/202412/6d5de642b070e208a38b037d8233df85.png"},
    "4006": {"Character Name": "Skyler", "Skill id": "4006", "Png Image": "https://freefiremobile-a.akamaihd.net/common/web_event/official2.ff.garena.all/img/20228/547dea01d82886891297443e8e9d270f.png"},
    "4106": {"Character Name": "Shirou", "Skill id": "4106", "Png Image": "https://freefiremobile-a.akamaihd.net/common/web_event/official2.ff.garena.all/img/20228/dbe25891f13c5752e84ad7daf57106cc.png"},
    "4206": {"Character Name": "Andrew the Fierce", "Skill id": "4206", "Png Image": "https://i.postimg.cc/ZK1Gzj1T/Andrew-The-Fierce.png"},
    "4306": {"Character Name": "Maro", "Skill id": "4306", "Png Image": "https://freefiremobile-a.akamaihd.net/common/web_event/official2.ff.garena.all/img/20228/8af9a328d62a330a76221b79670daf37.png"},
    "4406": {"Character Name": "Xayne", "Skill id": "4406", "Png Image": "https://freefiremobile-a.akamaihd.net/common/web_event/official2.ff.garena.all/img/20229/ea05dd27c4f4faf3267679d5f90cdaec.png"},
    "4506": {"Character Name": "D-Bee", "Skill id": "4506", "Png Image": "https://freefiremobile-a.akamaihd.net/common/web_event/official2.ff.garena.all/img/20228/f1a09717ed71e7302da8d4cc889d2e33.png"},
    "4606": {"Character Name": "Thiva", "Skill id": "4606", "Png Image": "https://freefiremobile-a.akamaihd.net/common/web_event/official2.ff.garena.all/img/20228/217c0184667efa92bcec0caa73af73b9.png"},
    "4706": {"Character Name": "Dimitri", "Skill id": "4706", "Png Image": "https://freefiremobile-a.akamaihd.net/common/web_event/official2.ff.garena.all/img/20228/024c98913571304db2cba9d257e7291a.png"},
    "4806": {"Character Name": "Moco Enigma", "Skill id": "4806", "Png Image": "https://i.postimg.cc/FznQS4Wc/Moco-Rebirth.png"},
    "4906": {"Character Name": "Leon", "Skill id": "4906", "Png Image": "https://freefiremobile-a.akamaihd.net/common/web_event/official2.ff.garena.all/img/20228/b79f47950001fb7f7130a6b3752b3446.png"},
    "5006": {"Character Name": "Otho", "Skill id": "5006", "Png Image": "https://freefiremobile-a.akamaihd.net/common/web_event/official2.ff.garena.all/img/20228/d0ea6553e85abbf0a8b718e29900b7f5.png"},
    "5206": {"Character Name": "Nairi", "Skill id": "5206", "Png Image": "https://freefiremobile-a.akamaihd.net/common/web_event/official2.ff.garena.all/img/20228/e21eb41a3705ff817156dd5758157274.png"},
    "5306": {"Character Name": "Luna", "Skill id": "5306", "Png Image": "https://dl.dir/freefiremobile.com/common/web_event/official2.ff.garena.all/202211/9d03033ed89089d1f25c6be01817ebca.png"},
    "5406": {"Character Name": "Kenta", "Skill id": "5406", "Png Image": "https://freefiremobile-a.akamaihd.net/common/web_event/official2.ff.garena.all/img/20228/f867281184a63b0ac1bd9cc03a484bce.png"},
    "5506": {"Character Name": "Homer", "Skill id": "5506", "Png Image": "https://freefiremobile-a.akamaihd.net/common/web_event/official2.ff.garena.all/img/20228/26d226fa08410cc418959e3cc30095c7.png"},
    "5606": {"Character Name": "Iris", "Skill id": "5606", "Png Image": "https://photos.app.goo.gl/tP89GY8ZDZ9mydCKA"},
    "5706": {"Character Name": "J.Biebs", "Skill id": "5706", "Png Image": "https://dl.dir/freefiremobile.com/common/web_event/official2.ff.garena.all/202412/d3eb3130503cd726a5b7bce881d46c93.png"},
    "5806": {"Character Name": "Tatsuya", "Skill id": "5806", "Png Image": "https://dl.dir/freefiremobile.com/common/web_event/official2.ff.garena.all/20229/e37e48adf72a2c014c2bfa8ed483f5b5.png"},
    "6006": {"Character Name": "Santino", "Skill id": "6006", "Png Image": "https://dl.dir/freefiremobile.com/common/web_event/official2.ff.garena.all/20233/a3810f993d32077e88c5226625bb55a9.png"},
    "6206": {"Character Name": "Orion", "Skill id": "6206", "Png Image": "https://dl.dir/freefiremobile.com/common/web_event/official2.ff.garena.all/20238/4f4fc6c6d43fc3bb5ef4617f9f5340f7.png"},
    "6306": {"Character Name": "Alvaro Rageblast", "Skill id": "6306", "Png Image": "https://i.postimg.cc/k5k6x0H0/Alvaro-Rageblast.png"},
    "6506": {"Character Name": "Sonia", "Skill id": "6506", "Png Image": "https://dl.dir/freefiremobile.com/common/web_event/official2.ff.garena.all/20238/8f978bdbe46d3d2366b82713082d6683.png"},
    "6606": {"Character Name": "Suzy", "Skill id": "6606", "Png Image": "https://dl.dir/freefiremobile.com/common/web_event/official2.ff.garena.all/20246/2cdde4e7d5010be2a35971e19f2285e4.png"},
    "6706": {"Character Name": "Ignis", "Skill id": "6706", "Png Image": "https://dl.dir/freefiremobile.com/common/web_event/official2.ff.garena.all/202311/a393f95f57bdaa3d2031a052b6acef24.png"},
    "22016": {"Character Name": "Awakened Alok", "Skill id": "22016", "Png Image": "https://i.postimg.cc/KvHMG3Nc/Awakend-Alok.png"},
    "6906": {"Character Name": "Kairos", "Skill id": "6906", "Png Image": "https://dl.dir/freefiremobile.com/common/web_event/official2.ff.garena.all/20246/ed1e34b6c47b37675eae84daffdf63b1.png"},
    "7106": {"Character Name": "Lila", "Skill id": "7106", "Png Image": "https://dl.dir/freefiremobile.com/common/web_event/official2.ff.garena.all/20249/b09e7f93ec7c7a47dccbd704d8e4d879.png"},
    "7006": {"Character Name": "Kassie", "Skill id": "7006", "Png Image": "https://dl.dir/freefiremobile.com/common/web_event/official2.ff.garena.all/20246/8d87fe1959e300741eda601e800c0f40.png"},
    "6806": {"Character Name": "Ryden", "Skill id": "6806", "Png Image": "https://dl.dir/freefiremobile.com/common/web_event/official2.ff.garena.all/20241/fb808bb7cfc4820384c7a52fee3201ea.png"},
    "7206": {"Character Name": "Koda", "Skill id": "7206", "Png Image": "https://dl.dir/freefiremobile.com/common/web_event/official2.ff.garena.all/202412/b2f635a96ed787a8e540031402ea751b.png"}
}

# ----------------------------------
# Helper Functions
# ----------------------------------
def validate_key():
    api_key = request.args.get('key')
    return api_key == 'ADITYA'

def format_custom_time(dt_str):
    dt = datetime.datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
    formatted_time = dt.strftime("%d %B %Y %I:%M:%S %p")
    return formatted_time[:-2] + formatted_time[-2:].lower()

def format_time(ts):
    try:
        if ts == "Not Found":
            return ts
        ts_int = int(ts)
        dt = datetime.datetime.utcfromtimestamp(ts_int)
        return format_custom_time(dt.strftime("%Y-%m-%d %H:%M:%S"))
    except Exception as e:
        logging.error("Error formatting time: %s", e)
        return ts

def get_skill_info(skill_id):
    return SKILL_MAPPING.get(str(skill_id), {"Character Name": f"Unknown ({skill_id})", "Skill id": str(skill_id), "Png Image": "Not Found"})

def format_equipped_skills(equipped_skills):
    if not equipped_skills:
        return 'Not Found'
      
    skip_ids = {"8", "16", "3", "2", "1"}
    filtered_skills = []
    for skill in equipped_skills:
        skill_str = str(skill)
        if skill_str in skip_ids:
            continue
        if len(skill_str) > 0 and skill_str[-1] != "6":
            transformed_skill = skill_str[:-1] + "6"
        else:
            transformed_skill = skill_str
        filtered_skills.append(transformed_skill)
      
    formatted_list = []
    for idx, skill in enumerate(filtered_skills):
        info = get_skill_info(skill)
        marker = "(P)" if idx == 0 else "(A)"
        formatted_list.append(f"{info['Character Name']} {marker}")
    return ', '.join(formatted_list)

# ----------------------------------
# Data Fetching from External API
# ----------------------------------
API_URL = "https://ariiflexlabs-playerinfo.onrender.com/ff_info?uid={uid}&region={region}"

def fetch_player_data(uid, region):
    try:
        response = requests.get(API_URL.format(uid=uid, region=region))
        if response.status_code == 200:
            return response.json()
        logging.error("API Response Error: %s", response.status_code)
    except Exception as e:
        logging.error("Error fetching data: %s", e)
    return None

# ----------------------------------
# Main Endpoint
# ----------------------------------
@app.route('/ADITYA-PLAYER-INFO')
def fetch_info():
    start_time = time.time()

    if not validate_key():
        return jsonify({"error": "Invalid API key"}), 403

    uid = request.args.get('uid')
    region = request.args.get('region')
    if not uid:
        return jsonify({"error": "Please provide UID"}), 400

    valid_regions = ["ind", "sg", "br", "ru", "id", "tw", "us", "vn", "th", "me", "pk", "cis", "bd", "na"]
    if region and region.lower() not in valid_regions:
        return jsonify({"error": "Invalid Region. Please enter a valid region."}), 400

    search_regions = [region] if region else valid_regions
    player_data = None
    used_region = None

    for reg in search_regions:
        data = fetch_player_data(uid, reg)
        if data and "AccountInfo" in data and data["AccountInfo"].get("AccountName", "Not Found") != "Not Found":
            player_data = data
            used_region = reg
            break

    if not player_data or not player_data.get("AccountInfo") or player_data["AccountInfo"].get("AccountName", "Not Found") == "Not Found":
        return jsonify({"error": "Invalid UID or Region. Please check and try again."}), 400

    account_info = player_data.get("AccountInfo", {})
    account_profile_info = player_data.get("AccountProfileInfo", {})
    captain_basic_info = player_data.get("captainBasicInfo", {})
    guild_info = player_data.get("GuildInfo", {})
    social_info = player_data.get("socialinfo", {})
    pet_info = player_data.get("petInfo", {})
    credit_score = player_data.get("creditScoreInfo", {})

    formatted_skills = format_equipped_skills(account_profile_info.get('EquippedSkills', []))
    create_time = format_time(account_info.get('AccountCreateTime', 'Not Found'))
    last_login = format_time(account_info.get('AccountLastLogin', 'Not Found'))

    response_message = f"""
<pre>
Response 1:
Fetching details for UID `{uid}`, nickname `{account_info.get('AccountName', 'Not Found')}` in region `{used_region}`...
</pre>

<pre>
Response 2:
Account Info:
┌ 👤 ACCOUNT BASIC INFO:
├─ AccountType: `{account_info.get('AccountType', 'Not Found')}`
├─ AccountName: `{account_info.get('AccountName', 'Not Found')}`
├─ AccountUid: `{uid}`
├─ AccountRegion: `{account_info.get('AccountRegion', 'Not Found')}`
├─ AccountLevel: `{account_info.get('AccountLevel', 'Not Found')}`
├─ AccountEXP: `{account_info.get('AccountEXP', 'Not Found')}`
├─ AccountBannerId: `{account_info.get('AccountBannerId', 'Not Found')}`
├─ AccountAvatarId: `{account_info.get('AccountAvatarId', 'Not Found')}`
├─ BrRankPoint: `{account_info.get('BrRankPoint', 'Not Found')}`
├─ hasElitePass: `{account_info.get('hasElitePass', 'False')}`
├─ Role: `{account_info.get('Role', 'Not Found')}`
├─ AccountBPBadges: `{account_info.get('AccountBPBadges', 'Not Found')}`
├─ AccountBPID: `{account_info.get('AccountBPID', 'Not Found')}`
├─ AccountSeasonId: `{account_info.get('AccountSeasonId', 'Not Found')}`
├─ AccountLikes: `{account_info.get('AccountLikes', 'Not Found')}`
├─ AccountLastLogin: `{format_time(account_info.get('AccountLastLogin', 'Not Found'))}`
├─ CsRankPoint: `{account_info.get('CsRankPoint', 'Not Found')}`
├─ EquippedWeapon: `{account_info.get('EquippedWeapon', 'Not Found')}`
├─ BrMaxRank: `{account_info.get('BrMaxRank', 'Not Found')}`
├─ CsMaxRank: `{account_info.get('CsMaxRank', 'Not Found')}`
├─ AccountCreateTime: `{format_time(account_info.get('AccountCreateTime', 'Not Found'))}`
├─ Title: `{account_info.get('Title', 'Not Found')}`
├─ ReleaseVersion: `{account_info.get('ReleaseVersion', 'Not Found')}`
├─ ShowBrRank: `{account_info.get('ShowBrRank', 'Not Found')}`
└─ ShowCsRank: `{account_info.get('ShowCsRank', 'Not Found')}`
┌ 👕 ACCOUNT OVERVIEW:
├─ EquippedOutfit: `{account_profile_info.get('EquippedOutfit', 'Not Found')}`
└─ EquippedSkills: `{formatted_skills}`
┌ 🛡️ GuildInfo:
├─ GuildID: `{guild_info.get('GuildID', 'Not Found')}`
├─ GuildName: `{guild_info.get('GuildName', 'Not Found')}`
├─ GuildOwner: `{guild_info.get('GuildOwner', 'Not Found')}`
├─ GuildLevel: `{guild_info.get('GuildLevel', 'Not Found')}`
├─ GuildCapacity: `{guild_info.get('GuildCapacity', 'Not Found')}`
└─ GuildMember: `{guild_info.get('GuildMember', 'Not Found')}`
     ├─ 👤 CaptainBasicInfo:
     ├─ accountId: `{captain_basic_info.get('accountId', 'N/A')}`
     ├─ accountType: `{captain_basic_info.get('accountType', 'N/A')}`
     ├─ nickname: `{captain_basic_info.get('nickname', 'N/A')}`
     ├─ region: `{captain_basic_info.get('region', 'N/A')}`
     ├─ level: `{captain_basic_info.get('level', 'N/A')}`
     ├─ exp: `{captain_basic_info.get('exp', 'N/A')}`
     ├─ bannerId: `{captain_basic_info.get('bannerId', 'N/A')}`
     ├─ headPic: `{captain_basic_info.get('headPic', 'N/A')}`
     ├─ lastLoginAt: `{format_time(captain_basic_info.get('lastLoginAt', 'N/A'))}`
     ├─ rank: `{captain_basic_info.get('rank', 'N/A')}`
     ├─ rankingPoints: `{captain_basic_info.get('rankingPoints', 'N/A')}`
     ├─ EquippedWeapon: `{captain_basic_info.get('EquippedWeapon', 'Not Found')}`
     ├─ maxRank: `{captain_basic_info.get('maxRank', 'N/A')}`
     ├─ csMaxRank: `{captain_basic_info.get('csMaxRank', 'N/A')}`
     ├─ createAt: `{format_time(captain_basic_info.get('createAt', 'N/A'))}`
     ├─ title: `{captain_basic_info.get('title', 'N/A')}`
     ├─ releaseVersion: `{captain_basic_info.get('releaseVersion', 'N/A')}`
     ├─ showBrRank: `{captain_basic_info.get('showBrRank', 'N/A')}`
     └─ showCsRank: `{captain_basic_info.get('showCsRank', 'N/A')}`
┌ 🐾 PetInfo:
├─ id: `{pet_info.get('id', 'Not Found')}`
├─ name: `{pet_info.get('name', 'Not Found')}`
├─ level: `{pet_info.get('level', 'Not Found')}`
├─ exp: `{pet_info.get('exp', 'Not Found')}`
├─ isSelected: `{pet_info.get('isSelected', 'Not Found')}`
└─ skinId: `{pet_info.get('skinId', 'Not Found')}`
┌ 🎮 socialinfo:
├─ AccountLanguage: `{social_info.get('AccountLanguage', 'Not Found')}`
├─ AccountSignature: `{social_info.get('AccountSignature', 'Not Found')}`
└─ AccountPreferMode: `{social_info.get('AccountPreferMode', 'Not Found')}`
┌ 🏆 CreditScoreInfo:
├─ creditScore: `{credit_score.get('creditScore', 'Not Found')}`
├─ rewardState: `{credit_score.get('rewardState', '0')}`
├─ periodicSummaryStartTime: `{format_time(credit_score.get('periodicSummaryStartTime', 'Not Found'))}`
└─ periodicSummaryEndTime: `{format_time(credit_score.get('periodicSummaryEndTime', 'Not Found'))}`
</pre>
"""
    total_time = time.time() - start_time
    response_message += f"\nTotal Time Taken: {total_time:.2f} seconds\n"

    # Send the response immediately
    return Response(response_message, mimetype='text/plain')

if __name__ == '__main__':
    app.run(debug=True)