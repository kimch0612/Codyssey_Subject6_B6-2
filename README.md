# 내가 고친 코드 설명을 AI가 대신 써주는 도우미

Git 변경 사항(`git status`, `git diff`)을 수집해 Google Gemini API로 커밋 메시지와 Pull Request 초안을 자동 생성하는 Python CLI 도구입니다.

## 특징

- 표준 라이브러리만 사용 — 별도 패키지 설치 없이 바로 실행 가능
- 커밋 메시지 / PR 제목·본문(Why / What / How to Test) 자동 생성
- 생성 결과의 길이·형식을 코드로 검증하고 자동으로 다듬음
- `-safe-mode`로 diff에 포함된 API Key/이메일 등 민감정보 마스킹

## 설치 및 실행 방법

Python 3.10 이상이면 됩니다. `requests`, `python-dotenv` 같은 외부 패키지가 전혀 필요 없고 표준 라이브러리(`urllib`, `argparse`, `re` 등)만 사용합니다.

```bash
git clone https://github.com/kimch0612/Codyssey_Subject6_B6-2.git
```

이 도구는 **Git이 초기화된 프로젝트의 루트 디렉토리에서** 실행해야 합니다. 자기 자신의 저장소뿐 아니라, `main.py`의 경로만 가리키면 다른 어떤 git 프로젝트 안에서도 그대로 쓸 수 있습니다 (복사할 필요 없음).

```bash
cd /path/to/your-git-project
python3 /path/to/this-repo/main.py commit
```

## 환경변수(API Key) 설정 방법

1. [Google AI Studio](https://ai.google.dev/gemini-api/docs/quickstart)에서 Gemini API Key를 발급받습니다 (무료 티어로 사용 가능).
2. 발급받은 키를 환경변수 `AI_API_KEY`로 등록합니다.

```bash
export AI_API_KEY="발급받은_키"
```

API Key는 코드나 저장소에 직접 저장하지 않으며, 항상 이 환경변수를 통해서만 전달됩니다.

## 사용법

```bash
# 변경 사항을 요약한 커밋 메시지 생성
python3 main.py commit

# PR 제목/본문(Why / What / How to Test) 초안 생성
python3 main.py pr
```

### 옵션

| 옵션 | 설명 | 기본값 |
|---|---|---|
| `-model` | 사용할 Gemini 모델 | `gemini-3.1-flash-lite` |
| `-temperature` | 응답의 창의성/무작위성 (0~2, 낮을수록 일관적) | `0.3` |
| `-max-tokens` | 응답 최대 토큰 수 | `1024` |
| `-safe-mode` | diff에서 API Key/이메일 형태 패턴을 마스킹 후 전송 | 꺼짐 |

```bash
python3 main.py commit -temperature 0 -max-tokens 500
python3 main.py pr -safe-mode
```

`commit`/`pr` 명령은 각각 실행당 AI API를 1회만 호출합니다.

## 출력 예시

### `python3 main.py commit`

```
[INFO] Git status 수집 완료: 1개 파일 변경 감지
[INFO] Git diff 수집 완료: 11줄
[INFO] AI API 요청 중... (model=gemini-3.1-flash-lite, temperature=0.3, max_tokens=1024)
[DONE] 커밋 메시지 생성 완료

--- Commit Message ---
chore: .gitignore에 __pycache__ 디렉토리 추가

- 파이썬 실행 시 생성되는 __pycache__ 폴더를 버전 관리에서 제외하도록 설정
----------------------
```

### `python3 main.py pr`

```
[INFO] 현재 브랜치: master
[INFO] AI API 요청 중... (model=gemini-3.1-flash-lite, temperature=0.3, max_tokens=1024)
[DONE] PR 초안 생성 완료

--- PR Title ---
chore: .gitignore 파일에 __pycache__/ 디렉토리 추가

--- PR Body ---
## Why
- 파이썬 실행 시 생성되는 __pycache__ 디렉토리가 원격 저장소에 포함되는 것을 방지하기 위함입니다.
- 불필요한 캐시 파일이 커밋되는 것을 막아 저장소를 깔끔하게 유지하고자 합니다.

## What
- .gitignore 파일에 `__pycache__/` 패턴을 추가했습니다.

## How to Test
- 터미널에서 `python` 파일을 실행하여 `__pycache__` 디렉토리가 생성되는지 확인합니다.
- `git status` 명령어를 입력했을 때, `__pycache__` 디렉토리가 추적되지 않는지 확인합니다.
```

### 변경 사항이 없을 때

```
[INFO] 변경 사항이 없습니다. 커밋 메시지를 생성하지 않고 종료합니다.
```

### API Key 미설정 시

```
[ERROR] AI_API_KEY 환경변수가 설정되지 않았습니다.
## 예) export AI_API_KEY="YOUR_KEY"
```

## 민감정보 대응 (Safe Mode)

`-safe-mode` 옵션을 사용하면 AI에 보내기 전 diff에서 아래 패턴을 마스킹합니다.

- 이메일 주소 → `[EMAIL]`
- `API_KEY = "..."`, `SECRET_TOKEN: '...'`처럼 민감해 보이는 변수명에 대입된 값 → `[MASKED]`

```diff
- NOTIFY_API_KEY = "AIzaSyD4example1234567890FAKEKEYXX"
- ADMIN_EMAIL = "admin@example.com"
+ NOTIFY_API_KEY = [MASKED]
+ ADMIN_EMAIL = "[EMAIL]"
```

변수 이름은 그대로 남기고 값만 가려서, AI가 "무엇이 추가됐는지"는 계속 이해하면서도 실제 키/이메일 값은 전송하지 않습니다. 다만 정규식 기반 탐지라 완벽하지 않으므로, 민감한 코드를 다룰 땐 생성 결과를 실제로 적용하기 전에 항상 직접 검토하시기 바랍니다.

## 주의사항

- Gemini API는 무료 티어에서도 모델별로 분당/일일 요청 수 제한이 있습니다. 반복 실행 시 `HTTP 429` 오류가 날 수 있습니다.
- 이 도구는 커밋/PR **초안 텍스트를 생성**하는 것까지가 목표입니다. `git commit`, `git push`, GitHub PR 생성 등 실제 반영은 직접 수행해야 합니다.
- 생성된 커밋/PR 문구는 최종 정답이 아니라 초안입니다. 항상 검토 후 적용하세요.
