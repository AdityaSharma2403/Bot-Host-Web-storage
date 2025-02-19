from flask import Flask, request, render_template_string, redirect, url_for, make_response, jsonify
import os
import subprocess
import threading

app = Flask(__name__)

# Set a known password for testing.
ACCESS_PASSWORD = "test"
UPLOAD_FOLDER = "user_bots"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Global dictionaries to track running bot processes and their outputs.
bot_processes = {}
bot_outputs = {}

def capture_output(bot_name, process):
    """Continuously capture output from the bot process."""
    bot_outputs[bot_name] = ""
    while True:
        out_line = process.stdout.readline()
        err_line = process.stderr.readline()
        if not out_line and not err_line and process.poll() is not None:
            break
        if out_line:
            try:
                bot_outputs[bot_name] += out_line.decode("utf-8")
            except Exception:
                bot_outputs[bot_name] += str(out_line)
        if err_line:
            try:
                bot_outputs[bot_name] += err_line.decode("utf-8")
            except Exception:
                bot_outputs[bot_name] += str(err_line)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <!-- Responsive Meta Tag -->
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>TEAM-AKIRU Bot Hosting</title>
  <style>
    /* Global Styles */
    body {
      font-family: Arial, sans-serif;
      background-color: #181818;
      color: white;
      text-align: center;
      padding: 10px;
      margin: 0;
    }
    .container {
      width: 95%;
      margin: auto;
      padding: 20px;
      background: #222;
      border-radius: 10px;
      box-shadow: 0 0 10px rgba(0,255,204,0.5);
    }
    h2 { color: #00ffcc; margin-bottom: 20px; }
    input, button, select {
      margin: 5px 0;
      padding: 10px;
      width: 100%;
      border: none;
      border-radius: 5px;
      font-size: 16px;
      box-sizing: border-box;
    }
    input, select { background: #333; color: white; }
    button {
      background: #00ffcc;
      color: black;
      font-weight: bold;
      cursor: pointer;
      transition: 0.3s;
    }
    button:hover { background: #00cc99; }
    .footer {
      margin-top: 20px;
      font-size: 14px;
      color: #bbb;
    }
    /* Active Bots (Terminal-like) */
    .active-bots {
      background-color: #000;
      color: #0f0;
      padding: 15px;
      font-family: monospace;
      border: 2px solid #0f0;
      border-radius: 5px;
      text-align: center;
      margin-bottom: 20px;
      min-height: 100px;
      max-height: 300px;
      overflow-y: auto;
    }
    .active-bots h3 { margin: 0 0 10px; font-size: 1.5em; text-align: center; }
    .active-bots pre { margin: 0; white-space: pre-wrap; text-align: center; }
    /* File Output Screen */
    .file-output {
      background-color: #111;
      color: #ff0;
      padding: 15px;
      font-family: monospace;
      border: 2px solid #ff0;
      border-radius: 5px;
      text-align: left;
      margin-top: 20px;
      min-height: 100px;
      max-height: 300px;
      overflow-y: auto;
    }
    .file-output h3 { margin: 0 0 10px; font-size: 1.5em; text-align: center; }
    .file-output pre { margin: 0; white-space: pre-wrap; }
    /* Copy Output Button */
    .copy-btn {
      margin-top: 10px;
      padding: 10px 20px;
      background: #00ffcc;
      color: black;
      border: none;
      border-radius: 5px;
      cursor: pointer;
      font-weight: bold;
    }
    .copy-btn:hover { background: #00cc99; }
    /* Desktop-specific Styles */
    @media (min-width: 600px) {
      .container { max-width: 800px; }
      h2 { font-size: 2em; }
    }
  </style>
  <script>
    // Function to flash a button on click (change color for 0.25 seconds)
    function flashButton(btn) {
      // Get computed background color to restore later.
      let orig = window.getComputedStyle(btn).backgroundColor;
      btn.style.backgroundColor = "#00cc99"; // Flash color.
      setTimeout(() => {
        btn.style.backgroundColor = orig;
      }, 250);
    }

    // Update the Active Bots section every second.
    function updateStatus(){
      fetch("/status")
        .then(res => res.json())
        .then(data => {
          let term = document.getElementById("activeBots");
          let content = "<h3>Activate Bot</h3>";
          if(data.active_bots.length > 0){
            content += "<pre>" + data.active_bots.map(bot => bot + " activate").join("\\n") + "</pre>";
          } else {
            content += "<pre>No active bots</pre>";
          }
          term.innerHTML = content;
          // Adjust button display based on selected bot.
          let botSelect = document.getElementById("botSelect");
          let selectedBot = botSelect ? botSelect.value : "";
          let startButton = document.getElementById("startBtn");
          let stopButton = document.getElementById("stopBtn");
          if(data.active_bots.includes(selectedBot)){
            startButton.style.display = "none";
            stopButton.style.display = "inline-block";
          } else {
            startButton.style.display = "inline-block";
            stopButton.style.display = "none";
          }
        });
    }

    // Update the File Output screen for the selected bot.
    function updateFileOutput(){
      let botSelect = document.getElementById("botSelect");
      if(botSelect){
        let bot = botSelect.value;
        fetch("/output/" + bot)
          .then(res => res.json())
          .then(data => {
            let lines = data.output.split("\\n");
            let formatted = "";
            let first = true;
            for (let i = 0; i < lines.length; i++){
              let line = lines[i].trim();
              if(line !== ""){
                if(first && line.startsWith('print("') && line.endsWith('")')){
                  // For first line wrapped in print("..."), remove wrapper.
                  formatted += line.substring(7, line.length - 2) + "\\n";
                  first = false;
                } else {
                  formatted += line + "\\n";
                }
              }
            }
            document.getElementById("fileOutput").innerText = "Output:\\n" + formatted;
          });
      }
    }

    // Generic function to perform a bot action (start, stop, restart).
    function botAction(action){
      let bot = document.getElementById("botSelect").value;
      fetch("/" + action + "/" + bot)
        .then(res => res.json())
        .then(data => {
          updateStatus();
          updateFileOutput();
        });
    }

    // Copy the File Output text to the clipboard (no popup message).
    function copyOutput(){
      let text = document.getElementById("fileOutput").innerText;
      navigator.clipboard.writeText(text);
    }

    setInterval(function(){
      updateStatus();
      updateFileOutput();
    }, 1000);
    document.addEventListener("DOMContentLoaded", function(){
      updateStatus();
      updateFileOutput();
    });
  </script>
</head>
<body>
  {% if not logged_in %}
    <div class="container">
      <h2>Login</h2>
      <form method="post">
        <input type="password" name="password" placeholder="Enter Password" required>
        <button type="submit" onclick="flashButton(this)">Login</button>
      </form>
    </div>
  {% else %}
    <div class="container">
      <div class="active-bots" id="activeBots">Activate Bot</div>
      <div>
        <h3>Upload Your Bot</h3>
        <form action="/upload" method="post" enctype="multipart/form-data">
          <input type="file" name="bot_file" required>
          <button type="submit" onclick="flashButton(this)">Upload</button>
        </form>
      </div>
      <div class="file-output" id="fileOutput">Output</div>
      <button class="copy-btn" onclick="flashButton(this); copyOutput()">Copy Output</button>
      {% if bots %}
        <div>
          <h3>Your Uploaded Bots</h3>
          <select id="botSelect" onchange="updateStatus(); updateFileOutput();">
            {% for bot in bots %}
              <option value="{{ bot }}">{{ bot }}</option>
            {% endfor %}
          </select>
          <br>
          <button id="startBtn" onclick="flashButton(this); botAction('start')">Start Bot</button>
          <button id="stopBtn" onclick="flashButton(this); botAction('stop')" style="display:none;">Stop Bot</button>
          <button id="restartBtn" onclick="flashButton(this); botAction('restart')">Restart Bot</button>
        </div>
      {% else %}
        <p>No bots uploaded yet.</p>
      {% endif %}
    </div>
    <p class="footer">© TEAM AKIRU - All Rights Reserved</p>
  {% endif %}
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def hosting_page():
    logged_in = request.cookies.get("logged_in") == "true"
    if request.method == "POST":
        if request.form.get("password") == ACCESS_PASSWORD:
            resp = make_response(redirect(url_for("hosting_page")))
            resp.set_cookie("logged_in", "true")
            return resp
        return "<h3 style='color:red;'>Wrong Password!</h3>"
    bots = set()
    for entry in os.listdir(UPLOAD_FOLDER):
        entry_path = os.path.join(UPLOAD_FOLDER, entry)
        if os.path.isdir(entry_path):
            for file in os.listdir(entry_path):
                bots.add(file)
    return render_template_string(HTML_TEMPLATE, logged_in=logged_in, bots=list(bots))

@app.route("/upload", methods=["POST"])
def upload_bot():
    if request.cookies.get("logged_in") != "true":
        return redirect(url_for("hosting_page"))
    file = request.files.get("bot_file")
    if file:
        user_id = request.remote_addr.replace(".", "_")
        user_folder = os.path.join(UPLOAD_FOLDER, user_id)
        os.makedirs(user_folder, exist_ok=True)
        file.save(os.path.join(user_folder, file.filename))
        return redirect(url_for("hosting_page"))
    return "<h3 style='color:red;'>Upload Failed!</h3>"

@app.route("/status")
def status():
    return jsonify(active_bots=list(bot_processes.keys()))

def find_bot_path(bot_name):
    for entry in os.listdir(UPLOAD_FOLDER):
        entry_path = os.path.join(UPLOAD_FOLDER, entry)
        if os.path.isdir(entry_path):
            path = os.path.join(entry_path, bot_name)
            if os.path.exists(path):
                return path
    return None

@app.route("/output/<bot>")
def get_output(bot):
    return jsonify(output=bot_outputs.get(bot, ""))

@app.route("/start/<bot>")
def start_bot(bot):
    if request.cookies.get("logged_in") != "true":
        return redirect(url_for("hosting_page"))
    if bot in bot_processes:
        return jsonify({"message": f"{bot} is already running!"})
    path = find_bot_path(bot)
    if path:
        try:
            proc = subprocess.Popen(["python3", path],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            bot_processes[bot] = proc
            threading.Thread(target=capture_output, args=(bot, proc), daemon=True).start()
            return jsonify({"message": f"{bot} started successfully!"})
        except Exception as e:
            return jsonify({"message": f"Failed to start bot: {str(e)}"})
    return jsonify({"message": "Bot not found!"})

@app.route("/stop/<bot>")
def stop_bot(bot):
    if request.cookies.get("logged_in") != "true":
        return redirect(url_for("hosting_page"))
    if bot in bot_processes:
        proc = bot_processes[bot]
        if proc.poll() is not None:
            del bot_processes[bot]
            return jsonify({"message": f"{bot} is already terminated."})
        try:
            proc.terminate()
        except Exception as e:
            del bot_processes[bot]
            return jsonify({"message": f"Failed to stop bot: {str(e)}"})
        del bot_processes[bot]
        return jsonify({"message": f"{bot} stopped successfully!"})
    return jsonify({"message": "Bot is not running!"})

@app.route("/restart/<bot>")
def restart_bot(bot):
    if request.cookies.get("logged_in") != "true":
        return redirect(url_for("hosting_page"))
    if bot in bot_processes:
        proc = bot_processes[bot]
        if proc.poll() is None:
            try:
                proc.terminate()
            except Exception:
                pass
        del bot_processes[bot]
    return start_bot(bot)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)