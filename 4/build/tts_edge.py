#!/usr/bin/env python3
"""Generate narration with Edge TTS (en-US-GuyNeural) for video 04."""
import asyncio, glob, os, subprocess, sys

BASE = "/home/j/문서/project/youtube/4"
VO = os.path.join(BASE, "vo")
CHUNKS = os.path.join(BASE, "tts_chunks")
GAP = 0.55
VOICE = "en-US-GuyNeural"
RATE = "-10%"
PITCH = "-2Hz"


async def synth_one(name, text):
    import edge_tts
    mp3 = os.path.join(VO, name + ".mp3")
    wav = os.path.join(VO, name + ".wav")
    c = edge_tts.Communicate(text.strip(), voice=VOICE, rate=RATE, pitch=PITCH)
    await c.save(mp3)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", mp3,
                    "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", wav],
                   check=True)
    os.remove(mp3)
    print("  ", name, "done")


async def main():
    os.makedirs(VO, exist_ok=True)
    files = sorted(glob.glob(os.path.join(CHUNKS, "*.txt")))
    for f in files:
        name = os.path.splitext(os.path.basename(f))[0]
        text = open(f, encoding="utf-8").read()
        await synth_one(name, text)

    gap = os.path.join(VO, "_gap.wav")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
                    "-i", "anullsrc=r=48000:cl=stereo", "-t", str(GAP),
                    "-c:a", "pcm_s16le", gap], check=True)
    lst = os.path.join(VO, "_list.txt")
    wavs = sorted(glob.glob(os.path.join(VO, "[0-9]*.wav")))
    entries = []
    for i, p in enumerate(wavs):
        entries.append(p)
        if i < len(wavs) - 1:
            entries.append(gap)
    with open(lst, "w") as fh:
        for p in entries:
            fh.write(f"file '{p}'\n")
    nar = os.path.join(VO, "narration.wav")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
                    "-i", lst, "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
                    "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", nar],
                   check=True)
    print("narration.wav written")
    subprocess.run([sys.executable, os.path.join(BASE, "build", "make_srt.py")], check=True)


if __name__ == "__main__":
    asyncio.run(main())
