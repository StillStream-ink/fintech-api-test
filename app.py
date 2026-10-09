import os
import logging
from pathlib import Path
from sqlalchemy import func
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

# 配置基础日志，保证logging.exception可以输出堆栈
logging.basicConfig(level=logging.INFO)

# 子进程启动时同步启动覆盖率统计（如果环境变量存在）
if os.getenv("COVERAGE_PROCESS_START"):
    import coverage
    coverage.process_startup()
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError
app = Flask(__name__)

# 全局异常捕获，防止内部异常详情泄露给前端
@app.errorhandler(Exception)
def handle_exception(e):
    logging.exception("Unhandled exception occurred")
    return jsonify({"error": "internal error"}), 500

# ==============================================================================
# 数据库配置
# 优先读 DATABASE_URL（MySQL / 其他数据库）
# 未设置时回退到 SQLite（本地开发 / 单元测试）
# ==============================================================================
def _build_db_uri() -> str:
    # 1. 显式传入完整 URL
    url = os.getenv("DATABASE_URL", "").strip()
    if url:
        return url
    # 2. 兼容旧逻辑：MOCK_DB_PATH 指定 SQLite 文件路径
    db_path = Path(os.getenv("MOCK_DB_PATH", "instance/loan.db")).resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{db_path.as_posix()}"
app.config['SQLALCHEMY_DATABASE_URI'] = _build_db_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
app.url_map.strict_slashes = False
# ==============================================================================
# 数据模型
# ==============================================================================
class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    income = db.Column(db.Integer, nullable=False)
    credit_score = db.Column(db.Integer, nullable=False)
class Loan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    principal = db.Column(db.Integer, nullable=False, default=0)
    interest_rate = db.Column(db.Float, nullable=False, default=0.0)
    paid_interest = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(20), default="PENDING", nullable=False)
class RepaymentFlow(db.Model):
    """还款流水（每次还款写一条）。"""
    id = db.Column(db.Integer, primary_key=True)
    loan_id = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Integer, nullable=False)              # 本次还款金额
    principal_part = db.Column(db.Integer, nullable=False)      # 其中本金部分
    interest_part = db.Column(db.Integer, nullable=False)
        # 其中利息部分
# ==============================================================================
# 贷款状态机
# ==============================================================================
LOAN_STATE_TRANSITIONS = {
    "PENDING": {"APPROVED", "REJECTED"},
    "APPROVED": {"DISBURSED"},
    "DISBURSED": {"SETTLED"},
    "REJECTED": set(),
    "SETTLED": set(),
}
def _can_transition(from_state, to_state):
    return to_state in LOAN_STATE_TRANSITIONS.get(from_state, set())
# ==============================================================================
# 通用校验函数
# ==============================================================================
def _require_json():
    # 1. 标准解析（需要 Content-Type: application/json）
    data = request.get_json(silent=True)
    if data is not None:
        return data, None
    # 2. 兜底：手动解析 raw body（兼容 JMeter 等不发 Content‑Type 的客户端）
    import json as _json
    raw = request.get_data(as_text=True)
    if raw:
        try:
            data = _json.loads(raw)
            return data, None
        except _json.JSONDecodeError:
            pass
    return None, (jsonify({"error": "请求体必须为合法 JSON"}), 400)
def _require_fields(data, fields):
    missing = [f for f in fields if f not in data]
    if missing:
        return jsonify({"error": "缺少必填字段", "missing": missing}), 400
    return None
def _require_int(data, field, min_val=None, max_val=None):
    val = data[field]
    if isinstance(val, bool) or not isinstance(val, int):
        return jsonify({"error": f"{field} 必须为整数"}), 400
    if min_val is not None and val < min_val:
        return jsonify({"error": f"{field} 不能小于 {min_val}"}), 400
    if max_val is not None and val > max_val:
        return jsonify({"error": f"{field} 不能大于 {max_val}"}), 400
    return None
def _require_str(data, field, min_len=1, max_len=32):
    val = data[field]
    if not isinstance(val, str):
        return jsonify({"error": f"{field} 必须为字符串"}), 400
    if len(val) < min_len:
        return jsonify({"error": f"{field} 不能为空"}), 400
    if len(val) > max_len:
        return jsonify({"error": f"{field} 长度不能超过 {max_len}"}), 400
    return None
