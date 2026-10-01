"""SQLite 数据库直连辅助。

用于接口 + 数据库双检：接口返回成功 → 数据真的落库。

设计要点：
- 数据库文件不存在时直接报错，而不是静默创建空库
- 启用 WAL + busy_timeout，避免 Flask 与测试并发访问时 database is locked
- 支持 MOCK_DB_PATH 环境变量覆盖默认路径，避免与 app.py 路径漂移
"""
import os
import sqlite3
from pathlib import Path


DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "instance" / "loan.db"
DB_PATH = Path(os.getenv("MOCK_DB_PATH", str(DEFAULT_DB_PATH)))


def _connect():
    """建立 SQLite 连接。

    如果数据库文件不存在，直接抛 FileNotFoundError，
    避免 sqlite3.connect 静默创建空库导致后续 "no such table" 的混乱报错。
    """
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"数据库不存在: {DB_PATH}\n"
            f"请先启动 Mock 服务 (app.py)，或检查 instance 目录。\n"
            f"如需自定义路径，设置环境变量 MOCK_DB_PATH。"
        )

    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    # WAL 模式：允许读写并发，避免 Flask 与测试互锁
    conn.execute("PRAGMA journal_mode=WAL")
    # busy_timeout：遇到锁时最多等 5 秒再报错，而不是立刻失败
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def get_customer(customer_id):
    """按 ID 查客户，返回 dict 或 None。"""
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT id, name, age, income, credit_score FROM customer WHERE id = ?",
            (customer_id,),
        ).fetchone()
    finally:
        conn.close()
    return dict(row) if row else None


def get_loan(loan_id):
    """按 ID 查贷款，返回 dict 或 None。"""
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT id, customer_id, amount, status FROM loan WHERE id = ?",
            (loan_id,),
        ).fetchone()
    finally:
        conn.close()
    return dict(row) if row else None


def count_customers():
    """客户表总行数。"""
    conn = _connect()
    try:
        return conn.execute("SELECT COUNT(*) FROM customer").fetchone()[0]
    finally:
        conn.close()


def count_loans():
    """贷款表总行数。"""
    conn = _connect()
    try:
        return conn.execute("SELECT COUNT(*) FROM loan").fetchone()[0]
    finally:
        conn.close()


def list_loans_by_customer(customer_id):
    """查某客户的所有贷款。"""
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT id, amount, status FROM loan WHERE customer_id = ?",
            (customer_id,),
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]