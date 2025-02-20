from flask import Flask, request, render_template_string, redirect, url_for, session, jsonify
import os
import subprocess
import threading
import json
import base64
import requests
import re
import sys
import asyncio  # Ensure asyncio is imported
import importlib.util  # For is_package_installed
import time

# ---------------------------
# App and global settings
# ---------------------------
app = Flask(__name__)
app.secret_key = "replace_with_a_secure_random_secret"  # Replace with a secure secret

UPLOAD_FOLDER = "user_bots"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

bot_processes = {}
bot_outputs = {}   # Stores output/error per bot
bot_status = {}    # Maps bot name to status string ("running", "stopped", or error message)

# Global dictionary to mark bots in restart mode
restarting_bots = {}  # { username: set([bot_name, ...]) }

# ---------------------------
# GitHub Settings
# ---------------------------
GITHUB_REPO = 'AdityaSharma2403/Bot-Host-Web-storage'  # For user files etc.
USERS_FILE_PATH = 'Account/users.json'  # Users credentials file on GitHub

# For updating requirements.txt if needed.
REQUIREMENTS_GITHUB_REPO = 'AdityaSharma2403/Bot-Host-Web'
REQUIREMENTS_FILE_PATH = 'requirements.txt'

# ---------------------------
# Helper functions for GitHub integration
# ---------------------------
def load_users():
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{USERS_FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        content = base64.b64decode(data['content']).decode('utf-8')
        try:
            return json.loads(content)
        except Exception:
            return {}
    return {}

def cleanup_start_markers():
    users = load_users()
    for username in users.keys():
        files = get_github_files_for_user(username)
        for file in files:
            if file.endswith(" start"):
                delete_file_from_github(username, file)

def update_users_file(users):
    content_str = json.dumps(users, indent=2)
    encoded_content = base64.b64encode(content_str.encode('utf-8')).decode('utf-8')
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{USERS_FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    get_response = requests.get(url, headers=headers)
    sha = get_response.json()['sha'] if get_response.status_code == 200 else None
    commit_message = "Update users.json via registration"
    payload = {"message": commit_message, "content": encoded_content}
    if sha:
        payload["sha"] = sha
    put_response = requests.put(url, headers=headers, data=json.dumps(payload))
    if put_response.status_code in [200, 201]:
        return True
    else:
        print("GitHub update error:", put_response.json())
        return False

def sanitize_file_content(file_content):
    try:
        text = file_content.decode('utf-8')
    except UnicodeDecodeError:
        return file_content
    sanitized_text = "\n".join(sanitized_lines)
    return sanitized_text.encode('utf-8')

def delete_file_from_github(username, filename):
    path = f"{username}/{filename}"
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    get_resp = requests.get(url, headers=headers)
    if get_resp.status_code == 200:
        data = get_resp.json()
        sha = data.get('sha')
        commit_message = f"Delete {filename} by {username}"
        payload = {"message": commit_message, "sha": sha}
        del_resp = requests.delete(url, headers=headers, data=json.dumps(payload))
        if del_resp.status_code in [200, 204]:
            return True
        else:
            print("GitHub file delete error:", del_resp.json())
            return False
    return True

def upload_file_to_github(username, filename, file_content):
    if not delete_file_from_github(username, filename):
        return False
    sanitized_content = sanitize_file_content(file_content)
    path = f"{username}/{filename}"
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    commit_message = f"Upload {filename} by {username}"
    content_encoded = base64.b64encode(sanitized_content).decode('utf-8')
    payload = {"message": commit_message, "content": content_encoded, "bypass_secret_scanning": True}
    put_resp = requests.put(url, headers=headers, data=json.dumps(payload))
    if put_resp.status_code in [200, 201]:
        return True
    else:
        print("GitHub file upload error:", put_resp.json())
        return False

def mark_bot_started(username, filename):
    marker = f"{filename} start"
    delete_file_from_github(username, marker)
    path = f"{username}/{marker}"
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    commit_message = f"Mark {filename} as started by {username}"
    content_encoded = base64.b64encode(b"started").decode('utf-8')
    payload = {"message": commit_message, "content": content_encoded, "bypass_secret_scanning": True}
    put_resp = requests.put(url, headers=headers, data=json.dumps(payload))
    if put_resp.status_code in [200, 201]:
        return True
    else:
        if put_resp.status_code == 422:
            return True
        print("GitHub mark started error:", put_resp.json())
        return False

def get_github_files_for_user(username):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{username}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    response = requests.get(url, headers=headers)
    files = []
    if response.status_code == 200:
        data = response.json()
        for item in data:
            if item.get("type") == "file":
                files.append(item.get("name"))
    return files

def get_started_files(username):
    files = get_github_files_for_user(username)
    started = [f[:-6].rstrip() for f in files if f.endswith(" start")]
    return started

# ---------------------------
# Auto-Restart Helpers
# ---------------------------
def run_bot_process(bot, username):
    path = find_bot_path(bot, username)
    if not path:
        return {"message": "Bot not found!"}
    try:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
        except Exception as e:
            print("Error upgrading pip:", e)
        requirements_url = "https://raw.githubusercontent.com/AdityaSharma2403/Bot-Host-Web/main/requirements.txt"
        r = requests.get(requirements_url)
        r.raise_for_status()
        packages = []
        for line in r.text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.lower().startswith("pip install"):
                pkg = line[len("pip install"):].strip()
                packages.append(pkg)
            else:
                packages.append(line)
        if packages:
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + packages)
    except Exception as e:
        print("Error installing dependencies:", e)
    try:
        process_bot_file_dependencies(path)
        install_missing_packages(path)
        install_requirements_file(path)
        bot_outputs[bot] = ""
        proc = subprocess.Popen([sys.executable, path],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        bot_processes[bot] = proc
        bot_status[bot] = "running"
        threading.Thread(target=capture_output, args=(bot, proc, username), daemon=True).start()
        mark_bot_started(username, bot)
        model_name = os.path.splitext(bot)[0]
        latest_version = get_latest_version(model_name)
        if latest_version:
            dependency = f"{model_name}=={latest_version}"
            install_dependency(dependency)
            update_requirements_file(dependency)
        return {"message": f"{bot} started successfully!"}
    except Exception as e:
        return {"message": f"Failed to start bot: {str(e)}"}

def auto_restart(bot, username):
    # Wait 5 seconds before auto-restart
    time.sleep(5)
    if bot not in bot_processes:
        print(f"Auto restarting bot: {bot}")
        result = run_bot_process(bot, username)
        print(result["message"])

# ---------------------------
# Helper: Capture Output with Auto-Restart
# ---------------------------
def capture_output(bot_name, process, username):
    # Clear previous output so that any error screen is reset on restart.
    bot_outputs[bot_name] = ""
    while True:
        out_line = process.stdout.readline()
        err_line = process.stderr.readline()
        if not out_line and not err_line and process.poll() is not None:
            break
        if out_line:
            try:
                decoded = out_line.decode("utf-8")
            except Exception:
                decoded = str(out_line)
            if decoded.strip() == "":
                decoded = "message\n"
            bot_outputs[bot_name] += decoded
        if err_line:
            try:
                decoded = err_line.decode("utf-8")
            except Exception:
                decoded = str(err_line)
            if decoded.strip() == "":
                decoded = "message\n"
            bot_outputs[bot_name] += decoded
    rc = process.poll()
    if rc is None or rc == -15:  # Normal termination (SIGTERM)
        bot_status[bot_name] = "stopped"
    else:
        bot_status[bot_name] = f"Error: return code {rc}"
        bot_outputs[bot_name] += f"\n[Program finished]"
    # If an error is detected, remove the "start" marker and auto-restart the bot.
    if "Error" in bot_outputs[bot_name] or "Traceback" in bot_outputs[bot_name]:
        delete_file_from_github(username, f"{bot_name} start")
        print(f"Bot {bot_name} encountered an error. Scheduling auto-restart...")
        # Remove bot process from global tracking (if still there)
        bot_processes.pop(bot_name, None)
        threading.Thread(target=auto_restart, args=(bot_name, username), daemon=True).start()

# ---------------------------
# Helper: Get Latest Version from PyPI
# ---------------------------
def get_latest_version(package_name):
    url = f"https://pypi.org/pypi/{package_name}/json"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return data["info"]["version"]
    except Exception as e:
        print(f"Error fetching latest version for {package_name}: {e}")
    return None

# ---------------------------
# Helper: Update requirements.txt on GitHub
# ---------------------------
def update_requirements_file(new_dependency):
    url = f"https://api.github.com/repos/{REQUIREMENTS_GITHUB_REPO}/contents/{REQUIREMENTS_FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        current_content = base64.b64decode(data['content']).decode('utf-8')
        lines = current_content.splitlines()
        package_name = new_dependency.split("==")[0].strip().lower()
        found = False
        for i, line in enumerate(lines):
            if not line.strip():
                continue
            if "==" in line:
                existing_package = line.split("==")[0].strip().lower()
            else:
                existing_package = line.strip().lower()
            if existing_package == package_name:
                if line.strip() != new_dependency:
                    lines[i] = new_dependency
                found = True
                break
        if not found:
            lines.append(new_dependency)
        new_content_str = "\n".join(lines) + "\n"
        new_content_encoded = base64.b64encode(new_content_str.encode("utf-8")).decode("utf-8")
        commit_message = f"Update requirements.txt with {new_dependency}"
        payload = {"message": commit_message, "content": new_content_encoded, "sha": data["sha"]}
        put_resp = requests.put(url, headers=headers, data=json.dumps(payload))
        if put_resp.status_code in [200, 201]:
            print(f"Requirements.txt updated with {new_dependency}")
            return True
        else:
            print("GitHub update requirements error:", put_resp.json())
            return False
    else:
        print("Error fetching requirements.txt from GitHub", response.json())
        return False

# ---------------------------
# Helper: Install a dependency locally using pip
# ---------------------------
def install_dependency(package_spec):
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_spec])
        print(f"Installed locally: {package_spec}")
    except Exception as e:
        print(f"Error installing {package_spec} locally:", e)

