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
    "a tiny clumsy robot watering a glowing flower in a greenhouse",
    "a brave street kitten rescuing a lost baby duckling in the rain",
    "a grumpy old baker and a tiny mouse secretly baking bread",
    "a wooden toy soldier protecting a sleeping child at midnight",
    "a baby dragon who sneezes snowflakes instead of fire",
    "a lonely lighthouse keeper befriending a glowing baby whale",
    "a tiny cloud afraid of thunder learning to make rainbows",
    "a curious squirrel finding a clockwork city inside an oak tree",
    "a stray dog sharing his last bread with a shivering bird",
    "a young wizard whose wand only makes delicious pastries",
]


def get_gemini_models():
    models = ["gemini-3.8-flash"]
    try:
        url = (
            f"{HTTPS}generativelanguage.googleapis.com"
            f"/v1beta/models?key={GEMINI_API_KEY}"
        )
        r = requests.get(url, timeout=25)
        if r.status_code == 200:
            for m in r.json().get("models", []):
                name = m.get("name", "").replace("models/", "")
                methods = m.get("supportedGenerationMethods", [])
                bad = ["image", "tts", "audio", "lite", "thinking"]
                if (
                    "generateContent" in methods
                    and "flash" in name
                    and not any(x in name for x in bad)
                    and name not in models
                ):
                    models.append(name)
    except Exception:
        pass
    return models


def generate_story():
    topic = random.choice(TOPICS)
    prompt = (
        "Create an emotional, viral 45-second 3D Pixar/Disney "
        f"style animated YouTube Short story about: {topic}.\n"
        "Return ONLY valid JSON with this exact structure:\n"
        '{"title": "Catchy English title under 65 chars", '
        '"description": "Short 2-sentence story summary", '
        '"scenes": [{"narration": "1 short English sentence '
        '(10-16 words)", "image_prompt": "Detailed 3D Pixar '
        "Disney animation still frame, cute expressive characters, "
        "cinematic lighting, vibrant colors, 8k render, vertical "
        '9:16 composition, no text, describing this moment"}]}\n'
        "Rules: Exactly 6 scenes with a heartwarming ending. "
        "Keep consistent character appearance across all 6 scenes. "
        "Never include text or watermarks in image_prompt."
    )

    last_error = ""
    for model in get_gemini_models():
        url = (
            f"{HTTPS}generativelanguage.googleapis.com"
            f"/v1beta/models/{model}:generateContent"
            f"?key={GEMINI_API_KEY}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.9,
            },
        }
        for attempt in range(2):
            try:
                print(f"[1/4] Story with {model} (#{attempt + 1})...")
                resp = requests.post(url, json=payload, timeout=120)
                if resp.status_code == 200:
                    data = resp.json()
                    part = data["candidates"][0]["content"]["parts"][0]
                    raw_text = part["text"].strip()
                    if raw_text.startswith("```"):
                        raw_text = raw_text.strip("`")
                        raw_text = raw_text.removeprefix("json").strip()
                    return json.loads(raw_text)
                last_error = f"{model}: {resp.status_code} {resp.text}"
                if resp.status_code in (400, 404):
                    break
            except Exception as e:
                last_error = f"{model}: {e}"
                print(f"Retrying story: {e}")
            time.sleep(3)
    raise RuntimeError(f"Gemini API error: {last_error}")


def download_image(prompt, filename):
    encoded = urllib.parse.quote(prompt[:450])
    seed = random.randint(1, 999999)
    headers = {"User-Agent": "Mozilla/5.0"}
    for attempt in range(5):
        m_param = "&model=flux" if attempt < 3 else ""
        url = (
            f"{HTTPS}image.pollinations.ai/prompt/{encoded}"
            f"?width=768&height=1344{m_param}"
            f"&nologo=true&seed={seed + attempt}"
        )
        try:
            r = requests.get(url, headers=headers, timeout=90)
            ctype = r.headers.get("content-type", "")
            if (
                r.status_code == 200
                and len(r.content) > 10000
                and "image" in ctype
            ):
                with open(filename, "wb") as f:
                    f.write(r.content)
                return
            print(f"Img #{attempt + 1}: {r.status_code}")
        except Exception as e:
            print(f"Img #{attempt + 1} err: {e}")
        time.sleep(4)
    raise RuntimeError(f"Failed image: {filename}")


async def make_audio(text, filename):
    comm = edge_tts.Communicate(text, "en-US-AndrewNeural", rate="+4%")
    await comm.save(filename)


def build_video(scenes):
    os.makedirs("work", exist_ok=True)
    clip_paths = []
    for i, scene in enumerate(scenes):
        img_path = f"work/img_{i}.jpg"
        aud_path = f"work/aud_{i}.mp3"
        clip_path = f"work/clip_{i}.mp4"

        print(f"[2/4] Scene {i + 1}/{len(scenes)}...")
        download_image(scene["image_prompt"], img_path)
        asyncio.run(make_audio(scene["narration"], aud_path))

        vf = (
            "scale=2160:3840:"
            "force_original_aspect_ratio=increase,"
            "crop=2160:3840,"
            "zoompan=z=min(zoom+0.0006\\,1.12):"
            "d=1:x=iw/2-(iw/zoom/2):"
            "y=ih/2-(ih/zoom/2):"
            "s=1080x1920:fps=30,"
            "format=yuv420p"
        )
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", img_path,
            "-i", aud_path,
            "-vf", vf,
            "-c:v", "libx264", "-preset", "fast", "-crf", "22",
            "-c:a", "aac", "-b:a", "128k",
            "-ar", "44100", "-ac", "2",
            "-shortest", clip_path,
        ]
        subprocess.run(cmd, check=True)
        clip_paths.append(f"file 'clip_{i}.mp4'\n")

    print("[3/4] Merging video...")
    list_path = "work/list.txt"
    with open(list_path, "w") as f:
        f.writelines(clip_paths)

    output_video = "final_short.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "concat",
            "-safe", "0", "-i", list_path,
            "-c", "copy", output_video,
        ],
        check=True,
    )
    return output_video


def upload_to_youtube(video_path, title, description):
    print("[4/4] Uploading to YouTube...")
    creds = Credentials(
        token=None,
        refresh_token=YT_REFRESH_TOKEN,
        token_uri=f"{HTTPS}[oauth2.googleapis.com/token](https://oauth2.googleapis.com/token)",
        client_id=YT_CLIENT_ID,
        client_secret=YT_CLIENT_SECRET,
    )
    youtube = build("youtube", "v3", credentials=creds)
    clean_title = f"{title[:88]} #Shorts"
    full_desc = (
        f"{description}\n\n"
        "Subscribe to Abu Toons for daily 3D animated stories!\n"
        "#Shorts #3DAnimation #PixarStyle #Cartoon #AbuToons"
    )
    body = {
        "snippet": {
            "title": clean_title,
            "description": full_desc,
            "tags": ["Shorts", "3D Animation", "Pixar Style", "Abu Toons"],
            "categoryId": "1",
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        },
    }
    media = MediaFileUpload(video_path, mimetype="video/mp4", resumable=True)
    req = youtube.videos().insert(
        part="snippet,status", body=body, media_body=media
    )
    res = req.execute()
    print("SUCCESS! Video ID:", res.get("id"))


if __name__ == "__main__":
    story = generate_story()
    print("Story title:", story["title"])
    video_file = build_video(story["scenes"])
    upload_to_youtube(video_file, story["title"], story["description"])
