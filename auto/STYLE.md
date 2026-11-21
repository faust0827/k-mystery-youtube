# K-Mystery 이미지 스타일 가이드 (나노바나나 고정 앵커)

## 원칙

완전 실사도, 완전 애니메이션도 아닌 **세미리얼 시네마틱 일러스트**.
다큐 신뢰감을 유지하면서 AI 왜곡을 "화풍"으로 흡수하고, i2v와 상성을 맞춘다.

---

## 공통 앵커 (모든 이미지 프롬프트 끝에 그대로 붙임)

```
Style: cinematic semi-realistic illustration, Joseon Korea,
muted earth tones, paper-lantern warm light, volumetric fog,
film grain, 35mm, low saturation, painterly texture,
dark mysterious atmosphere.
NOT photorealistic, NOT cartoon, NOT anime, no text, no watermark.
```

---

## 규칙 3개

1. **인물은 실루엣·측면·후면·원거리**
   - 얼굴 클로즈업 금지 (i2v 왜곡 + 신비감 유지)
   - 예: "a royal figure seen from behind, silhouette against lantern light"

2. **색상 팔레트 고정**
   - 먹빛 / 잿빛 베이스
   - 등불 주황(따뜻한 포인트)
   - 붉은 달 (썸네일 시그니처와 통일)

3. **실록 카드는 2D 그래픽 그대로**
   - `4/source_cards/*.png` 기존 자산 유지
   - 이미지 스타일 앵커를 카드에 적용하지 말 것
   - 텍스트 선명도가 최우선

---

## 섹션별 프롬프트 예시

| 섹션 | image_prompt | motion_prompt |
|---|---|---|
| 01_coldopen | "A Joseon palace corridor at night, paper lanterns, thin fog, empty, no people" | "slow camera pan forward, lantern light flickering, fog drifting" |
| 02_law | "A royal court in shadow, a seated silhouette, tall pillars, dim light" | "camera slowly tilts up, dust motes floating in light beam" |
| 03_starshine | "Night sky over an old palace roof, faint red moon, low clouds" | "clouds drifting slowly, red moon glow pulsing faintly" |
| 04_crackdown | "A dark palace gate half open, guards as silhouettes, cold blue tones" | "gate slowly creaking open, fog rolling in" |
| 05_why | "An old scroll on a wooden table, candle light, deep shadows" | "candle flame flickering, scroll edge lifting slightly" |
| 06_survived | "A shamanic ritual in a dark room, incense smoke, silhouettes" | "incense smoke rising and curling, soft light shifting" |
| 07_price | "A lone figure walking away down a misty road, dawn" | "figure walking slowly into fog, camera following from behind" |
| 08_close | "An empty palace courtyard at dusk, red moon rising" | "red moon slowly rising, clouds passing" |

---

## 예외: 썸네일

썸네일(`v4_FINAL.png`, "BANNED FOR 500 YEARS")은 **실사-like 대비 + 붉은 달** 그대로.
클릭이 목적이므로 본편 톤과 살짝 달라도 무방.