# ---------------------------
# Helper: Process bot file dependencies by scanning its import statements
# ---------------------------
def process_bot_file_dependencies(file_path):
    if not os.path.exists(file_path):
        print("Bot file not found for dependency processing.")
        return
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    pattern = r'^\s*(?:import|from)\s+([a-zA-Z0-9_\.]+)'
    modules = set()
    for line in content.splitlines():
        match = re.match(pattern, line)
        if match:
            module_full = match.group(1).strip()
            module_name = module_full.split('.')[0]
            if module_name in ["os", "sys", "json", "re", "threading", "subprocess", "base64", "requests", "asyncio", "flask"]:
                continue
            modules.add(module_name)
    for module in modules:
        latest_version = get_latest_version(module)
        if latest_version:
            dependency = f"{module}=={latest_version}"
            install_dependency(dependency)
            update_requirements_file(dependency)
        else:
            print(f"Could not find latest version for {module}, skipping.")

# ---------------------------
# New Helper Functions for Package Installation from Bot File
# ---------------------------
def is_package_installed(package_name):
    spec = importlib.util.find_spec(package_name)
    return spec is not None

def install_missing_packages(bot_path):
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
    bot_dir = os.path.dirname(bot_path)
    req_file = os.path.join(bot_dir, "requirements.txt")
    if os.path.exists(req_file):
        print(f"Installing dependencies from {req_file}")
        subprocess.call([sys.executable, "-m", "pip", "install", "-r", req_file])

