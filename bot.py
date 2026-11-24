import asyncio
import json
import os
import random
import subprocess
import time
import urllib.parse
import edge_tts
import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

HTTPS = "https" + "://"
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"].strip()
YT_CLIENT_ID = os.environ["YT_CLIENT_ID"].strip()
YT_CLIENT_SECRET = os.environ["YT_CLIENT_SECRET"].strip()
YT_REFRESH_TOKEN = os.environ["YT_REFRESH_TOKEN"].strip()

TOPICS = [
    "a tiny clumsy robot trying to water a delicate glowing flower in a futuristic greenhouse",
    "a brave little street kitten rescuing a lost baby duckling during a rainy night in Paris",
    "a grumpy old baker and a mischievous tiny mouse secretly helping him bake the best bread",
    "a small wooden toy soldier coming to life at midnight to protect a sleeping child from a shadow monster",
    "a baby dragon who sneezes snowflakes instead of fire trying to fit in with his family",
    "a lonely lighthouse keeper befriending a glowing baby whale on a stormy night",
    "a tiny cloud who is afraid of thunder learning how to make rainbows",
    "a curious squirrel discovering an abandoned miniature clockwork city inside an ancient oak tree",
    "a tired stray dog sharing his last piece of bread with a shivering little bird in winter",
    "a young apprentice wizard whose magic wand only turns things into delicious pastries",
]


def get_gemini_models():
    models = ["gemini-3.8-flash"]
    try:
        r = requests.get(
            f"{HTTPS}generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}",
            timeout=25,
        )
        if r.status_code == 200:
            for m in r.json().get("models", []):
                name = m.get("name", "").replace("models/", "")
                methods = m.get("supportedGenerationMethods", [])
                if (
                    "generateContent" in methods
                    and "flash" in name
                    and not any(x in name for x in ["image", "tts", "audio", "lite", "thinking"])
                    and name not in models
                ):
                    models.append(name)
    except Exception:
        pass
    return models


def generate_story():
    topic = random.choice(TOPICS)
    prompt = f"""Create an emotional, heartwarming, viral 45-second 3D Pixar/Disney style animated YouTube Short story about: {topic}.
Return ONLY valid JSON with this exact structure:
{{
  "title": "Catchy emotional English title under 65 characters",
  "description": "Short engaging 2-sentence English story summary",
  "scenes": [
    {{
      "narration": "1 short expressive English sentence (10-16 words) spoken by narrator",
      "image_prompt": "Detailed 3D Pixar Disney animation still frame, cute expressive characters, cinematic volumetric lighting, vibrant colors, 8k render, vertical 9:16 composition, no text, describing this exact moment"
    }}
  ]
}}
Rules:
- Exactly 6 scenes with a clear beginning, twist/emotion, and heartwarming ending.
- Keep consistent character appearance across all 6 image_prompt descriptions.
- Never include text, subtitles, or watermarks in image_prompt."""

    last_error = ""
    for model in get_gemini_models():
        url = f"{HTTPS}generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.9,
            },
        }
        for attempt in range(2):
            try:
                print(f"[1/4] Generating story with {model} (attempt {attempt + 1})...")
                resp = requests.post(url, json=payload, timeout=120)
                if resp.status_code == 200:
                    raw_text = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                    if raw_text.startswith("```"):
                        raw_text = raw_text.strip("`").removeprefix("json").strip()
                    return json.loads(raw_text)
                last_error = f"{model}: {resp.status_code} {resp.text}"
                if resp.status_code in (400, 404):
                    break
            except Exception as e:
                last_error = f"{model}: {e}"
                print(f"Retrying story generation: {e}")
            time.sleep(3)
    raise RuntimeError(f"Gemini API error: {last_error}")


def download_image(prompt, filename):
    encoded = urllib.parse.quote(prompt[:450])
    seed = random.randint(1, 999999)
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    for attempt in range(5):
        model_param = "&model=flux" if attempt < 3 else ""
        url = f"{HTTPS}image.pollinations.ai/prompt/{encoded}?width=768&height=1344{model_param}&nologo=true&seed={seed + attempt}"
        try:
            r = requests.get(url, headers=headers, timeout=90)
            ctype = r.headers.get("content-type", "")
            if r.status_code == 200 and len(r.content) > 10000 and "image" in ctype:
                with open(filename, "wb") as f:
                    f.write(r.content)
                return
            print(f"Image attempt {attempt + 1} status={r.status_code} size={len(r.content)}")
        except Exception as e:
            print(f"Image attempt {attempt + 1} error: {e}")
        time.sleep(4)
    raise RuntimeError(f"Failed to download image: {filename}")


async def make_audio(text, filename):
    communicate = edge_tts.Communicate(text, "en-US-AndrewNeural", rate="+4%")
    await communicate.save(filename)


def build_video(scenes):
    os.makedirs("work", exist_ok=True)
    clip_paths = []
    for i, scene in enumerate(scenes):
        img_path = f"work/img_{i}.jpg"
        aud_path = f"work/aud_{i}.mp3"
        clip_path = f"work/clip_{i}.mp4"

        print(f"[2/4] Creating scene {i + 1}/{len(scenes)}...")
        download_image(scene["image_prompt"], img_path)
        asyncio.run(make_audio(scene["narration"], aud_path))

        vf = (
            "scale=2160:3840:force_original_aspect_ratio=increase:flags=lanczos,"
            "crop=2160:3840,"
            "zoompan
