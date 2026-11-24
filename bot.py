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
