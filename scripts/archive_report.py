"""报告自动归档。

用法：
    py scripts/archive_report.py

行为：
- 把 allure-report/ + test-results/junit.xml 复制到 reports/YYYYMMDD_HHMMSS/
- 保留最近 10 份，超出的自动删除
"""
import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path


def parse_args():
    p = argparse.ArgumentParser(description="报告自动归档")
    p.add_argument("--keep", type=int, default=10)
    p.add_argument("--src-report", default="allure-report")
    p.add_argument("--src-junit", default="test-results/junit.xml")
    p.add_argument("--dst", default="reports")
    return p.parse_args()


def main():
    args = parse_args()
    src_report = Path(args.src_report)
    src_junit = Path(args.src_junit)
    dst_root = Path(args.dst)

    if not src_report.exists() and not src_junit.exists():
        print("[ERROR] 没有可归档的产物")
        return 1

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst_dir = dst_root / timestamp
    dst_dir.mkdir(parents=True, exist_ok=True)

    if src_report.exists():
        shutil.copytree(src_report, dst_dir / "allure-report", dirs_exist_ok=True)
        print(f"[OK] Allure 报告 -> {dst_dir / 'allure-report'}")

    if src_junit.exists():
        shutil.copy2(src_junit, dst_dir / "junit.xml")
        print(f"[OK] JUnit XML  -> {dst_dir / 'junit.xml'}")

    # 保留最近 N 份
    all_archives = sorted([d for d in dst_root.iterdir() if d.is_dir()], key=lambda d: d.name)
    if len(all_archives) > args.keep:
        for old in all_archives[: len(all_archives) - args.keep]:
            shutil.rmtree(old)
            print(f"[DEL] 清理旧归档: {old.name}")

    print(f"\n归档完成：{dst_dir}")
    print(f"当前归档总数：{len(list(dst_root.iterdir()))} 份")
    return 0


if __name__ == "__main__":
    sys.exit(main())
