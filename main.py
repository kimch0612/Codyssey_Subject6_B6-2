import argparse
import json
import os
import subprocess
import urllib.error
import urllib.request


COMMIT_TITLE_MAX_LENGTH = 72
PR_TITLE_MAX_LENGTH = 80
PR_SECTIONS = ["## Why", "## What", "## How to Test"]


COMMIT_SYSTEM_PROMPT = """당신은 git 커밋 메시지를 작성하는 도우미입니다. 아래 규칙을 반드시 지켜서 커밋 메시지를 작성하세요.

- 첫 줄은 커밋 제목이며, 50자 이내를 권장하고 72자를 넘지 않습니다.
- 제목 다음에 빈 줄을 하나 두고, 선택적으로 본문을 작성할 수 있습니다.
- 본문을 작성한다면, 변경된 파일/모듈 1~3개를 언급하거나 핵심 변경 사항을 1~2개의 불릿("- "로 시작)으로 요약합니다.
- 커밋 메시지 텍스트만 출력하고, 다른 설명이나 인사말은 포함하지 않습니다.

예시:
feat: Git 변경 사항 기반 커밋 메시지 자동 생성 기능 추가

- git diff 결과를 수집해 AI 입력 컨텍스트로 전달하도록 구현
- 커밋 메시지 템플릿(feat/fix 등) 생성 규칙 적용
- API Key 미설정 시 안내 메시지 및 에러 처리 개선"""


PR_SYSTEM_PROMPT = """당신은 Pull Request 제목과 본문을 작성하는 도우미입니다. 아래 규칙을 반드시 지켜서 작성하세요.

- 첫 줄은 PR 제목이며, 80자를 넘지 않습니다.
- 제목 다음에 빈 줄을 하나 두고, 그 다음부터 PR 본문을 작성합니다.
- 본문은 반드시 "## Why", "## What", "## How to Test" 세 섹션을 이 순서대로 포함합니다.
- 각 섹션에는 최소 1개 이상의 불릿("- "로 시작)을 작성합니다.
- 제목과 본문 텍스트만 출력하고, 다른 설명이나 인사말은 포함하지 않습니다.

예시:
feat: 커밋/PR 자동 생성 기능 추가

## Why
- 팀 협업 시 커밋 메시지와 PR 설명 작성에 시간이 소요되어 자동 생성 도구가 필요했습니다.
- Git 변경 사항을 기반으로 일관된 형식의 요약 텍스트를 생성해 리뷰 효율을 높이고자 했습니다.

## What
- git status, git diff 결과를 수집해 AI 입력 컨텍스트로 전달하는 로직 추가
- PR 제목/본문 자동 생성 기능 구현 및 템플릿 적용

## How to Test
- 환경변수 설정: export AI_API_KEY="YOUR_KEY"
- PR 초안 생성: python main.py pr
- 출력된 PR 본문이 Why/What/How to Test 구조와 길이 규칙을 만족하는지 확인"""


def get_git_status() -> str: # 현재 소스의 상태를 가져오자 (어떤 파일이 수정됐는지, 스테이징 됐는지, 언트랙인지 등)
    result = subprocess.run(
        ["git", "status", "--porcelain"], # --porcelain은 고정적인 포맷으로 보내줌 (파싱할 때 유리함)
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout # 콘솔 출력을 반환


def get_git_diff() -> str: # 현재 소스의 차이점을 구체적으로 diff 스타일로 출력함
    result = subprocess.run(
        ["git", "diff", "HEAD"], # --HEAD를 쓰는 이유? HEAD를 안 쓰면 스테이징이 된 파일에 대한 diff가 안 뜸 (수정된 파일은 있는데 수정 사항이 안 뜨는 모순 발생)
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def get_current_branch() -> str: # 현재 활성화 된 브랜치 정보를 가져옴
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def call_gemini( # 제미나이 공통 요청 엔트리 함수
    prompt: str, # 제미나이한테 쏠 프롬프트
    api_key: str, # 제미나이 api 키
    model: str = "gemini-3.1-flash-lite", # 모델명
    temperature: float = 0.3, # 답변의 창의성 (0~2 사이; 2로 갈수록 더 창의적임)
    max_tokens: int = 1024, # 최대 답변 길이 (넘으면 내용이 끊김)
    system_instruction: str | None = None, # 시스템 프롬프트 (공통 프롬프트)
) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        },
    }
    if system_instruction:
        body["systemInstruction"] = {"parts": [{"text": system_instruction}]}

    request = urllib.request.Request( # 요청 데이터 생성
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request) as response: # 요청을 날리고
            result = json.loads(response.read().decode("utf-8")) # 응답 온거 읽고 파싱
    except urllib.error.HTTPError as e: # 오류 핸들링 (http 에러)
        raise RuntimeError(f"API 호출 실패 (HTTP {e.code}): {e.read().decode('utf-8')}")
    except urllib.error.URLError as e: # 오류 핸들링 (네트워크 에러)
        raise RuntimeError(f"네트워크 오류: {e.reason}")

    return result["candidates"][0]["content"]["parts"][0]["text"] # 답변 중 필요한 것만 정제해서 반환


