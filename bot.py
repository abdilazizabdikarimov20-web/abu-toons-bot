import asyncio
import base64
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

G_API = "generativelanguage.google" + "apis.com"
O_URI = "https" + "://oauth2.google" + "apis.com/token"
HORDE = "https" + "://aihorde." + "net/api/v2/generate"
POLLI = "https" + "://image.pollinations." + "ai/prompt/"

GEMINI_KEY = os.environ["GEMINI_API_KEY"].strip()
YT_ID = os.environ["YT_CLIENT_ID"].strip()
YT_SEC = os.environ["YT_CLIENT_SECRET"].strip()
YT_REF = os.environ["YT_REFRESH_TOKEN"].strip()

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


def get_models():
    models = ["gemini-3-flash-preview", "gemini-2.5-flash"]
    url = f"https://{G_API}/v1beta/models?key={GEMINI_KEY}"
    try:
        r = requests.get(url, timeout=20)
        if r.status_code == 200:
            bad = ["image", "tts", "audio", "lite", "thinking"]
            for m in r.json().get("models", []):
                name = m.get("name", "").replace("models/", "")
                meth = m.get("supportedGenerationMethods", [])
                if (
                    "generateContent" in meth
                    and "flash" in name
                    and not any(x in name for x in bad)
                    and name not in models
                ):
                    models.append(name)
    except Exception:
        pass
    return models


def make_story():
    topic = random.choice(TOPICS)
    prompt = (
        "Write an emotional 45-second 3D Pixar/Disney style "
        f"YouTube Short story about: {topic}.\n"
        "Return ONLY valid JSON:\n"
        '{"title": "Catchy English title under 65 chars", '
        '"description": "Short 2-sentence story summary", '
        '"scenes": [{"narration": "1 short English sentence '
        '(10-15 words)", "image_prompt": "3D Pixar Disney '
        "animation still frame, cute expressive characters, "
        "cinematic lighting, vibrant colors, no text, "
        'describing this exact scene"}]}\n'
        "Rules: Exactly 6 scenes with a heartwarming ending. "
        "Keep character look consistent across all 6 scenes."
    )
    err = ""
    for model in get_models():
        url = (
            f"https://{G_API}/v1beta/models/"
            f"{model}:generateContent?key={GEMINI_KEY}"
        )
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.9,
            },
        }
        for i in range(2):
            try:
                print(f"[1/4] Story: {model} (#{i + 1})...")
                r = requests.post(url, json=body, timeout=120)
                if r.status_code == 200:
                    c = r.json()["candidates"][0]["content"]
                    txt = c["parts"][0]["text"].strip()
                    if txt.startswith("```"):
                        txt = txt.strip("`").removeprefix("json").strip()
                    return json.loads(txt)
                err = f"{model}: {r.status_code}"
                if r.status_code in (400, 404):
                    break
            except Exception as e:
                err = f"{model}: {e}"
            time.sleep(3)
    raise RuntimeError(f"Story failed: {err}")


def img_horde(prompt, path):
    hdr = {
        "apikey": "0000000000",
        "Client-Agent": "AbuToonsBot:1.0:abutoons",
        "Content-Type": "application/json",
    }
    clean_p = prompt[:320].replace("#", "")
    body = {
        "prompt": (
            f"3d pixar disney animation style, cute character, "
            f"cinematic lighting, vibrant colors, {clean_p} "
            f"### text, watermark, blurry, ugly, deformed"
        ),
        "params": {
            "width": 512,
            "height": 512,
            "steps": 16,
            "cfg_scale": 7.5,
            "sampler_name": "k_euler_a",
            "n": 1,
        },
        "nsfw": False,
        "censor_nsfw": True,
        "slow_workers": True,
        "r2": True,
    }
    for _ in range(2):
        try:
            r = requests.post(
                f"{HORDE}/async", json=body, headers=hdr, timeout=25
            )
            if r.status_code not in (200, 202):
                time.sleep(5)
                continue
            jid = r.json().get("id")
            if not jid:
                continue
            for _ in range(35):
                time.sleep(4)
                chk = requests.get(
                    f"{HORDE}/check/{jid}", headers=hdr, timeout=20
                )
                if chk.status_code == 200:
                    info = chk.json()
                    if info.get("faulted"):
                        break
                    if info.get("done"):
                        st = requests.get(
                            f"{HORDE}/status/{jid}", headers=hdr, timeout=20
                        )
                        gens = st.json().get("generations", [])
                        val = gens[0].get("img") if gens else None
                        if val:
                            raw = (
                                requests.get(val, timeout=45).content
                                if val.startswith("http")
                                else base64.b64decode(val)
                            )
                            if len(raw) > 5000:
                                with open(path, "wb") as f:
                                    f.write(raw)
                                print("Img ok via AI Horde")
                                return True
                        break
        except Exception as e:
            print(f"Horde err: {e}")
        time.sleep(4)
    return False


