"""AI 辅助测试失败诊断。

读取 junit.xml 中的失败/错误用例，组装 prompt 调 LLM，
生成中文诊断报告（失败原因 + 修复建议 + 历史 BUG 关联）。

设计原则：
- 只在 CI 失败时运行（本地默认无 API Key 时优雅跳过）
- 只发送必要信息（失败用例名 + 断言错误 + 堆栈前 N 行）
- 支持任何 OpenAI 兼容接口（DeepSeek / 通义 / OpenAI / 本地 Ollama）

环境变量：
    LLM_API_KEY    API 密钥（必需，否则跳过）
    LLM_BASE_URL   API 基础地址，默认 https://api.deepseek.com
    LLM_MODEL      模型名，默认 deepseek-chat
"""
import json
import os
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

import requests

JUNIT_PATH = Path("test-results/junit.xml")
KNOWN_BUGS_PATH = Path("KNOWN_BUGS.md")
OUTPUT_PATH = Path("reports/ai_diagnosis.md")

LLM_API_KEY = os.getenv("LLM_API_KEY", "").strip()
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com").rstrip("/")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")

MAX_STACK_LINES = 15           # 每个失败用例最多发送的堆栈行数
MAX_FAILURES = 10              # 最多分析多少个失败用例


# ==================== 1. 解析 junit.xml ====================

def parse_failures() -> list[dict]:
    """从 junit.xml 提取失败/错误的用例。"""
    if not JUNIT_PATH.exists():
        return []

    tree = ET.parse(JUNIT_PATH)
    root = tree.getroot()

    failures = []
    for testcase in root.iter("testcase"):
        name = testcase.get("name", "")
        classname = testcase.get("classname", "")

        for tag in ("failure", "error"):
            node = testcase.find(tag)
            if node is None:
                continue

            message = (node.get("message") or "").strip()
            body = (node.text or "").strip()

            # 堆栈只保留前 N 行
            body_lines = body.splitlines()
            if len(body_lines) > MAX_STACK_LINES:
                body = "\n".join(body_lines[:MAX_STACK_LINES]) + "\n...(已截断)"

            failures.append({
                "name": name,
                "classname": classname,
                "type": tag,
                "message": message,
                "stack": body,
            })

            if len(failures) >= MAX_FAILURES:
                return failures

    return failures


# ==================== 2. 读取历史 BUG ====================

def load_known_bugs() -> str:
    """读取 KNOWN_BUGS.md 作为上下文。"""
    if not KNOWN_BUGS_PATH.exists():
        return ""
    text = KNOWN_BUGS_PATH.read_text(encoding="utf-8")
    # 太长会浪费 token，截前 3000 字符
    return text[:3000]


# ==================== 3. 组装 prompt ====================

SYSTEM_PROMPT = """你是一位资深自动化测试工程师，擅长快速定位测试失败根因。

你的任务：分析 pytest 失败日志，输出中文诊断报告。

要求：
1. 每个失败用例给出：失败原因（一句话）+ 根因分类（BUG/环境/用例问题）+ 修复建议
2. 如果失败信息匹配 KNOWN_BUGS.md 中的已知缺陷，明确关联
3. 输出格式为 Markdown，简洁专业，不要废话
4. 不要编造没看到的信息，不确定就标注"需要人工确认"
"""


def build_user_prompt(failures: list[dict], known_bugs: str) -> str:
    lines = []
    lines.append(f"本次 CI 共有 {len(failures)} 个失败/错误用例。\n")

    if known_bugs:
        lines.append("## 已知 BUG 清单（供关联参考）\n")
        lines.append(known_bugs)
        lines.append("\n---\n")

    lines.append("## 失败用例详情\n")
    for i, f in enumerate(failures, 1):
        lines.append(f"### 失败 {i}: {f['classname']}::{f['name']}")
        lines.append(f"类型: {f['type']}")
        lines.append(f"断言消息: {f['message']}")
        lines.append("堆栈:")
        lines.append("```")
        lines.append(f["stack"])
        lines.append("```")
        lines.append("")

    lines.append("\n请输出诊断报告。")
    return "\n".join(lines)


# ==================== 4. 调用 LLM ====================

def call_llm(system: str, user: str) -> str:
    url = f"{LLM_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.3,
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


# ==================== 5. 主流程 ====================

def write_output(content: str, failures: list[dict]) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    header = f"# AI 测试诊断报告\n\n> 模型：`{LLM_MODEL}` · 失败用例数：{len(failures)}\n\n---\n\n"
    OUTPUT_PATH.write_text(header + content, encoding="utf-8")
    print(f"\n诊断报告已保存：{OUTPUT_PATH}")


def main() -> int:
    # 没有 API Key 时优雅跳过（本地开发默认不启用）
    if not LLM_API_KEY:
        print("[SKIP] 未配置 LLM_API_KEY，跳过 AI 诊断。")
        return 0

    print(f"[1/4] 解析 junit.xml: {JUNIT_PATH}")
    failures = parse_failures()
    if not failures:
        print("[SKIP] 没有失败用例，无需诊断。")
        return 0
    print(f"      发现 {len(failures)} 个失败/错误用例")

    print(f"[2/4] 加载历史 BUG 清单")
    known_bugs = load_known_bugs()

    print(f"[3/4] 调用 LLM: {LLM_MODEL} @ {LLM_BASE_URL}")
    user_prompt = build_user_prompt(failures, known_bugs)

    try:
        diagnosis = call_llm(SYSTEM_PROMPT, user_prompt)
    except requests.HTTPError as e:
        print(f"[ERROR] LLM 调用失败: {e}")
        print(f"        响应: {e.response.text[:500] if e.response else 'N/A'}")
        return 1
    except requests.RequestException as e:
        print(f"[ERROR] 网络错误: {e}")
        return 1

    print(f"[4/4] 写入报告")
    write_output(diagnosis, failures)

    # 同时打印到控制台，方便 CI 日志查看
    print("\n" + "=" * 60)
    print(diagnosis)
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())