import os
import subprocess
import time
import sys
import importlib.util
import json
import threading
import base64
import requests
from flask import Flask, request, render_template_string, redirect, url_for, session, jsonify, Response, flash
from github import Github

app = Flask(__name__)
app.secret_key = "your_secret_key_here"  # Change this to a secure random value

# --- GitHub Configuration ---
GITHUB_REPO = 'AdityaSharma2403/Bot-Host-Web-storage'  # Format: owner/repo

# --- Local Paths ---
BASE_UPLOAD_FOLDER = "user_bots"
os.makedirs(BASE_UPLOAD_FOLDER, exist_ok=True)
USERS_FILE = "users.json"
ACTIVE_BOTS_FILE = "active_bots.json"  # persist active bot state

# Initialize local users file if not exists
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w") as f:
        json.dump({}, f)

# Initialize active bots file if not exists
if not os.path.exists(ACTIVE_BOTS_FILE):
    with open(ACTIVE_BOTS_FILE, "w") as f:
        json.dump({}, f)

# --- GitHub API Client ---
g = Github(GITHUB_TOKEN)
repo = g.get_user().get_repo('Bot-Host-Web-storage')

# ----------------- Utility Functions -----------------
def push_file_to_github(content_bytes, repo_path):
    """Push (or update) the given binary content to GitHub at the given repo_path."""
    encoded_content = base64.b64encode(content_bytes).decode('utf-8')
    headers = {'Authorization': f'token {GITHUB_TOKEN}'}
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{repo_path}"
    r = requests.get(url, headers=headers)
    sha = r.json()['sha'] if r.status_code == 200 and 'sha' in r.json() else None
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

def delete_file_from_github(file_path):
    headers = {"Authorization": f"token {GITHUB_TOKEN}",
               "Accept": "application/vnd.github.v3+json"}
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{file_path}"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        sha = response.json()["sha"]
        delete_response = requests.delete(url, headers=headers, json={"message": "Deleting file", "sha": sha})
        if delete_response.status_code == 200:
            print("File deleted successfully from GitHub")
        else:
            print("Error deleting file from GitHub:", delete_response.text)
    else:
        print("File not found on GitHub")

# ----------------- Local Users Storage Functions -----------------
def load_users():
    try:
        file = repo.get_contents('Account/users.json')
        users_data = file.decoded_content.decode()
        return json.loads(users_data)
    except Exception as e:
        print("Error loading users from GitHub:", str(e))
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, "r") as f:
                return json.load(f)
        return {}

def save_users(users):
    users_data = json.dumps(users, indent=4)
    try:
        file = repo.get_contents('Account/users.json')
        repo.update_file(file.path, "Update users", users_data, file.sha)
    except Exception:
        repo.create_file('Account/users.json', "Create users file", users_data, branch="main")

    with open(USERS_FILE, "w") as f:
        json.dump(users, f)

# ----------------- Active Bots Persistence -----------------
def load_active_bots():
    with open(ACTIVE_BOTS_FILE, "r") as f:
        return json.load(f)

def save_active_bots(active_bots):
    with open(ACTIVE_BOTS_FILE, "w") as f:
        json.dump(active_bots, f, indent=4)
    # Also push this file to GitHub so that the data is stored there
    push_file_to_github(json.dumps(active_bots, indent=4).encode(), "ActiveBots.json")

def add_active_bot(username, bot_name):
    active_bots = load_active_bots()
    user_bots = active_bots.get(username)
    # Ensure user_bots is a list:
    if not isinstance(user_bots, list):
        user_bots = []
    if bot_name not in user_bots:
        user_bots.append(bot_name)
    active_bots[username] = user_bots
    save_active_bots(active_bots)

def remove_active_bot(username, bot_name):
    active_bots = load_active_bots()
    user_bots = active_bots.get(username)
    # Ensure user_bots is a list:
    if not isinstance(user_bots, list):
        user_bots = []
    if bot_name in user_bots:
        user_bots.remove(bot_name)
    active_bots[username] = user_bots
    save_active_bots(active_bots)

