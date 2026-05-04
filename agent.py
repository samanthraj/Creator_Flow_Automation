"""
YouTube Automation Agent — PREMIUM QUALITY MODE
================================================
Goal: Every video gets a VIRAL-worthy title, description, and thumbnail.
      Not just good enough. Top notch. Clickable. Professional.

Stack (all free, no credit card):
  - Groq (LLaMA 3.3 70B) — content generation
  - Whisper (local)       — transcription
  - Pollinations AI       — thumbnail image (no key, no card, unlimited)
  - Pillow                — thumbnail text overlay (bold, high contrast)
  - YouTube Data API v3   — publish back to channel
"""

import os, json, time, subprocess, requests, pickle, re
from pathlib import Path
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from groq import Groq
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from dotenv import load_dotenv
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
# ═══════════════════════════════════════════════════════════
#  CONFIG  —  fill these in before running
# ═══════════════════════════════════════════════════════════
FFMPEG_BIN = r"C:/Users/garel/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-8.1-full_build\bin"
os.environ["PATH"] = FFMPEG_BIN + os.pathsep + os.environ["PATH"]


YOUTUBE_CHANNEL_ID = "UCmbxowEZpaYELbM7ed6Fdcw"

# Describe your channel so the AI writes in YOUR style
CHANNEL_CONTEXT = """
This is a [YOUR NICHE, e.g. 'tech tutorials'] YouTube channel.
The audience is [WHO WATCHES, e.g. 'beginners learning Python'].
Tone: [e.g. energetic / educational / funny / professional].
Always write titles that create curiosity and urgency.
"""

SCOPES        = ["https://www.googleapis.com/auth/youtube.force-ssl"]
CREDS_FILE    = "credentials/client_secret.json"
TOKEN_FILE    = "credentials/token.pickle"
SEEN_FILE     = "logs/seen_videos.json"
THUMBNAIL_DIR = Path("thumbnails")
THUMBNAIL_DIR.mkdir(exist_ok=True)
Path("logs").mkdir(exist_ok=True)

# ── YOUR FACE PHOTOS ────────────────────────────────────────
# Create a folder called "my_photos" inside youtube_agent/
# Drop ALL your photos in there — the more the better.
# The agent picks the best one for each thumbnail automatically.
#
# Tips for good photos:
#   - Good lighting (natural light or ring light)
#   - Different expressions: neutral, happy, surprised, serious
#   - Waist-up or full body (not just face close-ups)
#   - Simple or plain background (helps rembg cut you out cleaner)
#   - Supported: .jpg .jpeg .png .webp
#
FACE_PHOTOS_DIR = "my_photos"   # folder name — put all your photos here


# ═══════════════════════════════════════════════════════════
#  YOUTUBE AUTH
# ═══════════════════════════════════════════════════════════
def get_youtube_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)
    return build("youtube", "v3", credentials=creds)


# ═══════════════════════════════════════════════════════════
#  STEP 1 — DETECT NEW VIDEOS
# ═══════════════════════════════════════════════════════════
def get_latest_videos(youtube, max_results=5):
    res = youtube.search().list(
        part="snippet", channelId=YOUTUBE_CHANNEL_ID,
        order="date", type="video", maxResults=max_results
    ).execute()
    return [
        {
            "video_id":  item["id"]["videoId"],
            "title":     item["snippet"]["title"],
            "published": item["snippet"]["publishedAt"]
        }
        for item in res.get("items", [])
    ]

def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f:
            return set(json.load(f))
    return set()

def mark_seen(video_id):
    seen = load_seen()
    seen.add(video_id)
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)


# ═══════════════════════════════════════════════════════════
#  STEP 2 — DOWNLOAD AUDIO
# ═══════════════════════════════════════════════════════════
def download_audio(video_id):
    url = f"https://www.youtube.com/watch?v={video_id}"
    Path("temp").mkdir(exist_ok=True)
    out = f"temp/{video_id}.%(ext)s"

    print("  Downloading audio...")
    subprocess.run(
        [
            "yt-dlp",
            "--ffmpeg-location",
            r"C:/Users/garel/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-8.1-full_build/bin",
            "-x",
            "--audio-format", "mp3",
            "-o", out,
            url
        ],
        check=True
    )

    return f"temp/{video_id}.mp3"


