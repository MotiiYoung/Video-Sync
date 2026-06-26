# Video Sync

> **최종 업데이트**: 2026-06-26

---

## Purpose

Google Drive에서 녹화 영상을 감지하여:
1. 프로젝트 폴더로 자동 이동
2. Observation Sheet에 링크 저장

---

## Source of Truth

| 항목 | 경로/ID |
|------|---------|
| 코드 | `/Users/young.kim/Projects/github/Video-Sync/` |
| GitHub | https://github.com/MotiiYoung/Video-Sync |
| 설정 | `config/projects.json` |
| Slack 알림 채널 | `C0BBQNNAEV8` |

---

## 사용법

### CLI 명령어

```bash
cd /Users/young.kim/Projects/github/Video-Sync

# Full: 녹화본 찾기 + 이동 + 링크 동기화
uv run python scripts/video_sync.py full

# 녹화본 찾아서 프로젝트 폴더로 이동
uv run python scripts/video_sync.py find

# 링크만 동기화
uv run python scripts/video_sync.py sync

# 영상 목록
uv run python scripts/video_sync.py list

# 미리보기
uv run python scripts/video_sync.py full --dry-run
```

### Slack 명령어

```
video sync 해줘
비디오 싱크
```

---

## 자동 트리거 (Quick Share Monitor)

```
┌─────────────────────────────────────────────────────────────┐
│  1. Quick Share Monitor - Primary                           │
│     → #all_user_research 채널 모니터링 (C056LP1M5P1)         │
│     → Quick Sharing 감지 시마다 Video Sync 실행              │
├─────────────────────────────────────────────────────────────┤
│  2. 수동 Fallback                                           │
│     → "Video Sync 해줘" or CLI 명령                          │
└─────────────────────────────────────────────────────────────┘
```

### Quick Share Monitor 명령어

```bash
# 데몬 시작 (백그라운드)
./scripts/run_quick_share_monitor.sh

# 데몬 중지
./scripts/stop_quick_share_monitor.sh

# 단일 체크 (테스트)
uv run python scripts/quick_share_monitor.py check

# 상태 확인
uv run python scripts/quick_share_monitor.py status

# 상태 리셋 (새 프로젝트 시작 시)
uv run python scripts/quick_share_monitor.py reset
```

### Payment Sync와 차이점

- **Payment Sync**: 마지막 유저 Quick Sharing 감지 → 1회 실행
- **Video Sync**: 매 Quick Sharing 감지 → 매번 실행

---

## 워크플로우

```
[개인 Google Drive]              [프로젝트 폴더]              [Observation Sheet]
Meet 녹화본 자동 저장    →    find 명령으로 이동    →    sync 명령으로 링크 추가
                              (full 명령 = 전체 자동화)
```

1. Google Meet에서 녹화 → 개인 드라이브에 저장됨
2. `video_sync.py find` → 프로젝트 관련 녹화본 찾아서 프로젝트 폴더로 이동
3. `video_sync.py sync` → 각 User 탭에 HYPERLINK로 링크 추가
4. `video_sync.py full` → 위 2+3 자동 실행

---

## 파일명 파싱

녹화본 파일명에서 세션 번호 추출:
```
12th SEP+UOL UT - 2026/05/17 11:04 IST – Recording
  ↓
세션 번호: 12 → User12 탭에 링크 추가
```

**패턴:**
```python
r'(\d+)(?:st|nd|rd|th)'  # 1st, 2nd, 3rd, 10th 등
```

---

## Slack 알림 형식

**Video Sync 완료:**
```
🎬 Video Sync 완료
• 프로젝트: SEP+UOL UT
• 이동된 영상: 12개
• 폴더: [Recording] SEP+UOL UT (클릭 가능 링크)
```

**Quick Share Monitor 감지 시:**
```
🎬 Quick Share Monitor
User 5 Quick Sharing 감지
→ SEP+UOL UT Video Sync 실행
```

---

## Google Drive Folders

| 폴더 | ID | 용도 |
|------|-----|------|
| Video Source (개인) | `1-GsFCTXEo8QGJhPqNzERVGLVfm5p3-7g` | Meet 녹화본 저장 |
| Target Base | `1Ypmm7Z4AvvPjiW2PWjI3aD8vPsr-e0Zw` | 프로젝트 폴더 |
| SEP+UOL Recording | `1e0Ludhfe7jGmRU71WnDihhIw4wOFG7Fa` | 프로젝트별 영상 폴더 |

---

## 설정 (config/projects.json)

```json
{
  "projects": {
    "SEP_UOL_UT": {
      "name": "SEP+UOL UT",
      "video_folder_id": "1e0Ludhfe7jGmRU71WnDihhIw4wOFG7Fa",
      "calendar_keywords": ["UT", "SEP", "UOL"]
    }
  }
}
```

---

## 인증

OAuth 토큰 위치:
```
~/.sidekick/sidekick/.claude/skills/google-oauth-token/.session/young.kim_oauth_token.json
```

필요한 스코프: `drive`, `sheets`

---

## 파일 구조

```
Video-Sync/
├── CLAUDE.md              # 이 파일
├── memory.md              # 맥락 유지
├── config/
│   └── projects.json      # 프로젝트 설정
├── scripts/
│   ├── video_sync.py      # VideoSync 메인
│   ├── quick_share_monitor.py   # Quick Share 모니터
│   ├── run_quick_share_monitor.sh
│   ├── stop_quick_share_monitor.sh
│   └── auto_auth.py       # OAuth 인증
├── data/
│   └── video_sync_state.json
├── logs/
└── .git/
```

---

## 관련 프로젝트

| 프로젝트 | 경로 | 역할 |
|----------|------|------|
| Payment-Sync | `~/Projects/github/Payment-Sync` | 결제 정보 동기화 |
| Recruiting | `~/Projects/github/Recruiting` | 참가자 모집 |

---

## Slack 채널

| 채널 | ID | 용도 |
|------|-----|------|
| Video 알림 | `C0BBQNNAEV8` | Sync 완료 알림 |
| all_user_research | `C056LP1M5P1` | Quick Share 모니터링 |
