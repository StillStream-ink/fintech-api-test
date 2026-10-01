import os
import multiprocessing
import time
from pathlib import Path

import pytest
import requests

# ==============================================================================
# 1. 并发隔离配置（必须在导入 app 之前执行）
# ==============================================================================
# 获取 pytest-xdist worker 标识，非并发运行时为 "master"
WORKER_ID = os.environ.get("PYTEST_XDIST_WORKER", "master")

# 统一的 instance 目录（与 app.py 的默认回退路径一致）
INSTANCE_DIR = Path(__file__).resolve().parent / "instance"
INSTANCE_DIR.mkdir(exist_ok=True)

if "gw" in WORKER_ID:
    # 并发模式：gw0 -> 端口 5001, gw1 -> 端口 5002，DB 也按 worker 隔离
    worker_num = int(WORKER_ID.replace("gw", ""))
    PORT = 5000 + worker_num + 1
    DB_FILE = f"loan_{WORKER_ID}.db"
else:
    # 串行模式：端口 5000，DB 为 loan.db
    PORT = 5000
    DB_FILE = "loan.db"

# 关键：设置为绝对路径，让 app.py 和 db_helper.py 指向同一个文件
os.environ["MOCK_DB_PATH"] = str(INSTANCE_DIR / DB_FILE)

# 让子进程（Flask 服务）也上报覆盖率
_COVERAGERC = Path(__file__).resolve().parent / ".coveragerc"
if _COVERAGERC.exists():
    os.environ["COVERAGE_PROCESS_START"] = str(_COVERAGERC)

# 必须在设置完环境变量后，再导入 app 和 CreditAPI
from credit_api import CreditAPI
from app import app, db

BASE_URL = f"http://127.0.0.1:{PORT}"


# ==============================================================================
# 2. 服务自动拉起
# ==============================================================================
def _is_server_ready() -> bool:
    """检查 Mock 服务是否已在运行。"""
    try:
        requests.get(f"{BASE_URL}/api/v1/view-loan/0", timeout=0.5)
        return True
    except requests.ConnectionError:
        return False


def _run_server():
    """在子进程中运行 Flask 服务（含覆盖率上报）。"""
    # 让子进程也参与覆盖率统计
    if os.getenv("COVERAGE_PROCESS_START"):
        import coverage
        coverage.process_startup()

    with app.app_context():
        db.drop_all()
        db.create_all()
    # use_reloader=False 至关重要，否则 debug 模式会启动两个进程
    app.run(host="127.0.0.1", port=PORT, debug=False, use_reloader=False)


@pytest.fixture(scope="session", autouse=True)
def mock_server():
    """自动启动 Mock 服务，如果已启动则复用。"""
    if _is_server_ready():
        print(f"\n[Mock] 检测到端口 {PORT} 已有服务，直接复用。")
        yield
        return

    print(f"\n[Mock] 正在启动 Mock 服务 (端口 {PORT}, DB: {DB_FILE})...")
    p = multiprocessing.Process(target=_run_server, daemon=True)
    p.start()

    # 等待服务就绪（最多 10 秒）
    for _ in range(100):
        if _is_server_ready():
            print("[Mock] 服务启动成功。")
            break
        time.sleep(0.1)
    else:
        p.terminate()
        p.join()
        raise RuntimeError(f"Mock 服务启动失败 (端口 {PORT})，请检查 app.py 是否报错。")

    yield

    print(f"\n[Mock] 正在关闭 Mock 服务 (端口 {PORT})...")
    p.terminate()
    p.join(timeout=5)


# ==============================================================================
# 3. 测试 Fixtures
# ==============================================================================
@pytest.fixture(scope="function")
def api_client():
    """API客户端，每个用例全新 session。"""
    return CreditAPI(base_url=BASE_URL)


@pytest.fixture(scope="function", autouse=True)
def reset_database(api_client):
    """每条用例自动重置数据库。"""
    resp = api_client.reset_db()
    assert resp.status_code == 200, f"数据库重置失败: {resp.text}"


@pytest.fixture(scope="function")
def sample_customer(api_client):
    """通过注册接口生成测试用户。"""
    resp = api_client.register({
        "name": "测试用户",
        "age": 25,
        "income": 8000,
        "credit_score": 700,
    })
    assert resp.status_code == 201, f"注册失败: {resp.text}"
    return resp.json()["customer_id"]


@pytest.fixture(scope="function")
def sample_loan(api_client, sample_customer):
    """通过创建贷款接口生成测试贷款。"""
    resp = api_client.create_loan({
        "customer_id": sample_customer,
        "amount": 50000,
    })
    assert resp.status_code == 201, f"创建贷款失败: {resp.text}"
    return resp.json()["loan_id"]