# ═══════════════════════════════════════════════════════════
#  STEP 3 — TRANSCRIBE (local Whisper, free & private)
# ═══════════════════════════════════════════════════════════
def transcribe(audio_path):
    print("  Transcribing with Whisper (runs locally on your machine)...")
    import whisper
    model = whisper.load_model("small")  # small = great accuracy + speed balance
    result = model.transcribe(audio_path, fp16=False)
    text = result["text"].strip()
    print(f"  Transcript ready: {len(text)} characters")
    return text


# ═══════════════════════════════════════════════════════════
#  STEP 4 — GENERATE VIRAL CONTENT WITH GROQ
# ═══════════════════════════════════════════════════════════

CONTENT_PROMPT = """
You are a YouTube growth expert who has scaled channels to millions of subscribers.
You are also a master copywriter who knows exactly what makes people stop scrolling and click.

CHANNEL CONTEXT:
{channel_context}

VIDEO DETAILS:
Original title: "{original_title}"
Transcript:
---
{transcript}
---

YOUR JOB: Generate the absolute best title, description, and thumbnail for this video.

═══ TITLE RULES ═══
- Max 70 characters (YouTube cuts off longer titles)
- Use psychological triggers: curiosity gap, urgency, self-interest, social proof
- Power words that work: Secret, Finally, Why, Nobody, You, How, This Changed, Honest, Truth
- Numbers work great ("7 Mistakes", "This 1 Thing")
- Speak to the viewer directly ("You", "Your")  
- The title MUST match what the video delivers — no bait and switch
- Think: a stranger scrolling YouTube at 2am — would they click this?

═══ DESCRIPTION RULES ═══
- First 2 lines are the HOOK — most interesting thing, no "In this video"
- Use timestamps if the transcript reveals distinct sections
- Include a strong call to action at the end
- Add 5-7 relevant hashtags at the very bottom

═══ THUMBNAIL TEXT RULES ═══
- 2-5 words MAX — huge, bold, readable on a phone screen
- Emotional or shocking — create desire to know more
- Works WITH the background image, not against it
- Think: what 3-word phrase would make someone stop scrolling?

Generate 5 title options, then pick the BEST one.

Respond ONLY with valid JSON (no markdown, no code fences):
{{
  "titles": ["title1", "title2", "title3", "title4", "title5"],
  "best_title": "the single best title here",
  "why_best": "one sentence explaining why this title wins",
  "description": "the full YouTube description here",
  "tags": ["tag1", "tag2", "tag3", ... up to 25 tags],
  "thumbnail": {{
    "main_text": "3-5 WORD HOOK",
    "sub_text": "optional smaller text or empty string",
    "background_scene": "detailed description: what setting, lighting, mood, colors",
    "style": "dark dramatic OR bright energetic OR clean minimal OR neon OR cinematic",
    "include_person": true or false,
    "person_expression": "shocked / excited / serious / smiling / thinking (or null)"
  }}
}}
"""

def generate_content(transcript, original_title):
    client = Groq(api_key=GROQ_API_KEY)
    prompt = CONTENT_PROMPT.format(
        channel_context=CHANNEL_CONTEXT,
        original_title=original_title,
        transcript=transcript[:5000]
    )
    print("  Asking Groq LLaMA 70B to generate viral content...")
    res = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.85,
        max_tokens=2500
    )
    raw = res.choices[0].message.content.strip()
    # Strip any accidental markdown fences
    raw = re.sub(r"^```[a-z]*\n?", "", raw).rstrip("```").strip()

    data = json.loads(raw)
    print(f"\n  All 5 titles generated:")
    for i, t in enumerate(data["titles"], 1):
        star = " <-- BEST" if t == data["best_title"] else ""
        print(f"    {i}. {t}{star}")
    print(f"\n  Thumbnail text: '{data['thumbnail']['main_text']}'")
    print(f"  Why this title wins: {data.get('why_best','')}")
    return data


