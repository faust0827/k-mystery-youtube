#!/usr/bin/env python3
"""K-Mystery YouTube longform 자동화 파이프라인.

사용:
  python3 auto/pipeline.py --help
  python3 auto/pipeline.py all "조선 실록에 기록된 UFO"

단계별 재실행:
  script → images → tts → i2v → render → upload
"""
import argparse
import base64
import datetime as dt
import glob
import json
import os
import re
import subprocess
import sys
import time

import requests

ROOT = "/home/j/문서/project/youtube"
AUTO = os.path.join(ROOT, "auto")
JOBS = os.path.join(AUTO, "jobs")
ENV_PATH = os.path.join(ROOT, ".env")

GEMINI_MODEL = "gemini-nano-banana-2.1"
KLING_MODEL = "kling-v2-6"
KLING_DURATION = "5"          # 2.6은 3초 미지원
VOICE = "en-US-GuyNeural"
N_SECTIONS = 8
GAP = 0.55
W, H, FPS = 1920, 1080, 30
BGM = os.path.join(ROOT, "1", "Missing Persons - Jeremy Blake.mp3")
INTRO = os.path.join(ROOT, "intro_5s.mp4")

# 스타일 앵커: auto/STYLE.md 와 동일한 값. 수정 시 둘 다 함께 갱신할 것.
ANCHOR = (
    "Style: cinematic semi-realistic illustration, Joseon Korea, "
    "muted earth tones, paper-lantern warm light, volumetric fog, "
    "film grain, 35mm, low saturation, painterly texture, "
    "dark mysterious atmosphere. NOT photorealistic, NOT cartoon, "
    "NOT anime, no text, no watermark."
)


# ---------------------------------------------------------------- utils

def load_env(path=ENV_PATH):
    out = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                out[k] = v.strip()
    return out


def run(cmd, check=True, quiet=False):
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       text=True)
    if check and r.returncode != 0:
        print("FAILED:", " ".join(str(c) for c in cmd), file=sys.stderr)
        print(r.stderr[-3000:], file=sys.stderr)
        sys.exit(1)
    if not quiet and r.stdout.strip():
        print(r.stdout.strip())
    return r


def dur(path):
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "csv=p=0", path]).decode().strip()
    return float(out)


def job_dir(jid):
    return os.path.join(JOBS, jid)


def load_job(jid):
    path = os.path.join(job_dir(jid), "job.json")
    if not os.path.exists(path):
        sys.exit("job not found: " + jid)
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def save_job(job):
    d = job_dir(job["id"])
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "job.json"), "w", encoding="utf-8") as fh:
        json.dump(job, fh, ensure_ascii=False, indent=2)
    print("job saved:", job["id"])


def latest_job():
    if not os.path.isdir(JOBS):
        sys.exit("no jobs yet")
    dirs = sorted(os.listdir(JOBS))
    if not dirs:
        sys.exit("no jobs yet")
    return dirs[-1]


def need_env(*keys):
    env = load_env()
    for k in keys:
        if not env.get(k):
            sys.exit("missing " + k + " in .env")
    return env


def extract_json(text):
    m = re.findall(r"```(?:json)?\s*(.*?)```", text, re.S)
    for cand in reversed(m):
        try:
            return json.loads(cand.strip())
        except Exception:
            pass
    # 배열 우선 (대본은 JSON array로 나옴)
    for opener, closer in (("[", "]"), ("{", "}")):
        i, j = text.find(opener), text.rfind(closer)
        if i >= 0 and j > i:
            try:
                return json.loads(text[i:j + 1])
            except Exception:
                pass
    sys.exit("could not parse JSON from opencode output")


# ---------------------------------------------------------------- steps

def cmd_script(topic):
    print("STEP 1/6: script (opencode run)", flush=True)
    prompt = f"""You are writing for K-Mystery, an English-language YouTube documentary
channel about Korean history, mysteries and folklore.

Topic: {topic}

Write a 6-8 minute documentary script in English, divided into EXACTLY
{N_SECTIONS} sections. Each section should be 40-60 seconds of narration.

Return ONLY a JSON array with this exact shape:
[
  {{
    "id": "01_coldopen",
    "narration": "English narration text for this section...",
    "image_prompt": "visual description for an illustration...",
    "motion_prompt": "slow camera movement description, loop-friendly..."
  }},
  ...
]

Rules for image_prompt: Joseon Korea, cinematic, no close-up faces,
silhouettes / side / back views preferred.
Rules for motion_prompt: camera pan, light flicker, fog drift, smoke rising.
NEVER describe walking people or actions that look wrong reversed.
No markdown, no commentary — valid JSON only.
"""
    r = subprocess.run(["opencode", "run", prompt],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       text=True, cwd=ROOT)
    if r.returncode != 0:
        print(r.stderr[-3000:], file=sys.stderr)
        sys.exit(1)
    sections = extract_json(r.stdout)
    if isinstance(sections, dict):
        sections = sections.get("sections", [])
    if len(sections) != N_SECTIONS:
        print("warning: got", len(sections), "sections, expected", N_SECTIONS)

    jid = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    job = {
        "id": jid,
        "topic": topic,
        "title": topic + " | K-Mystery",
        "sections": sections,
    }
    save_job(job)
    return jid


