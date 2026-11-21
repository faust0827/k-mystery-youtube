#!/usr/bin/env python3
"""한국어 숏폼(틱톡/유튜브 쇼츠) 자동화 파이프라인 — K-Mystery 시리즈.

기존 pipeline.py(영어 롱폼)는 그대로 두고, 이 파일은 한국어 60~90초 / 9:16 전용.

사용:
  python3 auto/pipeline_ko.py --help
  python3 auto/pipeline_ko.py all "조선 실록에 기록된 기이한 기록"

단계별 재실행:
  script → images → tts → i2v → render → distribute
"""
import argparse
import base64
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time

import requests

ROOT = "/home/j/문서/project/youtube"
AUTO = os.path.join(ROOT, "auto")
JOBS = os.path.join(AUTO, "jobs_ko")
ENV_PATH = os.path.join(ROOT, ".env")

GEMINI_MODEL = "gemini-nano-banana-2.1"
KLING_MODEL = "kling-v2-6"
KLING_DURATION = "5"
VOICE_KO = "ko-KR-SunHiNeural"      # 한국어 여성 목소리
N_SECTIONS = 3                       # 60~90초 = 훅/본문/반전 3섹션
GAP = 0.4
W, H, FPS = 1080, 1920, 30           # 9:16 세로
BGM = os.path.join(ROOT, "1", "Missing Persons - Jeremy Blake.mp3")
HOOK_SEC = 3.0                       # 첫 3초 훅

ANCHOR_KO = (
    "Style: cinematic semi-realistic illustration, Joseon Korea, "
    "muted earth tones, paper-lantern warm light, volumetric fog, "
    "film grain, 35mm, low saturation, painterly texture, "
    "dark mysterious atmosphere. NOT photorealistic, NOT cartoon, "
    "NOT anime, no text, no watermark."
)


# ---------------------------------------------------------------- utils

def load_env():
    out = {}
    with open(ENV_PATH, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                out[k] = v.strip()
    return out


def need_env(*keys):
    env = load_env()
    for k in keys:
        if not env.get(k):
            sys.exit("missing " + k + " in .env")
    return env


def run(cmd, check=True, quiet=False):
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       text=True)
    if check and r.returncode != 0:
        print("FAILED:", " ".join(str(c) for c in cmd), file=sys.stderr)
        print(r.stderr[-2000:], file=sys.stderr)
        sys.exit(1)
    if not quiet and r.stdout.strip():
        print(r.stdout.strip())
    return r


def dur(path):
    return float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "csv=p=0", path]).decode().strip())


def job_dir(jid):
    return os.path.join(JOBS, jid)


def save_job(job):
    d = job_dir(job["id"])
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "job.json"), "w", encoding="utf-8") as fh:
        json.dump(job, fh, ensure_ascii=False, indent=2)
    print("job saved:", job["id"])


def load_job(jid):
    p = os.path.join(job_dir(jid), "job.json")
    if not os.path.exists(p):
        sys.exit("job not found: " + jid)
    return json.load(open(p, encoding="utf-8"))


def latest_job():
    dirs = sorted(os.listdir(JOBS)) if os.path.isdir(JOBS) else []
    if not dirs:
        sys.exit("no jobs yet")
    return dirs[-1]


def extract_json(text):
    m = re.findall(r"```(?:json)?\s*(.*?)```", text, re.S)
    for cand in reversed(m):
        try:
            return json.loads(cand.strip())
        except Exception:
            pass
    for opener, closer in (("[", "]"), ("{", "}")):
        i, j = text.find(opener), text.rfind(closer)
        if i >= 0 and j > i:
            try:
                return json.loads(text[i:j + 1])
            except Exception:
                pass
    sys.exit("could not parse JSON from opencode output")


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


# ---------------------------------------------------------------- steps