# ═══════════════════════════════════════════════════════════
#  STEP 5 — GENERATE PREMIUM THUMBNAIL
#
#  Three-step process:
#  1. Pollinations AI generates a cinematic background (free, unlimited)
#  2. Your face photo is cut out and placed on the RIGHT side
#  3. Bold text is burned on the LEFT side
#
#  Layout: [ BIG TEXT | YOUR FACE ]  — exactly like top YouTubers
# ═══════════════════════════════════════════════════════════

def build_image_prompt(thumb: dict) -> str:
    style_details = {
        "dark dramatic":    "cinematic dark background, dramatic shadows, volumetric lighting, deep blacks, 8K quality",
        "bright energetic": "vibrant saturated colors, high energy composition, dynamic angles, bright and punchy",
        "clean minimal":    "clean light background, minimalist design, professional, lots of negative space",
        "neon":             "neon glowing elements, cyberpunk aesthetic, dark background, electric colors",
        "cinematic":        "cinematic widescreen composition, film-grade color grading, professional photography",
    }
    style = style_details.get(thumb.get("style", "dark dramatic"),
                              "cinematic high quality professional")
    return (
        f"YouTube thumbnail background image. {style}. "
        f"{thumb.get('background_scene', '')}. "
        f"NO people, NO faces, NO text, NO watermarks. "
        f"Left 55% slightly darker for bold text overlay. "
        f"Right 45% open space for a person cutout to be composited later. "
        f"Ultra detailed, professional YouTube thumbnail, 16:9 composition."
    )


def get_background_image(prompt: str) -> Image.Image:
    print("  Generating cinematic background with Pollinations AI (free, no limits)...")
    encoded = requests.utils.quote(prompt)
    seed = int(time.time()) % 99999
    url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width=1280&height=720&nologo=true&enhance=true&seed={seed}"
    )
    res = requests.get(url, timeout=90)
    res.raise_for_status()
    img = Image.open(BytesIO(res.content)).convert("RGB")
    print(f"  Background received: {img.size[0]}x{img.size[1]}")
    return img


def remove_background_from_photo(photo_path: str) -> Image.Image:
    """
    Removes background using rembg. Caches the cutout so rembg only
    runs ONCE per photo — not every time a thumbnail is generated.
    Cache lives in my_photos/cutouts/
    """
    cache_dir  = Path(FACE_PHOTOS_DIR) / "cutouts"
    cache_dir.mkdir(exist_ok=True)
    cache_path = cache_dir / (Path(photo_path).stem + "_cutout.png")

    # Return cached cutout if it exists
    if cache_path.exists():
        return Image.open(str(cache_path)).convert("RGBA")

    try:
        from rembg import remove as rembg_remove
        print(f"  Removing background: {Path(photo_path).name} (caching for next time)...")
        with open(photo_path, "rb") as f:
            raw = f.read()
        result = rembg_remove(raw)
        img = Image.open(BytesIO(result)).convert("RGBA")
        img.save(str(cache_path), "PNG")
        print(f"  Background removed and cached: {cache_path.name}")
        return img
    except ImportError:
        print("  TIP: pip install rembg onnxruntime — for cleaner face cutouts")
        return Image.open(photo_path).convert("RGBA")
    except Exception as e:
        print(f"  Background removal error ({e}) — using original photo.")
        return Image.open(photo_path).convert("RGBA")


def get_all_face_photos() -> list:
    """
    Returns all photo paths from the my_photos folder.
    Skips the cutouts subfolder.
    """
    photos_dir = Path(FACE_PHOTOS_DIR)
    if not photos_dir.exists():
        print(f"  No '{FACE_PHOTOS_DIR}' folder found.")
        print(f"  Create it and add your photos: youtube_agent/my_photos/")
        return []
    exts   = {".jpg", ".jpeg", ".png", ".webp"}
    photos = [
        str(p) for p in photos_dir.iterdir()
        if p.suffix.lower() in exts and p.parent.name != "cutouts"
    ]
    print(f"  Found {len(photos)} photo(s) in {FACE_PHOTOS_DIR}/")
    return photos


