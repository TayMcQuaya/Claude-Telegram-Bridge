#!/usr/bin/env python3
"""
Claude Response Sender - Sends Claude's responses to Telegram
This is a Stop hook that fires when Claude finishes responding.

Install: Copy to ~/.claude/hooks/ and register in ~/.claude/settings.json
"""

import json
import sys
import os
import requests

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

def get_bridge_data_dir():
    """Get the bridge data directory from config"""
    config = load_config()
    return config.get("bridge_data_dir", "/tmp/claude_telegram")

def get_thinking_file():
    return os.path.join(get_bridge_data_dir(), "thinking_msg_id.txt")

def load_config():
    if not os.path.exists(CONFIG_PATH):
        sys.exit(0)
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

def delete_thinking_message(config):
    """Delete the 'Thinking...' message if it exists"""
    thinking_file = get_thinking_file()
    if not os.path.exists(thinking_file):
        return
    try:
        with open(thinking_file, 'r') as f:
            msg_id = f.read().strip()
        os.remove(thinking_file)
        if msg_id:
            url = f"https://api.telegram.org/bot{config['telegram_bot_token']}/deleteMessage"
            requests.post(url, json={
                "chat_id": config["telegram_chat_id"],
                "message_id": int(msg_id)
            }, timeout=5)
    except:
        pass

def send_telegram(config, text):
    """Send a message to Telegram"""
    url = f"https://api.telegram.org/bot{config['telegram_bot_token']}/sendMessage"

    if len(text) > 4000:
        text = text[:4000] + "\n\n... (truncated)"

    try:
        requests.post(url, json={
            "chat_id": config["telegram_chat_id"],
            "text": text
        }, timeout=10)
    except:
        pass

def get_latest_assistant_message(transcript_path):
    """Parse transcript JSONL and get the latest assistant message"""
    if not transcript_path or not os.path.exists(transcript_path):
        return None

    latest_assistant = None

    try:
        with open(transcript_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("type") == "assistant":
                        message = entry.get("message", {})
                        content = message.get("content", [])
                        if isinstance(content, list):
                            text_parts = []
                            for item in content:
                                if isinstance(item, dict) and item.get("type") == "text":
                                    text_parts.append(item.get("text", ""))
                            if text_parts:
                                latest_assistant = "\n".join(text_parts)
                        elif isinstance(content, str):
                            latest_assistant = content
                except json.JSONDecodeError:
                    continue
    except:
        return None

    return latest_assistant

def main():
    config = load_config()

    try:
        hook_input = json.load(sys.stdin)
    except:
        sys.exit(0)

    transcript_path = hook_input.get("transcript_path")
    if not transcript_path:
        sys.exit(0)

    response = get_latest_assistant_message(transcript_path)

    if response and len(response.strip()) > 0:
        delete_thinking_message(config)
        send_telegram(config, f"🤖 Claude:\n\n{response}")

    sys.exit(0)

if __name__ == "__main__":
    main()