def img_pollinations(prompt, path):
    enc = urllib.parse.quote(prompt[:300])
    seed = random.randint(1, 999999)
    hdr = {"User-Agent": "Mozilla/5.0"}
    url = f"{POLLI}{enc}?width=512&height=512&seed={seed}"
    try:
        r = requests.get(url, headers=hdr, timeout=60)
        ct = r.headers.get("content-type", "")
        if r.status_code == 200 and len(r.content) > 8000 and "image" in ct:
            with open(path, "wb") as f:
                f.write(r.content)
            print("Img ok via Pollinations")
            return True
    except Exception:
        pass
    return False


def get_image(prompt, path):
    if img_horde(prompt, path):
        return
    if img_pollinations(prompt, path):
        return
    raise RuntimeError(f"Image failed: {path}")


async def make_audio(text, path):
    comm = edge_tts.Communicate(text, "en-US-AndrewNeural", rate="+4%")
    await comm.save(path)


def make_video(scenes):
    os.makedirs("work", exist_ok=True)
    clips = []
    for i, sc in enumerate(scenes):
        ip = f"work/img_{i}.jpg"
        ap = f"work/aud_{i}.mp3"
        cp = f"work/clip_{i}.mp4"
        print(f"[2/4] Scene {i + 1}/{len(scenes)}...")
        get_image(sc["image_prompt"], ip)
        asyncio.run(make_audio(sc["narration"], ap))
        vf = (
            "scale=2160:3840:force_original_aspect_ratio=increase,"
            "crop=2160:3840,"
            "zoompan=z=min(zoom+0.0006\\,1.12):"
            "d=1:x=iw/2-(iw/zoom/2):y=ih/2-(ih/zoom/2):"
            "s=1080x1920:fps=30,format=yuv420p"
        )
        cmd = [
            "ffmpeg", "-y", "-loop", "1", "-i", ip, "-i", ap,
            "-vf", vf, "-c:v", "libx264", "-preset", "fast",
            "-crf", "22", "-c:a", "aac", "-b:a", "128k",
            "-ar", "44100", "-ac", "2", "-shortest", cp,
        ]
        subprocess.run(cmd, check=True)
        clips.append(f"file 'clip_{i}.mp4'\n")

    print("[3/4] Merging video...")
    with open("work/list.txt", "w") as f:
        f.writelines(clips)
    out = "final_short.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", "work/list.txt", "-c", "copy", out,
        ],
        check=True,
    )
    return out


def upload_yt(video, title, desc):
    print("[4/4] Uploading to YouTube...")
    creds = Credentials(
        token=None,
        refresh_token=YT_REF,
        token_uri=O_URI,
        client_id=YT_ID,
        client_secret=YT_SEC,
    )
    yt = build("youtube", "v3", credentials=creds)
    body = {
        "snippet": {
            "title": f"{title[:88]} #Shorts",
            "description": (
                f"{desc}\n\nSubscribe to Abu Toons!\n"
                "#Shorts #3DAnimation #PixarStyle #AbuToons"
            ),
            "tags": ["Shorts", "3D Animation", "Pixar Style", "Abu Toons"],
            "categoryId": "1",
        },
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False},
    }
    media = MediaFileUpload(video, mimetype="video/mp4", resumable=True)
    res = yt.videos().insert(
        part="snippet,status", body=body, media_body=media
    ).execute()
    print("SUCCESS! Video ID:", res.get("id"))


if __name__ == "__main__":
    st = make_story()
    print("Title:", st["title"])
    vf = make_video(st["scenes"])
    upload_yt(vf, st["title"], st["description"])
