# Video Sync

**Purpose**: 유저 리서치 녹화 영상 자동 동기화
**Owner**: young.kim

---

## 기능

Google Drive에서 녹화 영상을 감지하여:
1. 프로젝트 폴더로 자동 이동
2. Observation Sheet에 링크 저장

---

## 사용법

### Claude에게 말하기
```
VideoSync 실행해줘
```

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
```

---

## 설정

`config/projects.json`:
```json
{
  "video_sync": {
    "source_folder_id": "1-GsFCTXEo8QGJhPqNzERVGLVfm5p3-7g",
    "target_base_folder_id": "1Ypmm7Z4AvvPjiW2PWjI3aD8vPsr-e0Zw",
    "recording_folder_pattern": "[Recording] {project_name} + Recorded Videos"
  }
}
```

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

## 파일 구조

```
Video-Sync/
├── CLAUDE.md              # 이 파일
├── config/
│   └── projects.json      # 프로젝트 설정
└── scripts/
    ├── auto_auth.py       # OAuth 인증
    └── video_sync.py      # VideoSync 메인
```
