#!/usr/bin/env python3
"""Build an SRT from the TTS chunk texts + measured chunk durations.

Synthetic VO is steady, so proportional allocation inside each chunk is
accurate enough for a rough cut. Final captions come from Whisper on the
real ElevenLabs audio.
"""
import glob, os, re, subprocess, sys

BASE = "/home/j/문서/project/youtube/4"
VO = os.path.join(BASE, "vo")
GAP = 0.55


def dur(path):
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "csv=p=0", path
    ]).decode().strip()
    return float(out)


def srt_time(t):
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    ms = int(round((t - int(t)) * 1000))
    if ms == 1000:
        s += 1; ms = 0
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def split_captions(text, max_len=56):
    # sentence-ish split, then wrap
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    caps = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if len(p) <= max_len:
            caps.append(p)
            continue
        # greedy wrap on word boundaries
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
    # merge very short fragments into a neighbour
    merged = []
    for c in caps:
        if merged and (len(c) < 16 or len(merged[-1]) < 16) and len(merged[-1]) + 1 + len(c) <= 64:
            merged[-1] = merged[-1] + " " + c
        else:
            merged.append(c)
    return merged


def main():
    files = sorted(glob.glob(os.path.join(VO, "[0-9]*.wav")))
    entries = []
    t = 0.0
    for f in files:
        name = os.path.basename(f).replace(".wav", "")
        txt_path = os.path.join(BASE, "tts_chunks", name + ".txt")
        text = open(txt_path, encoding="utf-8").read()
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        caps = []
        for p in paragraphs:
            caps += split_captions(p)

        d = dur(f)
        chars = sum(len(c) for c in caps) or 1
        t0 = t
        for c in caps:
            share = d * (len(c) / chars)
            # clamp so nothing is shorter than 0.9s
            share = max(share, 0.9)
            entries.append((t0, t0 + share, c))
            t0 += share
        # if clamping pushed past chunk end, rescale inside chunk
        if t0 > t + d:
            scale = d / (t0 - t)
            entries = [(t + (a - t) * scale, t + (b - t) * scale, c) if a >= t else (a, b, c)
                       for (a, b, c) in entries]
            t0 = t + d

        t = t0 + GAP

    out = os.path.join(VO, "narration_clean.srt")
    with open(out, "w", encoding="utf-8") as fh:
        for i, (a, b, c) in enumerate(entries, 1):
            fh.write(f"{i}\n{srt_time(a)} --> {srt_time(b)}\n{c}\n\n")
    print("wrote", out, len(entries), "captions, end", srt_time(t))


if __name__ == "__main__":
    main()