# ==============================================================================
# 接口：注册
# ==============================================================================
@app.route('/api/v1/register', methods=['POST'])
def register():
    data, err = _require_json()
    if err:
        return err
    err = _require_fields(data, ["name", "age", "income", "credit_score"])
    if err:
        return err
    err = _require_str(data, "name", min_len=1, max_len=32)
    if err:
        return err
    err = _require_int(data, "age", min_val=0, max_val=150)
    if err:
        return err
    err = _require_int(data, "income", min_val=0, max_val=100_000_000)
    if err:
        return err
    err = _require_int(data, "credit_score", min_val=0, max_val=1000)
    if err:
        return err
    try:
        cust = Customer(
            name=data["name"],
            age=data["age"],
            income=data["income"],
            credit_score=data["credit_score"],
        )
        db.session.add(cust)
        db.session.commit()
        return jsonify({"customer_id": cust.id}), 201
    except SQLAlchemyError as e:
        db.session.rollback()
        logging.exception("register db error")
        return jsonify({"error": "数据库操作失败"}), 500
# ==============================================================================
# 接口：资格预审
# ==============================================================================
@app.route('/api/v1/check-eligibility', methods=['POST'])
def check_eligibility():
    data, err = _require_json()
    if err:
        return err
    err = _require_fields(data, ["age", "income", "credit_score"])
    if err:
        return err
    err = _require_int(data, "age", min_val=0, max_val=150)
    if err:
        return err
    err = _require_int(data, "income", min_val=0, max_val=100_000_000)
    if err:
        return err
    err = _require_int(data, "credit_score", min_val=0, max_val=1000)
    if err:
        return err
    age, income, credit_score = data["age"], data["income"], data["credit_score"]
    if age < 18 or age > 60:
        return jsonify({"eligible": False, "reason": "年龄不符合要求"}), 200
    if income < 3000:
        return jsonify({"eligible": False, "reason": "收入不足"}), 200
    if credit_score < 600:
        return jsonify({"eligible": False, "reason": "信用评分不足"}), 200
    return jsonify({"eligible": True, "max_amount": 100000}), 200
# ==============================================================================
# 接口：创建贷款
# ==============================================================================
# 业务规则常量
MIN_CREDIT_SCORE = 600
MIN_INCOME = 5000
MAX_LOAN_RATIO = 0.8          # 单笔 ≤ 资质的 80%
MAX_MONTHLY_LOANS = 5          # 月借款次数上限
# 利率规则：按信用分区间
INTEREST_RATES = [
    (800, 0.02),   # 800+ -> 2%
    (700, 0.035),  # 700‑799 -> 3.5%
    (600, 0.05),   # 600‑699 -> 5%
]
def _calc_interest_rate(credit_score: int) -> float:
    """按信用分算利率。"""
    for threshold, rate in INTEREST_RATES:
        if credit_score >= threshold:
            return rate
    return 0.08  # 兜底
@app.route('/api/v1/loan', methods=['POST'])
def create_loan():
    data, err = _require_json()
    if err:
        return err
    err = _require_fields(data, ["customer_id", "amount"])
    if err:
        return err
    err = _require_int(data, "customer_id", min_val=1)
    if err:
        return err
    err = _require_int(data, "amount", min_val=1, max_val=10_000_000)
    if err:
        return err
    cust = db.session.get(Customer, data["customer_id"])
    if not cust:
        return jsonify({"error": "客户不存在"}), 404
    # ==================== 业务规则校验 ====================
    # 规则 1：信用分门槛
    if cust.credit_score < MIN_CREDIT_SCORE:
        return jsonify({
            "error": "信用评分不足",
            "reason": f"信用分 {cust.credit_score} < {MIN_CREDIT_SCORE}",
        }), 403
    # 规则 2：收入门槛
    if cust.income < MIN_INCOME:
        return jsonify({
            "error": "收入不足",
            "reason": f"月收入 {cust.income} < {MIN_INCOME}",
        }), 403
    # 规则 3：未结清贷款数量限制
    active_count = db.session.query(func.count(Loan.id)).filter(
        Loan.customer_id == cust.id,
        Loan.status.in_(["PENDING", "APPROVED", "DISBURSED"]),
    ).scalar() or 0
    if active_count >= MAX_MONTHLY_LOANS:
        return jsonify({
            "error": "未结清贷款已达上限",
            "reason": f"已有 {active_count} 笔未结清",
        }), 429
    # ==================== 创建贷款 ====================
    principal = data["amount"]
    rate = _calc_interest_rate(cust.credit_score)
    # ========== 修复浮点精度问题：Decimal金融计算，传统四舍五入ROUND_HALF_UP ==========
    interest = int(
        (Decimal(str(principal)) * Decimal(str(rate))).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    )
    total_amount = principal + interest
    try:
        loan = Loan(
            customer_id=data["customer_id"],
            amount=total_amount,
            principal=principal,
            interest_rate=rate,
            paid_interest=0,
            status="PENDING",
        )
        db.session.add(loan)
        db.session.commit()
        return jsonify({
            "loan_id": loan.id,
            "status": loan.status,
            "principal": principal,
            "interest_rate": rate,
            "total_amount": total_amount,
        }), 201
    except SQLAlchemyError as e:
        db.session.rollback()
        logging.exception("create_loan db error")
        return jsonify({"error": "数据库操作失败"}), 500
