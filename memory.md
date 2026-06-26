# Video Sync - Memory & Context

> 이 파일은 Claude 세션 간 맥락 유지를 위한 상세 기록입니다.
> 새 세션 시작 시 이 파일을 읽어서 전체 맥락을 로드하세요.

---

## 🎯 핵심 요약

Video Sync는 Google Meet 녹화본을 프로젝트 폴더로 이동하고 Observation Sheet에 링크를 추가하는 도구입니다.

**핵심 플로우:**
```
Google Meet 녹화 종료
  → (시간 소요) → Meeting Recordings 폴더에 생성
  → find: 프로젝트 키워드로 녹화본 감지
  → [Recording] {project_name} 폴더 자동 생성 (없으면)
  → 녹화본 이동
  → sync: Observation Sheet에 HYPERLINK 추가
  → Slack 알림 전송
```

---

## 🚀 자동 트리거 시스템

### 2단계 자동 트리거

```
┌─────────────────────────────────────────────────────────────┐
│  1. Quick Share Monitor - Primary                           │
│     → #all_user_research 채널 모니터링 (C056LP1M5P1)         │
│     → Quick Sharing 감지 시마다 Video Sync 실행              │
│     (Payment Sync와 다르게 매 유저마다 실행)                  │
├─────────────────────────────────────────────────────────────┤
│  2. 수동 Fallback                                           │
│     → "Video Sync 해줘" or CLI 명령                          │
└─────────────────────────────────────────────────────────────┘
```

### Payment Sync와 차이점

| 항목 | Payment Sync | Video Sync |
|------|--------------|------------|
| 트리거 조건 | 마지막 유저 (user >= goal) | 매 Quick Sharing |
| 실행 시점 | 프로젝트 완료 후 1회 | 세션마다 실행 |
| 중복 방지 | 플래그 파일 | synced_users 상태 |

### Quick Share Monitor 명령어

```bash
cd /Users/young.kim/Projects/github/Video-Sync

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

---

## 📋 CLI 명령어

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

# 특정 프로젝트
uv run python scripts/video_sync.py full --project SEP_UOL_UT
```

---

## 📊 워크플로우

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

## 🎬 파일명 파싱

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

## 🔔 Slack 알림

### 채널

| 채널 | ID | 용도 |
|------|-----|------|
| Video 알림 | `C0BBQNNAEV8` | Sync 완료 알림 |
| all_user_research | `C056LP1M5P1` | Quick Share 모니터링 |

### 메시지 형식

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

## 🗂️ Google Drive 폴더

| 폴더 | ID | 용도 |
|------|-----|------|
| Meeting Recordings (소스) | `1-GsFCTXEo8QGJhPqNzERVGLVfm5p3-7g` | Meet 녹화본 자동 저장 |
| SEP+UOL UT 프로젝트 폴더 | `15d1UmoFMedga140UTALhYA8odApshqkg` | 프로젝트 폴더 |
| [Recording] SEP+UOL UT | `1e0Ludhfe7jGmRU71WnDihhIw4wOFG7Fa` | 녹화본 저장 (자동 생성) |

### 폴더 자동 생성

```
Meeting Recordings 폴더 (source_folder_id)
  ↓ 녹화본 감지
프로젝트 폴더 (project_folder_id)
  └── [Recording] {project_name} ← 자동 생성
        └── 녹화본 이동
```

- `video_folder_id`가 설정되어 있으면 해당 폴더 사용
- 없으면 `project_folder_id` 내에 `[Recording] {project_name}` 폴더 자동 생성

---

## 📋 프로젝트 설정

### projects.json 구조

```json
{
  "projects": {
    "SEP_UOL_UT": {
      "name": "SEP+UOL UT",
      "observation_sheet": {
        "spreadsheet_id": "...",
        "user_tab_pattern": "User(\\d+)"
      },
      "video_folder_id": "1e0Ludhfe7jGmRU71WnDihhIw4wOFG7Fa",
      "calendar_keywords": ["UT", "SEP", "UOL"]
    }
  },
  "default_project": "SEP_UOL_UT"
}
```

---

## 🔐 인증

### OAuth 토큰 위치

```
~/.sidekick/sidekick/.claude/skills/google-oauth-token/.session/young.kim_oauth_token.json
```

### 필요한 스코프

- `https://www.googleapis.com/auth/drive`
- `https://www.googleapis.com/auth/spreadsheets`

### 토큰 갱신

자동 갱신됨 (refresh_token 사용)

수동 갱신:
```bash
cd ~/.sidekick/sidekick/.claude/skills/google-oauth-token
uv run python scripts/main.py --scopes drive sheets
```

---

## 📁 파일 구조

```
Video-Sync/
├── CLAUDE.md                    # 프로젝트 규칙
├── memory.md                    # 이 파일 (맥락 유지)
├── config/
│   └── projects.json            # 프로젝트 설정
├── scripts/
│   ├── video_sync.py            # VideoSync 메인
│   ├── quick_share_monitor.py   # Quick Share 모니터 데몬
│   ├── run_quick_share_monitor.sh   # 데몬 시작
│   ├── stop_quick_share_monitor.sh  # 데몬 중지
│   └── auto_auth.py             # OAuth 인증
├── data/
│   └── video_sync_state.json    # 모니터 상태 (synced_users)
├── logs/
│   └── quick_share_monitor.log  # 모니터 로그
└── .git/
```

---

## 📝 변경 이력

### 2026-06-26 (최신)

1. **Quick Share Monitor 추가**
   - `scripts/quick_share_monitor.py` - 데몬 스크립트
   - 매 Quick Sharing 감지 시 Video Sync 실행
   - `synced_users` 상태로 중복 방지

2. **Slack 메시지 형식 변경**
   - 폴더명: `Recording` → `[Recording] {project_name}`
   - 프로젝트명: config의 `name` 필드 그대로 사용

3. **프로젝트명 수정**
   - `SEP+UOL User Test` → `SEP+UOL UT`

---

## ⚠️ 주의사항

1. **토큰 만료**: API 호출 전 토큰 자동 갱신됨
2. **synced_users 리셋**: 새 프로젝트 시작 전 `reset` 명령 실행
3. **파일명 패턴**: `{N}st/nd/rd/th` 형식이어야 세션 번호 추출 가능

---

## 🔧 트러블슈팅

### 토큰 만료 에러

```bash
cd ~/.sidekick/sidekick/.claude/skills/google-oauth-token
uv run python scripts/main.py --scopes drive sheets
```

### Video Sync 안 됨

1. Quick Share Monitor 로그 확인: `tail -f logs/quick_share_monitor.log`
2. 상태 확인: `uv run python scripts/quick_share_monitor.py status`
3. synced_users에 이미 있는지 확인
4. 필요시 리셋: `uv run python scripts/quick_share_monitor.py reset`

### 녹화본 못 찾음

1. 파일명에 프로젝트 키워드 포함되어 있는지 확인
2. `calendar_keywords` 설정 확인
3. 개인 드라이브에 녹화본 있는지 확인

---

## 🔗 관련 프로젝트

| 프로젝트 | 경로 | 역할 |
|----------|------|------|
| Payment-Sync | `~/Projects/github/Payment-Sync` | 결제 정보 동기화 |
| Recruiting | `~/Projects/github/Recruiting` | 참가자 모집 |

---

## 📌 Quick Reference

### Google Sheets IDs

| 시트 | ID |
|------|-----|
| SEP+UOL Observation | `1iglGl92ePjQ5EUWa9brrBCHp24AP_OJHhgOSAx6WbxA` |

### Slack 명령어

```
video sync 해줘
비디오 싱크
```
