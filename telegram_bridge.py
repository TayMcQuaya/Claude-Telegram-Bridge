#!/usr/bin/env python3
"""
Telegram Bridge for Claude Code
Handles bidirectional communication between Telegram and Claude Code CLI.

Features:
- Send messages from Telegram → types into Claude Code
- Permission callbacks from Telegram buttons
- Plan mode toggle command

Run this in a separate terminal while Claude Code is running.
"""

import json
import os
import time
import requests
import pyautogui
import pyperclip

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")
CALLBACK_DIR = os.path.join(SCRIPT_DIR, "data", "callbacks")
THINKING_FILE = os.path.join(SCRIPT_DIR, "data", "thinking_msg_id.txt")
PLAN_MODE_FILE = os.path.join(SCRIPT_DIR, "data", "plan_mode_state.txt")
BRIDGE_RUNNING_FILE = os.path.join(SCRIPT_DIR, "data", "bridge_running.txt")

def load_config():
    if not os.path.exists(CONFIG_PATH):
        print(f"Config not found: {CONFIG_PATH}")
        print("Please copy config.example.json to config.json and fill in your credentials.")
        exit(1)
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

def send_telegram(config, text):
    """Send a message to Telegram, return message_id"""
    url = f"https://api.telegram.org/bot{config['telegram_bot_token']}/sendMessage"
    try:
        resp = requests.post(url, json={
            "chat_id": config["telegram_chat_id"],
            "text": text
        }, timeout=10)
        return resp.json().get("result", {}).get("message_id")
    except:
        return None

def send_thinking(config):
    """Send 'Thinking...' and save message_id for later deletion"""
    msg_id = send_telegram(config, "💭 Thinking...")
    if msg_id:
        os.makedirs(os.path.dirname(THINKING_FILE), exist_ok=True)
        with open(THINKING_FILE, 'w') as f:
            f.write(str(msg_id))
    return msg_id

def get_updates(config, offset):
    """Poll Telegram for ALL updates (messages AND callbacks)"""
    url = f"https://api.telegram.org/bot{config['telegram_bot_token']}/getUpdates"
    try:
        params = {
            "offset": offset,
            "timeout": 5
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json().get("result", [])
    except Exception as e:
        print(f"Polling error: {e}")
        return []

def answer_callback(config, callback_id, text="Received!"):
    """Acknowledge a callback query"""
    url = f"https://api.telegram.org/bot{config['telegram_bot_token']}/answerCallbackQuery"
    try:
        requests.post(url, json={
            "callback_query_id": callback_id,
            "text": text
        }, timeout=5)
    except:
        pass

def handle_callback(callback_data):
    """Handle permission callback - write response to file for approver hook"""
    if ":" not in callback_data:
        return

    request_id, decision = callback_data.split(":", 1)

    os.makedirs(CALLBACK_DIR, exist_ok=True)
    response_file = os.path.join(CALLBACK_DIR, f"{request_id}.response")

    with open(response_file, 'w') as f:
        f.write(decision)

    print(f"Callback: {request_id} -> {decision}")

def type_to_claude(text):
    """Type text into Claude Code CLI"""
    print(f"Typing to Claude: {text[:50]}...")

    pyperclip.copy(text)

    time.sleep(0.2)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(0.2)
    pyautogui.press('enter')

    print("Sent!")

def main():
    config = load_config()
    offset = 0

    os.makedirs(CALLBACK_DIR, exist_ok=True)

    with open(BRIDGE_RUNNING_FILE, 'w') as f:
        f.write("1")

    print("=" * 50)
    print("Telegram Bridge for Claude Code")
    print("=" * 50)
    print("Messages from Telegram will be typed into Claude Code.")
    print("Make sure the Claude Code terminal is focused!")
    print("=" * 50)

    send_telegram(config, "🌉 Bridge started!\n\nCommands:\n/help - Show help\n/plan - Toggle plan mode\n/stop - Stop bridge")

    while True:
        try:
            updates = get_updates(config, offset)

            for update in updates:
                offset = update["update_id"] + 1

                if "callback_query" in update:
                    callback = update["callback_query"]
                    callback_data = callback.get("data", "")
                    answer_callback(config, callback["id"])
                    handle_callback(callback_data)
                    continue

                if "message" not in update:
                    continue

                msg = update["message"]

                if "text" not in msg:
                    continue

                if str(msg["from"]["id"]) != config["telegram_chat_id"]:
                    continue

                text = msg["text"]

                if text == "/stop":
                    if os.path.exists(BRIDGE_RUNNING_FILE):
                        os.remove(BRIDGE_RUNNING_FILE)
                    send_telegram(config, "🛑 Bridge stopped")
                    print("Stopping bridge...")
                    return

                if text == "/plan":
                    plan_on = False
                    try:
                        if os.path.exists(PLAN_MODE_FILE):
                            with open(PLAN_MODE_FILE, 'r') as f:
                                plan_on = f.read().strip() == "1"
                    except:
                        pass

                    pyautogui.hotkey('shift', 'tab')
                    time.sleep(0.1)
                    pyautogui.hotkey('shift', 'tab')

                    plan_on = not plan_on
                    try:
                        os.makedirs(os.path.dirname(PLAN_MODE_FILE), exist_ok=True)
                        with open(PLAN_MODE_FILE, 'w') as f:
                            f.write("1" if plan_on else "0")
                    except:
                        pass

                    status = "📋 Plan mode: ON" if plan_on else "⚡ Plan mode: OFF"
                    send_telegram(config, status)
                    print(status)
                    continue

                if text == "/help":
                    help_text = """🤖 <b>Claude Telegram Bridge</b>

<b>Commands:</b>
/help - Show this help
/plan - Toggle plan mode on/off
/stop - Stop the bridge

<b>How to use:</b>
• Send any text → types into Claude Code
• Tap Allow/Deny buttons → responds to permission requests

<b>Limitations:</b>
• Claude Code terminal must be focused
• Plan mode may desync if toggled via keyboard
• One chat controls whichever terminal is focused"""

                    url = f"https://api.telegram.org/bot{config['telegram_bot_token']}/sendMessage"
                    requests.post(url, json={
                        "chat_id": config["telegram_chat_id"],
                        "text": help_text,
                        "parse_mode": "HTML"
                    }, timeout=10)
                    continue

                if text.startswith("/"):
                    continue

                send_thinking(config)
                type_to_claude(text)

            time.sleep(0.5)

        except KeyboardInterrupt:
            if os.path.exists(BRIDGE_RUNNING_FILE):
                os.remove(BRIDGE_RUNNING_FILE)
            print("\nStopping bridge...")
            send_telegram(config, "🛑 Bridge stopped (Ctrl+C)")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
