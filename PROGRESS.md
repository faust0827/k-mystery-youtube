# K-Mystery YouTube Channel - Progress

## Channel
- Name: Korean Mysteries
- Handle: @Korean_Mysteries
- URL: https://www.youtube.com/@Korean_Mysteries

## Video 01: The Korean Prince Locked in a Rice Chest
- Status: Uploaded ✅
- URL: (uploaded)
- Duration: 8:21
- Files: youtube/1/

## Video 02: Korea's Most Haunted Psychiatric Hospital
- Status: Uploaded ✅
- URL: https://youtu.be/TYOcCE4zp30
- Duration: 6:45
- Files: youtube/2/

## Video 03: Joseon Annals Recorded 'UFOs' 400 Years Ago
- Status: Uploaded ✅
- URL: https://youtu.be/xFBrv3fdRC4
- Duration: 8:02
- Files: youtube/3/

## Pipeline
1. Script (English documentary style)
2. TTS (EC2 ElevenLabs, Adam voice)
3. Whisper subtitles (English, CPU)
4. Images (Leonardo.ai/Krea/ChatGPT)
5. FFmpeg (Ken Burns + subtitles + audio)
6. BGM (YouTube Audio Library)
7. Intro prepend (intro_5s.mp4)
8. Metadata (title, description, tags, timestamps)
9. Upload (PostWire API)

## Infrastructure
- EC2: 54.116.201.144 (Seoul, t3.micro)
- TTS: port 80 /tts (ElevenLabs)
- Email: port 80 /send-email (Gmail SMTP)
- Nginx reverse proxy

## OpenCode Improvements (2026-11-10)
- thumbnails/design_specs.md — 3 thumbnail redesigns (2 per video)
- metadata/video1.md, video2.md, video3.md — new titles/descriptions/tags
- plan/12week.md — 12-week upload plan (longform 1/week, Shorts 3/week, 30 topics)
- shorts/docs/shorts_scripts.md — 6 Shorts scripts from existing videos

## Thumbnails generated (OpenCode, 2026-11-10)
- thumbnails/v1_a_buried_alive.png, v1_b_8days.png
- thumbnails/v2_a_42died.png, v2_b_dont_go.png
- thumbnails/v3_a_ufos1450.png, v3_b_korea_saw.png
- 1280x720, source stills from 1/, 2/, 3/ + text overlay + K-MYSTERY mark

## Video 04 rewrite (2026-11-10)
- New script: `4/script_04_shamanism_v2.md`
- Angle changed: "what shamanism is" → "500-year ban that the palace itself kept breaking" (Annals-based)
- Old narration (`4/narration_04*.mp3`) is obsolete — must re-TTS from v2
- Structure: cold open (1477 palace ritual) → law (1431) → Star Shrine → failed crackdowns → why → survival → sinbyeong → close
- Includes 8 on-screen source cards (Korean + English) — channel signature

## Video 04 production assets (2026-11-10)
- `4/source_cards/` — 실록 원문 카드 6장 (1920x1080, 한자/한글 + 영어 + 출처)
- `4/tts_chunks/` — 나레이션 8청크 (1,327 words ≈ 9.5~10분)
- `4/prompts/images.md` — 샷 리스트 50개 + 레오나르도 프롬프트
- `shorts/video04/` — Shorts 3개 완성 (1080x1920, 41/36/43초, Edge TTS, 카드 오버레이)
  - `short1_kings_secret_shaman.mp4`
  - `short2_dragon_robe.mp4`
  - `short3_why_ban_failed.mp4`
- `4/PRODUCTION_PLAN.md` — 제작 순서/체크리스트
- `thumbnails/v4_a_banned.png`, `v4_b_secret.png` — 4편 썸네일 초안
- 사실 수정: 성수청 인용 1503년 2월(연산군일기), 무세는 1464년 명부 작성 기준으로 정정
- `4/build/` — 렌더 파이프라인 (`make_srt.py`, `render.py`, `README.md`)
- `4/vo/` — Piper 임시 나레이션 8청크 + 합본 + 자막 (최종은 ElevenLabs로 교체)
- `4/roughcut_720p.mp4` — 720p 러프컷 (10:10, -16.1 LUFS, Edge TTS GuyNeural)
- `4/final_04.mp4` — 최종본 1080p 30fps (10:15, 인트로 5s + 본편, -16.1 LUFS, 오디오 포함)
- `4/metadata.md` — 제목 3안·설명·태그·고정댓글 (챕터는 러프컷 기준, 재TTS 후 재계산 필요)

## Next Steps
- Create thumbnail images (Canva/Leonardo)
- Generate Shorts videos from scripts
- SSH port restriction
- Channel art/profile image
EOF
## Thumbnail Decision
- **확정**: `thumbnails/v4_FINAL.png` (= `v4_a_banned.png`, 붉은 달 + "BANNED / FOR 500 YEARS")
  - 선정 이유: 6글자 한 덩어리 → 모바일에서 가장 크게 읽힘, 빨간 액센트가 "금지" 감정을 즉시 전달, 3/1.jpg의 붉은 달이 미스터리 톤과 맞음.
- 대안: `v4_b_secret.png` ("THE KING'S / SECRET SHAMAN") — A/B 테스트 시 사용.
- 최종 업로드 전 1280x720 PNG 그대로 사용 (이미 규격 충족).
