"""YAML 数据加载器（DDT 辅助）。

用于从 data/ 目录读取 YAML 测试数据，供 pytest 参数化使用。
"""
from pathlib import Path

import yaml

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_yaml(filename: str) -> list:
    """加载 data/ 目录下的 YAML 文件，返回 list[dict]。"""
    path = DATA_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"YAML 数据文件不存在: {path}")  # pragma: no cover

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, list):
        raise ValueError(f"YAML 文件顶层必须是 list 结构: {path}")  # pragma: no cover
    return data


def case_id(case: dict) -> str:
    """参数化 test id：优先取 case_id 字段。"""
    return case.get("case_id", "unknown")
