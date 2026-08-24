import json
import os
import subprocess
import urllib.error
import urllib.request


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


def call_gemini( # 제미나이 공통 요청 엔트리 함수
    prompt: str, # 제미나이한테 쏠 프롬프트
    api_key: str, # 제미나이 api 키
    model: str = "gemini-3.1-flash-lite", # 모델명
    temperature: float = 0.3, # 답변의 창의성 (0~2 사이; 2로 갈수록 더 창의적임)
    max_tokens: int = 1024, # 최대 답변 길이 (넘으면 내용이 끊김)
) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        },
    }

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


def main() -> None:
    status = get_git_status()
    if not status.strip():
        print("[INFO] 변경 사항이 없습니다. 커밋 메시지를 생성하지 않고 종료합니다.")
        return

    diff = get_git_diff()
    changed_files = len(status.splitlines()) # 여러 라인으로 넘어온 데이터를 쪼개서 일차원 리스트로 저장한다
    diff_lines = len(diff.splitlines())

    print(f"[INFO] Git status 수집 완료: {changed_files}개 파일 변경 감지")
    print(f"[INFO] Git diff 수집 완료: {diff_lines}줄")

    api_key = os.environ.get("AI_API_KEY") # api 키를 환경변수로 불러오고
    if not api_key: # 없으면 안내 띄우고 종료
        print("[ERROR] AI_API_KEY 환경변수가 설정되지 않았습니다.")
        print('## 예) export AI_API_KEY="YOUR_KEY"')
        return

    print("[INFO] AI API 요청 중...")
    try:
        summary = call_gemini(f"다음 git diff를 한 문장으로 요약해줘:\n\n{diff}", api_key)
    except RuntimeError as e:
        print(f"[ERROR] {e}")
        return

    print("[DONE] 응답:", summary) # 응답 온거 출력


if __name__ == "__main__":
    main()
