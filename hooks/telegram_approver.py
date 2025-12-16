#!/usr/bin/env python3
"""
Claude Code Permission Hook - Telegram Approval
Sends permission requests to Telegram and waits for user response.

Install: Copy to ~/.claude/hooks/ and register in ~/.claude/settings.json
"""

import json
import sys
import os
import time
import requests
import uuid

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

def get_bridge_data_dir():
    """Get the bridge data directory from config"""
    config = load_config()
    return config.get("bridge_data_dir", "/tmp/claude_telegram")

def load_config():
    """Load configuration from config.json"""
    if not os.path.exists(CONFIG_PATH):
        sys.stderr.write(f"Config not found: {CONFIG_PATH}\n")
        sys.exit(2)

    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

def get_callback_dir():
    return os.path.join(get_bridge_data_dir(), "callbacks")

def get_thinking_file():
    return os.path.join(get_bridge_data_dir(), "thinking_msg_id.txt")

def get_last_sent_file():
    return os.path.join(get_bridge_data_dir(), "last_sent_text.txt")

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

def send_telegram_message(config, text, keyboard=None):
    """Send a message to Telegram with optional inline keyboard"""
    url = f"https://api.telegram.org/bot{config['telegram_bot_token']}/sendMessage"

    payload = {
        "chat_id": config["telegram_chat_id"],
        "text": text,
        "parse_mode": "HTML"
    }

    if keyboard:
        payload["reply_markup"] = json.dumps(keyboard)

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return response.json().get("result", {}).get("message_id")
    except Exception as e:
        sys.stderr.write(f"Failed to send Telegram message: {e}\n")
        return None

def poll_for_response(config, request_id, timeout_seconds=60):
    """Wait for bridge to write callback response to file"""
    callback_dir = get_callback_dir()
    response_file = os.path.join(callback_dir, f"{request_id}.response")
    start_time = time.time()

    while time.time() - start_time < timeout_seconds:
        try:
            if os.path.exists(response_file):
                with open(response_file, 'r') as f:
                    decision = f.read().strip()
                os.remove(response_file)
                return decision
        except:
            pass
        time.sleep(0.5)

    return None

def escape_html(text):
    """Escape HTML special characters"""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def clean_escapes(text):
    """Convert escape sequences to actual characters for readable display"""
    if not isinstance(text, str):
        return text
    return text.replace('\\r\\n', '\n').replace('\\n', '\n').replace('\\r', '\n').replace('\\t', '  ')

def format_tool_details(tool_name, tool_input):
    """Format tool details for display - full text up to Telegram limit"""
    MAX_LEN = 3500

    if tool_name == "Bash":
        command = tool_input.get("command", "")
        command = escape_html(command)
        if len(command) > MAX_LEN:
            command = command[:MAX_LEN] + "\n\n... (truncated)"
        return f"<b>Command:</b>\n<code>{command}</code>"

    elif tool_name == "Write":
        file_path = tool_input.get("file_path", "")
        content = tool_input.get("content", "")
        content = escape_html(content)
        if len(content) > MAX_LEN:
            content = content[:MAX_LEN] + "\n\n... (truncated)"
        return f"<b>File:</b>\n<code>{escape_html(file_path)}</code>\n\n<b>Content:</b>\n<code>{content}</code>"

    elif tool_name == "Edit":
        file_path = tool_input.get("file_path", "")
        old_string = tool_input.get("old_string", "")
        new_string = tool_input.get("new_string", "")

        context_lines = 3
        diff_lines = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()

            pos = file_content.find(old_string)
            if pos != -1:
                before = file_content[:pos]
                after = file_content[pos + len(old_string):]

                before_lines = before.splitlines()[-context_lines:] if before else []
                after_lines = after.splitlines()[:context_lines] if after else []

                for line in before_lines:
                    diff_lines.append(f"   {escape_html(line)}")

                for line in old_string.splitlines():
                    diff_lines.append(f"🔴 {escape_html(line)}")

                for line in new_string.splitlines():
                    diff_lines.append(f"🟢 {escape_html(line)}")

                for line in after_lines:
                    diff_lines.append(f"   {escape_html(line)}")
            else:
                for line in old_string.splitlines():
                    diff_lines.append(f"🔴 {escape_html(line)}")
                for line in new_string.splitlines():
                    diff_lines.append(f"🟢 {escape_html(line)}")

        except:
            for line in old_string.splitlines():
                diff_lines.append(f"🔴 {escape_html(line)}")
            for line in new_string.splitlines():
                diff_lines.append(f"🟢 {escape_html(line)}")

        diff_text = "\n".join(diff_lines)
        if len(diff_text) > 3000:
            diff_text = diff_text[:3000] + "\n\n... (truncated)"

        return f"<b>File:</b>\n<code>{escape_html(file_path)}</code>\n\n<b>Changes:</b>\n<pre>{diff_text}</pre>"

    elif tool_name == "Read":
        file_path = tool_input.get("file_path", "")
        return f"<b>File:</b>\n<code>{escape_html(file_path)}</code>"

    elif tool_name == "WebFetch":
        url = tool_input.get("url", "")
        prompt = tool_input.get("prompt", "")
        return f"<b>URL:</b>\n<code>{escape_html(url)}</code>\n\n<b>Prompt:</b>\n{escape_html(prompt)}"

    elif tool_name == "Glob":
        pattern = tool_input.get("pattern", "")
        path = tool_input.get("path", "")
        return f"<b>Pattern:</b>\n<code>{escape_html(pattern)}</code>\n\n<b>Path:</b>\n<code>{escape_html(path or 'current directory')}</code>"

    elif tool_name == "Grep":
        pattern = tool_input.get("pattern", "")
        path = tool_input.get("path", "")
        return f"<b>Search:</b>\n<code>{escape_html(pattern)}</code>\n\n<b>Path:</b>\n<code>{escape_html(path or 'current directory')}</code>"

    else:
        lines = []
        for key, value in tool_input.items():
            if isinstance(value, str):
                value = clean_escapes(value)
                value = escape_html(value)
            else:
                value = escape_html(str(value))
            lines.append(f"<b>{escape_html(key)}:</b>\n{value}")
        details = "\n\n".join(lines)
        if len(details) > MAX_LEN:
            details = details[:MAX_LEN] + "\n\n... (truncated)"
        return details

