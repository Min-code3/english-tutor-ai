#!/usr/bin/env python3
"""
questions.json 저장 감지 → 자동으로 GitHub push → Vercel 자동 배포
실행: python3 watch-questions.py
종료: Ctrl+C
"""

import time
import os
import subprocess
from datetime import datetime

WATCH_FILE = "/Users/jsm/english-tutor/public/questions.json"
REPO_DIR   = "/Users/jsm/english-tutor"
INTERVAL   = 2  # 초마다 변경 확인


def push():
    print(f"\n📝 변경 감지! ({datetime.now().strftime('%H:%M:%S')})")
    print("🚀 GitHub 업로드 중...")

    subprocess.run(["git", "add", "public/questions.json"], cwd=REPO_DIR)

    commit = subprocess.run(
        ["git", "commit", "-m", f"update: questions {datetime.now().strftime('%Y-%m-%d %H:%M')}"],
        cwd=REPO_DIR, capture_output=True, text=True
    )

    if "nothing to commit" in commit.stdout + commit.stderr:
        print("ℹ️  변경사항 없음 (이미 최신)")
        return

    push_result = subprocess.run(
        ["git", "push", "origin", "main"],
        cwd=REPO_DIR, capture_output=True, text=True
    )

    if push_result.returncode == 0:
        print("✅ 완료! Vercel이 자동 배포 시작했어요 (약 30초)")
    else:
        print(f"⚠️  Push 실패:\n{push_result.stderr}")


def main():
    print("=" * 45)
    print("  👀 questions.json 자동 배포 감시 중")
    print("  파일 저장하면 자동으로 GitHub에 올라가요")
    print("  종료하려면 Ctrl+C")
    print("=" * 45)

    last_mtime = os.path.getmtime(WATCH_FILE)

    while True:
        try:
            mtime = os.path.getmtime(WATCH_FILE)
            if mtime != last_mtime:
                push()
                last_mtime = mtime
            time.sleep(INTERVAL)

        except KeyboardInterrupt:
            print("\n\n👋 감시 종료")
            break
        except Exception as e:
            print(f"⚠️ 오류: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
