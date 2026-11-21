#!/usr/bin/env python3
"""Smoke test: Nano Banana 2.1 이미지 1장 생성 (약 $0.034)."""
import base64
import json
import os
import sys

import requests

ROOT = "/home/j/문서/project/youtube"
ENV = os.path.join(ROOT, ".env")
OUT = os.path.join(ROOT, "auto", "_smoke_image.jpg")


def load_env(path):
    out = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                out[k] = v.strip()
    return out


def find_image(obj):
    """응답 JSON에서 base64 이미지를 재귀적으로 찾는다."""
    if isinstance(obj, dict):
        for key in ("data", "b64_json", "base64", "bytesBase64Encoded"):
            v = obj.get(key)
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


def main():
    key = load_env(ENV).get("GEMINI_API_KEY")
    if not key:
        sys.exit("GEMINI_API_KEY not found")

    url = "https://generativelanguage.googleapis.com/v1beta/interactions"
    payload = {
        "model": "gemini-nano-banana-2.1",
        "input": (
            "A dark cinematic painting of a Joseon palace corridor at night, "
            "paper lantern light, thin fog, low saturation, no text, no people"
        ),
        "response_format": {
            "type": "image",
            "mime_type": "image/jpeg",
            "aspect_ratio": "16:9",
            "image_size": "1K",
        },
    }
    print("POST", url, "model=gemini-nano-banana-2.1", flush=True)
    r = requests.post(
        url,
        headers={"x-goog-api-key": key, "Content-Type": "application/json"},
        json=payload,
        timeout=180,
    )
    print("status:", r.status_code, flush=True)
    if r.status_code != 200:
        print(r.text[:2000])
        sys.exit(1)

    data = r.json()
    print("top-level keys:", list(data.keys()), flush=True)
    with open(os.path.join(ROOT, "auto", "_smoke_response.json"), "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)

    b64 = find_image(data)
    if not b64:
        print("이미지 base64를 못 찾았습니다. 응답을 _smoke_response.json 에 저장했으니 확인해 주세요.")
        sys.exit(2)

    raw = base64.b64decode(b64)
    with open(OUT, "wb") as fh:
        fh.write(raw)
    print("saved:", OUT, len(raw), "bytes", flush=True)


if __name__ == "__main__":
    main()
