#!/usr/bin/env python3
"""PostWire REST로 YouTube unlisted 업로드."""
import json
import os
import sys
import uuid

import requests

ROOT = "/home/j/문서/project/youtube"
JOB = os.path.join(ROOT, "auto", "jobs", "20261121_110928")
VIDEO = os.path.join(JOB, "final_small.mp4")
PAYLOAD = os.path.join(JOB, "post_payload.json")
BASE = "https://postwire.io"


def load_env():
    out = {}
    with open(os.path.join(ROOT, ".env"), encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                out[k] = v.strip()
    return out


def main():
    key = load_env().get("POSTWIRE_API_KEY")
    if not key:
        sys.exit("POSTWIRE_API_KEY missing")
    size = os.path.getsize(VIDEO)
    print("video:", VIDEO, size, "bytes")

    h = {"Authorization": "Bearer " + key, "Content-Type": "application/json",
         "X-PostWire-Source": "mcp-sk-youtube"}

    # 1) 업로드 URL
    r = requests.post(BASE + "/api/media/upload-url", headers=h,
                      json={"content_type": "video/mp4",
                            "size_bytes": size, "multipart": True},
                      timeout=60)
    print("upload-url:", r.status_code, flush=True)
    if r.status_code not in (200, 201):
        print(r.text[:1500]); sys.exit(1)
    info = r.json()
    print("upload info keys:", list(info.keys()), flush=True)

    # 2) 파트별 PUT
    parts = info.get("parts") or info.get("upload_urls") or []
    path = info.get("path")
    if not parts:
        # 단일 URL 폴백
        url = info.get("upload_url")
        if not url:
            print(json.dumps(info, ensure_ascii=False)[:2000])
            sys.exit("no upload url in response")
        with open(VIDEO, "rb") as fh:
            p = requests.put(url, data=fh, timeout=600)
        print("PUT:", p.status_code, flush=True)
        if p.status_code not in (200, 201, 204):
            print(p.text[:1000]); sys.exit(1)
    else:
        with open(VIDEO, "rb") as fh:
            for i, part in enumerate(parts):
                url = part.get("upload_url") or part.get("url")
                start = part.get("start", 0)
                end = part.get("end", size)
                fh.seek(start)
                chunk = fh.read(end - start)
                p = requests.put(url, data=chunk, timeout=600)
                print("PUT part", i, p.status_code, flush=True)
                if p.status_code not in (200, 201, 204):
                    print(p.text[:1000]); sys.exit(1)

    # 3) finalize
    f = requests.get(BASE + "/api/media/finalize", headers=h,
                     params={"path": path}, timeout=60)
    print("finalize:", f.status_code, flush=True)
    if f.status_code != 200:
        print(f.text[:1500]); sys.exit(1)
    media_url = f.json().get("media_url")
    if not media_url:
        print(json.dumps(f.json(), ensure_ascii=False)[:1500])
        sys.exit("no media_url")
    print("media_url obtained:", media_url[:100], flush=True)

    # 4) post
    payload = json.load(open(PAYLOAD, encoding="utf-8"))
    payload["video_url"] = media_url
    payload["idempotency_key"] = "km-yeonsangun-" + uuid.uuid4().hex[:12]
    p = requests.post(BASE + "/api/post", headers=h, json=payload, timeout=120)
    print("post:", p.status_code, flush=True)
    print(p.text[:3000], flush=True)
    with open(os.path.join(JOB, "upload_result.json"), "w", encoding="utf-8") as fh:
        json.dump({"status": p.status_code, "body": p.text,
                   "media_url": media_url}, fh, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