def cmd_script(topic):
    print("STEP 1/5: script (opencode run, 한국어)", flush=True)
    prompt = f"""당신은 한국어 틱톡/유튜브 쇼츠 채널 '한국 미스터리'의 대본 작가입니다.

주제: {topic}

다음 조건으로 60~90초 분량 대본을 작성하세요:
- 정확히 {N_SECTIONS}개 섹션 (훅 / 본문 / 반전)
- 첫 섹션은 **첫 3초에 시청자를 멈추게 하는 충격적인 질문/사실**
- 한국어, 다큐멘터리 톤, 자극적 묘사 금지
- 실록/사료 기반일 경우 출처를 명시
- 각 섹션은 20~30초 분량

JSON 배열만 출력하세요 (마크다운/설명 없이):
[
  {{"id":"01_hook","narration":"첫 3초 훅 문장...","image_prompt":"이미지 묘사...","motion_prompt":"카메라가 천천히 앞으로 이동, 안개가 흐름 (되감기 없는 단방향 움직임)"}},
  {{"id":"02_body","narration":"본문...","image_prompt":"...","motion_prompt":"..."}},
  {{"id":"03_twist","narration":"반전...","image_prompt":"...","motion_prompt":"..."}}
]

이미지 프롬프트: 인물은 실루엣/후면/측면, 얼굴 클로즈업 금지.
모션 프롬프트: 되감기 어려운 움직임(걷기, 앞으로 전진)은 넣지 마세요.
"""
    r = subprocess.run(["opencode", "run", prompt],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       text=True, cwd=ROOT)
    if r.returncode != 0:
        print(r.stderr[-2000:], file=sys.stderr); sys.exit(1)
    sections = extract_json(r.stdout)
    jid = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    job = {
        "id": jid,
        "topic": topic,
        "title": topic + " | 한국 미스터리",
        "lang": "ko",
        "format": "9:16",
        "sections": sections,
    }
    save_job(job)
    return jid


def cmd_images(jid):
    print("STEP 2/5: images (nano banana)", flush=True)
    job = load_job(jid)
    key = need_env("GEMINI_API_KEY")["GEMINI_API_KEY"]
    d = os.path.join(job_dir(jid), "images")
    os.makedirs(d, exist_ok=True)
    url = "https://generativelanguage.googleapis.com/v1beta/interactions"
    for i, sec in enumerate(job["sections"], 1):
        out = os.path.join(d, f"{i:02d}.jpg")
        if os.path.exists(out) and os.path.getsize(out) > 10000:
            print("  skip", out); continue
        payload = {
            "model": GEMINI_MODEL,
            "input": sec["image_prompt"] + "\n" + ANCHOR_KO,
            "response_format": {
                "type": "image", "mime_type": "image/jpeg",
                "aspect_ratio": "9:16", "image_size": "1K",
            },
        }
        r = requests.post(url, headers={"x-goog-api-key": key,
                                        "Content-Type": "application/json"},
                          json=payload, timeout=180)
        if r.status_code != 200:
            print("image", i, "failed:", r.text[:500], file=sys.stderr); sys.exit(1)
        b64 = find_image(r.json())
        if not b64:
            sys.exit("no image in response " + str(i))
        open(out, "wb").write(base64.b64decode(b64))
        print("  image", i, os.path.getsize(out), "bytes")


