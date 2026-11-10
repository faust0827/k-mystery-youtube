#!/usr/bin/env python3
"""Render a rough cut of video 04 (720p) from existing stills + scratch VO.

Usage:
  python3 build/render.py            # full render
  python3 build/render.py --test 90  # first 90 seconds only
"""
import argparse, glob, json, os, subprocess, sys

BASE = "/home/j/문서/project/youtube/4"
ROOT = "/home/j/문서/project/youtube"
TMP = os.path.join(BASE, "build", "_tmp")
VO = os.path.join(BASE, "vo")
CARDS = os.path.join(BASE, "source_cards")
SRT = os.path.join(VO, "narration_clean.srt")
BGM = os.path.join(ROOT, "1", "Missing Persons - Jeremy Blake.mp3")

W, H, FPS = 1920, 1080, 30

SECTIONS = [
    ("01_coldopen",  ["1/1.jpg", "1/2.jpg", "1/3.jpg", "1/4.jpg", "1/5.jpg"]),
    ("02_law",       ["2/1.jpg", "2/2.png", "2/3.png", "2/4.png", "3/1.jpg", "3/2.jpg", "2/5.png"]),
    ("03_starshine", ["3/3.jpg", "3/4.jpg", "3/5.jpg", "1/6.jpg", "1/7.jpg"]),
    ("04_crackdown", ["2/6.png", "2/7.png", "2/8.png", "3/6.jpg", "3/7.jpg"]),
    ("05_why",       ["2/1.jpg", "2/3.png", "3/8.jpg", "1/8.jpg", "3/9.jpg"]),
    ("06_survived",  ["3/10.jpg", "1/2.jpg", "1/4.jpg", "2/4.png", "3/5.jpg"]),
    ("07_price",     ["1/3.jpg", "1/5.jpg", "3/2.jpg", "2/2.png"]),
    ("08_close",     ["3/9.jpg", "1/1.jpg", "3/10.jpg"]),
]

CARD_AT = {  # section index -> list of (offset_seconds, card file)
    0: [(22, "card1_1477.png")],
    1: [(55, "card2_1431.png")],
    2: [(70, "card3_1503.png")],
    3: [(20, "card4_1478.png"), (95, "card5_1684.png"), (120, "card6_1743.png")],
}


def run(cmd, **kw):
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kw)
    if r.returncode != 0:
        print("FAILED:", " ".join(cmd))
        print(r.stderr.decode()[-3000:])
        sys.exit(1)
    return r.stdout.decode()


def dur(path):
    return float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "csv=p=0", path]).decode().strip())


