# K-Mystery YouTube 자동화 — 최종 확정판

> 확정일: 2026-11-21
> 채널: K-Mystery (@Korean_Mysteries), 영어권 타겟
> 롱폼 1편/주 = **월 4편**, Shorts는 보류

---

## 1. 확정 사항 (한 장 요약)

| 항목 | 결정 |
|---|---|
| 대본 | `opencode run` (비대화형 CLI) → 8개 섹션 JSON |
| 이미지 | **나노바나나 2.1**, 8장, **세미리얼 시네마틱 일러스트** |
| 이미지 스타일 | `auto/STYLE.md` 앵커 고정 (실사❌ 애니❌, 중간 톤) |
| i2v | **Kling 2.6, 5초, 전 섹션 8개** (실록 카드만 제외) |
| 움직임 | ping-pong 10초 사이클 + zoompan 누적 |
| TTS | **완전 무료 Edge TTS**, `en-US-GuyNeural` |
| 자막 | 기존 `make_srt.py` 로직 (청크 길이 기반) |
| BGM | 기존 구글 무료 음악 + 사이드체인 덕킹 유지 |
| 실록 카드 | 기존 2D 그래픽 6장 유지 (텍스트 선명도 우선) |
| 조립 | 기존 `render.py` 로직 재사용 (segment만 i2v 클립화) |
| 인트로 | `intro_5s.mp4` 5초, **마지막에** prepend |
| 업로드 | **PostWire API** 유지 (`post_payload.json`) |
| 썸네일 | 기존 확정안 `v4_FINAL.png` ("BANNED FOR 500 YEARS") 유지 |

---

## 2. 파이프라인

```
주제 한 줄
 → ① opencode run → 8섹션 JSON
 → ② 나노바나나 → 이미지 8장 (세미리얼 앵커)
 → ③ Edge TTS → 섹션 오디오 + SRT
 → ④ Kling 2.6 i2v → 5초 클립 8개
 → ⑤ ping-pong(10초) + zoompan → 섹션 길이만큼
 → ⑥ 실록 카드 오버레이 + 자막 + 덕킹 + loudnorm
 → ⑦ 인트로 5초 prepend → final.mp4
 → ⑧ PostWire payload → 업로드(승인 후)
```

---

## 3. 비용 (월 4편)

| 항목 | 계산 | 월 |
|---|---|---|
| 이미지 | 8장 × 4 = 32장 × $0.0168 | ₩750 |
| i2v | 5초 × 8 × 4 = 160초 = 48유닛 | ₩6,600~9,400 |
| TTS/BGM/자막/조립/업로드 | 무료 | ₩0 |
| **합계** | | **≈ ₩7,500~10,000** |

---

## 4. API 검증 완료 (2026-11-21 스모크 테스트)

| 테스트 | 결과 | 비용 |
|---|---|---|
| 나노바나나 이미지 1장 | ✅ 1376×768, 1,120 image tokens | $0.0336 |
| Kling 2.6 i2v 5초 | ✅ 1284×716, 24fps, 5.04초 | $0.21 |

→ 두 API 모두 정상. `.env`에 키 저장 완료.

---

## 5. 스타일 결정 근거

- 완전 실사: AI 왜곡이 팩트 신뢰도를 깎음, i2v와 상성 나쁨
- 완전 애니: 영어권에서 키즈/교육으로 오인
- **세미리얼**: 다큐 신뢰감 + 왜곡 은닉 + i2v 상성 + 한국적 차별점

→ 실록 카드(2D)와 대비되어 오히려 채널 시그니처가 선명해짐.

---

## 6. 파일 구조

```
youtube/
├─ .env                  (키, git 제외)
├─ .env.example
├─ auto/
│  ├─ STYLE.md           스타일 앵커
│  ├─ pipeline.py         오케스트레이션
│  ├─ smoke_gemini.py     검증 완료
│  └─ smoke_kling.py      검증 완료
│  └─ jobs/<id>/          작업별 산출물
├─ 4/build/              기존 렌더 로직 (참고)
├─ intro_5s.mp4
└─ post_payload.json     업로드 템플릿
```

---

## 7. 실행

```bash
cd "/home/j/문서/project/youtube"
python3 auto/pipeline.py --help
python3 auto/pipeline.py all "조선 실록에 기록된 UFO"
```

단계별 재실행도 가능: `script` → `images` → `tts` → `i2v` → `render` → `upload`

---

## 8. 다음

1. `pipeline.py` 구현 (진행 중)
2. 4편 한 편으로 테스트 렌더
3. 검수 후 PostWire 업로드
