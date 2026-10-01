import argparse
import json
import sys
from pathlib import Path


class ResultsNotFound(Exception):
    pass


def parse_args():
    p = argparse.ArgumentParser(description="信贷测试质量门禁")
    p.add_argument("--threshold", type=float, default=90.0)
    p.add_argument("--results-dir", default="allure-results")
    p.add_argument("--no-dedup", action="store_true")
    return p.parse_args()


def collect_stats(results_dir: Path, dedup: bool = True) -> dict:
    stats = {"passed": 0, "failed": 0, "broken": 0, "skipped": 0, "unknown": 0}

    if not results_dir.exists():
        raise ResultsNotFound(f"结果目录不存在: {results_dir}")

    files = list(results_dir.glob("*-result.json"))
    if not files:
        raise ResultsNotFound(f"目录里没有 *-result.json: {results_dir}")

    records = []
    parse_failed = 0
    for f in files:
        try:
            records.append((f.name, json.loads(f.read_text(encoding="utf-8"))))
        except Exception:
            stats["unknown"] += 1
            parse_failed += 1

    total_raw = len(records)

    if dedup:
        key_to_latest = {}
        for file_name, r in records:
            key = r.get("historyId") or r.get("fullName") or r.get("uuid") or file_name
            start = r.get("start", 0) or 0
            if key not in key_to_latest or start > (key_to_latest[key].get("start", 0) or 0):
                key_to_latest[key] = r
        records = [(k, v) for k, v in key_to_latest.items()]

    for _, r in records:
        status = r.get("status", "unknown")
        if status in stats:
            stats[status] += 1
        else:
            stats["unknown"] += 1

    stats["_total_raw"] = total_raw + parse_failed
    stats["_total_dedup"] = len(records)
    stats["_parse_failed"] = parse_failed
    return stats


def main():
    args = parse_args()

    if not 0 <= args.threshold <= 100:
        print("[ERROR] threshold 必须在 0-100")
        return 2

    try:
        stats = collect_stats(Path(args.results_dir), dedup=not args.no_dedup)
    except ResultsNotFound as e:
        print(f"[ERROR] {e}")
        return 2

    effective = stats["passed"] + stats["failed"] + stats["broken"]

    if effective == 0:
        print("[ERROR] 有效用例数为 0")
        print(f"统计: {stats}")
        return 2

    pass_rate = stats["passed"] / effective * 100

    print("=" * 60)
    print("  信贷测试质量门禁")
    print("=" * 60)
    if not args.no_dedup:
        print(f"  原始文件数:    {stats['_total_raw']}   (去重后 {stats['_total_dedup']})")
    print(f"  有效用例:      {effective}  (不含 skipped)")
    print(f"   passed:     {stats['passed']}")
    print(f"   failed:     {stats['failed']}")
    print(f"   broken:     {stats['broken']}")
    print(f"  非阻塞:        skipped={stats['skipped']}  unknown={stats['unknown']}")
    print(f"  JSON 解析失败: {stats['_parse_failed']}")
    print("-" * 60)
    print(f"  通过率:        {pass_rate:.2f}%")
    print(f"  阈值:          {args.threshold}%")
    print("=" * 60)

    if pass_rate >= args.threshold:
        print("  [PASS] 质量门禁通过")
        return 0
    else:
        print(f"  [FAIL] 质量门禁未通过（差 {args.threshold - pass_rate:.2f}%）")
        return 1


if __name__ == "__main__":
    sys.exit(main())