def find_image(obj):
    if isinstance(obj, dict):
        for k in ("data", "b64_json", "base64", "bytesBase64Encoded"):
            v = obj.get(k)
            if isinstance(v, str) and len(v) > 1000:
                return v
        for v in obj.values():
            got = find_image(v)
            if got:
                return got
    elif isinstance(obj, list):
        for v in obj:
            got = find_image(v)
            if got:
                return got
    return None


def cmd_images(jid):
    print("STEP 2/6: images (nano banana)", flush=True)
    job = load_job(jid)
    key = need_env("GEMINI_API_KEY")["GEMINI_API_KEY"]
    d = os.path.join(job_dir(jid), "images")
    os.makedirs(d, exist_ok=True)
    url = "https://generativelanguage.googleapis.com/v1beta/interactions"

    for i, sec in enumerate(job["sections"], 1):
        out = os.path.join(d, f"{i:02d}.jpg")
        if os.path.exists(out) and os.path.getsize(out) > 10000:
            print("  skip", out)
            continue
        payload = {
            "model": GEMINI_MODEL,
            "input": sec["image_prompt"] + "\n" + ANCHOR,
            "response_format": {
                "type": "image", "mime_type": "image/jpeg",
                "aspect_ratio": "16:9", "image_size": "1K",
            },
        }
        r = requests.post(url, headers={"x-goog-api-key": key,
                                        "Content-Type": "application/json"},
                          json=payload, timeout=180)
        if r.status_code != 200:
            print("image", i, "failed:", r.text[:500], file=sys.stderr)
            sys.exit(1)
        b64 = find_image(r.json())
        if not b64:
            sys.exit("no image in response for section " + str(i))
        with open(out, "wb") as fh:
            fh.write(base64.b64decode(b64))
        print("  image", i, os.path.getsize(out), "bytes")


def srt_time(t):
    h = int(t // 3600); m = int((t % 3600) // 60); s = int(t % 60)
    ms = int(round((t - int(t)) * 1000))
    if ms == 1000:
        s += 1; ms = 0
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def split_captions(text, max_len=56):
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    caps = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if len(p) <= max_len:
            caps.append(p); continue
        cur = ""
        for w in p.split():
            if len(cur) + len(w) + 1 <= max_len:
                cur = (cur + " " + w).strip()
            else:
                if cur:
                    caps.append(cur)
                cur = w
        if cur:
            caps.append(cur)
    merged = []
    for c in caps:
        if merged and (len(c) < 16 or len(merged[-1]) < 16) and \
                len(merged[-1]) + 1 + len(c) <= 64:
            merged[-1] += " " + c
        else:
            merged.append(c)
    return merged


def cmd_tts(jid):
    print("STEP 3/6: TTS (edge-tts, free)", flush=True)
    job = load_job(jid)
    d = os.path.join(job_dir(jid), "vo")
    os.makedirs(d, exist_ok=True)
    entries = []
    t = 0.0
    for i, sec in enumerate(job["sections"], 1):
        out = os.path.join(d, f"{i:02d}.mp3")
        if not os.path.exists(out):
            run(["edge-tts", "--voice", VOICE,
                 "--text", sec["narration"], "--write-media", out])
        length = dur(out)
        caps = split_captions(sec["narration"])
        chars = sum(len(c) for c in caps) or 1
        t0 = t
        for c in caps:
            share = max(length * (len(c) / chars), 0.9)
            entries.append((t0, t0 + share, c))
            t0 += share
        if t0 > t + length:
            scale = length / (t0 - t)
            entries = [(t + (a - t) * scale, t + (b - t) * scale, c)
                       if a >= t else (a, b, c)
                       for (a, b, c) in entries]
            t0 = t + length
        t = t0 + GAP

    # concat audio
    lst = os.path.join(d, "list.txt")
    with open(lst, "w") as fh:
        for i in range(1, len(job["sections"]) + 1):
            fh.write(f"file '{i:02d}.mp3'\n")
            if i < len(job["sections"]):
                fh.write(f"file 'silence.mp3'\n")
    sil = os.path.join(d, "silence.mp3")
    if not os.path.exists(sil):
        run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
             "-i", "anullsrc=r=24000:cl=mono", "-t", str(GAP), sil])
    narration = os.path.join(d, "narration.mp3")
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
         "-i", lst, "-c", "copy", narration])
    srt = os.path.join(d, "narration.srt")
    with open(srt, "w", encoding="utf-8") as fh:
        for n, (a, b, c) in enumerate(entries, 1):
            fh.write(f"{n}\n{srt_time(a)} --> {srt_time(b)}\n{c}\n\n")
    print("narration:", dur(narration), "s, captions:", len(entries))


