import os
import json
import subprocess
import threading
import time
import base64
import requests
from flask import Flask, request, render_template_string, redirect, url_for, session, jsonify, Response

app = Flask(__name__)
app.secret_key = "your_secret_key_here"  # Change this to a secure random value

# --- GitHub Configuration ---
GITHUB_TOKEN = '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'  # Replace with your GitHub token
GITHUB_REPO = 'AdityaSharma2403/Bot-Host-Web-storage'  # Format: owner/repo

# --- Local Paths ---
BASE_UPLOAD_FOLDER = "user_bots"
os.makedirs(BASE_UPLOAD_FOLDER, exist_ok=True)
USERS_FILE = "users.json"
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w") as f:
        json.dump({}, f)

# --- GitHub Utility Functions ---

def push_file_to_github(content_bytes, repo_path):
    """Push (or update) the given binary content to GitHub at the given repo_path."""
    encoded_content = base64.b64encode(content_bytes).decode('utf-8')
    headers = {'Authorization': f'token {GITHUB_TOKEN}'}
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{repo_path}"
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        sha = r.json()['sha']
    else:
        sha = None
    data = {
        "message": f"Update {repo_path}",
        "content": encoded_content,
        "branch": "main"
    }
    if sha:
        data["sha"] = sha
    r2 = requests.put(url, headers=headers, json=data)
    if r2.status_code in [200, 201]:
        print(f"Updated {repo_path} on GitHub successfully.")
    else:
        print(f"Failed to update {repo_path} on GitHub:", r2.json())

def create_github_user_folder(username, password):
    """Create the GitHub folder structure for a new user by committing an empty .gitkeep file."""
    repo_path = f"Account/{username}/{password}/.gitkeep"
    push_file_to_github(b"", repo_path)

def push_users_to_github():
    """Push the local users.json file to GitHub under Account/users.json."""
    try:
        with open(USERS_FILE, "rb") as f:
            content = f.read()
    except Exception as e:
        print("Error reading users.json:", e)
        return
    push_file_to_github(content, "Account/users.json")

push_users_to_github()

def sync_github_files(username, password):
    """
    Sync all files stored on GitHub for this user (under Account/{username}/{password}/)
    into the local directory BASE_UPLOAD_FOLDER/{username}.
    """
    headers = {'Authorization': f'token {GITHUB_TOKEN}'}
    path = f"Account/{username}/{password}"
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}?ref=main"
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        print(f"No files found on GitHub for {username}")
        return
    files = r.json()
    local_folder = os.path.join(BASE_UPLOAD_FOLDER, username)
    for file in files:
        if file['type'] == 'file':
            download_url = file['download_url']
            content = requests.get(download_url).content
            local_path = os.path.join(local_folder, file['name'])
            with open(local_path, 'wb') as f:
                f.write(content)
            os.chmod(local_path, 0o755)
            print(f"Synced {file['name']} for {username}")

# --- Local User Storage Functions ---

def load_users():
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)
    push_users_to_github()

# --- Bot Process Management ---
bot_processes = {}  # { username: { bot_filename: process, ... } }
bot_logs = {}       # { username: { bot_filename: [log_line, ...], ... } }
bot_run_flags = {}  # { username: { bot_filename: True/False, ... } }
bot_threads = {}    # { username: { bot_filename: thread, ... } }

