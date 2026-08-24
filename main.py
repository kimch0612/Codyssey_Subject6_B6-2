import subprocess # 파이썬에서 콘솔 명령어를 호출할 때 사용함


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


if __name__ == "__main__":
    main()