def kling_i2v(image, prompt, dest):
    key = need_env("KLING_API_KEY")["KLING_API_KEY"]
    b64 = base64.b64encode(open(image, "rb").read()).decode("ascii")
    s = requests.Session()
    s.headers.update({"Authorization": "Bearer " + key,
                      "Content-Type": "application/json"})
    body = {"model_name": KLING_MODEL, "image": b64, "prompt": prompt,
            "duration": KLING_DURATION, "mode": "std", "aspect_ratio": "16:9"}
    r = s.post("https://api-singapore.klingai.com/v1/videos/image2video",
               json=body, timeout=120)
    if r.status_code != 200:
        print(r.text[:1000], file=sys.stderr); sys.exit(1)
    tid = (r.json().get("data") or {}).get("task_id")
    if not tid:
        sys.exit("no task_id")
    for _ in range(90):
        time.sleep(5)
        g = s.get("https://api-singapore.klingai.com/v1/videos/image2video/" + tid,
                  timeout=60)
        if g.status_code != 200:
            continue
        data = g.json().get("data") or {}
        status = data.get("task_status")
        if status == "succeed":
            videos = data.get("task_result", {}).get("videos", [])
            url = videos[0]["url"]
            v = requests.get(url, timeout=180)
            with open(dest, "wb") as fh:
                fh.write(v.content)
            return
        if status in ("failed", "cancelled"):
            print(json.dumps(data, ensure_ascii=False)[:1500], file=sys.stderr)
            sys.exit(1)
    sys.exit("kling timeout")


def cmd_i2v(jid):
    # B안: 섹션마다 클립 2개(a/b). 되감기 없이 정방향으로만 교대 재생.
    print("STEP 4/6: i2v (kling 2.6, 5s x2 per section)", flush=True)
    job = load_job(jid)
    d = os.path.join(job_dir(jid), "clips")
    os.makedirs(d, exist_ok=True)
    extra = " single continuous forward motion, no reversal, no walking toward camera"
    for i, sec in enumerate(job["sections"], 1):
        img = os.path.join(job_dir(jid), "images", f"{i:02d}.jpg")
        if not os.path.exists(img):
            sys.exit("missing image " + img)
        for suffix in ("a", "b"):
            out = os.path.join(d, f"{i:02d}_{suffix}.mp4")
            if os.path.exists(out) and os.path.getsize(out) > 100000:
                print("  skip", out); continue
            print("  clip", i, suffix, flush=True)
            kling_i2v(img, sec["motion_prompt"] + extra, out)
            print("  clip", i, suffix, os.path.getsize(out), "bytes")


