#!/usr/bin/env python3
"""Smoke test: Kling 2.6 image-to-video 5초 클립 1개 (약 $0.21)."""
import base64
import json
import os
import sys
import time

import requests

ROOT = "/home/j/문서/project/youtube"
ENV = os.path.join(ROOT, ".env")
IMAGE = os.path.join(ROOT, "auto", "_smoke_image.jpg")
OUT = os.path.join(ROOT, "auto", "_smoke_clip.mp4")
BASE = "https://api-singapore.klingai.com"


def load_env(path):
    out = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                out[k] = v.strip()
    return out


def post(session, path, body):
    r = session.post(BASE + path, json=body, timeout=120)
    print("POST", path, "->", r.status_code, flush=True)
    if r.status_code != 200:
        print(r.text[:2000])
    return r


def main():
    key = load_env(ENV).get("KLING_API_KEY")
    if not key:
        sys.exit("KLING_API_KEY not found")
    if not os.path.exists(IMAGE):
        sys.exit("first run smoke_gemini.py")

    b64 = base64.b64encode(open(IMAGE, "rb").read()).decode("ascii")
    prompt = (
        "Slow cinematic camera pan through a dark Joseon palace corridor at night, "
        "thin fog drifting, paper lantern light flickering gently, low saturation, "
        "no people walking, no text"
    )

    session = requests.Session()
    session.headers.update({
        "Authorization": "Bearer " + key,
        "Content-Type": "application/json",
    })

    body = {
        "model_name": "kling-v2-6",
        "image": b64,
        "prompt": prompt,
        "duration": "5",
        "mode": "std",
        "aspect_ratio": "16:9",
    }
    r = post(session, "/v1/videos/image2video", body)
    if r.status_code != 200:
        # 구 API가 model_name 대신 model 을 원할 수 있음
        body2 = dict(body)
        body2["model"] = body2.pop("model_name")
        r = post(session, "/v1/videos/image2video", body2)
    if r.status_code != 200:
        sys.exit(1)

    data = r.json()
    print("response:", json.dumps(data, ensure_ascii=False)[:1200], flush=True)
    task_id = (data.get("data") or {}).get("task_id")
    if not task_id:
        sys.exit("task_id not found in response")

    # poll
    for i in range(60):
        time.sleep(5)
        g = session.get(BASE + "/v1/videos/image2video/" + task_id, timeout=60)
        if g.status_code != 200:
            print("poll", i, "status", g.status_code, g.text[:300], flush=True)
            continue
        d = (g.json().get("data") or {})
        status = d.get("task_status")
        print("poll", i, status, flush=True)
        if status == "succeed":
            videos = d.get("task_result", {}).get("videos", [])
            if not videos:
                print(json.dumps(d, ensure_ascii=False)[:2000])
                sys.exit("no videos in result")
            url = videos[0].get("url")
            print("downloading:", url[:120], flush=True)
            v = requests.get(url, timeout=180)
            with open(OUT, "wb") as fh:
                fh.write(v.content)
            print("saved:", OUT, len(v.content), "bytes", flush=True)
            return
        if status in ("failed", "cancelled"):
            print(json.dumps(d, ensure_ascii=False)[:2000])
            sys.exit("task failed")

    sys.exit("timeout")


if __name__ == "__main__":
    main()
