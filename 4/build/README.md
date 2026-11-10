# Video 04 Build Pipeline

현재 이 폴더의 파이프라인은 **러프컷 검증용**입니다. 오디오는 Piper(무료 TTS)로 만든 임시 나레이션이고,
이미지는 1·2·3편 스틸을 재사용했습니다. 최종본은 아래 "최종 교체" 절차만 거치면 됩니다.

## 구성

```
4/
  script_04_shamanism_v2.md   대본 (원본)
  tts_chunks/*.txt            나레이션 8청크 (TTS 입력)
  vo/*.wav                    청크별 오디오  ← 최종은 ElevenLabs 출력으로 교체
  vo/narration.wav            합친 나레이션
  vo/narration_clean.srt      자막 (대본 텍스트 + 청크 길이 기반)
  source_cards/*.png          실록 카드 6장
  prompts/images.md           샷 리스트 50개 + 이미지 프롬프트
  build/make_srt.py           청크 오디오 → SRT
  build/render.py             스틸 + 오디오 + 자막 + 카드 + BGM → mp4
  roughcut.mp4                결과물
```

## 실행

```bash
cd 4
python3 build/make_srt.py      # vo/*.wav 길이로 자막 재생성
python3 build/render.py        # 전체 렌더 (720p)
python3 build/render.py --test 90   # 앞 90초만
```

## 렌더 구조

1. 섹션(8개)별로 스틸을 균등 배분, 4~9초/샷
2. 샷마다 zoompan (짝수=줌인, 홀수=줌아웃) → `build/_tmp/seg_*.mp4`
3. concat → `base.mp4`
4. 실록 카드 5초 오버레이 (`CARD_AT`에서 시점 지정)
5. 카드 구간과 겹치는 자막은 자동 제거
6. 나레이션 + BGM(사이드체인 덕킹) + loudnorm(-16 LUFS)
7. 자막 burn-in → `roughcut.mp4`

## 최종 교체 절차

1. `tts_chunks/*.txt`를 ElevenLabs에 넣고 결과를 `vo/01_coldopen.wav` … `vo/08_close.wav` 로 저장
   (파일명 유지 → 스크립트 수정 불필요)
2. `python3 build/make_srt.py`
   - 실제 음성 기준으로 정확히 맞추려면 Whisper로 `vo/narration.wav`를 받아
     `vo/narration.srt` 생성 후 `SRT` 상수를 그 파일로 바꿔도 됨
3. `4/img/`에 생성 이미지 50장을 넣고 `build/render.py`의 `SECTIONS` 경로 수정
4. `python3 build/render.py`
5. 인트로 삽입 (**타임스탬프가 5초 밀리므로 반드시 마지막에**)
   ```bash
   cd .. && ./prepend_intro.sh 4/roughcut.mp4 4/final_04.mp4
   ```
6. 썸네일 확정 → 업로드 (사용자 승인 후)

## 주의

- 카드 구간은 자막이 비어야 함 (스크립트에서 자동 처리)
- 카드와 겹치는 자막은 잘라냄(trim). 완전히 안에 들어간 자막만 삭제.
- 자막 스타일: `FontSize=15`, `MarginV=26` (libass는 384 기준으로 스케일 → 720p에서 약 28px)
- BGM은 1편에서 쓴 `Missing Persons - Jeremy Blake.mp3` 재사용 중. 최종은 4편 톤에 맞게 교체 권장.
- **최종 렌더는 1920x1080 / 30fps**로 할 것. `intro_5s.mp4`가 1080p 30fps라서 프레임레이트가 다르면
  `prepend_intro.sh`(stream copy)가 깨집니다. `W,H,FPS` 상수와 `FontSize`(22)를 함께 수정.
- 오디오는 `-ar 48000`으로 출력 (YouTube 권장).
