import base64, math, os, random, shutil, struct, subprocess, time, urllib.parse, wave
import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

O_URI = "https" + "://oauth2.google" + "apis.com/token"
HORDE = "https" + "://aihorde." + "net/api/v2/generate"
POLLI = "https" + "://image.pollinations." + "ai/prompt/"
REF_VIDEO = "https://www.youtube.com/watch?v=a3fwj9aWc8g"

YT_ID = os.environ["YT_CLIENT_ID"].strip()
YT_SEC = os.environ["YT_CLIENT_SECRET"].strip()
YT_REF = os.environ["YT_REFRESH_TOKEN"].strip()

NAMES = [
    # 90 ta o'g'il bolalar ismlari
    "JASUR", "AMIR", "MUHAMMAD", "AZIZ", "SARDOR", "BEKZOD", "UMID", "DILSHOD",
    "TIMUR", "BOBUR", "JAVOHIR", "OYBEK", "SHERZOD", "FARRUX", "ULUGBEK", "SANJAR",
    "RUSTAM", "ISLOM", "OTABEK", "AKMAL", "MIRZO", "ABDULLOH", "IBROHIM", "YUSUF",
    "UMAR", "USMON", "ALI", "HASAN", "HUSAN", "BILOL", "MUSTAFO", "IMRON",
    "DOSTON", "NODIR", "ELDOR", "SHOXRUX", "TEMUR", "KAMRON", "BEHRUZ", "ASADBEK",
    "SHOHJAHON", "BAXTIYOR", "DAVRON", "ERKIN", "FARHOD", "GAYRAT", "HAMZA", "ILHOM",
    "JAMSHID", "KARIM", "LAZIZ", "MANSUR", "NURIDDIN", "ORIF", "PULAT", "QODIR",
    "RAVSHAN", "SAMANDAR", "TOHIR", "UBAYDULLOH", "VALI", "XURSHID", "YAHYO", "ZAFAR",
    "ABROR", "ALISHER", "ANVAR", "ARSLON", "AZAMAT", "BAHRIDDIN", "BUNYOD", "DANIYOR",
    "ELYOR", "FIRDAVS", "HUMOYUN", "IKROM", "ISLOMBEK", "JAHONGIR", "KOMIL", "LUTFULLOH",
    "MAHMUD", "MURODJON", "NAVROZ", "ODIL", "OLIM", "QUVONCHBEK", "RAHMATULLOH", "SAID",
    "SUHROB", "ZOKIR",
    # 90 ta qiz bolalar ismlari
    "MADINA", "SEVARA", "MALIKA", "RAYHONA", "ZILOLA", "SHAHZODA", "NIGORA", "GULNORA",
    "NOZIMA", "FERUZA", "KAMOLA", "DILDORA", "MUNISA", "SABINA", "ZARINA", "MOHIRA",
    "SEVINCH", "LAYLO", "JASMINA", "SHAHNOZA", "PARIZODA", "OYSHA", "FOTIMA", "ZUHRA",
    "XADICHA", "MARYAM", "SOLIHA", "MUBINA", "IMONA", "SOFIYA", "ASAL", "DILNOZA",
    "GULNOZA", "HILOLA", "IRODA", "KUMUSH", "LOLA", "MAFTUNA", "NAFISA", "OZODA",
    "QUNDUZ", "ROBIYA", "SAIDA", "SHIRIN", "UMIDA", "YULDUZ", "ZEBO", "ZULFIYA",
    "AZIZA", "BARNO", "CHAROS", "DILFUZA", "DURDONA", "EZOZA", "FARANGIZ", "GAVHAR",
    "GULBAHOR", "GULCHEHRA", "GULSHAN", "HULKAR", "INTIZOR", "JAMILA", "KOMILA", "LOBAR",
    "MAHBUBA", "MARJONA", "MEHRINISO", "MOHINUR", "MUNIRA", "MUSLIMA", "NARGIZA", "NASIBA",
    "NILUFAR", "NODIRA", "ODINA", "OYDIN", "RUHSHONA", "SABOHAT", "SARVINOZ", "SHABNAM",
    "SHODIYA", "SHUKRONA", "SITORA", "SURAYYO", "TOJINISO", "VASILA", "XURSHIDA", "YASMINA",
    "ZARNIGOR", "ZAYNAB",
]

PALETTES = [
    ("royal blue and liquid gold leaf", "deep ocean blue and gold glitter"),
    ("emerald green and gold flakes", "jade green and shimmering gold"),
    ("ruby red and rose gold leaf", "crimson red and golden sparkles"),
    ("amethyst purple and silver glitter", "violet galaxy and gold flakes"),
    ("turquoise aqua and pearl gold", "cyan ocean wave and gold leaf"),
]


def get_yt():
    creds = Credentials(token=None, refresh_token=YT_REF, token_uri=O_URI, client_id=YT_ID, client_secret=YT_SEC)
    return build("youtube", "v3", credentials=creds)