def pick_best_photo(thumb_style: str) -> str | None:
    """
    Picks the best photo from your folder based on thumbnail style.
    - Dark/dramatic styles  → picks photo with most contrast (expressive face)
    - Bright/energetic      → picks brightest photo
    - Falls back to random if only 1 photo
    """
    import random
    import numpy as np

    photos = get_all_face_photos()
    if not photos:
        return None
    if len(photos) == 1:
        return photos[0]

    # Score each photo
    scored = []
    for path in photos:
        try:
            img  = Image.open(path).convert("RGB")
            arr  = np.array(img).astype(float)
            brightness = float(arr.mean())
            contrast   = float(arr.std())
            scored.append((path, brightness, contrast))
        except Exception:
            scored.append((path, 128, 50))

    style = thumb_style.lower()
    if "dark" in style or "dramatic" in style or "cinematic" in style:
        # Pick highest contrast photo — most expressive, stands out on dark bg
        best = max(scored, key=lambda x: x[2])
    elif "bright" in style or "energetic" in style:
        # Pick brightest photo — pops on light background
        best = max(scored, key=lambda x: x[1])
    else:
        # Random from top 3 most contrasted — keeps thumbnails varied
        top3 = sorted(scored, key=lambda x: x[2], reverse=True)[:3]
        best = random.choice(top3)

    print(f"  Selected photo: {Path(best[0]).name} (brightness={best[1]:.0f}, contrast={best[2]:.0f})")
    return best[0]


def composite_face(canvas: Image.Image, thumb_style: str = "dark dramatic") -> Image.Image:
    """
    Places your face on the RIGHT side of the thumbnail.
    Picks the best photo from your my_photos/ folder automatically.
    Caches background removal so rembg only runs once per photo.
    Adds white glow outline for that pro YouTube look.
    """
    photo_path = pick_best_photo(thumb_style)
    if not photo_path:
        print("  Skipping face composite — add photos to my_photos/ folder")
        return canvas

    face_rgba = remove_background_from_photo(photo_path)

    # Scale face to ~95% of thumbnail height
    target_h  = int(canvas.height * 0.95)
    scale     = target_h / face_rgba.height
    target_w  = int(face_rgba.width * scale)
    face_rgba = face_rgba.resize((target_w, target_h), Image.LANCZOS)

    # Pin to right edge, slight overlap, grounded at bottom
    x = canvas.width - target_w + 15
    y = canvas.height - target_h - 5

    # White glow effect around the person (pro thumbnail look)
    gw = int(target_w * 1.025)
    gh = int(target_h * 1.025)
    glow_img = face_rgba.resize((gw, gh), Image.LANCZOS)
    r, g, b, a = glow_img.split()
    white_glow = Image.merge("RGBA", (
        Image.new("L", glow_img.size, 255),
        Image.new("L", glow_img.size, 255),
        Image.new("L", glow_img.size, 255),
        Image.eval(a, lambda px: int(px * 0.40))
    ))
    glow_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    glow_layer.paste(white_glow, (x - int(target_w * 0.012), y - int(target_h * 0.012)), white_glow)
    canvas = Image.alpha_composite(canvas, glow_layer)

    # Paste actual face
    face_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    face_layer.paste(face_rgba, (x, y), face_rgba)
    canvas = Image.alpha_composite(canvas, face_layer)

    print(f"  Your face composited on the right side ({target_w}x{target_h}px)")
    return canvas


