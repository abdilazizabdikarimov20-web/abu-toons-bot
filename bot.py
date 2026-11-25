import asyncio, base64, json, math, os, random, re, struct, subprocess, textwrap, time, urllib.parse, wave
import edge_tts, requests
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


def parse_story_json(raw_txt):
    txt = raw_txt.strip()
    if txt.startswith("```"):
        lines = [l for l in txt.splitlines() if not l.strip().startswith("```")]
        txt = "\n".join(lines).strip()
        if txt.lower().startswith("json"):
            txt = txt[4:].strip()
    try:
        data = json.loads(txt)
    except Exception:
        s = min([i for i in (txt.find("{"), txt.find("[")) if i != -1])
        e = max(txt.rfind("}"), txt.rfind("]"))
        data = json.loads(txt[s : e + 1])
    if isinstance(data, list) and data:
        data = data[0]
    if not isinstance(data, dict) or "title" not in data or not data.get("scenes"):
        raise ValueError("Invalid JSON structure")
    data.setdefault("description", "A heartwarming 3D animated story from Abu Toons.")
    return data


def make_story():
    topic = random.choice(TOPICS)
    prompt = (
        f"Write a deeply emotional 45-second 3D Pixar/Disney style YouTube Short story about: {topic}.\n"
        'Return ONLY a single JSON object: {"title": "Emotional title under 65 chars", '
        '"description": "Heartfelt 2-sentence summary", "scenes": [{"narration": "1 poetic English '
        'sentence (10-15 words)", "image_prompt": "3D Pixar Disney movie still frame, expressive '
        'emotional eyes, cinematic lighting, shallow depth of field, no text, describing scene"}]}\n'
        "Rules: Exactly 6 scenes with a touching ending. Keep character identical across all scenes."
    )
    err = ""
    for model in ["gemini-3-flash-preview", "gemini-2.5-flash", "gemini-2.0-flash"]:
        url = f"https://{G_API}/v1beta/models/{model}:generateContent?key={GEMINI_KEY}"
        body = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "application/json", "temperature": 0.9}}
        for i in range(2):
            try:
                print(f"[1/4] Story: {model} (#{i + 1})...", flush=True)
                r = requests.post(url, json=body, timeout=120)
                if r.status_code == 200:
                    txt = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                    return parse_story_json(txt)
                err = f"{model}: {r.status_code}"
                if r.status_code in (400, 404):
                    break
            except Exception as e:
                err = f"{model}: {e}"
            time.sleep(3)
    raise RuntimeError(f"Story failed: {err}")


def img_horde(prompt, path):
    hdr = {"apikey": "0000000000", "Client-Agent": "AbuToonsBot:1.0:abutoons", "Content-Type": "application/json"}
    clean_p = prompt[:320].replace("#", "")
    body = {
        "prompt": f"3d pixar disney animation style, cute expressive character, cinematic lighting, {clean_p} ### text, watermark, blurry, deformed",
        "params": {"width": 512, "height": 512, "steps": 16, "cfg_scale": 7.5, "sampler_name": "k_euler_a", "n": 1},
        "nsfw": False, "censor_nsfw": True, "slow_workers": True, "r2": True,
    }
    for _ in range(2):
        try:
            r = requests.post(f"{HORDE}/async", json=body, headers=hdr, timeout=25)
            if r.status_code not in (200, 202):
                time.sleep(5)
                continue
            jid = r.json().get("id")
            for _ in range(35):
                time.sleep(4)
                chk = requests.get(f"{HORDE}/check/{jid}", headers=hdr, timeout=20).json()
                if chk.get("faulted"):
                    break
                if chk.get("done"):
                    gens = requests.get(f"{HORDE}/status/{jid}", headers=hdr, timeout=20).json().get("generations", [])
                    val = gens[0].get("img") if gens else None
                    if val:
                        raw = requests.get(val, timeout=45).content if val.startswith("http") else base64.b64decode(val)
                        if len(raw) > 5000:
                            open(path, "wb").write(raw)
                            return True
                    break
        except Exception:
            pass
        time.sleep(4)
    return False


def get_image(prompt, path):
    if img_horde(prompt, path):
        return
    url = f"{POLLI}{urllib.parse.quote(prompt[:300])}?width=512&height=512&seed={random.randint(1, 999999)}"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=60)
    if r.status_code == 200 and len(r.content) > 8000 and "image" in r.headers.get("content-type", ""):
        open(path, "wb").write(r.content)
        return
    raise RuntimeError(f"Image failed: {path}")