# ==============================================================================
# 接口：查询贷款
# ==============================================================================
@app.route('/api/v1/view-loan/<int:loan_id>', methods=['GET'])
def view_loan(loan_id):
    loan = db.session.get(Loan, loan_id)
    if not loan:
        return jsonify({"error": "贷款不存在"}), 404
    return jsonify({
        "loan_id": loan.id,
        "customer_id": loan.customer_id,
        "amount": loan.amount,
        "principal": loan.principal,
        "interest_rate": loan.interest_rate,
        "paid_interest": loan.paid_interest,
        "status": loan.status,
    }), 200
# ==============================================================================
# 状态流转通用函数
# ==============================================================================
def _transition_loan(loan_id, target_status):
    loan = db.session.get(Loan, loan_id)
    if not loan:
        return jsonify({"error": "贷款不存在"}), 404
    from_status = loan.status
    if not _can_transition(from_status, target_status):
        return jsonify({
            "error": f"非法状态流转：{from_status} → {target_status}",
            "current_status": from_status,
            "target_status": target_status,
        }), 409
    loan.status = target_status
    try:
        db.session.commit()
        return jsonify({
            "loan_id": loan.id,
            "from_status": from_status,
            "status": loan.status,
        }), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        logging.exception(f"transition loan {loan_id} db error")
        return jsonify({"error": "数据库操作失败"}), 500
@app.route('/api/v1/loan/<int:loan_id>/approve', methods=['POST'])
def approve_loan(loan_id):
    return _transition_loan(loan_id, "APPROVED")
@app.route('/api/v1/loan/<int:loan_id>/reject', methods=['POST'])
def reject_loan(loan_id):
    return _transition_loan(loan_id, "REJECTED")
@app.route('/api/v1/loan/<int:loan_id>/disburse', methods=['POST'])
def disburse_loan(loan_id):
    return _transition_loan(loan_id, "DISBURSED")
@app.route('/api/v1/loan/<int:loan_id>/repay', methods=['POST'])
def repay_loan(loan_id):
    """还款：状态流转 + 写流水。"""
    loan = db.session.get(Loan, loan_id)
    if not loan:
        return jsonify({"error": "贷款不存在"}), 404
    from_status = loan.status
    if not _can_transition(from_status, "SETTLED"):
        return jsonify({
            "error": f"非法状态流转：{from_status} → SETTLED",
            "current_status": from_status,
            "target_status": "SETTLED",
        }), 409
    # 还款拆分：amount、principal都是数据库int，减法安全无浮点
    interest_part = loan.amount - loan.principal
    principal_part = loan.principal
    try:
        loan.status = "SETTLED"
        loan.paid_interest = interest_part
        # 写还款流水
        flow = RepaymentFlow(
            loan_id=loan.id,
            amount=loan.amount,
            principal_part=principal_part,
            interest_part=interest_part,
        )
        db.session.add(flow)
        db.session.commit()
        return jsonify({
            "loan_id": loan.id,
            "from_status": from_status,
            "status": loan.status,
            "repaid_amount": loan.amount,
            "principal_part": principal_part,
            "interest_part": interest_part,
        }), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        logging.exception(f"repay loan {loan_id} db error")
        return jsonify({"error": "数据库操作失败"}), 500
# ==============================================================================
# 接口：重置数据库（仅测试用）
# ==============================================================================
@app.route('/api/v1/_reset_db', methods=['POST'])
def reset_db():
    try:
        db.drop_all()
        db.create_all()
        return jsonify({"msg": "db reset success"}), 200
    except SQLAlchemyError as e:
        logging.exception("reset db error")
        return jsonify({"error": "数据库操作失败"}), 500
# ==============================================================================
# 启动入口
# ==============================================================================
if __name__ == '__main__':
    with app.app_context():
        db.drop_all()
        db.create_all()
    debug_mode = os.getenv("FLASK_DEBUG", "1") == "1"
    # use_reloader=False 防止 debug 模式启动双进程抢端口
    app.run(host="127.0.0.1", port=5000, debug=debug_mode, use_reloader=False)