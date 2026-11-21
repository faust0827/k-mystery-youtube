#!/usr/bin/env python3
"""Render the 3 Shorts (vertical 1080x1920) for video 04."""
import asyncio, glob, os, subprocess, sys

BASE = "/home/j/문서/project/youtube/4"
ROOT = "/home/j/문서/project/youtube"
VO = os.path.join(BASE, "vo")
SHORTS = os.path.join(ROOT, "shorts", "video04")
OUTDIR = os.path.join(ROOT, "shorts", "video04")
CARDS = os.path.join(BASE, "source_cards")
BGM = os.path.join(ROOT, "1", "Missing Persons - Jeremy Blake.mp3")
W, H, FPS = 1080, 1920, 30
VOICE = "en-US-GuyNeural"

SHORTS_CFG = [
    dict(name="short1_kings_secret_shaman", text="shorts/video04/short1.txt",
         images=["1/1.jpg","1/3.jpg","3/1.jpg","1/8.jpg"],
         card="card1_1477.png", card_at=20),
    dict(name="short2_dragon_robe", text="shorts/video04/short2.txt",
         images=["2/7.png","2/8.png","3/6.jpg","1/4.jpg"],
         card="card5_1684.png", card_at=14),
    dict(name="short3_why_ban_failed", text="shorts/video04/short3.txt",
         images=["2/1.jpg","2/3.png","3/8.jpg","3/9.jpg","1/2.jpg"],
         card="card2_1431.png", card_at=8),
]


def run(cmd, **kw):
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kw)
    if r.returncode != 0:
        print("FAILED:", " ".join(cmd))
        print(r.stderr.decode()[-2000:])
        raise SystemExit(1)


def dur(p):
    return float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",p]).decode().strip())


async def synth(text_path, wav_path):
    import edge_tts
    text = open(text_path, encoding="utf-8").read().strip()
    c = edge_tts.Communicate(text, voice=VOICE, rate="-10%", pitch="-2Hz")
    mp3 = wav_path.replace(".wav", ".mp3")
    await c.save(mp3)
    run(["ffmpeg","-y","-v","error","-i",mp3,"-ar","48000","-ac","2","-c:a","pcm_s16le",wav_path])
    os.remove(mp3)


def make_srt(wav_path, text_path, srt_path):
    import re
    d = dur(wav_path)
    text = open(text_path, encoding="utf-8").read().strip()
    parts = re.split(r"(?<=[.!?])\s+", text)
    caps = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if len(p) <= 26:
            caps.append(p); continue
        cur = ""
        for w in p.split():
            if len(cur)+len(w)+1 <= 26:
                cur = (cur+" "+w).strip()
            else:
                if cur: caps.append(cur)
                cur = w
        if cur: caps.append(cur)
    merged = []
    for c in caps:
        if merged and (len(c) < 12 or len(merged[-1]) < 12) and len(merged[-1])+1+len(c) <= 30:
            merged[-1] = merged[-1] + " " + c
        else:
            merged.append(c)
    caps = merged
    chars = sum(len(c) for c in caps) or 1
    t0 = 0.0
    lines = []
    idx = 1
    for c in caps:
        share = max(d * (len(c)/chars), 0.8)
        a, b = t0, t0 + share
        def fmt(x):
            h=int(x//3600); m=int((x%3600)//60); s=int(x%60); ms=int(round((x-int(x))*1000))
            if ms==1000: s+=1; ms=0
            return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
        lines.append(f"{idx}\n{fmt(a)} --> {fmt(b)}\n{c}\n")
        t0 = b
        idx += 1
    open(srt_path, "w", encoding="utf-8").write("\n".join(lines))


def segment(img, out, seconds, zoom_in):
    frames = max(2, int(round(seconds * FPS)))
    if zoom_in:
        z = "min(zoom+0.0012,1.18)"
    else:
        z = "if(eq(on,0),1.18,max(zoom-0.0012,1.0))"
    vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,"
          f"crop={W}:{H},"
          f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
          f":d={frames}:s={W}x{H}:fps={FPS}")
    run(["ffmpeg","-y","-v","error","-loop","1","-i",img,
         "-vf",vf,"-frames:v",str(frames),"-r",str(FPS),
         "-c:v","libx264","-preset","veryfast","-crf","20",
         "-pix_fmt","yuv420p",out])


