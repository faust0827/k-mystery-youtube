#!/usr/bin/env python3
"""원본 마스터 MP4 보관 + 플랫폼별 배포 가이드 생성.

사용:
  python3 auto/distribute.py <job_id>

원본(final.mp4)은 워터마크 없는 마스터로 보관하고,
틱톡 / 유튜브 쇼츠 / 인스타 릴스 업로드용 체크리스트를 만든다.

중요: 틱톡 앱에서 내려받은 영상에는 틱톡 워터마크가 붙는다.
      절대 그 파일을 다른 플랫폼에 올리지 말고, 이 스크립트가
      보관하는 원본(master/)을 사용할 것.
"""
import json
import os
import shutil
import sys

ROOT = "/home/j/문서/project/youtube"
JOBS = os.path.join(ROOT, "auto", "jobs")


def load_job(jid):
    p = os.path.join(JOBS, jid, "job.json")
    if not os.path.exists(p):
        sys.exit("job not found: " + jid)
    return json.load(open(p, encoding="utf-8"))


def run(jid):
    base = os.path.join(JOBS, jid)
    job = load_job(jid)

    src = os.path.join(base, "final.mp4")
    if not os.path.exists(src):
        # 축소본만 있으면 그것을 사용
        src = os.path.join(base, "final_small.mp4")
    if not os.path.exists(src):
        sys.exit("final.mp4 / final_small.mp4 없음")

    # 1) 원본 마스터 보관 (워터마크 없는 버전)
    master_dir = os.path.join(base, "master")
    os.makedirs(master_dir, exist_ok=True)
    master = os.path.join(master_dir, "master_clean.mp4")
    if not os.path.exists(master):
        shutil.copy2(src, master)
    print("master:", master, os.path.getsize(master), "bytes")

    # 2) 플랫폼별 업로드 가이드
    title = job.get("title", job.get("topic", "K-Mystery"))
    hashtags = "#한국미스터리 #조선왕조실록 #역사미스터리 #괴담 #미해결사건"
    guide = f"""# 업로드 가이드 — {jid}

## ⚠️ 가장 중요한 규칙
**틱톡 앱에서 내려받은 영상은 절대 다른 플랫폼에 올리지 마세요.**
틱톡 워터마크가 붙어 유튜브 알고리즘이 불이익을 줍니다.
항상 이 폴더의 `master/master_clean.mp4` 를 사용하세요.

## 원본 파일
- `{master}`  (워터마크 없음, 이 파일만 배포에 사용)

---

## 1) 틱톡 (먼저)
- 방법: 틱톡 앱 → 업로드 → `master/master_clean.mp4` 선택
- 캡션 첫 줄에 검색 키워드: "조선 실록 미스터리"
- 해시태그: {hashtags}
- **AI 생성 표시 ON** (설정 → AI 생성 콘텐츠)
- 길이: 1분 이상 확인 (CRP条件)
- 공개: 공개

## 2) 유튜브 쇼츠 (1~2일 뒤)
- 방법: 유튜브 스튜디오 → 만들기 → 쇼츠 → 같은 원본 업로드
- 제목: {title} #shorts
- 설명 첫 줄에 같은 키워드 반복
- **틱톡 워터마크 없는 원본인지 재확인**
- 워터마크 방지를 위해 썸네일/인트로만 살짝 다르게 (선택)

## 3) 인스타 릴스 (선택)
- 같은 원본 업로드, 릴스 전용 자막 확인

---

## 순서 요약
```
master_clean.mp4 생성 (이 스크립트)
 → 틱톡 업로드 (当天)
 → 1~2일 후 유튜브 쇼츠 (같은 원본)
 → (선택) 인스타 릴스
```

## 수익화 참고
- 틱톡 CRP: 팔로워 1만 + 30일 10만뷰 + 1분 이상 (한국어 2X)
- 유튜브 쇼츠: 구독자 500 + 90일 3천만뷰 (진입장벽 더 낮음)
"""
    out = os.path.join(base, "UPLOAD_GUIDE.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(guide)
    print("guide:", out)
    return master, out


def main_with_jid(jid):
    return run(jid)


def main():
    if len(sys.argv) < 2:
        dirs = sorted(os.listdir(JOBS)) if os.path.isdir(JOBS) else []
        sys.exit("사용: python3 auto/distribute.py <job_id>\njobs: " + ", ".join(dirs))
    return run(sys.argv[1])


if __name__ == "__main__":
    main()
