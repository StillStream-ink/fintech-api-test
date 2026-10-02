"""一次性脚本：删除 test_boundary.py 中的旧边界用例。

删除后请手动删除本脚本文件。
"""
from pathlib import Path

PATH = Path('tests/test_boundary.py')
METHODS = [
    'test_eligibility_age_boundary',
    'test_eligibility_income_boundary',
    'test_eligibility_credit_score_boundary',
]


def find_range(lines, method_name):
    """返回 (起始行号, 结束行号)，均为 0-based，end 不包含。"""
    def_idx = None
    for i, line in enumerate(lines):
        if f'def {method_name}(' in line:
            def_idx = i
            break
    if def_idx is None:
        return None

    # 向上找装饰器
    start = def_idx
    while start > 0:
        line = lines[start - 1]
        stripped = line.strip()
        if not stripped:
            break
        indent = len(line) - len(line.lstrip())
        if indent >= 8:
            start -= 1
        elif indent == 4 and stripped.startswith('@'):
            start -= 1
        else:
            break

    # 向下找方法结束
    def_indent = len(lines[def_idx]) - len(lines[def_idx].lstrip())
    end = def_idx + 1
    while end < len(lines):
        line = lines[end]
        if not line.strip():
            end += 1
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.lstrip()
        if indent <= def_indent and (
            stripped.startswith('def ')
            or stripped.startswith('@')
            or stripped.startswith('class ')
        ):
            break
        end += 1

    # 回退尾部空行
    while end > def_idx and not lines[end - 1].strip():
        end -= 1

    return start, end


def main():
    lines = PATH.read_text(encoding='utf-8').splitlines(keepends=True)

    ranges = []
    for m in METHODS:
        r = find_range(lines, m)
        if r:
            ranges.append((m, r[0], r[1]))
        else:
            print(f'  [未找到] {m}')

    if not ranges:
        print('没有可删除的方法，文件未修改。')
        return

    print('将删除以下代码块：')
    for m, s, e in ranges:
        print(f'  {m}: 行 {s + 1} ~ {e}（共 {e - s} 行）')

    # 从后往前删除，避免行号错位
    for m, s, e in sorted(ranges, key=lambda x: -x[1]):
        del lines[s:e]

    PATH.write_text(''.join(lines), encoding='utf-8')
    print(f'\n✅ 已删除 {len(ranges)} 个方法。')
    print('请检查文件，并手动删除本脚本 (del_old_boundary.py)。')


if __name__ == '__main__':
    main()