def srt_time(t):
    h = int(t // 3600); m = int((t % 3600) // 60); s = int(t % 60)
    ms = int(round((t - int(t)) * 1000))
    if ms == 1000:
        s += 1; ms = 0
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def split_caps_ko(text, max_len=24):
    # 한국어: 문장/쉼표 기준으로 자막 분할
    parts = re.split(r"(?<=[.!?。])\s+|,\s*", text.strip())
    caps = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        while len(p) > max_len:
            cut = max_len
            for j in range(max_len, max(8, max_len - 6), -1):
                if p[j - 1] in " ,·의를이다가은는":
                    cut = j; break
            caps.append(p[:cut].strip())
            p = p[cut:].strip()
        if p:
            caps.append(p)
    return caps


def cmd_tts(jid):
    print("STEP 3/5: TTS (edge-tts, ko-KR, 무료)", flush=True)
    job = load_job(jid)
    d = os.path.join(job_dir(jid), "vo")
    os.makedirs(d, exist_ok=True)
    entries = []
    t = 0.0
    for i, sec in enumerate(job["sections"], 1):
        out = os.path.join(d, f"{i:02d}.mp3")
        if not os.path.exists(out):
            run(["edge-tts", "--voice", VOICE_KO,
                 "--text", sec["narration"], "--write-media", out])
        length = dur(out)
        caps = split_caps_ko(sec["narration"])
        chars = sum(len(c) for c in caps) or 1
        t0 = t
        for c in caps:
            share = max(length * (len(c) / chars), 0.8)
            entries.append((t0, t0 + share, c))
            t0 += share
        if t0 > t + length:
            scale = length / (t0 - t)
            entries = [(t + (a - t) * scale, t + (b - t) * scale, c)
                       if a >= t else (a, b, c) for a, b, c in entries]
            t0 = t + length
        t = t0 + GAP
    # concat
    lst = os.path.join(d, "list.txt")
    with open(lst, "w") as fh:
        for i in range(1, len(job["sections"]) + 1):
            fh.write(f"file '{i:02d}.mp3'\n")
            if i < len(job["sections"]):
                fh.write("file 'silence.mp3'\n")
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
    prompt += " single continuous forward motion, no reversal, no text"
    body = {"model_name": KLING_MODEL, "image": b64, "prompt": prompt,
            "duration": KLING_DURATION, "mode": "std", "aspect_ratio": "9:16"}
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
            url = data["task_result"]["videos"][0]["url"]
            v = requests.get(url, timeout=180)
            open(dest, "wb").write(v.content)
            return
        if status in ("failed", "cancelled"):
            print(json.dumps(data, ensure_ascii=False)[:1000], file=sys.stderr)
            sys.exit(1)
    sys.exit("kling timeout")


def cmd_i2v(jid):
    print("STEP 4/5: i2v (kling 2.6, 5초 x2, 정방향만)", flush=True)
    job = load_job(jid)
    d = os.path.join(job_dir(jid), "clips")
    os.makedirs(d, exist_ok=True)
    for i, sec in enumerate(job["sections"], 1):
        img = os.path.join(job_dir(jid), "images", f"{i:02d}.jpg")
        if not os.path.exists(img):
            sys.exit("missing " + img)
        for suffix in ("a", "b"):
            out = os.path.join(d, f"{i:02d}_{suffix}.mp4")
            if os.path.exists(out) and os.path.getsize(out) > 100000:
                print("  skip", out); continue
            print("  clip", i, suffix, flush=True)
            kling_i2v(img, sec["motion_prompt"], out)
            print("  clip", i, suffix, os.path.getsize(out), "bytes")


def cmd_render(jid):
    print("STEP 5/5: render (9:16, 자막, BGM)", flush=True)
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

    segs = []
    for i, length in enumerate(lengths, 1):
        cab = [os.path.join(clips, f"{i:02d}_{s}.mp4") for s in ("a", "b")]
        for c in cab:
            if not os.path.exists(c):
                sys.exit("missing " + c)
        cd = [dur(c) for c in cab]
        target = length + GAP
        pieces, elapsed, k = [], 0.0, 0
        vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,"
              f"crop={W}:{H},format=yuv420p")
        while elapsed < target - 0.1:
            src = cab[k % 2]
            take = min(cd[k % 2], target - elapsed)
            piece = os.path.join(tmp, f"piece_{i:02d}_{k:02d}.mp4")
            run(["ffmpeg", "-y", "-v", "error", "-t", f"{take:.3f}",
                 "-i", src, "-vf", vf, "-an",
                 "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                 "-r", str(FPS), piece])
            pieces.append(piece); elapsed += take; k += 1
        plst = os.path.join(tmp, f"pieces_{i:02d}.txt")
        with open(plst, "w") as fh:
            for p in pieces:
                fh.write(f"file '{p}'\n")
        seg = os.path.join(tmp, f"seg_{i:02d}.mp4")
        run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
             "-i", plst, "-c", "copy", seg])
        segs.append(seg)

    lst = os.path.join(tmp, "segments.txt")
    with open(lst, "w") as fh:
        for s in segs:
            fh.write(f"file '{s}'\n")
    silent = os.path.join(tmp, "base.mp4")
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
         "-i", lst, "-c", "copy", silent])

    srt = os.path.join(vo, "narration.srt")
    srt_esc = srt.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
    style = ("FontName=Noto Sans CJK KR,FontSize=18,PrimaryColour=&H00FFFFFF,"
             "OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=0,"
             "Alignment=2,MarginV=80")
    narration = os.path.join(vo, "narration.mp3")
    final = os.path.join(base, "final.mp4")
    if os.path.exists(BGM):
        af = ("[1:a]volume=1.0,asplit=2[n1][n2];"
              "[2:a]volume=0.18,aloop=loop=-1:size=2e9[bg];"
              "[bg][n1]sidechaincompress=threshold=0.02:ratio=4:"
              "attack=5:release=400[duck];"
              "[n2][duck]amix=inputs=2:duration=first:dropout_transition=0,"
              "loudnorm=I=-16:TP=-1.5:LRA=11[a]")
        extra = ["-i", BGM]
    else:
        af = "[1:a]loudnorm=I=-16:TP=-1.5:LRA=11[a]"
        extra = []
    run(["ffmpeg", "-y", "-v", "error", "-i", silent,
         "-i", narration, *extra,
         "-filter_complex", af,
         "-vf", f"subtitles='{srt_esc}':force_style='{style}'",
         "-map", "0:v", "-map", "[a]",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
         "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
         "-pix_fmt", "yuv420p", "-movflags", "+faststart", final])
    print("final:", final, f"{dur(final):.1f}s", f"{os.path.getsize(final)} bytes")