def render_one(cfg):
    name = cfg["name"]
    tmp = os.path.join(BASE, "build", "_tmp_" + name)
    os.makedirs(tmp, exist_ok=True)
    os.makedirs(OUTDIR, exist_ok=True)
    text_path = os.path.join(ROOT, cfg["text"])
    wav_path = os.path.join(VO, name + ".wav")
    srt_path = os.path.join(VO, name + "_short.srt")
    out_path = os.path.join(OUTDIR, name + ".mp4")

    print(f"\n=== {name} ===")
    if not os.path.exists(wav_path):
        asyncio.run(synth(text_path, wav_path))
    d = dur(wav_path)
    print(f"audio {d:.1f}s")
    make_srt(wav_path, text_path, srt_path)

    imgs = [os.path.join(ROOT, p) for p in cfg["images"]]
    nshots = max(3, min(6, int(round(d / 7))))
    per = d / nshots
    segs = []
    for i in range(nshots):
        img = imgs[i % len(imgs)]
        zoom_in = (i % 2 == 0)
        seg = os.path.join(tmp, f"seg_{i:02d}.mp4")
        if not os.path.exists(seg):
            segment(img, seg, per, zoom_in)
        segs.append(seg)
    lst = os.path.join(tmp, "list.txt")
    with open(lst, "w") as fh:
        for s in segs:
            fh.write(f"file '{s}'\n")
    base = os.path.join(tmp, "base.mp4")
    run(["ffmpeg","-y","-v","error","-f","concat","-safe","0","-i",lst,"-c","copy",base])

    card = os.path.join(CARDS, cfg["card"])
    card_clip = os.path.join(tmp, "cardclip.mp4")
    if not os.path.exists(card_clip):
        run(["ffmpeg","-y","-v","error","-loop","1","-t","5","-i",card,
             "-vf", f"scale={W}:-1,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:black",
             "-r",str(FPS),"-c:v","libx264","-preset","veryfast","-crf","20",
             "-pix_fmt","yuv420p", card_clip])
    card_at = cfg["card_at"]
    if card_at + 5 <= d:
        out_cards = os.path.join(tmp, "cards.mp4")
        run(["ffmpeg","-y","-v","error","-i",base,
             "-itsoffset",f"{card_at:.2f}","-i",card_clip,
             "-filter_complex",
             f"[0:v][1:v]overlay=enable='between(t\\,{card_at:.2f}\\,{card_at+5:.2f})':eof_action=pass[v]",
             "-map","[v]","-c:v","libx264","-preset","veryfast","-crf","20",
             "-pix_fmt","yuv420p", out_cards])
    else:
        out_cards = base

    burned_srt = srt_path
    if card_at + 5 <= d:
        w0, w1 = card_at, card_at + 5
        def sec(t):
            h,m,r = t.split(":"); s,ms = r.split(",")
            return int(h)*3600+int(m)*60+int(s)+int(ms)/1000.0
        def fmt(x):
            h=int(x//3600); m=int((x%3600)//60); s=int(x%60); ms=int(round((x-int(x))*1000))
            if ms==1000: s+=1; ms=0
            return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
        blocks = open(srt_path,encoding="utf-8").read().strip().split("\n\n")
        kept=[]; n=0
        for b in blocks:
            lines=b.split("\n")
            if len(lines)<3: continue
            a,bb=[x.strip() for x in lines[1].split("-->")]
            a,bb=sec(a),sec(bb)
            if a < w1 and bb > w0:
                if a <= w0:
                    bb=min(bb,w0-0.05)
                elif bb >= w1:
                    a=max(a,w1+0.05)
                else:
                    bb=a
            if bb-a < 0.4: continue
            n+=1
            kept.append(f"{n}\n{fmt(a)} --> {fmt(bb)}\n"+"\n".join(lines[2:]))
        burned_srt = os.path.join(tmp,"stripped.srt")
        open(burned_srt,"w",encoding="utf-8").write("\n\n".join(kept)+"\n")

    style = ("FontName=DejaVu Sans,FontSize=18,PrimaryColour=&H00FFFFFF,"
             "OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=0,"
             "Alignment=2,MarginV=260")
    srt_esc = burned_srt.replace("\\","/").replace(":","\\:").replace("'","\\'")
    run(["ffmpeg","-y","-v","error","-i",out_cards,
         "-i",wav_path,"-i",BGM,"-t",str(d),
         "-filter_complex",
         "[1:a]volume=1.0,asplit=2[n1][n2];"
         "[2:a]volume=0.20,aloop=loop=-1:size=2e9[bg];"
         "[bg][n1]sidechaincompress=threshold=0.02:ratio=4:attack=5:release=400[duck];"
         "[n2][duck]amix=inputs=2:duration=first:dropout_transition=0,"
         "loudnorm=I=-16:TP=-1.5:LRA=11[a]",
         "-vf", f"subtitles='{srt_esc}':force_style='{style}'",
         "-map","0:v","-map","[a]",
         "-c:v","libx264","-preset","veryfast","-crf","20",
         "-c:a","aac","-b:a","160k","-ar","48000","-pix_fmt","yuv420p",
         "-movflags","+faststart", out_path])
    print(f"done: {out_path} ({dur(out_path):.1f}s)")


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    for cfg in SHORTS_CFG:
        render_one(cfg)
    print("\nAll shorts rendered to", OUTDIR)


if __name__ == "__main__":
    main()
