import asyncio
import base64
import json
import math
import os
import random
import re
import struct
import subprocess
import textwrap
import time
import urllib.parse
import wave
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
    "an old stray dog waiting every rainy evening at a train station for his owner who never returned",
    "a tiny wooden robot sacrificing its glowing heart battery to save a dying baby bird in winter",
    "a lonely elderly grandfather and a small street kitten sharing their last piece of bread",
    "a mother bird shielding her baby chicks from a freezing snowstorm with her own wings",
    "a worn-out teddy bear secretly protecting a crying child from nightmares every night",
    "a blind old street musician and the loyal puppy who guides him through the busy city",
    "a tiny wilted flower in a cracked concrete alley saved by a poor boy's last drop of water",
    "a retired firehouse dog rescuing a trapped kitten from a burning building despite his limp",
    "a little paper boat sailing across a stormy puddle to deliver a child's wish to the stars",
    "a grumpy lonely clockmaker whose life changes when a shivering duckling taps on his window",
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


def parse_story_json(raw_txt):
    txt = raw_txt.strip()
    if txt.startswith("```"):
        lines = txt.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        txt = "\n".join(lines).strip()
        if txt.lower().startswith("json"):
            txt = txt[4:].strip()
    try:
        data = json.loads(txt)
    except Exception:
        start_obj = txt.find("{")
        start_arr = txt.find("[")
        candidates = [i for i in (start_obj, start_arr) if i != -1]
        if not candidates:
            raise
        first = min(candidates)
        end_obj = txt.rfind("}")
        end_arr = txt.rfind("]")
        last = max(end_obj, end_arr)
        data = json.loads(txt[first : last + 1])

    if isinstance(data, list) and data:
        data = data[0]
    if not isinstance(data, dict):
        raise ValueError("Story JSON is not a dict")
    if "title" not in data or "scenes" not in data or not data["scenes"]:
        raise ValueError("Missing title or scenes")
    if "description" not in data:
        data["description"] = "A heartwarming 3D animated story from Abu Toons."
    return data


def make_story():
    topic = random.choice(TOPICS)
    prompt = (
        "Write a deeply emotional, tear-jerking 45-second 3D Pixar/Disney "
        f"style YouTube Short story about: {topic}.\n"
        "Return ONLY a single JSON object (not an array):\n"
        '{"title": "Emotional English title under 65 chars", '
        '"description": "Heartfelt 2-sentence story summary", '
        '"scenes": [{"narration": "1 deeply emotional, poetic English '
        'sentence (10-15 words)", "image_prompt": "3D Pixar Disney '
        "animation movie still frame, expressive emotional eyes, "
        "cinematic warm and dramatic lighting, shallow depth of field, "
        'no text, describing this exact scene"}]}\n'
        "Rules: Exactly 6 scenes building up to a touching, unforgettable "
        "ending. Keep character appearance identical across all 6 scenes."
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
                    txt = c["parts"][0]["text"]
                    return parse_story_json(txt)
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
            f"3d pixar disney animation style, cute expressive character, "
            f"cinematic emotional lighting, vibrant colors, {clean_p} "
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


def create_sad_piano_bgm(path, duration=90):
    sr = 44100
    chords = [
        [220.00, 261.63, 329.63, 440.00],
        [174.61, 220.00, 261.63, 349.23],
        [130.81, 196.00, 261.63, 329.63],
        [196.00, 246.94, 293.66, 392.00],
    ]
    bar_sec = 3.2
    total_samples = int(sr * duration)
    buf = bytearray()
    for n in range(total_samples):
        t = n / sr
        bar_idx = int(t / bar_sec) % len(chords)
        bar_t = t % bar_sec
        chord = chords[bar_idx]
        val = 0.0
        for idx, freq in enumerate(chord):
            note_start = idx * 0.45
            if bar_t >= note_start:
                nt = bar_t - note_start
                env = min(nt * 12.0, 1.0) * math.exp(-nt * 1.15)
                tone = math.sin(2.0 * math.pi * freq * nt)
                val += env * tone
        sample = int(max(-32767, min(32767, val * 2800)))
        buf.extend(struct.pack("<hh", sample, sample))

    with wave.open(path, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(buf)


def esc_text(text):
    clean = re.sub(r"[^A-Za-z0-9 ,.!?-]", "", text)
    wrapped = "\n".join(textwrap.wrap(clean.strip(), width=24))
    return wrapped.replace(":", " ").replace("'", "").replace('"', "")


async def make_audio(text, path):
    comm = edge_tts.Commun