def truncate(text: str, max_length: int) -> str: # 글자수가 특정 수를 초과하면 자른다
    if len(text) <= max_length:
        return text
    print(f"[WARN] 제목이 {max_length}자를 초과해 잘렸습니다.")
    return text[:max_length]


def fix_pr_sections(body: str) -> str: # pr 응답으로 받은 데이터가 지정된 형식이 아닌 경우, 재포맷팅하는 함수
    sections = {header: [] for header in PR_SECTIONS}
    current = None
    for line in body.splitlines():
        if line.strip() in PR_SECTIONS:
            current = line.strip()
        elif current:
            sections[current].append(line)

    fixed_lines = []
    for header in PR_SECTIONS:
        fixed_lines.append(header)
        content_lines = sections[header]
        while content_lines and not content_lines[-1].strip():
            content_lines.pop()
        if not any(line.strip().startswith("- ") for line in content_lines):
            print(f"[WARN] '{header}' 섹션에 불릿이 없어 자동으로 채웠습니다.")
            content_lines.append("- (내용 누락, 직접 작성 필요)")
        fixed_lines.extend(content_lines)
        fixed_lines.append("")

    return "\n".join(fixed_lines).strip()


def run_commit() -> None: # 관련 데이터를 받아와서 커밋 메시지를 생성해주는 함수
    status = get_git_status()
    if not status.strip():
        print("[INFO] 변경 사항이 없습니다. 커밋 메시지를 생성하지 않고 종료합니다.")
        return

    diff = get_git_diff() # 수정된 세부 내역
    changed_files = len(status.splitlines()) # 수정된 파일 개수
    diff_lines = len(diff.splitlines()) # 수정된 세부 내역의 총 줄 수

    print(f"[INFO] Git status 수집 완료: {changed_files}개 파일 변경 감지")
    print(f"[INFO] Git diff 수집 완료: {diff_lines}줄")

    api_key = os.environ.get("AI_API_KEY")
    if not api_key:
        print("[ERROR] AI_API_KEY 환경변수가 설정되지 않았습니다.")
        print('## 예) export AI_API_KEY="YOUR_KEY"')
        return

    user_prompt = f"[git status]\n{status}\n[git diff]\n{diff}" # 수정/추가/삭제된 현황과 수정된 세부 내역으로 유저 프롬프트를 생성함

    print("[INFO] AI API 요청 중...")
    try:
        message = call_gemini(user_prompt, api_key, system_instruction=COMMIT_SYSTEM_PROMPT)
    except RuntimeError as e:
        print(f"[ERROR] {e}")
        return

    title, _, commit_body = message.strip().partition("\n\n")
    title = truncate(title, COMMIT_TITLE_MAX_LENGTH)
    final_message = f"{title}\n\n{commit_body}".strip() if commit_body else title

    print("[DONE] 커밋 메시지 생성 완료")
    print()
    print("--- Commit Message ---")
    print(final_message)
    print("----------------------")


def run_pr() -> None: # pr 초안을 제미나이를 이용해 뽑아오자
    status = get_git_status()
    if not status.strip():
        print("[INFO] 변경 사항이 없습니다. PR을 생성하지 않고 종료합니다.")
        return

    diff = get_git_diff()
    branch = get_current_branch()

    api_key = os.environ.get("AI_API_KEY")
    if not api_key:
        print("[ERROR] AI_API_KEY 환경변수가 설정되지 않았습니다.")
        print('## 예) export AI_API_KEY="YOUR_KEY"')
        return

    print(f"[INFO] 현재 브랜치: {branch}")
    user_prompt = f"[브랜치] {branch}\n\n[git status]\n{status}\n[git diff]\n{diff}"

    print("[INFO] AI API 요청 중...")
    try:
        response = call_gemini(user_prompt, api_key, system_instruction=PR_SYSTEM_PROMPT)
    except RuntimeError as e:
        print(f"[ERROR] {e}")
        return

    title, _, pr_body = response.strip().partition("\n\n")
    title = truncate(title, PR_TITLE_MAX_LENGTH)
    pr_body = fix_pr_sections(pr_body)

    print("[DONE] PR 초안 생성 완료")
    print()
    print("--- PR Title ---")
    print(title)
    print()
    print("--- PR Body ---")
    print(pr_body)


def main() -> None:
    parser = argparse.ArgumentParser() # 인자를 받을 수 있게 관련 기능 활성화
    subparsers = parser.add_subparsers(dest="command", required=True) # 인자를 받을 수 있게 준비 (required가 True이므로 항상 필요로 함)
    subparsers.add_parser("commit") # commit 인자 받을 수 있게 허용
    subparsers.add_parser("pr") # pr 인자 받을 수 있게 허용
    args = parser.parse_args() # 실제 인자 파싱

    if args.command == "commit": # 들어온 인자가 커밋이면
        run_commit() # 커밋 함수 실행
    elif args.command == "pr": # 들어온 인자가 피알이면
        run_pr() # 피알 함수 실행


if __name__ == "__main__":
    main()