def create_sad_piano_bgm(path, duration=90):
    sr = 44100
    chords = [[220.0, 261.63, 329.63, 440.0], [174.61, 220.0, 261.63, 349.23], [130.81, 196.0, 261.63, 329.63], [196.0, 246.94, 293.66, 392.0]]
    buf = bytearray()
    for n in range(sr * duration):
        t = n / sr
        chord = chords[int(t / 3.2) % 4]
        bar_t = t % 3.2
        val = sum(min((bar_t - idx * 0.45) * 12.0, 1.0) * math.exp(-(bar_t - idx * 0.45) * 1.15) * math.sin(2.0 * math.pi * f * (bar_t - idx * 0.45)) for idx, f in enumerate(chord) if bar_t >= idx * 0.45)
        s = int(max(-32767, min(32767, val * 2800)))
        buf.extend(struct.pack("<hh", s, s))
    with wave.open(path, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(buf)


def esc_text(text):
    clean = re.sub(r"[^A-Za-z0-9 ,.!?-]", "", text)
    return "\n".join(textwrap.wrap(clean.strip(), width=24)).replace(":", " ").replace("'", "").replace('"', "")


async def make_audio(text, path):
    await edge_tts.Communicate(text, "en-US-AndrewNeural", rate="-4%").save(path)


def make_video(scenes):
    os.makedirs("work", exist_ok=True)
    create_sad_piano_bgm("work/bgm.wav", 90)
    clips = []
    for i, sc in enumerate(scenes):
        ip, ap, cp = f"work/img_{i}.jpg", f"work/aud_{i}.mp3", f"work/clip_{i}.mp4"
        print(f"[2/4] Scene {i + 1}/{len(scenes)}...", flush=True)
        get_image(sc["image_prompt"], ip)
        asyncio.run(make_audio(sc["narration"], ap))
        sub = esc_text(sc["narration"])
        vf = f"scale=2160:3840:force_original_aspect_ratio=increase,crop=2160:3840,zoompan=z=min(zoom+0.0006\\,1.12):d=1:x=iw/2-(iw/zoom/2):y=ih/2-(ih/zoom/2):s=1080x1920:fps=30,drawtext=text='{sub}':fontcolor=white:fontsize=52:borderw=4:bordercolor=black:x=(w-text_w)/2:y=h*0.74,format=yuv420p"
        subprocess.run(["ffmpeg", "-y", "-loop", "1", "-i", ip, "-i", ap, "-vf", vf, "-c:v", "libx264", "-preset", "fast", "-crf", "22", "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2", "-shortest", cp], check=True)
        clips.append(f"file 'clip_{i}.mp4'\n")
    print("[3/4] Merging video + music...", flush=True)
    open("work/list.txt", "w").writelines(clips)
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "work/list.txt", "-c", "copy", "work/merged.mp4"], check=True)
    subprocess.run(["ffmpeg", "-y", "-i", "work/merged.mp4", "-i", "work/bgm.wav", "-filter_complex", "[0:a]volume=1.0[v];[1:a]volume=0.22[m];[v][m]amix=inputs=2:duration=first:dropout_transition=2[a]", "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "final_short.mp4"], check=True)
    return "final_short.mp4"


def upload_yt(video, title, desc):
    print("[4/4] Uploading to YouTube...", flush=True)
    creds = Credentials(token=None, refresh_token=YT_REF, token_uri=O_URI, client_id=YT_ID, client_secret=YT_SEC)
    yt = build("youtube", "v3", credentials=creds)
    body = {
        "snippet": {
            "title": f"{title[:88]} #Shorts",
            "description": f"{desc}\n\nSubscribe to Abu Toons for daily heartwarming 3D stories!\n#Shorts #3DAnimation #PixarStyle #EmotionalStory #AbuToons",
            "tags": ["Shorts", "3D Animation", "Pixar Style", "Emotional Story", "Abu Toons"],
            "categoryId": "1",
        },
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False},
    }
    res = yt.videos().insert(part="snippet,status", body=body, media_body=MediaFileUpload(video, mimetype="video/mp4", resumable=True)).execute()
    print("SUCCESS! Video ID:", res.get("id"), flush=True)


st = make_story()
print("Title:", st["title"], flush=True)
upload_yt(make_video(st["scenes"]), st["title"], st["description"])
