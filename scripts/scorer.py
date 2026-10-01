import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


def parse_args():
    p = argparse.ArgumentParser(description="信贷测试评分系统")
    p.add_argument("--results-dir", default="allure-results")
    p.add_argument("--output", default="reports/test_scores.txt")
    return p.parse_args()


def _is_xfail(result_data: dict) -> bool:
    """判断一条 Allure 结果是否为 xfail。"""
    if result_data.get("status") != "skipped":
        return False
    details = result_data.get("statusDetails", {}) or {}
    message = (details.get("message") or "").lower()
    # allure-pytest 对 xfail 的标记
    return "xfail" in message or "expected test failure" in message


def collect_stats(results_dir: Path) -> dict:
    stats = {"passed": 0, "failed": 0, "broken": 0, "skipped": 0, "xfail": 0, "unknown": 0}
    files = list(results_dir.glob("*-result.json"))
    if not files:
        print(f"[ERROR] {results_dir} 里没有 *-result.json")
        sys.exit(2)

    key_to_latest = {}
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            stats["unknown"] += 1
            continue
        key = data.get("historyId") or data.get("fullName") or data.get("uuid") or f.name
        start = data.get("start", 0) or 0
        if key not in key_to_latest or start > (key_to_latest[key].get("start", 0) or 0):
            key_to_latest[key] = data

    for r in key_to_latest.values():
        status = r.get("status", "unknown")
        if status == "skipped":
            if _is_xfail(r):
                stats["xfail"] += 1
            else:
                stats["skipped"] += 1
        elif status in stats:
            stats[status] += 1
        else:
            stats["unknown"] += 1
    return stats


def score(stats: dict) -> tuple:
    effective = stats["passed"] + stats["failed"] + stats["broken"]
    total = effective + stats["skipped"] + stats["xfail"] + stats["unknown"]

    # 1. 通过率（满分 15）
    pass_rate = stats["passed"] / effective if effective else 0
    score_pass = round(pass_rate * 15, 2)

    # 2. 用例规模（满分 3）
    score_size = round(min(total / 100, 1.0) * 3, 2)

    # 3. xfail 覆盖（满分 2）—— 真正统计 xfail，而不是 skipped
    score_xfail = round(min(stats["xfail"] / 20, 1.0) * 2, 2)

    total_score = round(score_pass + score_size + score_xfail, 2)
    return {
        "通过率": (score_pass, 15),
        "用例规模": (score_size, 3),
        "xfail 覆盖": (score_xfail, 2),
    }, total_score


def main():
    args = parse_args()
    stats = collect_stats(Path(args.results_dir))
    details, total = score(stats)

    effective = stats["passed"] + stats["failed"] + stats["broken"]
    all_count = sum(stats.values())
    pass_rate = stats["passed"] / effective * 100 if effective else 0

    lines = []
    lines.append("=" * 60)
    lines.append("  信贷测试评分报告")
    lines.append(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"  {'维度':<12} {'得分':>6} / {'满分':<4}   说明")
    lines.append(f"  {'-' * 50}")
    lines.append(f"  {'通过率':<12} {details['通过率'][0]:>6} / {details['通过率'][1]:<4}   {pass_rate:.2f}%")
    lines.append(f"  {'用例规模':<12} {details['用例规模'][0]:>6} / {details['用例规模'][1]:<4}   {all_count} 用例")
    lines.append(f"  {'xfail 覆盖':<12} {details['xfail 覆盖'][0]:>6} / {details['xfail 覆盖'][1]:<4}   {stats['xfail']} 个（发现 bug）")
    lines.append(f"  {'-' * 50}")
    lines.append(f"  {'总分':<12} {total:>6} / 20")
    lines.append("")
    lines.append("  评级：")
    if total >= 18:
        lines.append("      优秀（可交付）")
    elif total >= 15:
        lines.append("        良好")
    elif total >= 12:
        lines.append("          及格")
    else:
        lines.append("            需改进")
    lines.append("")
    lines.append("  统计明细：")
    lines.append(f"     passed:   {stats['passed']}")
    lines.append(f"     failed:   {stats['failed']}")
    lines.append(f"     broken:   {stats['broken']}")
    lines.append(f"     xfail:    {stats['xfail']}  (预期失败，发现 bug)")
    lines.append(f"     skipped:  {stats['skipped']}  (主动跳过)")
    lines.append(f"     unknown:  {stats['unknown']}")
    lines.append("=" * 60)

    text = "\n".join(lines)
    print(text)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"\n评分结果已保存到：{out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())