# 🤖 FRIDAY — Personal AI Voice Assistant

> Warm, casual, always-on voice assistant for macOS and Windows.
> Fully offline capable with online enhancements.

---

## ✨ Features

| Category | What you can say |
|---|---|
| **Apps** | "Open Chrome" · "Close Spotify" · "Launch VS Code" |
| **Web** | "Search for Python tutorials" · "Open github.com" |
| **Files** | "Create a folder called Projects on Desktop" · "Move Downloads to Desktop" |
| **System** | "Volume up" · "Mute" · "Brightness down" · "WiFi off" |
| **Media** | "Play" · "Pause" · "Next track" · "Previous song" |
| **Info** | "What time is it?" · "What's the weather in London?" |
| **Terminal** | "Run git status" · "Check disk space" |
| **Reminders** | "Set a reminder to call John at 3pm" |
| **Screen** | "Take a screenshot" · "Lock the screen" |
| **Power** | "Sleep" · "Restart" · "Shut down" |

---

## 🚀 Quick Start

### 1. Install dependencies

```bash
# macOS prerequisites
brew install ffmpeg portaudio mpg123

# All platforms
pip install -r requirements.txt
```

### 2. Set your Claude API key (for best AI understanding)

```bash
# macOS/Linux
export ANTHROPIC_API_KEY="your-key-here"

# Windows
set ANTHROPIC_API_KEY=your-key-here
```

Or edit `config.yaml` → `ai.claude_api_key`.

### 3. Run FRIDAY

```bash
python main.py
```

### 4. Install for auto-start on boot

```bash
python setup_autostart.py
```

---

## 🎙️ Wake Words

Say any of these to activate FRIDAY:
- **"Hey FRIDAY"**
- **"FRIDAY"**
- **"OK FRIDAY"**

Then speak your command naturally.

**Example:**
> "Hey FRIDAY, open Chrome and search for the weather"

---

## 🧠 AI Backends

| Mode | Engine | Requires |
|---|---|---|
| Online (best) | Claude API | `ANTHROPIC_API_KEY` |
| Offline (local AI) | Ollama + Llama 3 | [Install Ollama](https://ollama.ai) + `ollama pull llama3` |
| Fallback | Rule-based | Nothing — always works |

FRIDAY automatically picks the best available backend.

---

## 🔊 Voice Engines

| Mode | Engine | Voice |
|---|---|---|
| Online | edge-tts | Emily (Irish English — warm, natural) |
| Offline | pyttsx3 | System TTS voice |

---

## 📁 Project Structure

```
FRIDAY/
├── main.py                 ← Entry point
├── config.yaml             ← All settings
├── requirements.txt        ← Dependencies
├── setup_autostart.py      ← Boot integration
├── core/
│   ├── assistant.py        ← Main loop & orchestration
│   ├── listener.py         ← Speech-to-text (Whisper + Google)
│   ├── speaker.py          ← Text-to-speech (edge-tts + pyttsx3)
│   └── brain.py            ← AI intent parser (Claude + Ollama)
├── skills/
│   ├── dispatcher.py       ← Routes intents to skills
│   ├── apps.py             ← Open/close applications
│   ├── browser.py          ← Web search & URLs
│   ├── filesystem.py       ← File operations
│   ├── system.py           ← Volume, brightness, power
│   ├── media.py            ← Music/media control
│   ├── info.py             ← Time, weather, reminders
│   └── terminal.py         ← Shell commands
└── utils/
    └── network.py          ← Online/offline detection
```

---

## ⚙️ Configuration (`config.yaml`)

Key settings to customize:

```yaml
A:
  name: "FRIDAY"
  wake_words: ["hey friday", "friday"]

voice:
  edge_tts_voice: "en-IE-EmilyNeural"   # Change voice here
  pyttsx3_rate: 175                       # Speech speed

ai:
  claude_api_key: "sk-ant-..."           # Or use env var
  ollama_model: "llama3"                 # Local model name

speech:
  whisper_model: "base"                  # tiny=fast, medium=accurate
```

---

## 🛠️ Adding Custom Skills

1. Create a function in the appropriate `skills/` file:
```python
def my_skill(params: dict) -> str:
    # do something
    return "Done!"
```

2. Add it to `skills/dispatcher.py` SKILL_MAP:
```python
"my_intent": my_skill,
```

3. Update the AI system prompt in `core/brain.py` to recognize the new intent.

---

## 🔒 Privacy

- Whisper STT runs **100% locally** — your voice never leaves your machine
- Offline mode with Ollama means **zero cloud dependency**
- No conversation data is stored permanently

---

## 📋 Platform Notes

### macOS
- Microphone permission: System Preferences → Privacy → Microphone
- Accessibility permission (for GUI automation): System Preferences → Privacy → Accessibility
- `brightness` CLI: `brew install brightness`
- Bluetooth control: `brew install blueutil`

### Windows
- Run as Administrator for brightness/bluetooth control
- `pyaudio` installation: `pip install pipwin && pipwin install pyaudio`
- Volume control: `pip install pycaw`
- Add `ffmpeg` to PATH for audio playback
