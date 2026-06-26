# Video Sync - Memory & Context

> 이 파일은 Claude 세션 간 맥락 유지를 위한 상세 기록입니다.
> 새 세션 시작 시 이 파일을 읽어서 전체 맥락을 로드하세요.

---

## 🎯 핵심 요약

Video Sync는 Google Meet 녹화본을 프로젝트 폴더로 이동하고 Observation Sheet에 링크를 추가하는 도구입니다.

**핵심 플로우:**
```
Google Meet 녹화 종료
  → (2시간 대기) → Meeting Recordings 폴더에 생성
  → Video Sync 감지 (Calendar Monitor / Quick Share Monitor)
  → [Recording] {project_name} 폴더 자동 생성 (없으면)
  → 녹화본 이동
  → Observation Sheet에 HYPERLINK 추가
  → Slack 알림 전송
```

---

## 🚀 자동 트리거 시스템 (Hybrid)

### 4단계 자동 트리거

```
┌─────────────────────────────────────────────────────────────┐
│  1. Recruiting Dashboard (프로젝트 완료 시)                   │
│     → completed >= target 감지 → Full Video Sync 실행        │
│     (프로젝트 완료 시 전체 녹화본 일괄 처리 - 최종 점검)        │
├─────────────────────────────────────────────────────────────┤
│  2. Calendar Monitor (세션 종료 시)                          │
│     → Google Calendar에서 유저 리서치 일정 감지               │
│     → 미팅 종료 + 2시간 버퍼 후 → Video Sync 실행             │
│     (녹화 파일 생성 대기 후 자동 이동)                         │
├─────────────────────────────────────────────────────────────┤
│  3. Quick Share Monitor (Quick Sharing 감지 시)              │
│     → #all_user_research 채널 모니터링 (C056LP1M5P1)         │
│     → Quick Sharing 감지 시마다 Video Sync 실행              │
│     (세션별 실시간 처리)                                      │
├─────────────────────────────────────────────────────────────┤
│  4. 수동 Fallback                                           │
│     → "Video Sync 해줘" or CLI 명령                          │
└─────────────────────────────────────────────────────────────┘
```

### ⚠️ 로컬 실행 필요

현재 모든 트리거는 **로컬 실행 필요**:
- Calendar Monitor, Quick Share Monitor: 로컬 데몬
- Recruiting Dashboard: 로컬 서버 (localhost:8080)

**TODO:** Slack Bot (sk-young-kim) 서버 배포 시 연동 예정

### Calendar Monitor 플로우

```
Google Calendar 유저 리서치 일정
  ↓ 미팅 종료 감지
  ↓ 2시간 버퍼 (RECORDING_BUFFER = 7200초)
Meeting Recordings 폴더 확인
  ↓ 새 녹화본 감지
[Recording] {project_name} 폴더로 이동
  ↓
Observation Sheet에 링크 추가
```

### Calendar Monitor 명령어

```bash
cd /Users/young.kim/Projects/github/Video-Sync

# 데몬 시작 (백그라운드)
./scripts/run_calendar_monitor.sh

# 데몬 중지
./scripts/stop_calendar_monitor.sh

# 단일 체크 (테스트)
uv run python scripts/calendar_monitor.py check

# 상태 확인
uv run python scripts/calendar_monitor.py status
```

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

**Calendar Monitor 감지 시:**
```
📅 Calendar Monitor
User 5 세션 종료 감지
→ SEP+UOL UT Video Sync 실행
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

## 📋 프로젝트 설정

### projects.json 구조

```json
{
  "projects": {
    "SEP_UOL_UT": {
      "name": "SEP+UOL UT",
      "observation_sheet": {
        "spreadsheet_id": "1iglGl92ePjQ5EUWa9brrBCHp24AP_OJHhgOSAx6WbxA",
        "user_tab_pattern": "User(\\d+)"
      },
      "video_sync": {
        "source_folder_id": "1-GsFCTXEo8QGJhPqNzERVGLVfm5p3-7g",
        "target_base_folder_id": "1Ypmm7Z4AvvPjiW2PWjI3aD8vPsr-e0Zw",
        "recording_folder_pattern": "[Recording] {project_name}"
      },
      "project_folder_id": "15d1UmoFMedga140UTALhYA8odApshqkg",
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
- `https://www.googleapis.com/auth/calendar.readonly`

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
│   ├── calendar_monitor.py      # Calendar 모니터 데몬 (2시간 버퍼)
│   ├── quick_share_monitor.py   # Quick Share 모니터 데몬
│   ├── run_calendar_monitor.sh
│   ├── stop_calendar_monitor.sh
│   ├── run_quick_share_monitor.sh
│   ├── stop_quick_share_monitor.sh
│   └── auto_auth.py             # OAuth 인증
├── data/
│   ├── calendar_monitor_state.json
│   └── video_sync_state.json
├── logs/
│   ├── calendar_monitor.log
│   └── quick_share_monitor.log
└── .git/
```

---

## 📝 변경 이력

### 2026-06-26 (최신)

1. **4단계 하이브리드 트리거 시스템 구현**
   - Recruiting Dashboard: 프로젝트 완료 시 Full Sync (최종 점검)
   - Calendar Monitor: 세션 종료 + 2시간 후 실행
   - Quick Share Monitor: Quick Sharing 감지 시 즉시 실행
   - 수동: "Video Sync 해줘"

2. **Calendar Monitor 추가**
   - `RECORDING_BUFFER = 7200` (2시간)
   - Google Calendar에서 유저 리서치 일정 감지

3. **폴더 자동 생성 기능**
   - Meeting Recordings에서 녹화본 감지
   - `[Recording] {project_name}` 폴더 자동 생성

4. **Slack 알림 형식**
   - 🎬 Video Sync 완료
   - 📅 Calendar Monitor
   - 🎬 Quick Share Monitor

5. **프로젝트명 수정**
   - `SEP+UOL User Test` → `SEP+UOL UT`

---

## ⚠️ 주의사항

1. **로컬 실행 필요**: 모든 데몬/서버가 로컬에서 실행되어야 함
2. **토큰 만료**: API 호출 전 토큰 자동 갱신됨
3. **2시간 버퍼**: Calendar Monitor는 미팅 종료 후 2시간 대기
4. **synced_users 리셋**: 새 프로젝트 시작 전 `reset` 명령 실행

---

## 🔧 트러블슈팅

### 토큰 만료 에러

```bash
cd ~/.sidekick/sidekick/.claude/skills/google-oauth-token
uv run python scripts/main.py --scopes drive sheets calendar
```

### Video Sync 안 됨

1. 데몬 실행 확인: `ps aux | grep monitor`
2. 로그 확인: `tail -f logs/calendar_monitor.log`
3. 상태 확인: `uv run python scripts/calendar_monitor.py status`

### 녹화본 못 찾음

1. Meeting Recordings 폴더에 파일 있는지 확인
2. 파일명에 프로젝트 키워드 포함 확인
3. `calendar_keywords` 설정 확인

---

## 🔗 관련 프로젝트

| 프로젝트 | 경로 | 역할 |
|----------|------|------|
| Payment-Sync | `~/Projects/github/Payment-Sync` | 결제 정보 동기화 |
| Recruiting | `~/Projects/github/Recruiting` | 참가자 모집, Goal 관리 |

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

### 다음 세션 시작 시

```bash
cat /Users/young.kim/Projects/github/Video-Sync/memory.md
```
