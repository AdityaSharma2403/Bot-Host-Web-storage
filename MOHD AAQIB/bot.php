<?php
// Enable Error Reporting for Debugging
error_reporting(E_ALL);
ini_set('display_errors', 1);

// Telegram Bot Token (Replace with your actual bot token)
$botToken = "7920046087:AAHmENmGaTOh_2FeI1trgY0KK0QmCXUkEmc";
$apiUrl = "https://api.telegram.org/bot$botToken";

// Free Fire Search API
$searchApiKey = "wlx_demon";
$searchApiBase = "https://wlx-search-api.vercel.app/search";

// Ban Check API
$banCheckApiBase = "http://amin-team-api.vercel.app/check_banned";

// Main Admin Telegram ID
$mainAdminId = 5112593221; // Replace with your actual admin ID

// Get Incoming Telegram Update
$update = file_get_contents("php://input");

if ($update === false) {
    error_log("Error: Failed to read input");
    die("Error: Failed to read input");
}

$update = json_decode($update, true);
if ($update === null && json_last_error() !== JSON_ERROR_NONE) {
    error_log("Error: Invalid JSON received - " . json_last_error_msg());
    die("Error: Invalid JSON received");
}

// Log the Update for Debugging
file_put_contents("bot_log.txt", json_encode($update, JSON_PRETTY_PRINT), FILE_APPEND);

// Check if it's a message update
if (isset($update["message"])) {
    $chat_id = $update["message"]["chat"]["id"];
    $user_id = $update["message"]["from"]["id"];
    $message_text = trim($update["message"]["text"] ?? '');

    // Restrict group usage for non-admins
    if ($chat_id < 0 && $user_id !== $mainAdminId) {
        sendMessage($chat_id, "❌ Only the bot admin can use this command.");
        exit;
    }

    // Handle Commands
    if ($message_text === "/start") {
        sendMessage($chat_id, "✅ Bot is running!");
    } elseif (strpos($message_text, "/search") === 0) {
        handleSearch($chat_id, $message_text);
    } elseif (strpos($message_text, "/isbanned") === 0) {
        handleBanCheck($chat_id, $message_text);
    } else {
        sendMessage($chat_id, "Unknown command. Try /start, /search {player_name}, or /isbanned {uid}");
    }
}

// Function to Search Free Fire UID
function handleSearch($chat_id, $message_text) {
    global $searchApiBase, $searchApiKey;

    $parts = explode(" ", $message_text, 2);
    if (count($parts) < 2) {
        sendMessage($chat_id, "Usage: /search {player_name}");
        return;
    }

    $player_name = urlencode(trim($parts[1]));
    $apiEndpoint = "$searchApiBase?nickname=$player_name&region=ind&api_key=$searchApiKey";

    $response = getApiResponse($apiEndpoint);
    $data = json_decode($response, true);

    if ($data && isset($data["uid"])) {
        $uid = $data["uid"];
        $nickname = $data["nickname"] ?? "N/A";
        $level = $data["level"] ?? "N/A";
        $rank = $data["rank"] ?? "N/A";

        $message = "🎮 Player: $nickname\n🆔 UID: $uid\n📊 Level: $level\n🏆 Rank: $rank";
        sendMessage($chat_id, $message);
    } else {
        sendMessage($chat_id, "Player not found or API error.");
    }
}

// Function to Check Ban Status
function handleBanCheck($chat_id, $message_text) {
    global $banCheckApiBase;

    $parts = explode(" ", $message_text, 2);
    if (count($parts) < 2) {
        sendMessage($chat_id, "Usage: /isbanned {uid}");
        return;
    }

    $uid = trim($parts[1]);
    $apiEndpoint = "$banCheckApiBase?player_id=$uid";

    $response = getApiResponse($apiEndpoint);
    $data = json_decode($response, true);

    if ($data && isset($data["status"])) {
        $status = strtoupper($data["status"]);
        if ($status === "BANNED") {
            sendMessage($chat_id, "UID $uid is permanently banned 😕.");
        } elseif ($status === "NOT BANNED") {
            sendMessage($chat_id, "UID $uid is not banned ☠️.");
        } else {
            sendMessage($chat_id, "UID $uid status: $status");
        }
    } else {
        sendMessage($chat_id, "Error fetching ban status for UID $uid.");
    }
}

// Function to Send a Message via Telegram Bot API
function sendMessage($chat_id, $message) {
    global $apiUrl;

    $url = "$apiUrl/sendMessage";
    $params = [
        "chat_id" => $chat_id,
        "text" => $message
    ];

    getApiResponse($url, $params);
}

// Function to Make API Requests with cURL
function getApiResponse($url, $postData = null) {
    $ch = curl_init();

    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, 1);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);

    if ($postData) {
        curl_setopt($ch, CURLOPT_POST, 1);
        curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($postData));
        curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json']);
    }

    $response = curl_exec($ch);
    $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $curl_error = curl_error($ch);
    curl_close($ch);

    // Log errors if any
    if ($http_code !== 200 || !empty($curl_error)) {
        error_log("cURL Error: $curl_error | HTTP Code: $http_code");
    }

    return $response;
}
?>
