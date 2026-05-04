# YouTube Automation Agent

Automatically transcribes new YouTube uploads → generates viral titles, descriptions & thumbnails → publishes everything back to your channel.

---

## What APIs You Need (only 2, both free)

| API | Cost | Credit Card? | What it does |
|-----|------|-------------|--------------|
| **Groq API** | Free | Never | Generates titles, descriptions, tags |
| **YouTube Data API v3** | Free | Never | Updates your video automatically |

**Thumbnails use Pollinations AI — no account, no API key, no credit card, completely unlimited. It just works.**

---

## Step-by-Step Setup

### Step 1 — Add your Groq API key
You already have this. Open `agent.py` and paste it where it says `YOUR_GROQ_API_KEY_HERE`.

---

### Step 2 — Get YouTube Data API credentials (free, no card)

1. Go to **https://console.cloud.google.com**
2. Click **"Create Project"** → name it `YouTube Agent` → click Create
3. In the top search bar type **YouTube Data API v3** → click it → click **Enable**
4. In the left sidebar click **Credentials**
5. Click **+ Create Credentials** → choose **OAuth Client ID**
6. If it asks you to configure a consent screen first:
   - User Type: **External** → Create
   - App name: `YouTube Agent`, enter your email → Save and Continue
   - Skip the Scopes page → Save and Continue
   - Add your own Gmail as a **Test User** → Save
7. Now create the OAuth Client ID:
   - Application type: **Desktop App** → Name: `YouTube Agent` → Create
8. Click **Download JSON** → rename the file to `client_secret.json`
9. Put that file inside the `credentials/` folder in this project

---

### Step 3 — Get your YouTube Channel ID

1. Go to **https://studio.youtube.com**
2. Click **Settings** (gear icon, bottom left) → **Channel** → **Advanced Settings**
3. Copy your Channel ID (starts with `UC...`)
4. Paste it into `agent.py` where it says `YOUR_YOUTUBE_CHANNEL_ID_HERE`

---

### Step 4 — Describe your channel (important for quality)

Open `agent.py` and fill in the `CHANNEL_CONTEXT` at the top:

```python
CHANNEL_CONTEXT = """
This is a tech tutorials YouTube channel.
The audience is beginners learning Python and AI.
Tone: friendly, energetic, educational.
Always write titles that create curiosity and urgency.
"""
```

This is what makes titles sound like YOU, not generic AI output.

---

### Step 5 — Install and Run

```bash
# Install everything (run once)
bash setup.sh

# Start the agent
python agent.py
```

First run: a browser opens → log into Google → click Allow. The agent then runs forever, checking every 10 minutes for new uploads.

---

## How it works

```
You upload a video to YouTube
        ↓
Agent detects it (polls every 10 min)
        ↓
yt-dlp downloads the audio
        ↓
Whisper transcribes it (runs on your laptop, fully private)
        ↓
Groq LLaMA 70B generates:
   5 title options + picks the best one
   Full description with hook + CTA
   25 SEO tags
   Thumbnail concept (text, mood, background scene)
        ↓
Pollinations AI generates a cinematic background image
   (free, no account, no key, no daily limit)
        ↓
Bold outlined text burned onto the thumbnail (pro YouTuber style)
        ↓
YouTube Data API updates: new title + description + thumbnail
        ↓
Live on YouTube. Done. ✅
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Whisper slow on first run | Downloads a ~140MB model once. Normal. |
| Google popup doesn't appear | Run from a terminal, not an IDE |
| YouTube `quotaExceeded` | Free = 10,000 units/day. One video update = ~50 units. You're safe. |
| Thumbnail takes a while | Pollinations needs 30–60 sec to generate. Script waits automatically. |
