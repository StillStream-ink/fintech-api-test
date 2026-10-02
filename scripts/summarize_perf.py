"""Locust 压测结果汇总。

读取 reports/perf/*_stats.csv（Locust 每个梯度产出的文件），
按并发数排序，输出对比表格 + Markdown 文件。

用法：
    py scripts/summarize_perf.py
    py scripts/summarize_perf.py --timestamp 20261002_133054
"""
import argparse
import csv
import re
from datetime import datetime
from pathlib import Path

PERF_DIR = Path(__file__).resolve().parent.parent / "reports" / "perf"
OUTPUT_MD = PERF_DIR / "summary.md"


# ==================== 工具函数 ====================

def to_float(val, default: float = 0.0) -> float:
    """把 CSV 里的字符串转成 float，处理 N/A / 空 / 数字 三种情况。"""
    if val is None:
        return default
    s = str(val).strip()
    if not s or s.upper() in ("N/A", "NA", "NAN", "-"):
        return default
    try:
        return float(s)
    except ValueError:
        return default


def parse_args():
    p = argparse.ArgumentParser(description="Locust 压测结果汇总")
    p.add_argument("--timestamp", help="只汇总指定时间戳的结果，如 20261002_133054")
    return p.parse_args()


def extract_users(csv_path: Path) -> int:
    """从文件名 xxx_100u_stats.csv 里提取并发数 100。"""
    m = re.search(r"_(\d+)u_stats\.csv$", csv_path.name)
    return int(m.group(1)) if m else 0


def read_aggregated_row(csv_path: Path):
    """读取 *_stats.csv 中 Aggregated 那一行。

    Locust 在 Windows 上按系统编码（GBK）写 CSV，
    这里做编码回退：先试 utf-8，失败再试 gbk / utf-8-sig。
    """
    for encoding in ("utf-8", "gbk", "utf-8-sig"):
        try:
            with csv_path.open("r", encoding=encoding, newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("Name") == "Aggregated":
                        return row
            return None
        except UnicodeDecodeError:
            continue
    return None


# ==================== 数据收集 ====================

def collect(timestamp=None):
    pattern = f"{timestamp}_*_stats.csv" if timestamp else "*_stats.csv"
    files = sorted(PERF_DIR.glob(pattern))

    # 排除 *_stats_history.csv（按秒的明细，不是汇总）
    files = [f for f in files if not f.name.endswith("_stats_history.csv")]

    results = []
    for f in files:
        users = extract_users(f)
        if users == 0:
            continue
        row = read_aggregated_row(f)
        if not row:
            continue

        results.append({
            "users": users,
            "requests": int(to_float(row.get("Request Count"))),
            "failures": int(to_float(row.get("Failure Count"))),
            "median": to_float(row.get("Median Response Time")),
            "avg": to_float(row.get("Average Response Time")),
            "p95": to_float(row.get("95%")),
            "p99": to_float(row.get("99%")),
            "rps": to_float(row.get("Requests/s")),
            "file": f.name,
        })

    results.sort(key=lambda r: r["users"])
    return results


# ==================== 渲染 ====================

def calc_failure_rate(r):
    if r["requests"] == 0:
        return 0.0
    return r["failures"] / r["requests"] * 100


def render_markdown(results):
    lines = []
    lines.append("# Locust 梯度压测结果")
    lines.append("")
    lines.append(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    if not results:
        lines.append("_没有找到压测结果文件_")
        return "\n".join(lines)

    lines.append("## 梯度对比")
    lines.append("")
    lines.append("| 并发 | 总请求 | 失败数 | 失败率 | 平均响应 | P95 | P99 | RPS |")
    lines.append("|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in results:
        lines.append(
            f"| {r['users']} "
            f"| {r['requests']} "
            f"| {r['failures']} "
            f"| {calc_failure_rate(r):.2f}% "
            f"| {r['avg']:.1f} ms "
            f"| {r['p95']:.0f} ms "
            f"| {r['p99']:.0f} ms "
            f"| {r['rps']:.1f} |"
        )
    lines.append("")

    # 拐点分析
    lines.append("## 拐点分析")
    lines.append("")
    rps_values = [(r["users"], r["rps"]) for r in results]
    p95_values = [(r["users"], r["p95"]) for r in results]

    if len(rps_values) >= 2:
        best_rps = max(rps_values, key=lambda x: x[1])
        lines.append(f"- **RPS 最高**：{best_rps[0]} 并发，{best_rps[1]:.1f} req/s")

    if len(p95_values) >= 2:
        baseline_p95 = p95_values[0][1]
        for users, p95 in p95_values[1:]:
            if baseline_p95 > 0 and p95 > baseline_p95 * 2:
                lines.append(
                    f"- **P95 明显上升**：{users} 并发时达 {p95:.0f} ms"
                    f"（首档 {baseline_p95:.0f} ms），可能是性能拐点"
                )
                break

    lines.append("")
    lines.append("## 原始文件")
    lines.append("")
    for r in results:
        lines.append(f"- `{r['file']}`")
    return "\n".join(lines)


# ==================== 主流程 ====================

def main():
    args = parse_args()
    results = collect(args.timestamp)

    md = render_markdown(results)
    print(md)

    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.write_text(md, encoding="utf-8")
    print(f"\n汇总已保存：{OUTPUT_MD}")


if __name__ == "__main__":
    main()