def make_decision(behavior, message=None):
    """Create the hook output JSON"""
    decision = {"behavior": behavior}
    if message:
        decision["message"] = message

    output = {
        "hookSpecificOutput": {
            "hookEventName": "PermissionRequest",
            "decision": decision
        }
    }
    return output

def get_latest_claude_text(transcript_path):
    """Get Claude's latest text response from transcript"""
    if not transcript_path or not os.path.exists(transcript_path):
        return None

    latest_text = None
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
                                latest_text = "\n".join(text_parts)
                except:
                    continue
    except:
        pass
    return latest_text

def main():
    config = load_config()

    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        sys.stderr.write(f"Invalid JSON input: {e}\n")
        sys.exit(2)

    tool_name = hook_input.get("tool_name", "Unknown")
    tool_input = hook_input.get("tool_input", {})
    transcript_path = hook_input.get("transcript_path")

    delete_thinking_message(config)

    claude_text = get_latest_claude_text(transcript_path)
    if claude_text and len(claude_text.strip()) > 0:
        text_key = claude_text[:200].strip()
        already_sent = False
        last_sent_file = get_last_sent_file()
        try:
            if os.path.exists(last_sent_file):
                with open(last_sent_file, 'r', encoding='utf-8') as f:
                    if f.read().strip() == text_key:
                        already_sent = True
        except:
            pass

        if not already_sent:
            text_preview = claude_text[:2000] if len(claude_text) > 2000 else claude_text
            send_telegram_message(config, f"🤖 Claude:\n\n{escape_html(text_preview)}")
            try:
                os.makedirs(os.path.dirname(last_sent_file), exist_ok=True)
                with open(last_sent_file, 'w', encoding='utf-8') as f:
                    f.write(text_key)
            except:
                pass

    auto_approve = config.get("auto_approve", ["Read", "Glob", "Grep"])
    if tool_name in auto_approve:
        output = make_decision("allow")
        print(json.dumps(output))
        sys.exit(0)

    auto_deny = config.get("auto_deny", [])
    if tool_name in auto_deny:
        output = make_decision("deny", f"{tool_name} is blocked")
        print(json.dumps(output))
        sys.exit(0)

    request_id = str(uuid.uuid4())[:8]

    details = format_tool_details(tool_name, tool_input)
    message = f"🔔 <b>Permission Request</b>\n\n<b>Tool:</b> {tool_name}\n\n{details}"

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "✅ Allow", "callback_data": f"{request_id}:allow"},
                {"text": "❌ Deny", "callback_data": f"{request_id}:deny"}
            ]
        ]
    }

    msg_id = send_telegram_message(config, message, keyboard)

    if not msg_id:
        output = make_decision("deny", "Failed to send Telegram notification")
        print(json.dumps(output))
        sys.exit(0)

    timeout = config.get("timeout_seconds", 60)
    response = poll_for_response(config, request_id, timeout)

    if response == "allow":
        send_telegram_message(config, "✅ Allowed")
        output = make_decision("allow")
    else:
        reason = "Denied by user" if response == "deny" else f"No response within {timeout}s"
        send_telegram_message(config, f"❌ {reason}")
        output = make_decision("deny", reason)

    print(json.dumps(output))
    sys.exit(0)

if __name__ == "__main__":
    main()