def segment(img, out, seconds, zoom_in):
    frames = max(2, int(round(seconds * FPS)))
    if zoom_in:
        z = "min(zoom+0.0009,1.14)"
    else:
        z = "if(eq(on,0),1.14,max(zoom-0.0009,1.0))"
    vf = (
        f"scale={W}:{H}:force_original_aspect_ratio=increase,"
        f"crop={W}:{H},"
        f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        f":d={frames}:s={W}x{H}:fps={FPS}"
    )
    run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", img,
         "-vf", vf, "-frames:v", str(frames), "-r", str(FPS),
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
         "-pix_fmt", "yuv420p", out])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", type=float, default=0)
    args = ap.parse_args()

    os.makedirs(TMP, exist_ok=True)
    files = sorted(glob.glob(os.path.join(VO, "[0-9]*.wav")))
    durs = {os.path.basename(f)[:2]: dur(f) for f in files}

    # build shot timeline
    shots = []
    cursor = 0.0
    for idx, (name, pool) in enumerate(SECTIONS):
        key = name[:2]
        d = durs[key] + (0.55 if idx < len(SECTIONS) - 1 else 0)
        per = max(4.0, min(9.0, d / max(1, len(pool))))
        n = max(1, int(round(d / per)))
        for i in range(n):
            img = pool[i % len(pool)]
            zoom_in = (i % 2 == 0)
            shots.append(dict(img=os.path.join(ROOT, img), dur=d / n, zoom_in=zoom_in,
                              section=idx, start=cursor))
            cursor += d / n

    total = cursor
    limit = min(total, args.test) if args.test else total
    print(f"shots={len(shots)} total={total:.1f}s limit={limit:.1f}s")

    # segments
    seg_files = []
    for i, s in enumerate(shots):
        if s["start"] >= limit:
            break
        d = min(s["dur"], limit - s["start"])
        if d < 0.5:
            break
        out = os.path.join(TMP, f"seg_{i:03d}.mp4")
        if not os.path.exists(out) or abs(dur(out) - d) > 0.15:
            segment(s["img"], out, d, s["zoom_in"])
        seg_files.append(out)
        if i % 10 == 0:
            print("  segment", i, f"{d:.1f}s")

    lst = os.path.join(TMP, "list.txt")
    with open(lst, "w") as fh:
        for f in seg_files:
            fh.write(f"file '{f}'\n")
    base = os.path.join(TMP, "base.mp4")
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
         "-i", lst, "-c", "copy", base])
    print("base:", f"{dur(base):.1f}s")

    # cards overlay (pre-rendered 5s clips, no alpha fades)
    card_clips = []
    for idx, items in CARD_AT.items():
        sec_start = sum(durs[SECTIONS[j][0][:2]] + (0.55 if j < len(SECTIONS) - 1 else 0)
                        for j in range(idx))
        for off, card in items:
            t0 = sec_start + off
            if t0 >= limit - 6:
                continue
            clip = os.path.join(TMP, "clip_" + card.replace(".png", ".mp4"))
            if not os.path.exists(clip):
                run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-t", "5",
                     "-i", os.path.join(CARDS, card),
                     "-vf", f"scale={W}:{H}", "-r", str(FPS),
                     "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                     "-pix_fmt", "yuv420p", clip])
            card_clips.append((clip, t0))

    inputs = ["-i", base]
    filt = []
    last = "0:v"
    for k, (clip, t0) in enumerate(card_clips):
        idx_in = k + 1
        inputs += ["-itsoffset", f"{t0:.2f}", "-i", clip]
        filt.append(f"[{last}][{idx_in}:v]overlay="
                    f"enable='between(t\\,{t0:.2f}\\,{t0 + 5:.2f})'"
                    f":eof_action=pass[v{k}]")
        last = f"v{k}"

    if card_clips:
        out_cards = os.path.join(TMP, "cards.mp4")
        run(["ffmpeg", "-y", "-v", "error", *inputs,
             "-filter_complex", ";".join(filt), "-map", f"[{last}]",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
             "-pix_fmt", "yuv420p", out_cards])
        print("cards:", f"{dur(out_cards):.1f}s")
    else:
        out_cards = base

    # strip captions that fall inside card windows
    burned_srt = SRT
    if card_clips:
        import re as _re
        def _sec(t):
            h, m, rest = t.split(":")
            sec, ms = rest.split(",")
            return int(h) * 3600 + int(m) * 60 + int(sec) + int(ms) / 1000.0
        wins = [(t0, t0 + 5) for _, t0 in card_clips]
        blocks = open(SRT, encoding="utf-8").read().strip().split("\n\n")
        kept, n = [], 0
        for b in blocks:
            lines = b.split("\n")
            if len(lines) < 3:
                continue
            a, bb = [x.strip() for x in lines[1].split("-->")]
            a, bb = _sec(a), _sec(bb)
            for w0, w1 in wins:
                if a < w1 and bb > w0:
                    if a <= w0:
                        bb = min(bb, w0 - 0.05)      # keep, end before card
                    elif bb >= w1:
                        a = max(a, w1 + 0.05)        # keep, start after card
                    else:
                        bb = a                        # fully inside: drop
                    break
            if bb - a < 0.5:
                continue
            n += 1
            def _fmt(t):
                h = int(t // 3600); m = int((t % 3600) // 60); sec = int(t % 60)
                ms = int(round((t - int(t)) * 1000))
                if ms == 1000:
                    sec += 1; ms = 0
                return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"
            kept.append(f"{n}\n{_fmt(a)} --> {_fmt(bb)}\n" + "\n".join(lines[2:]))
        burned_srt = os.path.join(TMP, "cards_stripped.srt")
        open(burned_srt, "w", encoding="utf-8").write("\n\n".join(kept) + "\n")
        print("captions:", len(kept), "of", len(blocks))

    # subtitles + audio mix
    final = os.path.join(BASE, "roughcut.mp4")
    srt_esc = burned_srt.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
    style = ("FontName=DejaVu Sans,FontSize=22,PrimaryColour=&H00FFFFFF,"
             "OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=0,"
             "Alignment=2,MarginV=40")
    af = (
        "[1:a]volume=1.0,asplit=2[nar1][nar2];"
        "[2:a]volume=0.20,aloop=loop=-1:size=2e9[bg];"
        "[bg][nar1]sidechaincompress=threshold=0.02:ratio=4:attack=5:release=400[duck];"
        "[nar2][duck]amix=inputs=2:duration=first:dropout_transition=0,"
        "loudnorm=I=-16:TP=-1.5:LRA=11[a]"
    )
    run(["ffmpeg", "-y", "-v", "error", "-i", out_cards,
         "-i", os.path.join(VO, "narration.wav"), "-i", BGM,
         "-t", str(limit),
         "-filter_complex", af,
         "-vf", f"subtitles='{srt_esc}':force_style='{style}'",
         "-map", "0:v", "-map", "[a]",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
         "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-pix_fmt", "yuv420p",
         "-movflags", "+faststart", final])
    print("done:", final, f"{dur(final):.1f}s")


if __name__ == "__main__":
    main()