def burn_text_on_thumbnail(img: Image.Image, thumb: dict) -> Image.Image:
    """
    Burns bold text on the LEFT side of the thumbnail.
    Your face is on the right, text is on the left — classic YouTube layout.
    """
    draw = ImageDraw.Draw(img)

    main_text = thumb.get("main_text", "").upper()
    sub_text  = thumb.get("sub_text", "").upper()

    bold_fonts = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "C:/Windows/Fonts/arialbd.ttf",
    ]
    font_path = next((fp for fp in bold_fonts if os.path.exists(fp)), None)

    def get_font(size):
        if font_path:
            try: return ImageFont.truetype(font_path, size=size)
            except: pass
        return ImageFont.load_default()

    # Text fills the LEFT 58% of the thumbnail (right side reserved for face)
    TEXT_ZONE_W = 700   # left 700px out of 1280
    TEXT_MARGIN = 50    # left margin

    def best_font_size(text, max_w, start_size=130, min_size=60):
        for size in range(start_size, min_size - 1, -4):
            f = get_font(size)
            bbox = draw.textbbox((0, 0), text, font=f)
            if (bbox[2] - bbox[0]) <= max_w:
                return f, size
        return get_font(min_size), min_size

    words = main_text.split()
    if len(words) > 3:
        mid   = len(words) // 2
        lines = [" ".join(words[:mid]), " ".join(words[mid:])]
    else:
        lines = [main_text]

    longest           = max(lines, key=len)
    font_main, fsize  = best_font_size(longest, TEXT_ZONE_W - TEXT_MARGIN)
    line_height       = int(fsize * 1.15)
    total_h           = line_height * len(lines) + (int(fsize * 0.6) if sub_text else 0) + 20
    text_y            = 720 - total_h - 50   # anchor to bottom-left

    # Dark gradient on left side for text readability
    overlay   = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
    grad_draw = ImageDraw.Draw(overlay)
    fade_y    = max(text_y - 80, 350)
    for y in range(fade_y, 720):
        alpha = int(185 * ((y - fade_y) / (720 - fade_y)))
        grad_draw.rectangle([(0, y), (TEXT_ZONE_W + 80, y)], fill=(0, 0, 0, alpha))
    img  = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    def draw_outlined(draw, x, y, text, font, fill, outline_px=7):
        for dx in range(-outline_px, outline_px + 1, 2):
            for dy in range(-outline_px, outline_px + 1, 2):
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy), text, font=font, fill=(0, 0, 0))
        draw.text((x, y), text, font=font, fill=fill)

    y = text_y
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font_main)
        # Left-align text in the left zone
        x = TEXT_MARGIN
        draw_outlined(draw, x, y, line, font_main, fill=(255, 245, 0), outline_px=7)
        y += line_height

    if sub_text:
        font_sub = get_font(max(fsize // 2, 40))
        draw_outlined(draw, TEXT_MARGIN, y + 8, sub_text, font_sub,
                      fill=(255, 255, 255), outline_px=4)

    return img



# ═══════════════════════════════════════════════════════════
#  THUMBNAIL CRITIC AGENT
#  Analyses the finished thumbnail image and checks:
#  1. Is your face clearly visible? (right side brightness check)
#  2. Is the text readable? (contrast ratio on left side)
#  3. Is the overall brightness good? (not too dark/washed out)
#  4. If any check fails — rewrites the prompt and regenerates
#  Max 2 retry attempts before accepting best result.
# ═══════════════════════════════════════════════════════════

def analyse_thumbnail(image_path: str) -> dict:
    """
    Pixel-level analysis of the finished thumbnail.
    Returns scores and pass/fail for each check.
    """
    img  = Image.open(image_path).convert("RGB")
    w, h = img.size  # should be 1280x720

    # ── Zone 1: Left 55% — text area ──
    left_zone  = img.crop((0, 0, int(w * 0.55), h))
    # ── Zone 2: Right 45% — face area ──
    right_zone = img.crop((int(w * 0.55), 0, w, h))
    # ── Bottom strip: where text lives ──
    text_zone  = img.crop((0, int(h * 0.55), int(w * 0.55), h))

    def avg_brightness(zone):
        import numpy as np
        arr = np.array(zone)
        return float(arr.mean())

    def contrast_score(zone):
        """Checks if dark and light pixels coexist — sign of readable text on bg"""
        import numpy as np
        arr = np.array(zone).astype(float)
        return float(arr.std())

    try:
        import numpy as np
        right_bright  = avg_brightness(right_zone)
        text_contrast  = contrast_score(text_zone)
        overall_bright = avg_brightness(img)

        # Face check: right side should have enough brightness variation
        # (a visible face has lots of contrast, a blank bg does not)
        face_visible   = right_bright > 30 and contrast_score(right_zone) > 25

        # Text check: bottom-left should have high contrast (dark bg + bright text)
        text_readable  = text_contrast > 40

        # Overall brightness: not too dark (<20) not too washed out (>220)
        brightness_ok  = 25 < overall_bright < 210

        score = sum([face_visible, text_readable, brightness_ok])

        results = {
            "face_visible":    face_visible,
            "text_readable":   text_readable,
            "brightness_ok":   brightness_ok,
            "right_brightness": round(right_bright, 1),
            "text_contrast":   round(text_contrast, 1),
            "overall_bright":  round(overall_bright, 1),
            "score":           score,
            "passed":          score >= 2,   # at least 2 of 3 checks must pass
        }
    except ImportError:
        # numpy not installed — skip pixel analysis, just pass
        print("  [Critic] numpy not installed — skipping pixel analysis, accepting thumbnail.")
        results = {
            "face_visible": True, "text_readable": True, "brightness_ok": True,
            "score": 3, "passed": True,
            "right_brightness": 0, "text_contrast": 0, "overall_bright": 0
        }

    return results


def fix_thumbnail_prompt(thumb: dict, critique: dict) -> dict:
    """
    Rewrites the thumbnail concept based on what the critic found wrong.
    Returns an improved thumb dict.
    """
    fixes = []
    if not critique["face_visible"]:
        fixes.append("Make the right side brighter and more contrast-rich so the person stands out clearly")
    if not critique["text_readable"]:
        fixes.append("Make the left background much darker so bold yellow text is highly readable")
    if not critique["brightness_ok"]:
        if critique["overall_bright"] < 25:
            fixes.append("The image is too dark overall — use brighter lighting, more vibrant colors")
        else:
            fixes.append("The image is too washed out — increase contrast, use deeper background colors")

    improved = thumb.copy()
    fix_note = ". ".join(fixes)
    improved["background_scene"] = (
        thumb.get("background_scene", "") +
        f". IMPORTANT FIXES: {fix_note}. "
        f"Left side must be very dark (almost black gradient at bottom) for text. "
        f"Right side must have clear bright area for person cutout."
    )
    improved["style"] = "dark dramatic"   # force dark style on retry
    return improved


def thumbnail_critic_loop(thumb: dict, video_id: str, max_retries: int = 2) -> str:
    """
    Full thumbnail generation with critic loop:
    1. Generate thumbnail
    2. Analyse it
    3. If it fails — fix the prompt and regenerate
    4. Accept best result after max_retries
    """
    best_path  = None
    best_score = -1

    for attempt in range(1, max_retries + 2):   # +2 so we always get at least 1
        print(f"\n  [Thumbnail] Attempt {attempt} of {max_retries + 1}...")

        # Build background
        prompt = build_image_prompt(thumb)
        bg     = get_background_image(prompt)

        # Composite face
        canvas = composite_face(bg.convert("RGBA"), thumb_style=thumb.get("style", "dark dramatic"))

        # Burn text
        final  = burn_text_on_thumbnail(canvas, thumb)

        # Save this attempt
        attempt_path = str(THUMBNAIL_DIR / f"{video_id}_attempt{attempt}.jpg")
        final.save(attempt_path, "JPEG", quality=95)

        # Run critic
        critique = analyse_thumbnail(attempt_path)
        score    = critique["score"]

        print(f"  [Critic] Score: {score}/3 — "
              f"Face: {'OK' if critique['face_visible'] else 'FAIL'} | "
              f"Text: {'OK' if critique['text_readable'] else 'FAIL'} | "
              f"Brightness: {'OK' if critique['brightness_ok'] else 'FAIL'}")

        # Keep best so far
        if score > best_score:
            best_score = score
            best_path  = attempt_path

        if critique["passed"]:
            print(f"  [Critic] Approved on attempt {attempt}!")
            break
        elif attempt <= max_retries:
            print(f"  [Critic] Not good enough — fixing prompt and retrying...")
            thumb = fix_thumbnail_prompt(thumb, critique)
        else:
            print(f"  [Critic] Max retries reached — using best result (score {best_score}/3)")

    # Copy best result to final path
    final_path = str(THUMBNAIL_DIR / f"{video_id}.jpg")
    import shutil
    shutil.copy(best_path, final_path)

    # Clean up attempt files
    for i in range(1, max_retries + 2):
        p = THUMBNAIL_DIR / f"{video_id}_attempt{i}.jpg"
        if p.exists():
            p.unlink()

    size_kb = Path(final_path).stat().st_size // 1024
    print(f"  [Thumbnail] Final saved: {final_path} ({size_kb} KB, score {best_score}/3)")
    return final_path


def generate_thumbnail(thumb: dict, video_id: str) -> str:
    print("  Building premium thumbnail with critic loop...")
    # Runs: generate → critic checks → fix prompt → retry if needed
    return thumbnail_critic_loop(thumb, video_id, max_retries=2)


# ═══════════════════════════════════════════════════════════
#  STEP 6 — PUBLISH TO YOUTUBE
# ═══════════════════════════════════════════════════════════
def update_youtube_video(youtube, video_id, title, description, tags, thumbnail_path):
    print("  Updating title & description on YouTube...")
    youtube.videos().update(
        part="snippet",
        body={
            "id": video_id,
            "snippet": {
                "title":       title[:100],
                "description": description,
                "tags":        tags,
                "categoryId":  "22"   # People & Blogs — change if needed
            }
        }
    ).execute()
    print("  Uploading thumbnail to YouTube...")
    youtube.thumbnails().set(
        videoId=video_id,
        media_body=MediaFileUpload(thumbnail_path, mimetype="image/jpeg")
    ).execute()
    print("  YouTube updated successfully!")


# ═══════════════════════════════════════════════════════════
#  MAIN LOOP
# ═══════════════════════════════════════════════════════════
def process_video(youtube, video):
    vid   = video["video_id"]
    title = video["title"]
    print(f"\n{'='*60}")
    print(f"  NEW VIDEO: {title}")
    print(f"  ID:        {vid}")
    print(f"{'='*60}")

    audio      = download_audio(vid)
    transcript = transcribe(audio)
    os.remove(audio)

    content    = generate_content(transcript, title)
    thumb_path = generate_thumbnail(content["thumbnail"], vid)

    update_youtube_video(
        youtube,
        video_id       = vid,
        title          = content["best_title"],
        description    = content["description"],
        tags           = content["tags"],
        thumbnail_path = thumb_path,
    )

    log = {
        "video_id":     vid,
        "old_title":    title,
        "new_title":    content["best_title"],
        "all_titles":   content["titles"],
        "why_best":     content.get("why_best", ""),
        "thumbnail":    content["thumbnail"]["main_text"],
        "processed_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    log_path = Path("logs") / f"{vid}.json"
    with open(log_path, "w") as f:
        json.dump(log, f, indent=2)

    print(f"\n  RESULT:")
    print(f"  Old title : {title}")
    print(f"  New title : {content['best_title']}")
    print(f"  Thumbnail : '{content['thumbnail']['main_text']}'")
    print(f"  Log       : {log_path}")
    print(f"\n  Done! Video is live on YouTube with new title + thumbnail.")


def run():
    print("\n  YouTube Premium Agent started!")
    print(f"  Channel: {YOUTUBE_CHANNEL_ID}")
    print(f"  Polling every 10 minutes for new uploads...\n")
    youtube = get_youtube_service()

    while True:
        try:
            print(f"[{time.strftime('%H:%M:%S')}] Checking for new videos...")
            seen   = load_seen()
            videos = get_latest_videos(youtube)
            new    = [v for v in videos if v["video_id"] not in seen]

            if not new:
                print("  No new videos found.")
            else:
                for video in new:
                    process_video(youtube, video)
                    mark_seen(video["video_id"])

        except Exception as e:
            print(f"  Error: {e}")
            import traceback; traceback.print_exc()

        print(f"  Next check in 10 minutes...\n")
        time.sleep(600)


if __name__ == "__main__":
    run()