def run_bot_loop(user, bot_name, bot_path):
    """Continuously runs the bot until the run_flag is set to False. Logs are stored indefinitely."""
    while bot_run_flags[user].get(bot_name, False):
        try:
            process = subprocess.Popen(
                ["python3", bot_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
        except Exception as e:
            print(f"Error running {bot_name}: {str(e)}")
            break
        if user not in bot_processes:
            bot_processes[user] = {}
        bot_processes[user][bot_name] = process
        if user not in bot_logs:
            bot_logs[user] = {}
        if bot_name not in bot_logs[user]:
            bot_logs[user][bot_name] = []  # Do not clear existing logs.
        process.wait()
        if bot_run_flags[user].get(bot_name, False):
            time.sleep(1)

# ---------------------- HTML Templates ----------------------
CREATE_FILE_TEMPLATE = """ 
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Create File - TEAM-AKIRU Bot Hosting</title>
  <style>
    body { font-family: Arial, sans-serif; background: black; color: #f0f0f0; padding: 20px; text-align: center; }
    .container { width: 600px; margin: 40px auto; background: #111; padding: 20px; border-radius: 10px;
                 box-shadow: 0 0 15px rgba(0,255,0,0.6); }
    input[type="text"], textarea { width: 90%; padding: 12px; margin: 10px 0; border: none; border-radius: 5px; font-size: 16px; }
    textarea { height: 300px; font-family: monospace; }
    .btn { padding: 12px 20px; background: #28a745; color: #fff; border: none; border-radius: 5px; cursor: pointer; font-size: 18px; margin-top: 10px; }
    .back-btn { margin-top: 20px; display: inline-block; color: #28a745; text-decoration: none; font-size: 16px; }
  </style>
</head>
<body>
  <div class="container">
    <h2>Create New File</h2>
    <form action="/create_file" method="post">
      <input type="text" name="filename" placeholder="Enter file name (e.g. mybot.py)" required>
      <br>
      <textarea name="filecontent" placeholder="Enter your code here..."></textarea>
      <br>
      <button type="submit" class="btn">Create File</button>
    </form>
    <a href="/" class="back-btn">← Back to Home</a>
  </div>
</body>
</html>
"""

EDIT_FILE_TEMPLATE = """ 
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Edit File - TEAM-AKIRU Bot Hosting</title>
  <style>
    body { font-family: Arial, sans-serif; background: black; color: #f0f0f0; padding: 20px; text-align: center; }
    .container { width: 600px; margin: 40px auto; background: #111; padding: 20px; border-radius: 10px;
                 box-shadow: 0 0 15px rgba(0,255,0,0.6); }
    textarea { width: 90%; height: 300px; padding: 12px; margin: 10px 0; border: none; border-radius: 5px;
               font-size: 16px; font-family: monospace; }
    .btn { padding: 12px 20px; background: #28a745; color: #fff; border: none; border-radius: 5px;
           cursor: pointer; font-size: 18px; margin-top: 10px; }
    .back-btn { margin-top: 20px; display: inline-block; color: #28a745; text-decoration: none; font-size: 16px; }
  </style>
</head>
<body>
  <div class="container">
    <h2>Edit File: {{ filename }}</h2>
    <form action="/edit_file/{{ filename }}" method="post">
      <textarea name="filecontent">{{ filecontent }}</textarea>
      <br>
      <button type="submit" class="btn">Save Changes</button>
    </form>
    <a href="/" class="back-btn">← Back to Home</a>
  </div>
</body>
</html>
"""

EDIT_FILE_SELECT_TEMPLATE = """ 
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Select File to Edit - TEAM-AKIRU Bot Hosting</title>
  <style>
    body { font-family: Arial, sans-serif; background: black; color: #f0f0f0; padding: 20px; text-align: center; }
    .container { width: 400px; margin: 40px auto; background: #111; padding: 20px; border-radius: 10px;
                 box-shadow: 0 0 15px rgba(0,255,0,0.6); }
    .file-btn { display: block; width: 100%; padding: 10px; margin: 10px 0; background: #444; color: #fff;
                border: none; border-radius: 5px; cursor: pointer; text-decoration: none; }
    .file-btn:hover { background: #00ffcc; color: #000; }
    .back-btn { margin-top: 20px; display: inline-block; color: #28a745; text-decoration: none; font-size: 16px; }
  </style>
</head>
<body>
  <div class="container">
    <h2>Select a File to Edit</h2>
    {% for file in files %}
      <a class="file-btn" href="/edit_file/{{ file }}">{{ file }}</a>
    {% endfor %}
    <a href="/" class="back-btn">← Back to Home</a>
  </div>
</body>
</html>
"""

MAIN_TEMPLATE = """ 
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>TEAM-AKIRU Bot Hosting</title>
  <style>
    body { font-family: Arial, sans-serif; background: black; color: #f0f0f0; padding: 20px; text-align: center; position: relative; }
    .container { padding: 20px; }
    .bot-controls { display: none; margin-top: 10px; }
    .btn { padding: 12px 20px; margin: 5px; font-weight: bold; border: none; border-radius: 5px; cursor: pointer; width: 22%; }
    .start-btn { background: #28a745; color: #fff; }
    .stop-btn { background: #dc3545; color: #fff; display: none; }
    .restart-btn { background: #ffc107; color: #000; }
    .rename-btn { background: #007bff; color: #fff; }
    .log-container { width: 80%; max-height: 300px; overflow-y: auto; border: 1px solid #00c8ff; background: #222;
         text-align: left; margin: 20px auto; padding: 10px; font-size: 14px; }
    .copy-btn { width: 80%; display: block; margin: 20px auto; background: #007bff; color: #fff; font-weight: bold;
         padding: 10px; border: none; border-radius: 5px; cursor: pointer; }
    .file-upload-container { margin-top: 20px; display: flex; flex-direction: column; align-items: center; }
    .custom-file-upload, .upload-btn, #remove-file-btn { display: flex; align-items: center; justify-content: center;
         background: #28a745; color: white; font-weight: bold; text-align: center; width: 200px; height: 45px;
         border-radius: 5px; cursor: pointer; border: none; position: relative; font-size: 16px; margin: 5px 0; }
    .custom-file-upload input { position: absolute; width: 100%; height: 100%; opacity: 0; left: 0; top: 0; cursor: pointer; }
    #file-name { display: block; font-size: 14px; color: #ddd; margin-top: 10px; }
    #remove-file-btn { display: none; background: #dc3545; color: white; font-weight: bold; padding: 10px; border: none;
         border-radius: 5px; cursor: pointer; margin-top: 10px; }
    .menu-btn { position: fixed; top: 20px; right: 20px; background: #ff9800; color: #fff; border: none; border-radius: 50%;
         width: 50px; height: 50px; cursor: pointer; font-size: 24px; z-index: 1000; }
    .menu-panel { position: fixed; top: 80px; right: 20px; background: #222; padding: 20px; border-radius: 10px; width: 250px;
         box-shadow: 0 0 10px #fff; display: none; z-index: 1000; }
    .menu-panel h3 { margin-top: 0; border-bottom: 1px solid #444; padding-bottom: 5px; }
    .menu-panel a, .menu-panel button { display: block; width: 100%; background: #444; color: #fff; border: none; padding: 10px;
         margin: 5px 0; border-radius: 5px; text-align: left; cursor: pointer; text-decoration: none; }
    .menu-panel a:hover, .menu-panel button:hover { background: #00ffcc; color: #000; }
  </style>
  <script>
    let eventSource;
    function toggleMenu() {
      const panel = document.getElementById("menu-panel");
      if (panel.style.display === "none" || panel.style.display === "") { panel.style.display = "block"; }
      else { panel.style.display = "none"; }
    }
    function showBotControls(botName) {
      document.getElementById("selected-bot").innerText = botName;
      document.getElementById("bot-controls").style.display = "block";
      updateBotStatus(botName);
      startLogStream(botName);
      document.getElementById("menu-panel").style.display = "none";
    }
    function updateBotStatus(botName) {
      fetch('/bot_status/' + botName)
        .then(response => response.json())
        .then(data => {
          document.getElementById("start-btn").style.display = data.running ? "none" : "inline-block";
          document.getElementById("stop-btn").style.display = data.running ? "inline-block" : "none";
        });
    }
    function controlBot(action) {
      var botName = document.getElementById("selected-bot").innerText;
      let btn;
      if (action === "start") { btn = document.getElementById("start-btn"); }
      else if (action === "restart") { btn = document.getElementById("restart-btn"); }
      else if (action === "stop") { btn = document.getElementById("stop-btn"); }
      if (btn && btn.disabled) return;
      if (btn) { btn.disabled = true; btn.style.opacity = 0.6; }
      fetch('/control_bot/' + botName + '/' + action)
        .then(() => {
           updateBotStatus(botName);
           if (btn) { btn.disabled = false; btn.style.opacity = 1; }
        });
    }
    function startLogStream(botName) {
      if (eventSource) eventSource.close();
      eventSource = new EventSource('/stream/' + botName);
      let logContainer = document.getElementById("bot-logs");
      logContainer.innerHTML = "";
      eventSource.onmessage = function(event) {
        logContainer.innerHTML += event.data + "<br>";
        logContainer.scrollTop = logContainer.scrollHeight;
      };
    }
    function copyLogs() {
      let logs = document.getElementById("bot-logs").innerText;
      navigator.clipboard.writeText(logs).then(() => { alert("Logs copied to clipboard!"); });
    }
    function updateFileName(input) {
      const fileName = document.getElementById("file-name");
      const removeBtn = document.getElementById("remove-file-btn");
      if (input.files.length > 0) { fileName.innerText = input.files[0].name; removeBtn.style.display = "inline-block"; }
      else { fileName.innerText = "No file chosen"; removeBtn.style.display = "none"; }
    }
    function removeFile() {
      const fileInput = document.getElementById("bot-file-input");
      fileInput.value = "";
      updateFileName(fileInput);
    }
    function deleteForever(fileName) {
      if (confirm("Are you sure you want to permanently delete " + fileName + "?")) {
        window.location.href = "/permanent_delete/" + encodeURIComponent(fileName);
      }
    }
    function renameBot() {
      var botName = document.getElementById("selected-bot").innerText;
      var newName = prompt("Enter new file name for " + botName + ":", botName);
      if(newName && newName.trim() !== "" && newName.trim() !== botName) {
        window.location.href = "/rename/" + encodeURIComponent(botName) + "/" + encodeURIComponent(newName.trim());
      }
    }
  </script>
</head>
<body>
  <button class="menu-btn" onclick="toggleMenu()">☰</button>
  <div id="menu-panel" class="menu-panel">
    <h3>Menu</h3>
    <strong>Bot Files:</strong>
    {% for bot in bots %}
      <button onclick="showBotControls('{{ bot }}')">{{ bot }}</button>
    {% endfor %}
    <hr>
    <strong>Recycle:</strong>
    {% for bot in bots %}
      <button onclick="deleteForever('{{ bot }}')">Delete: {{ bot }}</button>
    {% endfor %}
    <hr>
    <a href="/update_account">Update Account</a>
    <a href="/logout">Logout</a>
    <hr>
    <a href="/create_file">Create New File</a>
    <a href="/edit_file_select">Edit File</a>
  </div>
  <div class="container">
    <h2>Welcome, {{ username }}</h2>
    <h2>🛠 Bot File Manager</h2>
    <div id="bot-controls" class="bot-controls">
      <h3>📌 Selected Bot: <span id="selected-bot"></span></h3>
      <button id="start-btn" class="btn start-btn" onclick="controlBot('start')">▶ Start</button>
      <button id="stop-btn" class="btn stop-btn" onclick="controlBot('stop')">⏹ Stop</button>
      <button id="restart-btn" class="btn restart-btn" onclick="controlBot('restart')">🔄 Restart</button>
      <button id="rename-btn" class="btn rename-btn" onclick="renameBot()">Rename</button>
      <h3>📜 Live Logs:</h3>
      <div id="bot-logs" class="log-container"></div>
      <button id="copy-btn" class="btn copy-btn" onclick="copyLogs()">📋 Copy Logs</button>
    </div>
    <div class="file-upload-container">
      <h3>⬆ Choose File</h3>
      <form action="/upload" method="post" enctype="multipart/form-data">
        <div class="custom-file-upload">
          <span id="file-label">⬆ Choose File</span>
          <input type="file" name="bot_file" id="bot-file-input" onchange="updateFileName(this)">
        </div>
        <br>
        <span id="file-name">No file chosen</span>
        <br>
        <button type="button" id="remove-file-btn" onclick="removeFile()">❌ Remove File</button>
        <br><br>
        <button type="submit" class="upload-btn btn">Upload File</button>
      </form>
    </div>
  </div>
</body>
</html>
"""

LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>TEAM-AKIRU Bot Hosting - Login</title>
  <style>
    body { font-family: Arial, sans-serif; background: black; color: #f0f0f0; padding: 20px; text-align: center; }
    .login-container { width: 400px; background: #111; padding: 30px; border-radius: 10px;
         box-shadow: 0 0 15px rgba(0,255,0,0.6); margin: auto; margin-top: 100px; text-align: center; }
    .login-container h2 { margin-bottom: 20px; }
    .login-container input { width: 90%; padding: 12px; margin: 10px 0; border: none; border-radius: 5px; font-size: 16px; }
    .login-btn { width: 100%; background: #28a745; color: #fff; font-weight: bold; padding: 12px;
         border: none; border-radius: 5px; cursor: pointer; font-size: 18px; margin-top: 10px; }
    .login-btn:hover { }
    .show-pass { margin-top: 10px; cursor: pointer; font-size: 14px; }
  </style>
  <script>
    function togglePassword() {
      var pwdInput = document.getElementById("password");
      if (pwdInput.type === "password") { pwdInput.type = "text"; } else { pwdInput.type = "password"; }
    }
  </script>
</head>
<body>
  <div class="login-container">
    <h2>🔒 Login to Bot Hosting</h2>
    <form action="/login" method="post">
      <input type="text" name="username" placeholder="Username" required>
      <input type="password" name="password" placeholder="Password" id="password" required>
      <div class="show-pass">
        <input type="checkbox" id="show-password" onclick="togglePassword()">
        <label for="show-password">Show Password</label>
      </div>
      <button type="submit" class="login-btn">Login</button>
    </form>
  </div>
</body>
</html>
"""

UPDATE_ACCOUNT_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Update Account - TEAM-AKIRU Bot Hosting</title>
  <style>
    body { font-family: Arial, sans-serif; background: black; color: #f0f0f0; padding: 20px; text-align: center; }
    .update-container { width: 400px; background: #111; padding: 30px; border-radius: 10px;
         box-shadow: 0 0 15px rgba(0,255,0,0.6); margin: auto; margin-top: 100px; text-align: center; }
    .update-container h2 { margin-bottom: 20px; }
    .update-container input { width: 90%; padding: 12px; margin: 10px 0; border: none; border-radius: 5px;
         font-size: 16px; }
    .update-btn { width: 100%; background: #28a745; color: #fff; font-weight: bold; padding: 12px;
         border: none; border-radius: 5px; cursor: pointer; font-size: 18px; margin-top: 10px; }
    .back-btn { margin-top: 20px; display: inline-block; color: #28a745; text-decoration: none; font-size: 16px; }
    .show-pass { margin-top: 10px; cursor: pointer; font-size: 14px; }
  </style>
  <script>
    function toggleNewPassword() {
      var newPwdInput = document.getElementById("new_password");
      var confirmPwdInput = document.getElementById("confirm_password");
      if (newPwdInput.type === "password") { newPwdInput.type = "text"; confirmPwdInput.type = "text"; }
      else { newPwdInput.type = "password"; confirmPwdInput.type = "password"; }
    }
  </script>
</head>
<body>
  <div class="update-container">
    <h2>Update Account Credentials</h2>
    <form action="/update_account" method="post">
      <input type="text" name="new_username" placeholder="New Username (leave blank to keep unchanged)">
      <input type="password" name="new_password" placeholder="New Password (leave blank to keep unchanged)" id="new_password">
      <input type="password" name="confirm_password" placeholder="Confirm New Password" id="confirm_password">
      <div class="show-pass">
        <input type="checkbox" id="show-new-password" onclick="toggleNewPassword()">
        <label for="show-new-password">Show Passwords</label>
      </div>
      <button type="submit" class="update-btn">Update</button>
    </form>
    <a href="/" class="back-btn">← Back to Home</a>
  </div>
</body>
</html>
"""

# ---------------------- Routes ----------------------
@app.route("/", methods=["GET"])
def home():
    if "username" not in session:
        return redirect(url_for("login"))
    user = session["username"]
    user_folder = os.path.join(BASE_UPLOAD_FOLDER, user)
    os.makedirs(user_folder, exist_ok=True)
    bots = os.listdir(user_folder)
    return render_template_string(MAIN_TEMPLATE, bots=bots, username=user)

@app.route("/upload", methods=["POST"])
def upload_bot():
    if "username" not in session:
        return redirect(url_for("login"))
    user = session["username"]
    # Instead of saving to local storage, we push the uploaded file directly to GitHub.
    file = request.files.get("bot_file")
    if file:
        content = file.read()  # Read file content in memory.
        users = load_users()
        password = users.get(user, "default")
        repo_path = f"Account/{user}/{password}/{file.filename}"
        push_file_to_github(content, repo_path)
    return redirect(url_for("home"))

@app.route("/bot_status/<bot_name>", methods=["GET"])
def bot_status(bot_name):
    if "username" not in session:
        return jsonify({"running": False})
    user = session["username"]
    bot_name = os.path.basename(bot_name)
    if user not in bot_processes:
        bot_processes[user] = {}
    running = bot_name in bot_processes[user] and bot_processes[user][bot_name].poll() is None
    return jsonify({"running": running})

@app.route("/control_bot/<bot_name>/<action>", methods=["GET"])
def control_bot(bot_name, action):
    if "username" not in session:
        return redirect(url_for("login"))
    user = session["username"]
    bot_name = os.path.basename(bot_name)
    user_folder = os.path.join(BASE_UPLOAD_FOLDER, user)
    bot_path = os.path.join(user_folder, bot_name)
    if user not in bot_run_flags:
        bot_run_flags[user] = {}
    if user not in bot_threads:
        bot_threads[user] = {}
    if action == "start":
        bot_run_flags[user][bot_name] = True
        if bot_name not in bot_threads[user] or not bot_threads[user][bot_name].is_alive():
            bot_threads[user][bot_name] = threading.Thread(target=run_bot_loop, args=(user, bot_name, bot_path), daemon=True)
            bot_threads[user][bot_name].start()
        return f"{bot_name} started successfully!"
    elif action == "restart":
        if bot_run_flags[user].get(bot_name):
            bot_run_flags[user][bot_name] = False
            if bot_name in bot_processes[user] and bot_processes[user][bot_name].poll() is None:
                bot_processes[user][bot_name].terminate()
            time.sleep(1)
        bot_run_flags[user][bot_name] = True
        if bot_name not in bot_threads[user] or not bot_threads[user][bot_name].is_alive():
            bot_threads[user][bot_name] = threading.Thread(target=run_bot_loop, args=(user, bot_name, bot_path), daemon=True)
            bot_threads[user][bot_name].start()
        return f"{bot_name} restarted successfully!"
    elif action == "stop":
        bot_run_flags[user][bot_name] = False
        if bot_name in bot_processes[user] and bot_processes[user][bot_name].poll() is None:
            bot_processes[user][bot_name].terminate()
        return f"{bot_name} stopped successfully!"
    return "Invalid action!"

def stream_logs(user, bot_name, process):
    while True:
        output = process.stdout.readline()
        if output == "" and process.poll() is not None:
            break
        if user in bot_logs and bot_name in bot_logs[user]:
            bot_logs[user][bot_name].append(output.strip())

@app.route("/stream/<bot_name>")
def stream(bot_name):
    if "username" not in session:
        return redirect(url_for("login"))
    user = session["username"]
    bot_name = os.path.basename(bot_name)
    def event_stream():
        last_len = 0
        while True:
            if user in bot_logs and bot_name in bot_logs[user]:
                new_logs = bot_logs[user][bot_name][last_len:]
                last_len += len(new_logs)
                for line in new_logs:
                    yield f"data: {line}\n\n"
    return Response(event_stream(), mimetype="text/event-stream")

@app.route("/permanent_delete/<bot_name>", methods=["GET"])
def permanent_delete(bot_name):
    if "username" not in session:
        return redirect(url_for("login"))
    user = session["username"]
    bot_name = os.path.basename(bot_name)
    user_folder = os.path.join(BASE_UPLOAD_FOLDER, user)
    bot_path = os.path.join(user_folder, bot_name)
    if os.path.exists(bot_path):
        os.remove(bot_path)
    return redirect(url_for("home"))

@app.route("/rename/<old_name>/<new_name>", methods=["GET"])
def rename_bot(old_name, new_name):
    if "username" not in session:
        return redirect(url_for("login"))
    user = session["username"]
    old_name = os.path.basename(old_name)
    new_name = os.path.basename(new_name)
    user_folder = os.path.join(BASE_UPLOAD_FOLDER, user)
    old_path = os.path.join(user_folder, old_name)
    new_path = os.path.join(user_folder, new_name)
    if os.path.exists(new_path):
        return f"File with name {new_name} already exists. <a href='/'>Return</a>"
    if os.path.exists(old_path):
        os.rename(old_path, new_path)
        if user in bot_logs and old_name in bot_logs[user]:
            bot_logs[user][new_name] = bot_logs[user].pop(old_name)
        if user in bot_processes and old_name in bot_processes[user]:
            bot_processes[user][new_name] = bot_processes[user].pop(old_name)
        return redirect(url_for("home"))
    else:
        return f"File {old_name} not found. <a href='/'>Return</a>"

@app.route("/create_file", methods=["GET", "POST"])
def create_file():
    if "username" not in session:
        return redirect(url_for("login"))
    user = session["username"]
    user_folder = os.path.join(BASE_UPLOAD_FOLDER, user)
    if request.method == "POST":
        filename = request.form.get("filename").strip()
        filecontent = request.form.get("filecontent")
        file_path = os.path.join(user_folder, filename)
        if os.path.exists(file_path):
            return f"File {filename} already exists. <a href='/create_file'>Try again</a>"
        with open(file_path, "w") as f:
            f.write(filecontent)
        os.chmod(file_path, 0o755)
        # Push the new file to GitHub under Account/{user}/{password}/{filename}
        users = load_users()
        password = users.get(user, "default")
        repo_path = f"Account/{user}/{password}/{filename}"
        push_file_to_github(filecontent.encode('utf-8'), repo_path)
        return redirect(url_for("home"))
    return render_template_string(CREATE_FILE_TEMPLATE)

@app.route("/edit_file/<filename>", methods=["GET", "POST"])
def edit_file(filename):
    if "username" not in session:
        return redirect(url_for("login"))
    user = session["username"]
    filename = os.path.basename(filename)
    user_folder = os.path.join(BASE_UPLOAD_FOLDER, user)
    file_path = os.path.join(user_folder, filename)
    if not os.path.exists(file_path):
        return f"File {filename} does not exist. <a href='/'>Return Home</a>"
    if request.method == "POST":
        filecontent = request.form.get("filecontent")
        with open(file_path, "w") as f:
            f.write(filecontent)
        # Update file on GitHub
        users = load_users()
        password = users.get(user, "default")
        repo_path = f"Account/{user}/{password}/{filename}"
        push_file_to_github(filecontent.encode('utf-8'), repo_path)
        return redirect(url_for("home"))
    with open(file_path, "r") as f:
        filecontent = f.read()
    return render_template_string(EDIT_FILE_TEMPLATE, filename=filename, filecontent=filecontent)

@app.route("/edit_file_select", methods=["GET"])
def edit_file_select():
    if "username" not in session:
        return redirect(url_for("login"))
    user = session["username"]
    user_folder = os.path.join(BASE_UPLOAD_FOLDER, user)
    files = os.listdir(user_folder)
    return render_template_string(EDIT_FILE_SELECT_TEMPLATE, files=files)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username").strip()
        password = request.form.get("password").strip()
        users = load_users()
        if username not in users:
            users[username] = password
            save_users(users)
            os.makedirs(os.path.join(BASE_UPLOAD_FOLDER, username), exist_ok=True)
            create_github_user_folder(username, password)
            session["username"] = username
            # Sync any GitHub files (if present)
            sync_github_files(username, password)
            return redirect(url_for("home"))
        else:
            if users[username] == password:
                session["username"] = username
                os.makedirs(os.path.join(BASE_UPLOAD_FOLDER, username), exist_ok=True)
                sync_github_files(username, users[username])
                return redirect(url_for("home"))
            else:
                return "Invalid credentials. <a href='/login'>Try again</a>"
    return render_template_string(LOGIN_TEMPLATE)

@app.route("/update_account", methods=["GET", "POST"])
def update_account():
    if "username" not in session:
        return redirect(url_for("login"))
    current_user = session["username"]
    users = load_users()
    if request.method == "POST":
        new_username = request.form.get("new_username").strip()
        new_password = request.form.get("new_password").strip()
        confirm_password = request.form.get("confirm_password").strip()
        if new_password or confirm_password:
            if new_password != confirm_password:
                return "New passwords do not match. <a href='/update_account'>Try again</a>"
        if new_username and new_username != current_user:
            if new_username in users:
                return f"Username {new_username} already exists. <a href='/update_account'>Try again</a>"
            old_folder = os.path.join(BASE_UPLOAD_FOLDER, current_user)
            new_folder = os.path.join(BASE_UPLOAD_FOLDER, new_username)
            if os.path.exists(old_folder):
                os.rename(old_folder, new_folder)
            users[new_username] = new_password if new_password else users[current_user]
            users.pop(current_user)
            save_users(users)
            session["username"] = new_username
        else:
            if new_password:
                users[current_user] = new_password
                save_users(users)
        return redirect(url_for("home"))
    return render_template_string(UPDATE_ACCOUNT_TEMPLATE)

@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)