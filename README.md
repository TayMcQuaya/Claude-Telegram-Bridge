# Claude Telegram Bridge

Control Claude Code remotely via Telegram! Send prompts, receive responses, and approve permission requests - all from your phone.

## Features

- 📱 **Send prompts from Telegram** → Types directly into Claude Code
- 🤖 **Receive Claude's responses** → Automatically sent to Telegram
- ✅ **Approve/Deny permissions remotely** → Inline buttons for quick actions
- 📋 **Toggle Plan Mode** → `/plan` command
- 💭 **Thinking indicator** → Shows "Thinking..." while Claude works
- 🔴🟢 **Diff view for edits** → See code changes with context

## Prerequisites

- [Claude Code CLI](https://claude.ai/code) installed and working
- Python 3.8+
- A Telegram account
- Windows with WSL2 (or native Linux/macOS)

## Quick Start

### Step 1: Create a Telegram Bot

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` and follow the prompts
3. Copy the **bot token** (looks like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)
4. Start a chat with your new bot (search for it and click "Start")

### Step 2: Get Your Chat ID

1. Search for `@userinfobot` on Telegram
2. Send it any message
3. Copy your **chat ID** (a number like `123456789`)

### Step 3: Install Dependencies

```bash
pip install requests pyautogui pyperclip
```

### Step 4: Configure the Bridge

1. Copy the config template:
   ```bash
   cp config.example.json config.json
   ```

2. Edit `config.json` with your credentials:
   ```json
   {
     "telegram_bot_token": "YOUR_BOT_TOKEN_HERE",
     "telegram_chat_id": "YOUR_CHAT_ID_HERE",
     "auto_approve": ["Read", "Glob", "Grep"],
     "auto_deny": [],
     "timeout_seconds": 300
   }
   ```

### Step 5: Install the Hooks

The hooks integrate with Claude Code to send notifications and handle permissions.

#### 5a. Copy hooks to Claude's hooks directory

**Linux/macOS/WSL:**
```bash
mkdir -p ~/.claude/hooks
cp hooks/telegram_approver.py ~/.claude/hooks/
cp hooks/response_sender.py ~/.claude/hooks/
cp hooks/config.example.json ~/.claude/hooks/config.json
```

#### 5b. Configure the hooks

Edit `~/.claude/hooks/config.json`:
```json
{
  "telegram_bot_token": "YOUR_BOT_TOKEN_HERE",
  "telegram_chat_id": "YOUR_CHAT_ID_HERE",
  "bridge_data_dir": "/full/path/to/ClaudeTelegramBridge/data",
  "auto_approve": ["Read", "Glob", "Grep"],
  "auto_deny": [],
  "timeout_seconds": 300
}
```

**Important:** Set `bridge_data_dir` to the full path of the `data` folder inside this project. For example:
- Windows (via WSL): `/mnt/c/Users/YourName/ClaudeTelegramBridge/data`
- Linux: `/home/yourname/ClaudeTelegramBridge/data`
- macOS: `/Users/yourname/ClaudeTelegramBridge/data`

#### 5c. Register hooks in Claude Code settings

Edit `~/.claude/settings.json` (create it if it doesn't exist):

```json
{
  "hooks": {
    "PermissionRequest": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/hooks/telegram_approver.py"
          }
        ]
      }
    ],
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/hooks/response_sender.py"
          }
        ]
      }
    ]
  }
}
```

### Step 6: Create the data directory

```bash
mkdir -p data
```

### Step 7: Run the Bridge

1. **Start Claude Code** in one terminal:
   ```bash
   claude
   ```

2. **Start the bridge** in another terminal:
   ```bash
   python telegram_bridge.py
   ```

3. **Keep the Claude Code terminal focused** (the bridge types using keyboard simulation)

4. **Send a message from Telegram** to your bot - it will appear in Claude Code!

## Usage

### Telegram Commands

| Command | Description |
|---------|-------------|
| `/plan` | Toggle Plan Mode on/off |
| `/stop` | Stop the bridge |
| (any text) | Send as prompt to Claude |

### Permission Requests

When Claude wants to use a tool (like editing a file), you'll receive a message with:
- Tool name and details
- **Allow** ✅ and **Deny** ❌ buttons

Just tap to respond!

### Auto-Approve/Deny

Configure which tools are automatically approved or denied in `config.json`:

```json
{
  "auto_approve": ["Read", "Glob", "Grep"],
  "auto_deny": ["Bash"]
}
```

## Troubleshooting

### "Config not found" error
Make sure you've copied `config.example.json` to `config.json` and filled in your credentials.

### Messages not typing into Claude Code
- Make sure the Claude Code terminal window is **focused**
- The bridge uses keyboard simulation - it types into whatever window is active

### 409 Conflict error
This happens if multiple scripts poll Telegram simultaneously. Make sure only one bridge is running.

### Hooks not firing
- Restart Claude Code after modifying `settings.json`
- Check that Python 3 is available: `python3 --version`
- Check hook paths are correct in settings.json

### Permission request times out
Increase `timeout_seconds` in both config files (default is 300 seconds / 5 minutes).

## Architecture

```
┌─────────────┐     polls      ┌──────────────┐
│  Telegram   │ ◄───────────── │ telegram_    │
│    Bot      │                │ bridge.py    │ (background)
└─────────────┘ ───────────────► │              │
                  messages      └──────┬───────┘
                                       │ keyboard simulation
                                       ▼
                               ┌──────────────┐
                               │ Claude Code  │
                               │    CLI       │
                               └──────────────┘
                                       │ hooks
                                       ▼
                               ┌──────────────┐
                               │ telegram_    │
                               │ approver.py  │ (permission requests)
                               │              │
                               │ response_    │
                               │ sender.py    │ (Claude responses)
                               └──────────────┘
```

## File Structure

```
ClaudeTelegramBridge/
├── telegram_bridge.py      # Main bridge script (run this)
├── config.json             # Bridge config (don't commit!)
├── config.example.json     # Template for bridge config
├── hooks/
│   ├── telegram_approver.py    # Permission request hook
│   ├── response_sender.py      # Response sender hook
│   ├── config.json             # Hooks config (don't commit!)
│   └── config.example.json     # Template for hooks config
├── data/                   # State files (auto-created)
│   ├── callbacks/          # Permission response files
│   ├── thinking_msg_id.txt # Current "Thinking..." message ID
│   └── plan_mode_state.txt # Plan mode toggle state
├── .gitignore
└── README.md
```

## Why Two Config Files?

| Config | Used By | Runs On |
|--------|---------|---------|
| `config.json` | `telegram_bridge.py` | Windows/your OS |
| `hooks/config.json` | Hook scripts | WSL/Linux (via Claude Code) |

The hooks run inside Claude Code's environment (typically WSL on Windows), while the bridge runs directly on your OS. They need to share data through the `data/` folder, so the hooks config has an extra `bridge_data_dir` field to locate it.

**Both configs need the same `telegram_bot_token` and `telegram_chat_id`!**

## Security Notes

- **Never commit** `config.json` files - they contain your bot token!
- The bot token gives full access to your Telegram bot
- Only share your chat ID with trusted bots
- Consider using a dedicated bot for this purpose

## License

MIT License - feel free to use and modify!

## Credits

Built with Claude Code 🤖