def cmd_distribute(jid):
    print("DISTRIBUTE: 원본 마스터 보관 + 업로드 가이드", flush=True)
    base = job_dir(jid)
    job = load_job(jid)
    src = os.path.join(base, "final.mp4")
    master_dir = os.path.join(base, "master")
    os.makedirs(master_dir, exist_ok=True)
    master = os.path.join(master_dir, "master_clean.mp4")
    if not os.path.exists(master):
        import shutil
        shutil.copy2(src, master)
    tags = "#한국미스터리 #조선왕조실록 #역사미스터리 #괴담 #미해결사건"
    guide = f"""# 업로드 가이드 — {jid} (한국어 숏폼)

⚠️ 틱톡에서 내려받은 영상(워터마크)은 절대 다른 플랫폼에 올리지 마세요.
항상 `master/master_clean.mp4` 를 사용할 것.

## 원본
- {master}

## 1) 틱톡 (당일)
- 틱톡 앱 → 업로드 → master_clean.mp4
- 캡션 첫 줄: "{job['topic']} — 조선 실록에 남은 기록"
- 해시태그: {tags}
- **AI 생성 표시 ON**, 공개, 1분 이상 확인

## 2) 유튜브 쇼츠 (1~2일 뒤)
- 스튜디오 → 만들기 → 쇼츠 → 같은 원본
- 제목: {job['title']} #shorts
- 설명 첫 줄에 검색 키워드 반복

## 3) 인스타 릴스 (선택)
- 같은 원본 업로드

## 수익화
- 틱톡 CRP: 팔로워 1만 + 30일 10만뷰 + 1분+ (한국어 2X)
- 유튜브 쇼츠: 구독자 500 + 90일 3천만뷰
"""
    out = os.path.join(base, "UPLOAD_GUIDE.md")
    open(out, "w", encoding="utf-8").write(guide)
    print("guide:", out)


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description="한국어 숏폼 파이프라인 (틱톡/쇼츠)")
    ap.add_argument("command", choices=[
        "all", "script", "images", "tts", "i2v", "render", "distribute"])
    ap.add_argument("topic", nargs="?", help="주제 (script/all)")
    ap.add_argument("--job", help="job id")
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
    if args.command in ("images", "all"):
        cmd_images(jid)
    if args.command in ("tts", "all"):
        cmd_tts(jid)
    if args.command in ("i2v", "all"):
        cmd_i2v(jid)
    if args.command in ("render", "all"):
        cmd_render(jid)
    if args.command in ("distribute", "all"):
        cmd_distribute(jid)


if __name__ == "__main__":
    main()
