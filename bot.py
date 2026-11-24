import os, json, random, time, base64, asyncio, subprocess, urllib.parse
from pathlib import Path
from datetime import datetime, timezone
import requests, edge_tts
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

BASE = Path(__file__).resolve().parent
WORK = BASE / "work"
STATE = BASE / "state.json"
LIMIT = 180
API = "https://generativelanguage.googleapis.com"

def env(k):
    v = os.getenv(k, "").strip()
    if not v:
        raise RuntimeError(f"Missing GitHub secret: {k}")
    return v

GEMINI_KEY = env("GEMINI_API_KEY")
YT_ID = env("YT_CLIENT_ID")
YT_SECRET = env("YT_CLIENT_SECRET")
YT_REFRESH = env("YT_REFRESH_TOKEN")
PRIVACY = os.getenv("YT_PRIVACY_STATUS", "private").lower()
MADE_FOR_KIDS = os.getenv("YT_MADE_FOR_KIDS", "false").lower() == "true"
if PRIVACY not in ("private", "unlisted", "public"):
    raise RuntimeError("YT_PRIVACY_STATUS must be private, unlisted or public")

TOPICS = [
 "a tiny robot caring for a glowing flower",
 "a kitten helping a lost duckling in the rain",
 "a baker and a tiny mouse secretly making bread",
 "a baby dragon who sneezes snowflakes",
 "a lonely lighthouse keeper befriending a baby whale",
 "a tiny cloud learning to make rainbows",
 "a squirrel discovering a clockwork city",
 "a stray dog sharing food with a little bird",
 "a shy moon rabbit helping a lost star",
 "a little penguin building a warm shelter for a seal",
 "a young wizard whose wand makes pastries",
 "a fox returning a lost bell to a village"
]
S = requests.Session()
S.headers["User-Agent"] = "AbuToonsAutoShorts/2.0"

def state_load():
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    try: data = json.loads(STATE.read_text(encoding="utf-8"))
    except Exception: data = {}
    if data.get("month") != month:
        data = {"month": month, "uploaded": 0, "video_ids": []}
    data.setdefault("video_ids", [])
    return data

def state_save(data):
    STATE.write_text(json.dumps(data, indent=2), encoding="utf-8")

def models():
    r = S.get(f"{API}/v1beta/models", params={"key": GEMINI_KEY}, timeout=30)
    r.raise_for_status()
    return r.json().get("models", [])

def story_make():
    available = [
        m["name"].replace("models/", "") for m in models()
        if "generateContent" in m.get("supportedGenerationMethods", [])
        and "flash" in m.get("name", "").lower()
        and not any(x in m.get("name", "").lower() for x in ("image","audio","tts","lite"))
    ]
    if not available: raise RuntimeError("No Gemini Flash text model available.")
    topic = random.choice(TOPICS)
    prompt = f"""Create an original family-friendly animated YouTube Short about {topic}.
Return only JSON: {{"title":"under 65 characters","description":"two sentences","scenes":[{{"narration":"18-24 English words","image_prompt":"detailed vertical 9:16 scene prompt"}}]}}
Exactly 6 scenes. Keep character appearance consistent. Aim for 45-60 seconds total narration. Original characters only; no logos, text or watermarks. Use a polished colorful 3D animated-film look."""
    for model in available:
        try:
            r = S.post(f"{API}/v1beta/models/{model}:generateContent",
                params={"key": GEMINI_KEY},
                json={"contents":[{"parts":[{"text":prompt}]}],
                      "generationConfig":{"responseMimeType":"application/json","temperature":0.9}},
                timeout=120)
            if r.status_code in (400,404): continue
            r.raise_for_status()
            raw = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            if raw.startswith("```"):
                raw = raw.strip("`").removeprefix("json").strip()
            data = json.loads(raw)
            if len(data.get("scenes", [])) != 6: raise ValueError("Expected 6 scenes")
            return data
        except Exception as e: print("Story model failed:", model, e)
    raise RuntimeError("Gemini could not create a valid story.")

def image_models():
    found = []
    for m in models():
        name = m.get("name", "").replace("models/", "")
        methods = m.get("supportedGenerationMethods", [])
        if "generateContent" in methods and "image" in name.lower():
            found.append((name, "generateContent"))
        elif "predict" in methods and "imagen" in name.lower():
            found.append((name, "predict"))
    return found

def image_gemini(prompt, path):
    for model, method in image_models():
        try:
            if method == "generateContent":
                r = S.post(f"{API}/v1beta/models/{model}:generateContent",
                    params={"key": GEMINI_KEY},
                    json={"contents":[{"parts":[{"text":"Vertical 9:16 original 3D animated frame, no text or watermark: "+prompt}]}],
                          "generationConfig":{"responseModalities":["IMAGE","TEXT"]}}, timeout=90)
                if r.status_code != 200: continue
                parts = r.json().get("candidates",[{}])[0].get("content",{}).get("parts",[])
                for p in parts:
                    item = p.get("inlineData") or p.get("inline_data")
                    if item and item.get("data"):
                        raw = base64.b64decode(item["data"])
                        if len(raw) > 5000: Path(path).write_bytes(raw); return True
            else:
                r = S.post(f"{API}/v1beta/models/{model}:predict",
                    params={"key": GEMINI_KEY},
                    json={"instances":[{"prompt":prompt}],
                          "parameters":{"sampleCount":1,"aspectRatio":"9:16"}}, timeout=90)
                if r.status_code == 200:
                    pred = r.json().get("predictions",[{}])[0]
                    b64 = pred.get("bytesBase64Encoded")
                    if b64:
                        raw = base64.b64decode(b64)
                        if len(raw) > 5000: Path(path).write_bytes(raw); return True
        except Exception as e: print("Gemini image failed:", e)
    return False

