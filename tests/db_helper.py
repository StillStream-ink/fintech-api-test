"""数据库直连辅助（支持 SQLite / MySQL）。

用于接口 + 数据库双检：接口返回成功 → 数据真的落库。

通过环境变量 DATABASE_URL 切换数据库：
- 默认：SQLite（instance/loan.db）
- MySQL：mysql+pymysql://root:pass@localhost:3306/fintech
"""
import os
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

# ==================== 引擎（单例） ====================

DEFAULT_SQLITE_PATH = Path(__file__).resolve().parent.parent / "instance" / "loan.db"

_engine: Engine | None = None


def _build_db_url() -> str:
    url = os.getenv("DATABASE_URL", "").strip()
    if url:
        return url

    # 兼容旧逻辑
    mock_path = os.getenv("MOCK_DB_PATH", "").strip()
    if mock_path:
        return f"sqlite:///{Path(mock_path).as_posix()}"

    return f"sqlite:///{DEFAULT_SQLITE_PATH.as_posix()}"


def get_engine() -> Engine:
    """获取数据库引擎（单例）。"""
    global _engine
    if _engine is None:
        url = _build_db_url()
        if not url.startswith("sqlite") and not DEFAULT_SQLITE_PATH.exists():
            # 非 SQLite 场景下，SQLite 文件不存在不是错误
            pass
        elif url.startswith("sqlite") and not DEFAULT_SQLITE_PATH.exists():
            raise FileNotFoundError(
                f"SQLite 数据库不存在: {DEFAULT_SQLITE_PATH}\n"
                f"请先启动 Mock 服务 (app.py)，或设置 MOCK_DB_PATH。"
            )

        connect_args = {}
        if url.startswith("sqlite"):
            connect_args = {"check_same_thread": False}

        _engine = create_engine(url, connect_args=connect_args, pool_pre_ping=True)

        # SQLite 启用 WAL 模式，减少锁竞争
        if url.startswith("sqlite"):
            with _engine.connect() as conn:
                conn.execute(text("PRAGMA journal_mode=WAL"))
                conn.execute(text("PRAGMA busy_timeout=5000"))
    return _engine


def reset_engine() -> None:
    """重置引擎（测试环境用）。"""
    global _engine
    if _engine is not None:
        _engine.dispose()
    _engine = None


# ==================== 查询接口 ====================

def get_customer(customer_id: int) -> dict | None:
    """按 ID 查客户，返回 dict 或 None。"""
    with get_engine().connect() as conn:
        row = conn.execute(
            text("SELECT id, name, age, income, credit_score FROM customer WHERE id = :id"),
            {"id": customer_id},
        ).mappings().first()
    return dict(row) if row else None


def get_loan(loan_id: int) -> dict | None:
    """按 ID 查贷款，返回 dict 或 None（含新增字段）。"""
    with get_engine().connect() as conn:
        row = conn.execute(
            text(
                "SELECT id, customer_id, amount, principal, interest_rate, "
                "paid_interest, status FROM loan WHERE id = :id"
            ),
            {"id": loan_id},
        ).mappings().first()
    return dict(row) if row else None


def count_customers() -> int:
    """客户表总行数。"""
    with get_engine().connect() as conn:
        return conn.execute(text("SELECT COUNT(*) FROM customer")).scalar() or 0


def count_loans() -> int:
    """贷款表总行数。"""
    with get_engine().connect() as conn:
        return conn.execute(text("SELECT COUNT(*) FROM loan")).scalar() or 0


def list_loans_by_customer(customer_id: int) -> list[dict]:  # pragma: no cover
    """查某客户的所有贷款。"""
    with get_engine().connect() as conn:
        rows = conn.execute(
            text("SELECT id, amount, status FROM loan WHERE customer_id = :cid"),
            {"cid": customer_id},
        ).mappings().all()
    return [dict(r) for r in rows]