# ----------------- User Activity Logging -----------------
user_activity = {}

def update_activity_log_on_github():
    log_entries = []
    for user, logs in user_activity.items():
        log_entries.append(f"--- Activity for {user} ---")
        log_entries.extend(logs)
    content = "\n".join(log_entries)
    push_file_to_github(content.encode(), "ActivityLog.txt")

def log_user_activity(username, message):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    entry = f"{timestamp} - {message}"
    user_activity.setdefault(username, []).append(entry)
    print(f"Activity for {username}: {entry}")
    update_activity_log_on_github()

# ----------------- Bot Process Management -----------------
# These dictionaries hold runtime state.
bot_processes = {}    # { username: { bot_filename: process, ... } }
bot_logs = {}         # { username: { bot_filename: [log_line, ...], ... } }
bot_run_flags = {}    # { username: { bot_filename: True/False, ... } }
bot_start_times = {}  # { username: { bot_filename: start_time, ... } }

def is_package_installed(package_name):
    """Check if a package is installed."""
    spec = importlib.util.find_spec(package_name)
    return spec is not None

def install_missing_packages(bot_path):
    """Extract dependencies from bot file and install missing ones."""
    try:
        with open(bot_path, "r", encoding="utf-8") as f:
            content = f.readlines()

        imports = set()
        for line in content:
            line = line.strip()
            if line.startswith("import "):
                module = line.split()[1].split(".")[0]
                imports.add(module)
            elif line.startswith("from "):
                module = line.split()[1].split(".")[0]
                imports.add(module)

        missing_packages = {pkg for pkg in imports if not is_package_installed(pkg)}

        if missing_packages:
            print(f"Installing missing packages: {', '.join(missing_packages)}")
            subprocess.run([sys.executable, "-m", "pip", "install", *missing_packages], check=True)
        else:
            print("All dependencies are already installed.")

    except Exception as e:
        print(f"Error in installing dependencies: {e}")

def install_requirements_file(bot_path):
    """Check for requirements.txt and install dependencies if present."""
    bot_dir = os.path.dirname(bot_path)
    req_file = os.path.join(bot_dir, "requirements.txt")

    if os.path.exists(req_file):
        print(f"Installing dependencies from {req_file}")
        subprocess.call([sys.executable, "-m", "pip", "install", "-r", req_file])

# Global dictionary to mark bots in restart mode
restarting_bots = {}  # { username: set([bot_name, ...]) }

