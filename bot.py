import base64, math, os, random, struct, subprocess, time, urllib.parse, wave
import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

O_URI = "https" + "://oauth2.google" + "apis.com/token"
HORDE = "https" + "://aihorde." + "net/api/v2/generate"
POLLI = "https" + "://image.pollinations." + "ai/prompt/"
REF_VIDEO = "https://www.youtube.com/watch?v=mOqdlsUrsng"

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


def pick_unique_name():
    used = set()
    try:
        yt = get_yt()
        res = yt.search().list(part="snippet", forMine=True, type="video", maxResults=50).execute()
        for item in res.get("items", []):
            first_word = item["snippet"]["title"].split()[0].strip("—-.,!?").upper()
            used.add(first_word)
    except Exception:
        pass
    available = [n for n in NAMES if n not in used]
    return random.choice(available if available else NAMES)


def img_horde(prompt, path):
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
    url = f"{POLLI}{urllib.parse.quote(prompt[:320])}?width=512&height=512&seed={random.randint(1, 999999)}"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=60)
    if r.status_code == 200 and len(r.content) > 8000 and "image" in r.headers.get("content-type", ""):
        open(path, "wb").write(r.content)
        return
    raise RuntimeError(f"Image failed: {path}")


def create_fallback_beat(path, duration=14):
    sr = 44100
    beat_sec = 60.0 / 92.0
    chords = [[174.61, 220.0, 261.63, 329.63], [164.81, 196.0, 246.94, 293.66], [146.83, 174.61, 220.0, 261.63], [130.81, 196.0, 246.94, 329.63]]
    random.seed(42)
    noise_tbl = [random.uniform(-1.0, 1.0) for _ in range(sr)]
    buf = bytearray()
    for n in range(sr * duration):
        t = n / sr
        beat_idx = int(t / beat_sec)
        bt = t % beat_sec
        chord = chords[(beat_idx // 4) % 4]
        bar_t = t % (beat_sec * 4)
        pad = sum(min(bar_t * 10.0, 1.0) * math.exp(-bar_t * 0.65) * math.sin(2.0 * math.pi * f * t) for f in chord) * 0.16
        bass = min(bt * 25.0, 1.0) * math.exp(-bt * 3.5) * math.sin(2.0 * math.pi * (chord[0] * 0.5) * bt) * 0.34 if beat_idx % 2 == 0 else 0.0
        kick = math.exp(-bt * 18.0) * math.sin(2.0 * math.pi * (48.0 + 110.0 * math.exp(-bt * 38.0)) * bt) * 0.45 if (beat_idx % 2 == 0 and bt < 0.22) else 0.0
        snare = math.exp(-bt * 24.0) * noise_tbl[n % sr] * 0.26 if (beat_idx % 2 == 1 and bt < 0.18) else 0.0
        ht = t % (beat_sec * 0.5)
        hat = math.exp(-ht * 55.0) * noise_tbl[(n * 3) % sr] * 0.09
        s = int(max(-0.95, min(0.95, pad + bass + kick + snare + hat)) * 29000)
        buf.extend(struct.pack("<hh", s, s))
    with wave.open(path, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(buf)


def get_music(out_audio="work/music.m4a"):
    if os.path.exists("music.mp3"):
        print("Using custom music.mp3 from repo!", flush=True)
        return "music.mp3"
    try:
        print("Downloading audio from reference video...", flush=True)
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
            print("Reference music downloaded!", flush=True)
            return out_audio
    except Exception as e:
        print(f"yt-dlp fallback ({e})", flush=True)
    create_fallback_beat("work/beat.wav", 14)
    return "work/beat.wav"


def make_keychain_video(name):
    os.makedirs("work", exist_ok=True)
    music_file = get_music()
    p_mix, p_glow = random.choice(PALETTES)

    scenes = [
        (f"close up hands stirring glossy {p_mix} epoxy resin inside a clear glass cup with a wooden stick, sparkling swirling pigments, bright craft table, macro shot", ""),
        (f"overhead macro shot pouring liquid {p_glow} epoxy resin into a silicone alphabet letter mold spelling {name}, glossy shiny surface, ASMR craft", ""),
        (f"close up jeweler hands attaching a shiny gold metal keychain ring and clasp onto glossy {p_glow} resin letters spelling {name}, luxury craft studio", ""),
        (f"luxury custom handmade glossy {p_glow} resin keychain spelling the name {name} in bold 3D shiny letters resting inside an open black velvet jewelry gift box, cinematic sparkle", name),
    ]

    clips = []
    for i, (prompt, overlay_name) in enumerate(scenes):
        ip, cp = f"work/img_{i}.jpg", f"work/clip_{i}.mp4"
        print(f"[1/3] Step {i + 1}/4 for '{name}'...", flush=True)
        get_image(prompt, ip)

        zoom_expr = "zoompan=z=min(zoom+0.0018\\,1.16):d=84:x=iw/2-(iw/zoom/2):y=ih/2-(ih/zoom/2):s=1080x1920:fps=30"
        if overlay_name:
            with open("work/name.txt", "w") as f:
                f.write(overlay_name)
            vf = (
                "scale=2160:3840:force_original_aspect_ratio=increase,"
                f"crop=2160:3840,{zoom_expr},"
                "drawtext=textfile='work/name.txt':"
                "fontcolor=white:fontsize=96:borderw=6:bordercolor=black:"
                "x=(w-text_w)/2:y=h*0.76,format=yuv420p"
            )
        else:
            vf = f"scale=2160:3840:force_original_aspect_ratio=increase,crop=2160:3840,{zoom_expr},format=yuv420p"

        subprocess.run(
            ["ffmpeg", "-y", "-loop", "1", "-t", "2.8", "-i", ip, "-vf", vf, "-c:v", "libx264", "-preset", "fast", "-crf", "21", "-pix_fmt", "yuv420p", cp],
            check=True,
        )
        clips.append(f"file 'clip_{i}.mp4'\n")

    print("[2/3] Merging clips + reference music...", flush=True)
    open("work/list.txt", "w").writelines(clips)
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "work/list.txt", "-c", "copy", "work/merged.mp4"], check=True)
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", "work/merged.mp4", "-stream_loop", "-1", "-i", music_file,
            "-map", "0:v", "-map", "1:a", "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k", "-shortest", "final_short.mp4",
        ],
        check=True,
    )
    return "final_short.mp4"


def upload_yt(video, name):
    print(f"[3/3] Uploading '{name}' to YouTube...", flush=True)
    yt = get_yt()
    pretty = name.capitalize()
    body = {
        "snippet": {
            "title": f"{pretty} keyingisi qaysi ism bo'lsin? ✍️ #Shorts",
            "description": (
                f"{pretty} — maxsus epoksid smoladan tayyorlangan ismli brelok! ✨\n"
                "Keyingi videoda qaysi ismni yasaylik? Izohda yozib qoldiring! ✍️👇\n\n"
                "#Shorts #ResinArt #Keychain #Satisfying #ASMR #Handmade #AbuToons"
            ),
            "tags": ["Shorts", "Resin Art", "Keychain", "Satisfying", "ASMR", "Handmade", pretty, "Abu Toons"],
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


chosen_name = pick_unique_name()
print("Selected Name:", chosen_name, flush=True)
upload_yt(make_keychain_video(chosen_name), chosen_name)