def cmd_render(jid):
    print("STEP 5/6: render", flush=True)
    job = load_job(jid)
    base = job_dir(jid)
    vo = os.path.join(base, "vo")
    clips = os.path.join(base, "clips")
    tmp = os.path.join(base, "_tmp")
    os.makedirs(tmp, exist_ok=True)

    lengths = []
    for i in range(1, len(job["sections"]) + 1):
        f = os.path.join(vo, f"{i:02d}.mp3")
        if not os.path.exists(f):
            sys.exit("missing " + f)
        lengths.append(dur(f))

    # B안: 섹션마다 클립 2개(a/b)를 정방향으로만 번갈아 재생.
    # 되감기(ping-pong) 없음 — 앞뒤 왔다갔다 피드백 반영.
    segs = []
    for i, length in enumerate(lengths, 1):
        clips_ab = [os.path.join(clips, f"{i:02d}_{s}.mp4") for s in ("a", "b")]
        for c in clips_ab:
            if not os.path.exists(c):
                sys.exit("missing " + c)
        seg = os.path.join(tmp, f"seg_{i:02d}.mp4")
        target = length + GAP
        vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,"
              f"crop={W}:{H},format=yuv420p")
        clip_durs = [dur(c) for c in clips_ab]
        pieces = []
        elapsed = 0.0
        k = 0
        while elapsed < target - 0.1:
            src = clips_ab[k % 2]
            take = min(clip_durs[k % 2], target - elapsed)
            piece = os.path.join(tmp, f"piece_{i:02d}_{k:02d}.mp4")
            run(["ffmpeg", "-y", "-v", "error", "-t", f"{take:.3f}",
                 "-i", src, "-vf", vf, "-an",
                 "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                 "-r", str(FPS), piece])
            pieces.append(piece)
            elapsed += take
            k += 1
        plst = os.path.join(tmp, f"pieces_{i:02d}.txt")
        with open(plst, "w") as fh:
            for piece in pieces:
                fh.write(f"file '{piece}'\n")
        run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
             "-i", plst, "-c", "copy", seg])
        segs.append(seg)

    lst = os.path.join(tmp, "segments.txt")
    with open(lst, "w") as fh:
        for s in segs:
            fh.write(f"file '{s}'\n")
    silent_video = os.path.join(tmp, "base.mp4")
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
         "-i", lst, "-c", "copy", silent_video])

    srt = os.path.join(vo, "narration.srt")
    srt_esc = srt.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
    style = ("FontName=DejaVu Sans,FontSize=22,PrimaryColour=&H00FFFFFF,"
             "OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=0,"
             "Alignment=2,MarginV=40")
    narration = os.path.join(vo, "narration.mp3")
    raw = os.path.join(base, "roughcut.mp4")
    if os.path.exists(BGM):
        af = ("[1:a]volume=1.0,asplit=2[n1][n2];"
              "[2:a]volume=0.20,aloop=loop=-1:size=2e9[bg];"
              "[bg][n1]sidechaincompress=threshold=0.02:ratio=4:"
              "attack=5:release=400[duck];"
              "[n2][duck]amix=inputs=2:duration=first:dropout_transition=0,"
              "loudnorm=I=-16:TP=-1.5:LRA=11[a]")
        extra = ["-i", BGM]
    else:
        af = "[1:a]loudnorm=I=-16:TP=-1.5:LRA=11[a]"
        extra = []
    run(["ffmpeg", "-y", "-v", "error", "-i", silent_video,
         "-i", narration, *extra,
         "-filter_complex", af,
         "-vf", f"subtitles='{srt_esc}':force_style='{style}'",
         "-map", "0:v", "-map", "[a]",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
         "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
         "-pix_fmt", "yuv420p", "-movflags", "+faststart", raw])

    final = os.path.join(base, "final.mp4")
    if os.path.exists(INTRO):
        lst2 = os.path.join(tmp, "final_list.txt")
        with open(lst2, "w") as fh:
            fh.write(f"file '{INTRO}'\n")
            fh.write(f"file '{raw}'\n")
        run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
             "-i", lst2, "-c", "copy", final])
    else:
        final = raw
    print("final:", final, f"{dur(final):.1f}s")


def cmd_upload(jid):
    print("STEP 6/6: upload payload", flush=True)
    job = load_job(jid)
    final = os.path.join(job_dir(jid), "final.mp4")
    if not os.path.exists(final):
        sys.exit("final.mp4 missing — run render first")
    payload = {
        "platforms": ["youtube"],
        "per_platform": {"youtube": {
            "title": job["title"],
            "text": "Korean mysteries, told from the historical record. "
                    "Subscribe for more.",
        }},
        "title": job["title"],
        "privacy": "public",
        "video_url": "UPLOADED_VIDEO_URL_HERE",
        "brand_id": "71e65546-2e0f-4e64-9cb8-7c0d259f8873",
    }
    out = os.path.join(job_dir(jid), "post_payload.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    print("payload:", out)
    print("실제 업로드는 승인 후 video_url 을 넣어 PostWire 로 실행합니다.")


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description="K-Mystery 자동화 파이프라인")
    ap.add_argument("command", choices=[
        "all", "script", "images", "tts", "i2v", "render", "upload", "distribute"])
    ap.add_argument("topic", nargs="?", help="주제 (script/all 명령에서 사용)")
    ap.add_argument("--job", help="job id (생략하면 최신 job)")
    args = ap.parse_args()

    os.makedirs(JOBS, exist_ok=True)

    if args.command in ("script", "all"):
        if not args.topic:
            sys.exit("주제를 입력하세요")
        jid = cmd_script(args.topic)
    else:
        jid = args.job or latest_job()
        print("job:", jid)

    if args.command == "script":
        return
    if args.command == "images" or args.command == "all":
        cmd_images(jid)
    if args.command == "tts" or args.command == "all":
        cmd_tts(jid)
    if args.command == "i2v" or args.command == "all":
        cmd_i2v(jid)
    if args.command == "render" or args.command == "all":
        cmd_render(jid)
    if args.command == "upload":
        cmd_upload(jid)
    if args.command == "distribute":
        # 원본 마스터 보관 + 플랫폼별 업로드 가이드
        import distribute as _dist  # type: ignore
        _dist.main_with_jid(jid)
    if args.command == "all":
        cmd_upload(jid)
        try:
            import distribute as _dist  # type: ignore
            _dist.main_with_jid(jid)
        except Exception as e:
            print("distribute skipped:", e)


if __name__ == "__main__":
    main()