def pick_unique_item():
    used = set()
    try:
        yt = get_yt()
        res = yt.search().list(part="snippet", forMine=True, type="video", maxResults=50).execute()
        for item in res.get("items", []):
            title = item["snippet"]["title"].upper()
            for w in title.split():
                used.add(w.strip("—-.,!?✍️#"))
    except Exception:
        pass

    # 75% ehtimol bilan 180 ta ismdan biri, 25% ehtimol bilan "A ❤️ M" juftlik harflari
    if random.random() < 0.75:
        available = [n for n in NAMES if n not in used]
        name = random.choice(available if available else NAMES)
        pretty = name.capitalize()
        return name, pretty, f"{pretty} keyingisi qaysi ism bo'lsin? ✍️ #Shorts"
    else:
        letters = "ABDEFGHIJKLMNOPQRSTUVXYZ"
        l1, l2 = random.sample(letters, 2)
        pair = f"{l1} ❤️ {l2}"
        return f"{l1} and {l2}", pair, f"{pair} keyingisi qaysi harf bo'lsin? ✍️ #Shorts"


def get_music(out_audio="work/music.m4a"):
    if os.path.exists("music.mp3"):
        print("Using custom music.mp3 from repo!", flush=True)
        return "music.mp3"
    try:
        print("Downloading audio from a3fwj9aWc8g...", flush=True)
        subprocess.run(
            [
                "yt-dlp", "-f", "bestaudio[ext=m4a]/bestaudio",
                "--extractor-args", "youtube:player_client=android,ios",
                "-o", out_audio, REF_VIDEO,
            ],
            check=True,
            timeout=60,
        )
        if os.path.exists(out_audio) and os.path.getsize(out_audio) > 5000:
            print("Music downloaded successfully!", flush=True)
            return out_audio
    except Exception as e:
        print(f"yt-dlp fallback ({e})", flush=True)

    # Zaxira ritmli beat (agar YouTube server IP ni cheklasa)
    sr = 44100
    beat_sec = 60.0 / 98.0
    notes = [220.0, 246.94, 261.63, 293.66, 329.63, 293.66, 261.63, 246.94]
    buf = bytearray()
    for n in range(sr * 12):
        t = n / sr
        idx = int(t / (beat_sec * 0.5))
        bt = t % (beat_sec * 0.5)
        mel = math.exp(-bt * 5.0) * math.sin(2.0 * math.pi * notes[idx % len(notes)] * bt) * 0.25
        kick = math.exp(-bt * 18.0) * math.sin(2.0 * math.pi * 55.0 * bt) * 0.45 if idx % 2 == 0 else 0.0
        s = int(max(-0.95, min(0.95, mel + kick)) * 28000)
        buf.extend(struct.pack("<hh", s, s))
    with wave.open("work/beat.wav", "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(buf)
    return "work/beat.wav"


def try_hf_video(prompt, out_mp4):
    try:
        from gradio_client import Client
        spaces = ["Lightricks/LTX-Video", "Wan-AI/Wan2.1-T2V-1.3B"]
        for sp in spaces:
            try:
                client = Client(sp, verbose=False)
                res = client.predict(prompt, api_name="/predict")
                vid_path = res[0] if isinstance(res, (list, tuple)) else res
                if isinstance(vid_path, dict):
                    vid_path = vid_path.get("video") or vid_path.get("path")
                if vid_path and os.path.exists(str(vid_path)):
                    shutil.copy(str(vid_path), out_mp4)
                    print(f"Real AI video generated via {sp}!", flush=True)
                    return True
            except Exception:
                continue
    except Exception:
        pass
    return False


def get_image(prompt, path):
    hdr = {"apikey": "0000000000", "Client-Agent": "AbuToonsBot:1.0:abutoons", "Content-Type": "application/json"}
    clean_p = prompt[:340].replace("#", "")
    body = {
        "prompt": f"ultra realistic macro photography, 8k resolution, studio lighting, shallow depth of field, {clean_p} ### blurry, ugly, deformed, cartoon, watermark",
        "params": {"width": 512, "height": 512, "steps": 18, "cfg_scale": 7.5, "sampler_name": "k_euler_a", "n": 1},
        "nsfw": False, "censor_nsfw": True, "slow_workers": True, "r2": True,
    }
    for _ in range(2):
        try:
            r = requests.post(f"{HORDE}/async", json=body, headers=hdr, timeout=25)
            if r.status_code in (200, 202):
                jid = r.json().get("id")
                for _ in range(30):
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
                                return
                        break
        except Exception:
            pass
        time.sleep(3)

    url = f"{POLLI}{urllib.parse.quote(prompt[:320])}?width=512&height=512&seed={random.randint(1, 999999)}"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=60)
    if r.status_code == 200 and len(r.content) > 8000 and "image" in r.headers.get("content-type", ""):
        open(path, "wb").write(r.content)
        return
    raise RuntimeError(f"Image failed: {path}")