def run_bot_loop(user, bot_name, bot_path):
    """Ensure dependencies are installed and start the bot, then stream logs indefinitely."""
    install_missing_packages(bot_path)   # Extract dependencies from bot file and install if missing
    install_requirements_file(bot_path)  # Install dependencies from requirements.txt if available

    while bot_run_flags.get(user, {}).get(bot_name, False):
        try:
            process = subprocess.Popen(
                [sys.executable, bot_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            bot_processes.setdefault(user, {})[bot_name] = process
            bot_logs.setdefault(user, {})[bot_name] = []

            for line in iter(process.stdout.readline, ""):
                if line:
                    line = line.strip()
                    bot_logs[user][bot_name].append(line)
                    # Agar koi error ya traceback dikhe, toh stop kar dein
                    if "Traceback" in line or "Error" in line:
                        bot_run_flags[user][bot_name] = False
                        process.terminate()
                        break

            process.stdout.close()
            process.wait()

        except Exception as e:
            bot_logs.setdefault(user, {}).setdefault(bot_name, []).append("Exception: " + str(e))
            bot_run_flags[user][bot_name] = False
        
        if bot_run_flags.get(user, {}).get(bot_name, False):
            time.sleep(1)

    # Agar bot restart mode mein nahin hai, toh active marker hata dein
    if not (user in restarting_bots and bot_name in restarting_bots[user]):
        remove_active_bot(user, bot_name)

def stop_bot(user, bot_name):
    """Stop the bot process if running."""
    if user in bot_processes and bot_name in bot_processes[user]:
        process = bot_processes[user][bot_name]
        if process.poll() is None:
            process.terminate()
            process.wait()
        del bot_processes[user][bot_name]
        return f"{bot_name} stopped."
    return f"{bot_name} is not running."

def stop_bot(user, bot_name):
    if user in bot_processes and bot_name in bot_processes[user]:
        process = bot_processes[user][bot_name]
        if process.poll() is None:
            process.terminate()
            process.wait()
        del bot_processes[user][bot_name]
        return f"{bot_name} stopped."
    return f"{bot_name} is not running."

# (Remaining Flask routes and app.run() go below)

# ----------------- HTML Templates -----------------
MAIN_TEMPLATE = """ 
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>TEAM-AKIRU Bot Hosting</title>
  <style>
    body { 
      font-family: Arial, sans-serif; 
      background: black; 
      color: #f0f0f0; 
      padding: 20px; 
      text-align: center; 
    }
    .container { padding: 20px; }
    .bot-controls { display: none; margin-top: 10px; }
    .btn { 
      padding: 12px 20px; 
      margin: 5px; 
      font-weight: bold; 
      border: none; 
      border-radius: 5px; 
      cursor: pointer; 
      width: 18%; 
    }
    .start-btn { background: #28a745; color: #fff; }
    .stop-btn { background: #dc3545; color: #fff; display: none; }
    .restart-btn { background: #ffc107; color: #000; }
    .rename-btn { background: #007bff; color: #fff; width: 18%; }
    .edit-btn { background: #6c757d; color: #fff; width: 18%; }
    .log-container { 
      width: 80%; 
      max-height: 300px; 
      overflow-y: auto; 
      border: 1px solid #00c8ff; 
      background: #222; 
      text-align: left; 
      margin: 20px auto; 
      padding: 10px; 
      font-size: 14px; 
    }
    .copy-btn { 
      width: 80%; 
      display: block; 
      margin: 20px auto; 
      background: #007bff; 
      color: #fff; 
      font-weight: bold;  
      padding: 10px; 
      border: none; 
      border-radius: 5px; 
      cursor: pointer; 
    }
    .file-upload-container { 
      margin-top: 20px; 
      display: flex; 
      flex-direction: column; 
      align-items: center; 
    }
    .custom-file-upload, .upload-btn, #remove-file-btn { 
      display: flex; 
      align-items: center; 
      justify-content: center; 
      background: #28a745; 
      color: white; 
      font-weight: bold; 
      text-align: center; 
      width: 200px; 
      height: 45px; 
      border-radius: 5px; 
      cursor: pointer; 
      border: none; 
      position: relative; 
      font-size: 16px; 
      margin: 5px 0; 
    }
    .custom-file-upload input { 
      position: absolute; 
      width: 100%; 
      height: 100%; 
      opacity: 0; 
      left: 0; 
      top: 0; 
      cursor: pointer; 
    }
    #file-name { 
      display: block; 
      font-size: 14px; 
      color: #ddd; 
      margin-top: 10px; 
    }
    #remove-file-btn { 
      display: none; 
      background: #dc3545; 
      color: white; 
      font-weight: bold; 
      padding: 10px; 
      border: none;  
      border-radius: 5px; 
      cursor: pointer; 
      margin-top: 10px; 
    }
    .menu-btn { 
      position: fixed; 
      top: 20px; 
      right: 20px; 
      background: #ff9800; 
      color: #fff; 
      border: none; 
      border-radius: 50%;  
      width: 50px; 
      height: 50px; 
      cursor: pointer; 
      font-size: 24px; 
      z-index: 1000; 
    }
    .menu-panel { 
      position: fixed; 
      top: 80px; 
      right: 20px; 
      background: #222; 
      padding: 20px; 
      border-radius: 10px; 
      width: 250px;  
      box-shadow: 0 0 10px #fff; 
      display: none; 
      z-index: 1000;  
      max-height: 80vh;  
      overflow-y: auto;  
    }
    .menu-panel h3 { 
      margin-top: 0; 
      border-bottom: 1px solid #444; 
      padding-bottom: 5px; 
    }
    .bot-file-item { 
      position: relative; 
      margin: 5px 0; 
    }
    .file-btn { 
      width: 100%; 
      height: 45px; 
      display: flex; 
      align-items: center; 
      justify-content: center; 
      text-align: center; 
      padding: 0; 
    }
    .trash-btn { 
      position: absolute; 
      top: -5px; 
      right: 25px; 
      height: 100%; 
      width: 100%; 
      max-width: 45px; 
      font-size: 18px; 
      cursor: pointer; 
      display: flex; 
      align-items: center; 
      justify-content: center; 
    }
    .menu-panel a, .menu-panel button { 
      display: block; 
      width: 200px; 
      height: 45px; 
      line-height: 45px; 
      background: #444; 
      color: #fff; 
      border: none; 
      margin: 5px auto; 
      border-radius: 5px; 
      text-align: center; 
      cursor: pointer; 
      text-decoration: none; 
      font-size: 16px;  
    }
    .menu-panel a:hover, .menu-panel button:hover { 
      background: #00ffcc; 
      color: #000; 
    }
    .running-bots { 
      background: #222; 
      border: 1px solid #00c8ff; 
      padding: 10px; 
      margin: 20px auto; 
      width: 80%; 
      max-width: 600px; 
      text-align: left; 
      font-size: 16px; 
      border-radius: 5px; 
    }
    .running-bots h3 { margin-top: 0; }
    .running-bots ul { list-style: none; padding-left: 20px; }
    .user-activity { 
      background: #222; 
      border: 1px solid #00c8ff; 
      padding: 10px; 
      margin: 20px auto; 
      width: 80%; 
      max-width: 600px; 
      text-align: left; 
      font-size: 16px; 
      border-radius: 5px; 
    }
    .user-activity h3 { margin-top: 0; }
    .user-activity ul { list-style: none; padding-left: 20px; }
  </style>
  <script>
    let eventSource;
    function toggleMenu() {
      const panel = document.getElementById("menu-panel");
      panel.style.display = (panel.style.display === "none" || panel.style.display === "") ? "block" : "none";
    }
    function showBotControls(botName) {
      document.getElementById("selected-bot").innerText = botName;
      updateBotButtons(botName);
      startLogStream(botName);
      document.getElementById("bot-controls").style.display = "block";
      document.getElementById("menu-panel").style.display = "none";
    }
    function updateBotButtons(botName) {
      fetch('/bot_status/' + botName)
        .then(response => response.json())
        .then(data => {
          if (data.running) {
            document.getElementById("start-btn").style.display = "none";
            document.getElementById("stop-btn").style.display = "inline-block";
          } else {
            document.getElementById("start-btn").style.display = "inline-block";
            document.getElementById("stop-btn").style.display = "none";
          }
        });
    }
    function controlBot(action) {
      var botName = document.getElementById("selected-bot").innerText;
      fetch('/control_bot/' + encodeURIComponent(botName) + '/' + action)
        .then(response => response.json())
        .then(data => {
          if(data.success) {
            if (action === "start") {
              setTimeout(() => { window.location.reload(); }, 500);
            } else if (action === "stop") {
              document.getElementById("stop-btn").style.display = "none";
              document.getElementById("start-btn").style.display = "inline-block";
            } else if (action === "restart") {
              setTimeout(() => { window.location.reload(); }, 500);
            }
          } else {
            alert("Action failed: " + data.message);
          }
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
      if (input.files.length > 0) {
        fileName.innerText = input.files[0].name;
        removeBtn.style.display = "inline-block";
      } else {
        fileName.innerText = "No file chosen";
        removeBtn.style.display = "none";
      }
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
      window.location.href = "/edit_name/" + encodeURIComponent(botName);
    }
    function editBot() {
      var botName = document.getElementById("selected-bot").innerText;
      window.location.href = "/edit_file/" + botName;
    }
    function updateRunningBots() {
      fetch('/running_bots')
        .then(response => response.json())
        .then(data => {
          var list = document.getElementById("running-bots-list");
          list.innerHTML = "";
          for (let bot in data.running) {
            let li = document.createElement("li");
            li.textContent = bot + " :- " + data.running[bot];
            list.appendChild(li);
          }
        });
    }
    function updateUserActivity() {
      fetch('/user_activity')
        .then(response => response.json())
        .then(data => {
          var list = document.getElementById("user-activity-list");
          list.innerHTML = "";
          data.activity.forEach(function(entry) {
            let li = document.createElement("li");
            li.textContent = entry;
            list.appendChild(li);
          });
        });
    }
    setInterval(updateRunningBots, 1000);
    setInterval(updateUserActivity, 5000);
  </script>
</head>
<body>
  <button class="menu-btn" onclick="toggleMenu()">☰</button>
  <div id="menu-panel" class="menu-panel">
    <h3>Menu</h3>
    <strong>Bot Files:</strong>
    {% for bot in bots %}
      <div class="bot-file-item">
        <button class="file-btn" onclick="showBotControls('{{ bot }}')">{{ bot }}</button>
        <button class="trash-btn" onclick="deleteForever('{{ bot }}')">&#128465;</button>
      </div>
    {% endfor %}
    <hr>
    <a href="/create_file">Create New File</a>
    <a href="/edit_file_select">Edit File</a>
    <hr>
    <a href="/logout">Logout</a>
  </div>
  
  <div class="running-bots">
    <h3>Running Bots:</h3>
    <ul id="running-bots-list"></ul>
  </div>
  
  <div class="container">
    <h2>Welcome, {{ username }}</h2>
    <h2>🛠 Bot File Manager</h2>
    <div id="bot-controls" class="bot-controls">
      <h3>📌 Selected Bot: <span id="selected-bot"></span></h3>
      <button id="start-btn" class="btn start-btn" onclick="controlBot('start')">Start</button>
      <button id="stop-btn" class="btn stop-btn" onclick="controlBot('stop')">Stop</button>
      <button id="restart-btn" class="btn restart-btn" onclick="controlBot('restart')">Restart</button>
      <button class="btn rename-btn" onclick="renameBot()">Rename</button>
      <button class="btn edit-btn" onclick="editBot()">Edit</button>
    </div>

    <div id="bot-logs" class="log-container"></div>
    <button class="copy-btn" onclick="copyLogs()">Copy Logs</button>

    <div class="file-upload-container">
      <form action="/upload_file" method="post" enctype="multipart/form-data">
        <div class="custom-file-upload">
          <input type="file" name="file" id="bot-file-input" onchange="updateFileName(this)">
          Choose File
        </div>
        <p id="file-name">No file chosen</p>
        <button id="remove-file-btn" type="button" onclick="removeFile()">Remove File</button>
        <button class="upload-btn" type="submit">Upload File</button>
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
    .show-pass-btn { width: auto; background: #28a745; color: white; padding: 8px 15px; font-size: 14px; border: none; 
         border-radius: 5px; cursor: pointer; text-align: center; margin-bottom: 10px; }
    .show-pass-btn:hover { background: #218838; }
  </style>
  <script>
    function togglePassword() {
      var pwdInput = document.getElementById("password");
      var showPassButton = document.getElementById("show-pass-btn");
      if (pwdInput.type === "password") {
        pwdInput.type = "text";
        showPassButton.textContent = "Hide Password";
      } else {
        pwdInput.type = "password";
        showPassButton.textContent = "Show Password";
      }
    }
  </script>
</head>
<body>
  <div class="login-container">
    <h2>🔒 Login to Bot Hosting</h2>
    <form action="/login" method="post">
      <input type="text" name="username" placeholder="Username" required>
      <input type="password" name="password" placeholder="Password" id="password" required>
      <button type="button" id="show-pass-btn" class="show-pass-btn" onclick="togglePassword()">Show Password</button>
      <br>
      <button type="submit" class="login-btn">Login</button>
    </form>
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        <ul>
        {% for category, message in messages %}
          <li style="color: red;">{{ message }}</li>
        {% endfor %}
        </ul>
      {% endif %}
    {% endwith %}
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
    textarea { width: 90%; height: 900px; padding: 12px; margin: 10px 0; border: none; border-radius: 5px;
               font-size: 16px; font-family: monospace; }
    .btn { padding: 12px 20px; background: #28a745; color: #fff; border: none; border-radius: 5px;
           cursor: pointer; font-size: 18px; margin-top: 10px; }
    .back-btn { margin-top: 20px; display: inline-block; color: #28a745; text-decoration: none; font-size: 16px; }
  </style>
</head>
<body>
  <div class="container">
    <h2>Edit File: {{ bot_name }}</h2>
    <form action="/edit_file/{{ bot_name }}" method="post">
      <textarea name="content">{{ content }}</textarea>
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
    .file-btn { display: block; width: 100%; padding: 15px; margin: 10px 0; background: #444; color: #fff;
                border: none; border-radius: 5px; cursor: pointer; text-decoration: none; box-sizing: border-box; }
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

EDIT_NAME_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Rename File - TEAM-AKIRU Bot Hosting</title>
  <style>
    body { font-family: Arial, sans-serif; background: black; color: #f0f0f0; padding: 20px; text-align: center; }
    .container { width: 400px; margin: 40px auto; background: #111; padding: 20px; border-radius: 10px;
                 box-shadow: 0 0 15px rgba(0,255,0,0.6); }
    input { width: 90%; padding: 12px; margin: 10px 0; border: none; border-radius: 5px; font-size: 16px; }
    .btn { padding: 12px 20px; background: #28a745; color: #fff; border: none; border-radius: 5px;
           cursor: pointer; font-size: 18px; margin-top: 10px; }
    .back-btn { margin-top: 20px; display: inline-block; color: #28a745; text-decoration: none; font-size: 16px; }
  </style>
</head>
<body>
  <div class="container">
    <h2>Rename File: {{ bot_name }}</h2>
    <form action="/edit_name/{{ bot_name }}" method="post">
      <input type="text" name="new_name" placeholder="New file name" required>
      <br>
      <button type="submit" class="btn">Rename</button>
    </form>
    <a href="/" class="back-btn">← Back to Home</a>
  </div>
</body>
</html>
"""

# ----------------- Flask Routes -----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        users = load_users()
        
        if username in users:
            if users[username] == password:
                session["username"] = username
                log_user_activity(username, "Logged in successfully.")
                return redirect(url_for("index"))
            else:
                flash("Invalid username or password!", "error")
                return redirect(url_for("login"))
        else:
            # Register new user
            users[username] = password
            save_users(users)
            session["username"] = username
            log_user_activity(username, "New user registered and logged in.")
            return redirect(url_for("index"))

    return render_template_string(LOGIN_TEMPLATE)

@app.route("/logout")
def logout():
    username = session.get("username")
    if username:
        log_user_activity(username, "Logged out.")
    session.pop("username", None)
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("login"))

@app.route("/")
def index():
    if "username" not in session:
        return redirect(url_for("login"))
    username = session["username"]
    user_folder = os.path.join(BASE_UPLOAD_FOLDER, username)
    bots = os.listdir(user_folder) if os.path.exists(user_folder) else []
    return render_template_string(MAIN_TEMPLATE, username=username, bots=bots)

# ----------------- /control_bot route -----------------
@app.route('/control_bot/<bot_name>/<action>')
def control_bot(bot_name, action):
    username = session.get("username")
    if not username:
        return jsonify({"success": False, "message": "Not logged in."})
    
    bot_path = os.path.join(BASE_UPLOAD_FOLDER, username, bot_name)
    
    if action == "start":
        # Manual on: set flag, start bot thread, update active marker
        bot_run_flags.setdefault(username, {})[bot_name] = True
        thread = threading.Thread(target=run_bot_loop, args=(username, bot_name, bot_path))
        thread.start()
        add_active_bot(username, bot_name)
        log_user_activity(username, f"Started bot {bot_name}")
        return jsonify({"success": True})
    
    elif action == "stop":
        # Manual off: stop bot process and remove active marker
        message = stop_bot(username, bot_name)
        bot_run_flags.setdefault(username, {})[bot_name] = False
        remove_active_bot(username, bot_name)
        log_user_activity(username, f"Stopped bot {bot_name}")
        return jsonify({"success": True, "message": message})
    
    elif action == "restart":
        # For restart: 
        # 1. Mark bot as restarting (so that run_bot_loop na active marker na remove kare)
        restarting_bots.setdefault(username, set()).add(bot_name)
        # 2. Stop the bot first and update flag to show "start" state on UI.
        message = stop_bot(username, bot_name)
        bot_run_flags.setdefault(username, {})[bot_name] = False
        log_user_activity(username, f"Restarting bot {bot_name}")
        
        # 3. Wait for 3 seconds (bot remains in off state)
        time.sleep(3)
        
        # 4. Start the bot again and update active marker
        bot_run_flags.setdefault(username, {})[bot_name] = True
        thread = threading.Thread(target=run_bot_loop, args=(username, bot_name, bot_path))
        thread.start()
        add_active_bot(username, bot_name)
        
        # 5. Remove bot from restarting mode
        if username in restarting_bots and bot_name in restarting_bots[username]:
            restarting_bots[username].remove(bot_name)
        
        log_user_activity(username, f"Restarted bot {bot_name}")
        return jsonify({"success": True})
    
    return jsonify({"success": False, "message": "Invalid action"})

@app.route('/bot_status/<bot_name>')
def bot_status(bot_name):
    username = session.get("username")
    active_bots = load_active_bots()
    running = False
    if username in active_bots and bot_name in active_bots[username]:
         running = True
    return jsonify({"running": running})

@app.route("/stream/<bot_name>")
def stream(bot_name):
    username = session.get("username")
    if not username:
        return redirect(url_for("login"))
    def generate():
        last_index = 0
        while True:
            logs = bot_logs.get(username, {}).get(bot_name, [])
            if last_index < len(logs):
                for line in logs[last_index:]:
                    yield f"data: {line}\n\n"
                last_index = len(logs)
            time.sleep(1)
    return Response(generate(), mimetype="text/event-stream")

@app.route("/permanent_delete/<bot_name>")
def permanent_delete(bot_name):
    username = session.get("username")
    if not username:
        return redirect(url_for("login"))
    bot_path = os.path.join(BASE_UPLOAD_FOLDER, username, bot_name)
    if os.path.exists(bot_path):
        os.remove(bot_path)
    delete_file_from_github(f"{username}/{bot_name}")
    log_user_activity(username, f"Deleted file {bot_name}.")
    return redirect(url_for("index"))

@app.route("/edit_file/<bot_name>", methods=["GET", "POST"])
def edit_file(bot_name):
    username = session.get("username")
    if not username:
        return redirect(url_for("login"))
    user_folder = os.path.join(BASE_UPLOAD_FOLDER, username)
    file_path = os.path.join(user_folder, bot_name)
    if request.method == "POST":
        new_content = request.form.get("content")
        with open(file_path, "w") as f:
            f.write(new_content)
        push_file_to_github(new_content.encode(), f"{username}/{bot_name}")
        log_user_activity(username, f"Edited file {bot_name}.")
        return redirect(url_for("index"))
    else:
        content = open(file_path, "r").read() if os.path.exists(file_path) else ""
        return render_template_string(EDIT_FILE_TEMPLATE, bot_name=bot_name, content=content)

@app.route("/edit_name/<bot_name>", methods=["GET", "POST"])
def edit_name(bot_name):
    username = session.get("username")
    if not username:
        return redirect(url_for("login"))
    user_folder = os.path.join(BASE_UPLOAD_FOLDER, username)
    old_path = os.path.join(user_folder, bot_name)
    if request.method == "POST":
        new_name = request.form.get("new_name").strip()
        if new_name and new_name != bot_name:
            new_path = os.path.join(user_folder, new_name)
            os.rename(old_path, new_path)
            with open(new_path, "rb") as f:
                content = f.read()
            push_file_to_github(content, f"{username}/{new_name}")
            delete_file_from_github(f"{username}/{bot_name}")
            log_user_activity(username, f"Renamed file {bot_name} to {new_name}.")
            return redirect(url_for("index"))
        else:
            flash("Invalid new name!")
            return redirect(url_for("edit_name", bot_name=bot_name))
    return render_template_string(EDIT_NAME_TEMPLATE, bot_name=bot_name)

@app.route("/create_file", methods=["GET", "POST"])
def create_file():
    username = session.get("username")
    if not username:
        return redirect(url_for("login"))
    if request.method == "POST":
        filename = request.form.get("filename")
        content = request.form.get("filecontent", "")
        user_folder = os.path.join(BASE_UPLOAD_FOLDER, username)
        os.makedirs(user_folder, exist_ok=True)
        file_path = os.path.join(user_folder, filename)
        with open(file_path, "w") as f:
            f.write(content)
        push_file_to_github(content.encode(), f"{username}/{filename}")
        log_user_activity(username, f"Created file {filename}.")
        return redirect(url_for("index"))
    return """
         <!DOCTYPE html><html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Create File - TEAM-AKIRU Bot Hosting</title>
  <style>
    body { font-family: Arial, sans-serif; background: black; color: #f0f0f0; padding: 20px; text-align: center; }
    .container { width: 600px; margin: 40px auto; background: #111; padding: 20px; border-radius: 10px;
                 box-shadow: 0 0 15px rgba(0,255,0,0.6); }
    input[type="text"], textarea { width: 90%; padding: 12px; margin: 10px 0; border: none; border-radius: 5px; font-size: 16px; }
    textarea { height: 900px; font-family: monospace; }
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

@app.route("/edit_file_select")
def edit_file_select():
    username = session.get("username")
    if not username:
        return redirect(url_for("login"))
    user_folder = os.path.join(BASE_UPLOAD_FOLDER, username)
    files = os.listdir(user_folder) if os.path.exists(user_folder) else []
    return render_template_string(EDIT_FILE_SELECT_TEMPLATE, files=files)

@app.route("/upload_file", methods=["POST"])
def upload_file():
    username = session.get("username")
    if not username:
        return redirect(url_for("login"))
    if "file" not in request.files:
        return "No file part"
    file = request.files["file"]
    if file.filename == "":
        return "No selected file"
    user_folder = os.path.join(BASE_UPLOAD_FOLDER, username)
    os.makedirs(user_folder, exist_ok=True)
    file_path = os.path.join(user_folder, file.filename)
    file.save(file_path)
    with open(file_path, "rb") as f:
        content = f.read()
    push_file_to_github(content, f"{username}/{file.filename}")
    log_user_activity(username, f"Uploaded file {file.filename}.")
    return redirect(url_for("index"))

@app.route("/running_bots")
def running_bots():
    username = session.get("username")
    running = {}
    if username in bot_run_flags:
        for bot, flag in bot_run_flags[username].items():
            if flag:
                running[bot] = "Active"
    return jsonify({"running": running})

@app.route("/user_activity")
def user_activity_route():
    username = session.get("username")
    if not username:
        return jsonify({"activity": []})
    return jsonify({"activity": user_activity.get(username, [])})

# ----------------- On Startup: Restart Active Bots -----------------
def restart_active_bots():
    active_bots = load_active_bots()
    for username, bots in active_bots.items():
        user_folder = os.path.join(BASE_UPLOAD_FOLDER, username)
        for bot_name in bots:
            bot_path = os.path.join(user_folder, bot_name)
            # Only start if the file exists and is not already running in our current state
            if os.path.exists(bot_path):
                bot_run_flags.setdefault(username, {})[bot_name] = True
                bot_logs.setdefault(username, {})[bot_name] = []
                bot_start_times.setdefault(username, {})[bot_name] = time.time()
                log_user_activity(username, f"Resuming active bot {bot_name} after restart.")
                threading.Thread(target=run_bot_loop, args=(username, bot_name, bot_path), daemon=True).start()

# Restart bots on startup
restart_active_bots()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)