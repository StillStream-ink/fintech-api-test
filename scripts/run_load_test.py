"""Locust 梯度压测脚本（Python 版）。

用法：
    1. 终端 A：py app.py            （保持不关）
    2. 终端 B：py scripts\\run_load_test.py
"""
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import requests

# ==================== 可配置项 ====================
HOST = "http://127.0.0.1:5000"
LOCUSTFILE = "locustfile.py"
RESULT_DIR = Path("reports/perf")
DURATION = "60s"                # 每档时长
SPAWN_RATE = 10                 # 每秒启动用户数
GRADIENTS = [10, 30, 60, 100]   # ← 并发梯度，按需修改


def check_service() -> None:
    """检查 Mock 服务是否在线。"""
    print("[准备] 检查 Mock 服务...")
    try:
        requests.get(f"{HOST}/api/v1/view-loan/0", timeout=2)
        print("  [OK] Mock 服务在线")
    except requests.ConnectionError:
        print("  [FAIL] Mock 服务未启动，请先运行：py app.py")
        sys.exit(1)


def run_one(users: int, timestamp: str) -> None:
    """跑单档并发。"""
    print(f"\n===== 并发 {users} 用户，运行 {DURATION} =====")
    prefix = RESULT_DIR / f"{timestamp}_{users}u"

    cmd = [
        sys.executable, "-m", "locust",
        "-f", LOCUSTFILE,
        "--headless",
        "--host", HOST,
        "-u", str(users),
        "-r", str(SPAWN_RATE),
        "-t", DURATION,
        "--csv", str(prefix),
        "--html", f"{prefix}.html",
        "--only-summary",
    ]
    print(f"  $ {' '.join(cmd)}")

    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        print(f"  [FAIL] 退出码 {result.returncode}")
        sys.exit(result.returncode)
    print(f"  [OK] 完成：{prefix}.csv")


def main():
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    check_service()

    for users in GRADIENTS:
        run_one(users, timestamp)

    print("\n===== 全部梯度完成 =====")
    print(f"结果目录：{RESULT_DIR}")
    for f in sorted(RESULT_DIR.glob(f"{timestamp}_*.csv")):
        print(f"  {f.name}  ({f.stat().st_size} bytes)")

    print("\n下一步：py scripts\\summarize_perf.py")


if __name__ == "__main__":
    main()