def image_horde(prompt, path):
    api = "https://aihorde.net/api/v2"
    headers = {"apikey":"0000000000","Client-Agent":"AbuToonsBot:2.0:github"}
    try:
        r = S.post(api+"/generate/async",
            headers=headers, json={"prompt":prompt[:450],
            "params":{"width":512,"height":896,"steps":20,"n":1},
            "nsfw":False,"censor_nsfw":True,"r2":True}, timeout=30)
        if r.status_code not in (200,202): return False
        job = r.json().get("id")
        if not job: return False
        for _ in range(45):
            time.sleep(4)
            c = S.get(api+f"/generate/check/{job}", headers=headers, timeout=20)
            if c.status_code == 200 and c.json().get("done"):
                st = S.get(api+f"/generate/status/{job}", headers=headers, timeout=30)
                gen = st.json().get("generations", [{}])[0]
                val = gen.get("img")
                if not val: return False
                raw = S.get(val, timeout=60).content if val.startswith("http") else base64.b64decode(val)
                if len(raw)>5000: Path(path).write_bytes(raw); return True
                return False
            if c.status_code == 200 and c.json().get("faulted"): return False
    except Exception as e: print("AI Horde failed:", e)
    return False

def image_pollinations(prompt, path):
    encoded = urllib.parse.quote(prompt[:400], safe="")
    for n in range(3):
        try:
            r = S.get(f"https://image.pollinations.ai/prompt/{encoded}?width=576&height=1024&seed={random.randint(1,999999)}",
                      timeout=90)
            if r.status_code == 200 and len(r.content)>10000 and "image" in r.headers.get("content-type",""):
                Path(path).write_bytes(r.content); return True
        except Exception as e: print("Pollinations failed:", e)
        time.sleep(3)
    return False

def image_get(prompt, path):
    if image_gemini(prompt,path) or image_horde(prompt,path) or image_pollinations(prompt,path): return
    raise RuntimeError("All image services failed: "+path)

async def audio_make(text, path):
    voice = os.getenv("TTS_VOICE","en-US-AndrewNeural")
    await edge_tts.Communicate(text, voice, rate="+4%").save(path)

def ffmpeg(args):
    subprocess.run(args, check=True)

def video_make(scenes):
    WORK.mkdir(exist_ok=True)
    clips=[]
    for i, scene in enumerate(scenes):
        img=WORK/f"img_{i}.png"; aud=WORK/f"aud_{i}.mp3"; clip=WORK/f"clip_{i}.mp4"
        print(f"Scene {i+1}/6")
        image_get(scene["image_prompt"],str(img))
        asyncio.run(audio_make(scene["narration"],str(aud)))
        vf=("scale=2160:3840:force_original_aspect_ratio=increase,crop=2160:3840,"
            "zoompan=z='min(zoom+0.0006,1.12)':d=1:"
            "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30,format=yuv420p")
        ffmpeg(["ffmpeg","-hide_banner","-loglevel","error","-y","-loop","1","-i",str(img),"-i",str(aud),
                "-vf",vf,"-c:v","libx264","-preset","veryfast","-crf","23",
                "-c:a","aac","-b:a","128k","-ar","44100","-ac","2","-shortest",
                "-movflags","+faststart",str(clip)])
        clips.append(clip)
    listing=WORK/"concat.txt"
    with listing.open("w",encoding="utf-8") as f:
        for p in clips: f.write("file '"+str(p.resolve()).replace("'","'\\''")+"'\n")
    output=BASE/"final_short.mp4"
    ffmpeg(["ffmpeg","-hide_banner","-loglevel","error","-y","-f","concat","-safe","0","-i",str(listing),
            "-c:v","libx264","-preset","veryfast","-crf","23","-c:a","aac","-b:a","128k",
            "-pix_fmt","yuv420p","-movflags","+faststart",str(output)])
    return output

def youtube_upload(path,title,description):
    creds=Credentials(token=None,refresh_token=YT_REFRESH,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=YT_ID,client_secret=YT_SECRET)
    yt=build("youtube","v3",credentials=creds,cache_discovery=False)
    body={"snippet":{"title":title[:75]+" #Shorts","description":description+
          "\n\nOriginal animated story.\n#Shorts #3DAnimation #AnimatedStory",
          "tags":["Shorts","3D Animation","Animated Story"],"categoryId":"1"},
          "status":{"privacyStatus":PRIVACY,"selfDeclaredMadeForKids":MADE_FOR_KIDS}}
    media=MediaFileUpload(str(path),mimetype="video/mp4",resumable=True,chunksize=8*1024*1024)
    req=yt.videos().insert(part="snippet,status",body=body,media_body=media)
    response=None
    while response is None: _,response=req.next_chunk()
    if not response.get("id"): raise RuntimeError("YouTube returned no video ID")
    return response["id"]

def main():
    state=state_load()
    print(f"Monthly uploads: {state['uploaded']}/{LIMIT}")
    if state["uploaded"]>=LIMIT:
        print("Monthly limit reached; stopping."); return
    story=story_make()
    mp4=video_make(story["scenes"])
    video_id=youtube_upload(mp4,story["title"],story["description"])
    state["uploaded"]+=1
    state["video_ids"].append(video_id)
    state_save(state)
    print(f"Uploaded {video_id}; monthly total {state['uploaded']}/{LIMIT}")

if __name__=="__main__":
    main()
