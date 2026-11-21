# [OpenClaw 작업 지시] K-Mystery 유튜브 채널 개선 적용

작성: OpenCode 세션 (2026-11-10)
작업 디렉토리: `/home/j/문서/project/youtube`
채널: https://www.youtube.com/@Korean_Mysteries

## 0. 먼저 읽을 것
- `K_Mystery_AI_Youtube_Strategy.md`
- `PROGRESS.md`
- `채널/` (배너·프로필 이미지 원본)

## 1. 현재 진단 (OpenCode가 실제 채널 데이터를 확인한 결과)

| 항목 | 값 |
|---|---|
| 개설 | 2026-11-07 (3일 전) |
| 영상 | 롱폼 3편 (6:45 / 8:21 / 8:22) |
| 조회수 | 0 / 0 / 3 |
| 카테고리 | Education, 영어 |
| 채널 소개 | 비어 있음 |
| 태그 | 1편만 있음, 나머지 0개 |
| 자막 | 커스텀 자막 없음 (자동자막만) |

영상 목록:
1. `PyQKq9igFwg` — The Korean Prince Locked in a Rice Chest by His Own Father (2026-11-07, 8:21, 3회)
2. `TYOcCE4zp30` — Korea's Most Haunted Psychiatric Hospital (2026-11-08, 6:45, 0회)
3. `xFBrv3fdRC4` — Joseon Annals Recorded 'UFOs' 400 Years Ago (2026-11-09, 8:02, 0회)

## 2. 문제점 (우선순위 순)

### P0 — 썸네일
- 현재 썸네일이 **영상 프레임 + 자막 캡처**임. 클릭 유도 요소 0.
- 모바일에서 자막 텍스트가 안 읽힘. 브랜딩/로고 없음.
- 1편 썸네일 자막에 오타: "Courteers" → "Courtiers"
- 개선: 1280x720, 텍스트 3~4단어(예: "BURIED ALIVE"), 인물 클로즈업, 고대비, 우하단 채널 마크. 자막 캡처 금지.

### P0 — 제목
- 현재 제목은 설명적이나 클릭 훅이 약함.
- 개선 공식: [구체적 인물/사건] + [반전/결과]. 예:
  - "The Prince Left to Die in a Rice Chest"
  - "The Hospital Korea Wants Forgotten"
  - "Korea's Annals Recorded UFOs in 1450"

### P1 — 유입 구조
- 롱폼만 3편. 초기 채널은 Shorts가 사실상 유일한 발견 경로.
- 개선: 같은 소재를 45~60초 Shorts로 재편집, 주 3~5개. 롱폼은 주 1~2개.

### P1 — 독창성/수익화 리스크
- AI 이미지 + TTS + Ken Burns 조합은 "재사용 콘텐츠" 정책 리스크가 큼.
- 개선: 영상 내 **실록 원문 인용 + 연도** 자막 삽입, 고유 리서치 흔적 남기기, 채널 워터마크/색보정 통일.

### P2 — 채널 기본기
- 채널 소개글, 배너/프로필 적용 여부 확인, 영상별 태그·설명 통일, 고정 댓글, 재생목록 구성.

## 3. 이번에 적용할 일 (산출물)

다음을 실제로 만들어서 파일로 남겨라. **유튜브 업로드/수정은 하지 마라** (사용자 승인 전 금지).

1. `thumbnails/` — 3편 썸네일 리디자인 안 (1280x720 PNG). 텍스트 오버레이 포함. 기존 이미지 소스가 있으면 재사용, 없으면 `채널/` 스타일 참고해 생성. 각 안은 2개씩.
2. `metadata/` — 3편의 새 제목·설명·태그 (복붙 가능한 형태, `metadata/video1.md` 형식)
3. `plan/12week.md` — 12주 업로드 계획 (롱폼 주 1~2, Shorts 주 3~5, 소재 30개 리스트 포함)
4. `shorts/docs/shorts_scripts.md` — 기존 3편 기반 Shorts 대본 6개 (훅 3초 포함)
5. `PROGRESS.md` 업데이트 — 위 작업 내역 추가

## 4. 제약

- 작업 디렉토리 밖 파일 수정 금지.
- `git commit`/`push` 금지. 변경만 남겨라.
- 유튜브 API/업로드 호출 금지.
- 비용이 큰 대량 이미지 생성은 하지 말고, 썸네일 6장 이내로 제한.
- 완료 후: 만든 파일 목록 + 각 파일 요약 + 다음에 사용자가 결정할 것 3가지를 보고해라.