def make_keychain_video(prompt_label, display_label):
    os.makedirs("work", exist_ok=True)
    music_file = get_music()
    p_mix, p_glow = random.choice(PALETTES)

    # 5 ta tezkor 2.2 soniyalik kadr = jami ANIQ 11.0 soniya!
    scenes = [
        (f"macro ASMR video of hands stirring glossy {p_mix} liquid epoxy resin in a clear glass cup with wooden stick, swirling gold glitter", ""),
        (f"overhead macro ASMR video pouring liquid {p_glow} epoxy resin into a silicone alphabet mold spelling {prompt_label}, glossy shiny resin", ""),
        (f"close up hands smoothing glossy {p_glow} resin letters with a mini spatula tool on craft table, bright studio lighting", ""),
        (f"close up jeweler pliers attaching shiny gold metal keychain ring onto glossy {p_glow} resin letters {prompt_label}, macro craft", ""),
        (f"luxury custom handmade glossy {p_glow} resin keychain spelling {prompt_label} inside an open black velvet gift box, sparkling macro shot", display_label),
    ]

    clips = []
    for i, (prompt, overlay_text) in enumerate(scenes):
        raw_v = f"work/raw_{i}.mp4"
        ip = f"work/img_{i}.jpg"
        cp = f"work/clip_{i}.mp4"
        print(f"[1/3] Clip {i + 1}/5 for '{display_label}'...", flush=True)

        # Avval haqiqiy jonli video generatsiya qilib ko'ramiz; bo'lmasa 2.2s silliq zoom kadr
        got_real_video = try_hf_video(prompt, raw_v)

        # MUHIM: d=1 bo'lishi shart! Aks holda video 13 daqiqaga cho'zilib ketadi!
        zoom_expr = "zoompan=z='min(zoom+0.0025,1.18)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30"

        if overlay_text:
            with open("work/label.txt", "w", encoding="utf-8") as f:
                f.write(overlay_text)
            draw = (
                ",drawtext=textfile='work/label.txt':"
                "fontcolor=white:fontsize=92:borderw=6:bordercolor=black:"
                "x=(w-text_w)/2:y=h*0.76"
            )
        else:
            draw = ""

        if got_real_video:
            vf = f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30{draw},format=yuv420p"
            subprocess.run(
                ["ffmpeg", "-y", "-stream_loop", "-1", "-i", raw_v, "-t", "2.2", "-vf", vf, "-c:v", "libx264", "-preset", "fast", "-crf", "21", "-an", cp],
                check=True,
            )
        else:
            get_image(prompt, ip)
            vf = f"scale=2160:3840:force_original_aspect_ratio=increase,crop=2160:3840,{zoom_expr}{draw},format=yuv420p"
            subprocess.run(
                ["ffmpeg", "-y", "-loop", "1", "-t", "2.2", "-i", ip, "-vf", vf, "-c:v", "libx264", "-preset", "fast", "-crf", "21", "-an", cp],
                check=True,
            )
        clips.append(f"file 'clip_{i}.mp4'\n")

    print("[2/3] Merging 5 clips into exact 11s Short...", flush=True)
    open("work/list.txt", "w").writelines(clips)
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "work/list.txt", "-c", "copy", "work/merged.mp4"], check=True)
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", "work/merged.mp4", "-stream_loop", "-1", "-i", music_file,
            "-map", "0:v", "-map", "1:a", "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k", "-t", "11.0", "final_short.mp4",
        ],
        check=True,
    )
    return "final_short.mp4"


def upload_yt(video, display_label, title):
    print(f"[3/3] Uploading '{title}' to YouTube...", flush=True)
    yt = get_yt()
    body = {
        "snippet": {
            "title": title,
            "description": (
                f"{display_label} — maxsus epoksid smoladan tayyorlangan brelok! ✨\n"
                "Keyingi videoda qaysi ism yoki harf bo'lsin? Izohda yozing! ✍️👇\n\n"
                "#Shorts #ResinArt #Keychain #Satisfying #ASMR #Handmade #AbuToons"
            ),
            "tags": ["Shorts", "Resin Art", "Keychain", "Satisfying", "ASMR", "Handmade", display_label, "Abu Toons"],
            "categoryId": "26",
        },
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False},
    }
    res = yt.videos().insert(
        part="snippet,status",
        body=body,
        media_body=MediaFileUpload(video, mimetype="video/mp4", resumable=True),
    ).execute()
    print("SUCCESS! Video ID:", res.get("id"), flush=True)


p_label, d_label, yt_title = pick_unique_item()
print("Selected:", yt_title, flush=True)
upload_yt(make_keychain_video(p_label, d_label), d_label, yt_title)
