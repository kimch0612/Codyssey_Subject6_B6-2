import json
import os
import urllib.error
import urllib.request


def load_env(path: str = ".env") -> None:
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key.strip(), value)


def main() -> None:
    load_env()

    api_key = os.environ.get("AI_API_KEY")
    if not api_key:
        print('[ERROR] AI_API_KEY 환경변수가 설정되지 않았습니다.')
        print('## 예) export AI_API_KEY="YOUR_KEY"')
        return

    model = "gemini-3.1-flash-lite"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {
        "contents": [
            {"parts": [{"text": "연결 테스트야. 한 문장으로만 답해줘."}]}
        ]
    }

    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"[ERROR] API 호출 실패 (HTTP {e.code}): {e.read().decode('utf-8')}")
        return
    except urllib.error.URLError as e:
        print(f"[ERROR] 네트워크 오류: {e.reason}")
        return

    try:
        text = result["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        print("[ERROR] 응답에서 텍스트를 찾지 못했습니다. 원본 응답:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print("[DONE] 응답:", text)


if __name__ == "__main__":
    main()