# ---------------------------
# Dashboard HTML Template with persistent file selection, output polling, and copy button
# ---------------------------
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>TEAM AKIRU Bot Hosting</title>
  <style>
    body { font-family: Arial, sans-serif; background-color: #181818; color: white; text-align: center; padding: 0; margin: 0; }
    .container { width: 80%; max-width: 600px; margin: auto; padding: 30px; background: #222; border-radius: 10px; box-shadow: 0px 0px 15px rgba(0,255,204,0.5); position: relative; margin-top: 60px; }

    .logout-btn { 
      position: absolute; top: -15px; right: 0; width: 100px; height: 50px;
      background: red; color: white; border: none; cursor: pointer;
      font-weight: bold; text-align: center; display: flex; align-items: center; 
      justify-content: center; border-radius: 0 10px 0 10px; font-size: 18px;
    }

    .active-bots-screen {
      width: 90%; max-width: 600px; background: #222; border-radius: 10px; padding: 15px;
      color: #00ffcc; font-size: 18px; text-align: center; margin: 10px auto; border: 2px solid #00ffcc;
    }

    input, button, select { 
      margin: 10px; padding: 15px; font-size: 18px; border: none; border-radius: 5px; 
    }
    input, select { background: #333; color: white; }
    
    button { 
      background: #00ffcc; color: black; font-weight: bold; cursor: pointer; transition: 0.3s; 
      width: 250px; font-size: 18px; display: block; margin: 15px auto; padding: 18px; 
    }
    button:hover { background: #00cc99; }

    #outputPanel { 
      margin: 20px auto; width: 90%; max-width: 600px; height: 100px;
      border: 2px solid #00ffcc; background: #111; color: #00ffcc; font-size: 1em;
      overflow-y: auto; text-align: left; padding: 10px; position: relative;
    }

    /* Copy Button */
    #copyOutputButton {
      margin-top: 10px;
      background: #00ffcc;
      color: black;
      border: none;
      border-radius: 5px;
      cursor: pointer;
      font-size: 18px;
      padding: 10px 20px;
      font-weight: bold;
    }
  </style>

  <script>
    var startedBots = {{ started_bots|tojson|safe }};
    
    function pollActiveBots() {    
      fetch("/status")    
        .then(response => response.json())    
        .then(data => {    
          var activeBotsPanel = document.getElementById("activeBotsPanel");
          activeBotsPanel.innerHTML = "<strong>Active Bots:</strong><br>" + (data.active_bots.length ? data.active_bots.join(",<br>") : "None");
        })    
        .catch(() => {    
          document.getElementById("activeBotsPanel").innerHTML = "<strong>Active Bots:</strong><br>None";    
        });    
    }    
    setInterval(pollActiveBots, 1000);

    function pollStartedBots() {    
      fetch("/started")    
        .then(response => response.json())    
        .then(data => {    
          startedBots = data.started_bots;    
          updateButtonLabel();    
        })    
        .catch(err => console.error("Error fetching started bots:", err));    
    }    
    setInterval(pollStartedBots, 1000);

    function updateButtonLabel() {    
      var selectElem = document.getElementById("botSelect");    
      var selectedBot = selectElem.value;    
      var toggleButton = document.getElementById("toggleBotButton");    
      toggleButton.textContent = startedBots.includes(selectedBot) ? "⏹ Stop Bot" : "▶ Start Bot";    
    }    

    function toggleBot() {    
      var selectElem = document.getElementById("botSelect");    
      var selectedBot = selectElem.value;    
      var url = startedBots.includes(selectedBot) ? ("/stop/" + selectedBot) : ("/start/" + selectedBot);    
      fetch(url)    
        .then(response => response.json())    
        .then(() => { pollStartedBots(); })    
        .catch(() => {});    
    }    

    function restartBot() {    
      var selectElem = document.getElementById("botSelect");    
      var selectedBot = selectElem.value;    
      fetch("/restart/" + selectedBot)    
        .then(response => response.json())    
        .then(() => { pollStartedBots(); })    
        .catch(() => {});    
    }
    
    function pollOutput() {
      var selectElem = document.getElementById("botSelect");
      var selectedBot = selectElem.value;
      if (selectedBot) {
        fetch("/output/" + selectedBot)
          .then(response => response.json())
          .then(data => {
            document.getElementById("outputPanel").innerText = data.output;
          })
          .catch(err => console.error("Error fetching output:", err));
      }
    }
    setInterval(pollOutput, 1000);

    function copyOutput() {
      var outputText = document.getElementById("outputPanel").innerText;
      navigator.clipboard.writeText(outputText).catch(() => {});
    }
  </script>
</head>
<body>
  <div class="container">
    <button class="logout-btn" onclick="window.location.href='{{ url_for('logout') }}'">Logout</button>
    
    <div class="header">
      <h2>Welcome, {{ username }}!</h2>
    </div>

    <div class="active-bots-screen" id="activeBotsPanel">
      <strong>Active Bots:</strong> Loading...
    </div>

    <h3>Upload Your Bot</h3>
    <form action="{{ url_for('upload_bot') }}" method="post" enctype="multipart/form-data">
      <input type="file" name="bot_file" required>
      <button type="submit">Upload</button>
    </form>

    <!-- Output Panel -->
    <div id="outputPanel"></div>

    <!-- Copy Output Button (Now Below the Output Panel) -->
    <button id="copyOutputButton" onclick="copyOutput()">📋 Copy Output</button>

    {% if bots %}
      <select id="botSelect">
        {% for bot in bots %}
          <option value="{{ bot }}">{{ bot }}</option>
        {% endfor %}
      </select>
      <button id="toggleBotButton" onclick="toggleBot()">▶ Start Bot</button>
      <button onclick="restartBot()">🔄 Restart Bot</button>
      <button onclick="window.location.href='/edit/' + document.getElementById('botSelect').value;">📝 Edit File</button>
      <button onclick="window.location.href='/rename/' + document.getElementById('botSelect').value;">✏ Rename File</button>
      <button onclick="window.location.href='/create';">➕ Create File</button>
    {% else %}
      <p>No bots uploaded yet.</p>
    {% endif %}
  </div>

  <p class="footer">© TEAM AKIRU - All Rights Reserved</p>
</body>
</html>
"""

# ---------------------------
# Route: Dashboard / Hosting Page
# ---------------------------
@app.route("/")
def hosting_page():
    if "username" not in session:
        return redirect(url_for("login"))
    username = session["username"]
    bots = [f for f in get_github_files_for_user(username) if not f.endswith(" start")]
    started_bots = get_started_files(username)
    return render_template_string(HTML_TEMPLATE, bots=bots, username=username, started_bots=started_bots)

# ---------------------------
# Route: File Upload
# ---------------------------
@app.route("/upload", methods=["POST"])
def upload_bot():
    if "username" not in session:
        return redirect(url_for("login"))
    file = request.files.get("bot_file")
    if file:
        username = session["username"]
        filename = file.filename
        file_content = file.read()
        user_folder = os.path.join(UPLOAD_FOLDER, username)
        os.makedirs(user_folder, exist_ok=True)
        local_file_path = os.path.join(user_folder, filename)
        with open(local_file_path, "wb") as f:
            f.write(file_content)
        if upload_file_to_github(username, filename, file_content):
            return redirect(url_for("hosting_page"))
        else:
            return "<h3 style='color:red;'>GitHub upload failed!</h3>"
    return "<h3 style='color:red;'>Upload Failed!</h3>"

# ---------------------------
# Route: Delete File
# ---------------------------
@app.route("/delete/<filename>")
def delete_file(filename):
    if "username" not in session:
        return redirect(url_for("login"))
    username = session["username"]
    if not delete_file_from_github(username, filename):
        return "<h3 style='color:red;'>Error deleting file from GitHub!</h3>"
    delete_file_from_github(username, f"{filename} start")
    local_file_path = os.path.join(UPLOAD_FOLDER, username, filename)
    if os.path.exists(local_file_path):
        os.remove(local_file_path)
    return redirect(url_for("hosting_page"))

# ---------------------------
# Route: Edit File
# ---------------------------
@app.route("/edit/<filename>", methods=["GET", "POST"])
def edit_file(filename):
    if "username" not in session:
        return redirect(url_for("login"))
    username = session["username"]
    user_folder = os.path.join(UPLOAD_FOLDER, username)
    file_path = os.path.join(user_folder, filename)
    if request.method == "POST":
        new_content = request.form.get("file_content")
        if new_content is None:
            return "<h3 style='color:red;'>No content provided!</h3>"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        with open(file_path, "rb") as f:
            file_data = f.read()
        if upload_file_to_github(username, filename, file_data):
            return redirect(url_for("hosting_page"))
        else:
            return "<h3 style='color:red;'>Error updating file on GitHub!</h3>"
    else:
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        else:
            content = ""
        edit_template = """
        <!DOCTYPE html>
        <html>
          <head>
            <meta charset="UTF-8">
            <title>Edit File - {{ filename }}</title>
            <style>
              body { font-family: Arial, sans-serif; background-color: #181818; color: white; text-align: center; padding: 20px; }
              .container { width: 95%; max-width: 1000px; margin: auto; background: #222; padding: 20px; border-radius: 10px; }
              textarea { width: 100%; height: 1500px; padding: 10px; border: none; border-radius: 5px; background: #333; color: white; font-size: 1em; }
              button { margin-top: 50px; padding: 10px 20px; background: #00ffcc; color: black; border: none; border-radius: 5px; cursor: pointer; font-size: 2em; }
              button:hover { background: #00cc99; }
              a { color: #00ffcc; text-decoration: none; font-size: 2em; }
            </style>
          </head>
          <body>
            <div class="container">
              <h2>Edit File - {{ filename }}</h2>
              <form method="post">
                <textarea name="file_content">{{ content }}</textarea>
                <br>
                <button type="submit">Save Changes</button>
              </form>
              <p><a href="{{ url_for('hosting_page') }}">Back to Dashboard</a></p>
            </div>
          </body>
        </html>
        """
        return render_template_string(edit_template, filename=filename, content=content)

# ---------------------------
# Route: Rename File
# ---------------------------
@app.route("/rename/<filename>", methods=["GET", "POST"])
def rename_file(filename):
    if "username" not in session:
        return redirect(url_for("login"))
    username = session["username"]
    user_folder = os.path.join(UPLOAD_FOLDER, username)
    old_file_path = os.path.join(user_folder, filename)
    if request.method == "POST":
        new_filename = request.form.get("new_filename")
        if not new_filename:
            return "<h3 style='color:red;'>New file name required!</h3>"
        new_file_path = os.path.join(user_folder, new_filename)
        try:
            os.rename(old_file_path, new_file_path)
        except Exception as e:
            return f"<h3 style='color:red;'>Error renaming file: {str(e)}</h3>"
        with open(new_file_path, "rb") as f:
            file_data = f.read()
        if upload_file_to_github(username, new_filename, file_data):
            delete_file_from_github(username, filename)
            delete_file_from_github(username, f"{filename} start")
            return redirect(url_for("hosting_page"))
        else:
            return "<h3 style='color:red;'>Error updating file on GitHub!</h3>"
    else:
        rename_template = """
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="UTF-8">
          <title>Rename File - {{ filename }}</title>
          <style>
            body { font-family: Arial, sans-serif; background-color: #181818; color: white; text-align: center; padding: 20px; margin: 0; }
            .container { position: relative; top: 20px; width: 100%; height: 400px; margin: auto; background: #222; padding: 20px; border-radius: 10px; filter: brightness(1.2); display: flex; flex-direction: column; align-items: center; justify-content: center; }
            h2 { font-size: 1.8em; margin-bottom: 20px; }
            input { width: 80%; padding: 10px; border: none; border-radius: 60px; margin-top: 10px; background: #333; color: white; font-size: 1em; text-align: center; }
            button { margin-top: 20px; padding: 10px 20px; background: #00ffcc; color: black; border: none; border-radius: 5px; cursor: pointer; font-size: 1em; }
            button:hover { background: #00cc99; }
            a { color: #00ffcc; text-decoration: none; font-size: 1em; }
            @media (min-width: 600px) {
              .container { max-width: 800px; padding: 40px; }
              h2 { font-size: 2.5em; }
              input { padding: 20px; font-size: 1.5em; }
              button { padding: 20px 40px; font-size: 2em; }
              a { font-size: 2em; }
            }
          </style>
        </head>
        <body>
          <div class="container">
            <h2>Rename File - {{ filename }}</h2>
            <form method="post">
              <input type="text" name="new_filename" placeholder="Enter new file name" required>
              <button type="submit">Rename</button>
            </form>
            <p><a href="{{ url_for('hosting_page') }}">Back to Dashboard</a></p>
          </div>
        </body>
        </html>
        """
        return render_template_string(rename_template, filename=filename)

@app.route("/create", methods=["GET", "POST"])
def create_file():
    if "username" not in session:
        return redirect(url_for("login"))
    username = session["username"]
    if request.method == "POST":
        filename = request.form.get("filename")
        content = request.form.get("file_content", "")
        if not filename:
            return "<h3 style='color:red;'>File name is required!</h3>"
        user_folder = os.path.join(UPLOAD_FOLDER, username)
        os.makedirs(user_folder, exist_ok=True)
        local_file_path = os.path.join(user_folder, filename)
        with open(local_file_path, "wb") as f:
            f.write(content.encode("utf-8"))
        if upload_file_to_github(username, filename, content.encode("utf-8")):
            return redirect(url_for("hosting_page"))
        else:
            return "<h3 style='color:red;'>Failed to create file on GitHub!</h3>"
    create_template = """
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="UTF-8">
        <title>Create New File</title>
        <style>
          body { font-family: Arial, sans-serif; background-color: #181818; color: white; text-align: center; padding: 20px; }
          .container { width: 95%; max-width: 600px; margin: auto; background: #222; padding: 20px; border-radius: 10px; }
          input, textarea, button { margin: 10px; padding: 12px; font-size: 16px; border: none; border-radius: 5px; }
          input, textarea { background: #333; color: white; width: 100%; }
          button { background: #00ffcc; color: black; font-weight: bold; cursor: pointer; }
          button:hover { background: #00cc99; }
          a { color: #00ffcc; text-decoration: none; }
        </style>
      </head>
      <body>
        <div class="container">
          <h2>Create New File</h2>
          <form method="post">
            <input type="text" name="filename" placeholder="Enter file name" required>
            <textarea name="file_content" placeholder="Enter file content (optional)" rows="10"></textarea>
            <br>
            <button type="submit">Create File</button>
          </form>
          <p><a href="{{ url_for('hosting_page') }}">Back to Dashboard</a></p>
        </div>
      </body>
    </html>
    """
    return render_template_string(create_template)

# ---------------------------
# Route: Bot Process Status and Output
# ---------------------------
@app.route("/status")
def status():
    active = []
    for bot, proc in bot_processes.items():
        if proc.poll() is None:
            active.append(bot)
    return jsonify(active_bots=active, bot_status=bot_status)

@app.route("/output/<bot>")
def get_output(bot):
    return jsonify(output=bot_outputs.get(bot, ""))

# ---------------------------
# New Endpoint: Get Started Bots
# ---------------------------
@app.route("/started")
def started():
    if "username" not in session:
        return jsonify(started_bots=[])
    username = session["username"]
    started = get_started_files(username)
    return jsonify(started_bots=started)

# ---------------------------
# New Endpoint: Remove Marker if polling error occurs
# ---------------------------
@app.route("/remove_marker/<bot>")
def remove_marker(bot):
    if "username" not in session:
        return jsonify({"message": "Not logged in"})
    username = session["username"]
    if delete_file_from_github(username, f"{bot} start"):
        return jsonify({"message": "Marker removed"})
    else:
        return jsonify({"message": "Failed to remove marker"}), 500

# ---------------------------
# Helper: Find bot file path (local)
# ---------------------------
def find_bot_path(bot_name, username):
    user_folder = os.path.join(UPLOAD_FOLDER, username)
    path = os.path.join(user_folder, bot_name)
    if os.path.exists(path):
        return path
    return None

# ---------------------------
# Route: Start Bot (24/7 auto-restart enabled)
# ---------------------------
@app.route("/start/<bot>")
def start_bot(bot):
    if "username" not in session:
        return redirect(url_for("login"))
    # Prevent multiple instances.
    if bot in bot_processes:
        delete_file_from_github(session["username"], f"{bot} start")
        return jsonify({"message": f"{bot} is already running!"})
    result = run_bot_process(bot, session["username"])
    return jsonify(result)

@app.route("/stop/<bot>")
def stop_bot(bot):
    if "username" not in session:
        return redirect(url_for("login"))
    if bot in bot_processes:
        proc = bot_processes[bot]
        if proc.poll() is not None:
            del bot_processes[bot]
            bot_status[bot] = "stopped"
            delete_file_from_github(session["username"], f"{bot} start")
            return jsonify({"message": f"{bot} is already terminated."})
        try:
            proc.terminate()
        except Exception as e:
            try:
                proc.kill()
            except Exception as e2:
                del bot_processes[bot]
                bot_status[bot] = f"Error: {str(e2)}"
                return jsonify({"message": f"Failed to stop bot: {str(e2)}"})
        del bot_processes[bot]
        bot_status[bot] = "stopped"
        delete_file_from_github(session["username"], f"{bot} start")
        return jsonify({"message": f"{bot} stopped successfully!"})
    return jsonify({"message": "Bot is not running!"})

@app.route("/restart/<bot>")
def restart_bot(bot):
    if "username" not in session:
        return redirect(url_for("login"))
    username = session["username"]
    if username not in restarting_bots:
         restarting_bots[username] = set()
    restarting_bots[username].add(bot)
    if bot in bot_processes:
        proc = bot_processes[bot]
        try:
            proc.terminate()
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        del bot_processes[bot]
    delete_file_from_github(username, f"{bot} start")
    time.sleep(0)
    result = run_bot_process(bot, username)
    restarting_bots[username].discard(bot)
    return jsonify(result)

# ---------------------------
# Routes: User Authentication
# ---------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    error = ""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        if not username or not password:
            error = "Username and password are required!"
        elif password != confirm_password:
            error = "Passwords do not match!"
        else:
            users = load_users()
            if username in users:
                error = "User already exists!"
            else:
                users[username] = password
                if update_users_file(users):
                    return redirect(url_for("login"))
                else:
                    error = "Error updating GitHub file"
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>Register</title>
      <style>
        body { font-family: Arial, sans-serif; background-color: #181818; color: white; text-align: center; padding: 20px; margin: 0; }
        .container { width: 90%; max-width: 300px; margin: 20px auto; padding: 20px; background: #222; border-radius: 10px; }
        .password-container { position: relative; display: flex; align-items: center; }
        .password-container input { flex: 1; padding-right: 50px; height: 40px; background: #333; color: white; border: none; border-radius: 5px; }
        .password-container .toggle-btn { position: absolute; right: 0; top: 0; height: 40px; width: 50px; background: #00ffcc; border: none; cursor: pointer; font-weight: bold; display: flex; align-items: center; justify-content: center; border-radius: 0 5px 5px 0; }
        input, button { margin: 5px 0; padding: 10px; width: 100%; box-sizing: border-box; border: none; border-radius: 5px; }
        input { background: #333; color: white; }
        button { background: #00ffcc; color: black; font-weight: bold; cursor: pointer; }
        button:hover { background: #00cc99; }
        a { color: #00ffcc; text-decoration: none; }
        .error { color: red; margin-top: 5px; }
      </style>
      <script>
        function togglePasswordVisibility(id, btnId) {
          var input = document.getElementById(id);
          var btn = document.getElementById(btnId);
          if (input.type === "password") {
            input.type = "text";
            btn.textContent = "Hide";
          } else {
            input.type = "password";
            btn.textContent = "Show";
          }
        }
      </script>
    </head>
    <body>
      <div class="container">
        <h2>Register</h2>
        <form method="post">
          <input type="text" name="username" id="regUsername" placeholder="Username" required>
          <div class="password-container">
            <input type="password" name="password" id="regPassword" placeholder="Password" required>
            <button type="button" class="toggle-btn" id="toggleRegPassword" onclick="togglePasswordVisibility('regPassword', 'toggleRegPassword')">Show</button>
          </div>
          <div class="password-container">
            <input type="password" name="confirm_password" id="confirmRegPassword" placeholder="Confirm Password" required>
            <button type="button" class="toggle-btn" id="toggleConfirmRegPassword" onclick="togglePasswordVisibility('confirmRegPassword', 'toggleConfirmRegPassword')">Show</button>
          </div>
          {% if error %}
            <div class="error">{{ error }}</div>
          {% endif %}
          <button type="submit">Register</button>
        </form>
        <p>Already have an account? <a href="{{ url_for('login') }}">Login here</a></p>
      </div>
    </body>
    </html>
    ''', error=error)

@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        users = load_users()
        if username in users and users[username] == password:
            session["username"] = username
            user_agent = request.headers.get("User-Agent", "")
            session["device_type"] = "mobile" if "Mobile" in user_agent else "desktop"
            return redirect(url_for("hosting_page"))
        error = "Invalid credentials!"
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>Login</title>
      <style>
        body { font-family: Arial, sans-serif; background-color: #181818; color: white; text-align: center; padding: 20px; margin: 0; }
        .container { width: 90%; max-width: 300px; margin: 20px auto; padding: 20px; background: #222; border-radius: 10px; }
        .password-container { position: relative; display: flex; align-items: center; }
        .password-container input { flex: 1; padding-right: 50px; height: 40px; background: #333; color: white; border: none; border-radius: 5px; }
        .password-container .toggle-btn { position: absolute; right: 0; top: 0; height: 40px; width: 50px; background: #00ffcc; border: none; cursor: pointer; font-weight: bold; display: flex; align-items: center; justify-content: center; border-radius: 0 5px 5px 0; }
        input, button { margin: 5px 0; padding: 10px; width: 100%; box-sizing: border-box; border: none; border-radius: 5px; }
        input { background: #333; color: white; }
        button { background: #00ffcc; color: black; font-weight: bold; cursor: pointer; }
        button:hover { background: #00cc99; }
        a { color: #00ffcc; text-decoration: none; }
        .error { color: red; margin-top: 5px; }
      </style>
      <script>
        function togglePasswordVisibility(id, btnId) {
          var input = document.getElementById(id);
          var btn = document.getElementById(btnId);
          if (input.type === "password") {
            input.type = "text";
            btn.textContent = "Hide";
          } else {
            input.type = "password";
            btn.textContent = "Show";
          }
        }
      </script>
    </head>
    <body>
      <div class="container">
        <h2>Login</h2>
        <form method="post">
          <input type="text" name="username" id="username" placeholder="Username" required>
          <div class="password-container">
            <input type="password" name="password" id="password" placeholder="Password" required>
            <button type="button" class="toggle-btn" id="togglePassword" onclick="togglePasswordVisibility('password', 'togglePassword')">Show</button>
          </div>
          {% if error %}
            <div class="error">{{ error }}</div>
          {% endif %}
          <button type="submit">Login</button>
        </form>
        <p>Don't have an account? <a href="{{ url_for('register') }}">Register here</a></p>
      </div>
    </body>
    </html>
    ''', error=error)

@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))

if __name__ == "__main__":
    cleanup_start_markers()  # Clean up any lingering "start" markers on GitHub.
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)