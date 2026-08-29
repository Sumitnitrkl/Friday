# 🤖 FRIDAY — Personal AI Voice Assistant

> A warm, always-on voice assistant for Windows and macOS. Say the wake word,
> talk naturally, and FRIDAY uses **Google Gemini with function calling** to
> actually *do things* on your computer — it's an agent, not a fixed command list.

---

## ✨ What it can do

Talk to it naturally — Gemini decides which of its tools to use, and can chain
several in one request ("open Chrome **and** tell me the weather").

| Category | Examples |
|---|---|
| **Apps** | "open WhatsApp" · "close Spotify" · "launch VS Code" (opens Store apps too) |
| **Web & info** | "search the web for the iPhone 16 price" · "what's the weather in Delhi?" · "what time is it?" |
| **System** | "set volume to 40" · "mute" · "brightness up" · "turn wifi off" · "battery status" |
| **Media** | "play" · "pause" · "next track" |
| **Files** | "make a folder called Projects on my desktop" · "open my downloads folder" |
| **Screen & power** | "take a screenshot" · "lock the screen" · "shut down the computer" |
| **Productivity** | "remind me in 20 minutes to join standup" · "add buy milk to my list" · "read my to-do list" · "take a note" |
| **Type & run** | "type my email address" · "run git status" |
| **Anything else** | full conversational AI — "explain black holes in one line", "write a birthday message" |

Say **"stop listening"** or **"go to sleep"** to pause it (or press Ctrl+C).
After a reply you can keep talking for a couple of turns without repeating the wake word.

---

## 🚀 Setup (5 minutes)

### 1. Install Python 3.10+ and dependencies
```bash
pip install -r requirements.txt
```
If **PyAudio** fails (it's the mic driver):
- **Windows:** `pip install pipwin && pipwin install pyaudio`
- **macOS:** `brew install portaudio && pip install pyaudio`
- **Linux:** `sudo apt install portaudio19-dev python3-pyaudio && pip install pyaudio`

Windows extras for volume/brightness: `pip install pycaw comtypes wmi`

### 2. Add your FREE Gemini API key
Get one (no credit card) at **https://aistudio.google.com/apikey**, then copy
`.env.example` to `.env` and paste it:
```
GEMINI_API_KEY=your_key_here
```
`.env` is gitignored — your key never gets committed.

### 3. Run it
```bash
python main.py          # terminal
python main.py --ui     # + holographic HUD in your browser
```
Wait for "FRIDAY online", then say: **"Hey FRIDAY, what can you do?"**

---

## 🖥️ The Holographic HUD (`--ui`)

Run with `--ui` and FRIDAY opens a cinematic JARVIS-style interface in your
browser — a glowing reactive energy core, rotating holographic rings, orbiting
particles, a live clock, and captions of what you said and what FRIDAY replies.
It reacts in real time to FRIDAY's actual state:

| State | What you see |
|---|---|
| **Standby** | slow cyan breathing core |
| **Listening** | green, expanding rings + reactive waveform |
| **Processing** | amber, fast spin |
| **Speaking** | cyan waveform pulses while the reply types out |

**Click the core** (or say the wake word) to start talking. The HUD is served
locally at `http://127.0.0.1:8760`; nothing leaves your machine. It's plain
HTML/JS ([ui/index.html](ui/index.html)) driven over a WebSocket by
[ui/server.py](ui/server.py), so you can restyle it freely.

---

## 🧠 How it works

```
your voice ─▶ microphone (SpeechRecognition + Google STT)  → core/listener.py
           ─▶ Gemini with function calling                  → core/brain.py
              (it picks & runs tools automatically)          → skills/tools.py
           ─▶ reply spoken in a natural neural voice         → core/speaker.py
```

- **Brain:** Google Gemini (`gemini-3.5-flash-lite` by default) with automatic
  function calling over every tool in `skills/tools.py`.
- **Ears:** Google's free speech recognizer (needs internet, no ffmpeg).
- **Voice:** Microsoft Edge neural TTS (free), played via `pygame`.
- **Everything is free** — just needs internet and a free Gemini key.

---

## ⚙️ Customizing (`config.yaml`)

```yaml
assistant:
  wake_words: ["hey friday", "friday", "ok friday"]   # rename to anything
  followup_window: 2                                   # turns without re-waking

voice:
  edge_tts_voice: "en-US-JennyNeural"   # try en-IN-NeerjaNeural, en-GB-SoniaNeural
                                        # list all: edge-tts --list-voices

ai:
  gemini_model: "gemini-3.5-flash-lite" # smarter: gemini-2.5-flash / gemini-3.6-flash
  personality: >                        # edit to change how FRIDAY talks + behaves
    You are FRIDAY, a warm, friendly assistant...
```

> **Note on models:** the free tier is rate-limited per minute. `flash-lite` has
> the most generous limit (best for voice). Bigger models are smarter but you'll
> hit "give me a few seconds" more often.

---

## 🛠️ Add a new power (this is the magic)

Adding a capability is one function — Gemini figures out when to use it:

```python
# in skills/tools.py
def flip_a_coin() -> str:
    """Flip a coin and return heads or tails."""
    import random
    return random.choice(["Heads.", "Tails."])

# then add it to the list at the bottom:
ALL_TOOLS = [ ..., flip_a_coin ]
```

That's it — say "flip a coin" and it works. Write clear type hints and a good
docstring; that's what Gemini reads to decide when and how to call your tool.

---

## 📁 Project structure

```
FRIDAY/
├── main.py               ← entry point (loads .env, starts the loop)
├── config.yaml           ← all settings + personality
├── core/
│   ├── assistant.py      ← wake-word loop, follow-ups, reminders
│   ├── listener.py       ← speech-to-text (Google)
│   ├── speaker.py        ← neural TTS + pygame playback
│   └── brain.py          ← Gemini function-calling brain
├── skills/
│   ├── tools.py          ← ★ the tools Gemini can call (add powers here)
│   ├── apps.py           ← open/close apps (Store apps via AppUserModelID)
│   ├── system.py         ← volume, brightness, wifi, bluetooth, power, screenshot
│   ├── filesystem.py     ← file create/open/delete/move
│   ├── browser.py        ← web search / open URL
│   └── media_info_terminal.py ← media keys, time, weather, run command
└── utils/network.py      ← online/offline detection
```

---

## 🔧 Troubleshooting

- **It doesn't hear me** — lower `energy_threshold` in `config.yaml` (try 150); check mic permission for your terminal.
- **It hears random noise** — raise `energy_threshold` (try 600+).
- **"I'm getting a lot of requests"** — free-tier rate limit; wait a few seconds, or switch to a `flash-lite` model.
- **"My API key seems missing/invalid"** — check `GEMINI_API_KEY` in `.env`.
- **No voice** — needs internet for the neural voice; it falls back to the offline voice. Replies always print too.
- Speech recognition, the neural voice, and Gemini all need internet.
